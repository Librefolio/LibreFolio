# Review visiva 22/09/2026 — giro pulito in produzione

> **Come è stata prodotta.** Il developer ha ricreato il server di produzione da zero
> (`db create-clean`), si è registrato come nuovo utente, ha seguito l'onboarding, ha
> importato le transazioni reali via wizard e ha percorso dashboard, grafici P&L,
> strumenti e pagine di rischio. È la **prima prova d'uso end-to-end** dopo la catena di
> merge dei sette workstream su `e4a46e9e0`.
>
> **Cosa aggiunge questo foglio ai suoi appunti.** Ogni voce è stata verificata contro il
> codice: dove la causa è stata trovata, è citata con `file:riga`; dove **non** è stata
> trovata, è detto esplicitamente, perché un owner che parte dal file sbagliato perde un
> giro. Tre voci che sembravano difetti **non lo sono** e sono isolate in §3.

| | |
|---|---|
| **Data review** | 22/09/2026, sessione prod porta 6040, utente `alfy` |
| **Revisione codice** | `e4a46e9e0`, build frontend delle 13:10 (fresco) |
| **Voci raccolte** | 20 — 14 difetti, 3 non-difetti, 3 richieste evolutive |
| **Verificate nel codice** | 6 con causa esatta · 4 con superficie · 9 da riprodurre |
| **Secondo passaggio** | 16:23 — 5 sospetti chiusi, 1 difetto nuovo, 3 decisioni di perimetro (§8) |

---

## 1 · Quadro sinottico

Severità: 🔴 blocca o falsa un dato · 🟠 rompe un flusso · 🟡 attrito · 💡 evoluzione.

| # | Area | Voce | Sev | Owner proposto | Causa |
|---|---|---|---|---|---|
| R1 | i18n / risk | `lastedDays` MALFORMED_ARGUMENT ×11 | 🔴 | **A** | ✅ **esatta** |
| R2 | Versione | Versione corrente sbagliata nell'update check | 🔴 | **coordinator** | ✅ **esatta** |
| R3 | Versione | Modale nuova versione sotto quella corrente (z-index) | 🟠 | **J** | ⚠️ superficie |
| R4 | Versione | Nessun banner "sei aggiornato" a schermo | 🟠 | **J** | ⚠️ superficie |
| R5 | Privacy | Asse Y in **Abs** mostra valori assoluti | 🔴 | **J** + **I** | ✅ P4-11 |
| R6 | Privacy | Asse Y in **P&L** stesso problema | 🔴 | **J** + **I** | ✅ P4-11 |
| R7 | Privacy | Infobox mostra valori assoluti | 🔴 | **J** | ⚠️ superficie |
| R8 | Grafici | Candele: più bucket nello stesso mese | 🟠 | **I** | ❓ riprodurre |
| R9 | Grafici | Frase sotto le candele: sintetizzare + scroll CSS | 🟡 | **I** | ✅ superficie |
| R10 | Grafici | Income: barre troppo sottili | 🟠 | **I** | ❓ riprodurre |
| R11 | Grafici | Income: manca il valore di acquisto nello stack | 🟠 | **I** | 📐 progetto |
| R12 | Allocazione | Torta a 1 livello, non 2 come concordato | 🟠 | **Risk** | ❓ riprodurre |
| R13 | Select | "CSV" non trova "Generic CSV" | 🟠 | **K** | 🔴 **non è optionFilter** |
| R14 | Select | Tipo **asset**: evolvere a `SearchSelect` | 💡 | **K** | ✅ superficie |
| R15 | Select | Tipo **asset**: 2 livelli come pannello segnali | 🟠 | **K** | 📐 progetto |
| R16 | Select | ETF: manca la seconda icona sovrapposta | 🟠 | **K** (era Risk) | 📐 nei piani risk |
| R17 | Tipologie | Aggiungere crowdfunding immobiliare | 💡 | **K** | 📐 progetto |
| R18 | Import | Doppia modale ISIN (race condition) | 🔴 | **K** | ⚠️ superficie |
| R19 | Onboarding | Testo "l'import ha una sua guida" da togliere | 🟡 | **J** | ✅ superficie |
| R20 | Privacy | Broker global: si nascondono ma non si riscoprono | 🔴 | **J** | ⚠️ superficie |
| R21 | Dashboard | Crescita e Allocazione non ricordano la vista scelta | 🟡 | **I** | ✅ **pattern esistente** |

**Non difetti** (§3): PAC senza UI · privacy che "nasconde la valuta" · benchmark MSCI World.

---

## 2 · Dettaglio con evidenza

### R1 🔴 `lastedDays` — causa esatta, correzione di un carattere

**Osservato.** Aprendo Strumenti, 11 volte in console:
```
[svelte-i18n] Message "risk.assetSet.levels.l1.lastedDays" has syntax error: MALFORMED_ARGUMENT
  at AssetSetLossComparisonSection.svelte:163
```

**Causa.** La chiave esiste in tutti e quattro i cataloghi, ma usa la sintassi sbagliata:

| file | riga | contenuto |
|---|---|---|
| `frontend/src/lib/i18n/en.json` | 3093 | `"lastedDays": "lasted {{days}} d"` |
| `frontend/src/lib/i18n/it.json` | 3093 | `"lastedDays": "durata {{days}} g"` |
| `frontend/src/lib/i18n/fr.json` | 3093 | `"lastedDays": "durée {{days}} j"` |
| `frontend/src/lib/i18n/es.json` | 3093 | `"lastedDays": "duró {{days}} d"` |

`svelte-i18n` parla **ICU MessageFormat**, che vuole la graffa singola `{days}`. La doppia
`{{days}}` è sintassi **i18next/Mustache**: ICU apre l'argomento sulla prima `{`, trova una
`{` dove si aspetta un nome, e alza `MALFORMED_ARGUMENT`.

**Estensione misurata.** È **isolata**: `grep -c "{{"` su ciascun catalogo restituisce `1`,
ed è questa riga. Nessun'altra chiave del progetto usa la doppia graffa.

> ⚠️ **Il reperto che conta più della correzione.** `./dev.py i18n audit` dà questa chiave
> per **completa** — c'è in tutte e quattro le lingue. L'audit misura *presenza e
> completezza*, **non validità ICU**. Quindi il registro i18n è verde su una chiave che a
> runtime non rende nulla. Vale la pena chiedersi se l'audit debba imparare a parsare.

**Owner: A.** `AssetSetLossComparisonSection.svelte` è la sezione di confronto che A ha
inserito fra le due di F (heatmap e replay). Se in revisione risulta di F, passa a F: la
correzione è la stessa riga.

---

### R2 🔴 Versione corrente sbagliata — causa esatta, azione immediata

**Osservato.** Console, due volte (anche dopo logout/login, quindi non è cache di sessione):
```
[UpdateCheck] release check {current: 'v1.0.1-97-g98efa725-dirty', latest: '1.1.0', …}
[UpdateCheck] prompting for release {version: '1.1.0', tag: 'v1.1.0', …}
```
La versione reale è `v1.1.0-224-ge4a46e9e0`, cioè **224 commit oltre** la 1.1.0.

**Causa.** Alla root del repo esiste un file `VERSION`:

```
cat VERSION                   → v1.0.1-97-g98efa725-dirty     ← stringa congelata
git describe --tags --dirty   → v1.1.0-224-ge4a46e9e0         ← la realtà
```

`get_git_version()` **preferisce il file `VERSION` a `git describe`** — deliberatamente,
perché l'immagine Docker non ha `.git/` e dentro al container `git describe` non può girare
(`dev.py:1547-1549`).

Il file viene rigenerato **solo** durante la preparazione dell'immagine Docker, e quel
codice è già corretto: sa del rischio e lo previene cancellando prima di ricalcolare.

```python
# dev.py:1551-1562 — "Remove any stale VERSION file from a previous build first,
# so this recomputes a true fresh value instead of just re-reading what's already there."
version_file.unlink(missing_ok=True)
get_git_version.cache_clear()
version = get_git_version()
version_file.write_text(version)
```

**Il punto è dove quel codice gira.** Solo nel build Docker. In sviluppo non gira mai, e il
file resta lì con la precedenza. Il `-dirty` in coda dice che fu generato da un albero
sporco: è un residuo di un tuo vecchio `docker build`.

**Stato git verificato.** `VERSION` è **ignorato** (`.gitignore:62`) e **non è in HEAD**.
Quindi è un artefatto **locale alla tua macchina**: nessun altro utente ha questo problema,
e nessuna release lo eredita.

**Si è già propagato a un secondo artefatto.** Una ricerca della stringa su tutto il repo
la trova anche qui:

```
frontend/src/lib/api/openapi.json:5:  "version": "v1.0.1-97-g98efa725-dirty"
```

`./dev.py api sync` avvia un server temporaneo per esportare lo schema; quel server ha letto
`VERSION`, e la stringa stantia è finita nello schema. Non è la fonte del sintomo — a runtime
il frontend interroga `GET /api/v1/system/info`, che rilegge il backend — ma dice **da quanto**
il file è fermo: è sopravvissuto almeno a un `api sync`. Anche `openapi.json` è ignorato
(`frontend/.gitignore:12-13`), quindi anche questa copia è locale. Dopo `rm VERSION`, il
prossimo `api sync` la riallinea da sé.

> ✅ **Azione immediata**: `rm VERSION` e il tuo server mostra la versione vera al riavvio.
>
> 📐 **Difetto di design che resta**: chiunque faccia `docker build` una volta si porta
> dietro quella versione **per sempre** in sviluppo, silenziosamente, perché il file ha la
> precedenza ed è ignorato da git — quindi non compare mai in `git status` a ricordartelo.
> Vale una decisione: rigenerare a ogni `server`, o leggere il file solo in assenza di `.git/`.

**⚠️ Nota di metodo, a mio carico.** Ho scritto nel primo passaggio che `VERSION` era
*tracciato*, e non lo è. Avevo usato `git ls-files VERSION && echo "TRACCIATO"`, ma
`git ls-files` esce **0 anche quando non trova nulla**: ho letto una conferma dall'exit code
di un comando che non usa l'exit code per segnalare presenza. È la stessa forma
dell'omonimia trovata stamattina — un comando che risponde "sì" per una ragione diversa da
quella che credevo. Corretto con `git cat-file -p HEAD:VERSION` e `git check-ignore -v`.

---

### R3 🟠 · R4 🟠 Modali update — ~~z-index e banner assente~~ → **rinvio applicato a un'azione richiesta** *(J, 23/09)*

> ⚠️ **Non è z-index**, per quanto dice il codice (lettura di J, owner di `DeferredAppPopups`):
>
> ```
> admin      ChangelogModal:242 → updateAvailable.show() → DeferredAppPopups:41   modalDepth > 0 → RINVIATA
> non-admin  ChangelogModal:325 → <AskAdminModal> annidata                        → SUBITO
> stato 'newer'   nessuna resa inline
> ```
>
> Il componente ha fatto il suo lavoro — rinviare i popup mentre un'altra modale è aperta —
> ma su un controllo **chiesto dall'utente**, dove il rinvio è sbagliato: per questo la
> modale è comparsa solo alla chiusura. E con R2 attiva la versione era `v1.0.1-97-…`,
> quindi l'esito era `update-available`: **nessun «sei aggiornato» era dovuto**. R4 va
> **ri-verificata** con R2 riparata (il server ora riporta `v1.1.0-228-gf1047f766`, cioè lo
> stato `newer`, che oggi non ha resa inline). Discriminante nel DOM:
> `deferred-app-popups[data-active-popup]` col changelog aperto.

**Osservato.** Cliccando "verifica aggiornamenti" non compare **nessun banner** a schermo,
benché la console mostri `probeStatus: 'success'`. La modale "nuova versione disponibile"
esiste ma si apre **sotto** quella corrente: il developer l'ha vista solo chiudendo la prima.

**Da verificare in riparazione.** Le due voci probabilmente hanno la stessa radice: la
modale si monta ma finisce dietro. Il banner "sei aggiornato" potrebbe essere anch'esso
renderizzato e invisibile, non assente.

> 📌 R3 e R4 vanno riparate **dopo R2**: con la versione corretta il flusso cambia — non
> ci sarà più una "nuova versione" da annunciare, e il caso da mostrare diventa proprio
> quello del banner mancante. Ripararle prima significa collaudarle sullo scenario sbagliato.

---

### R5 🔴 · R6 🔴 · R7 🔴 Privacy — l'asse Y e l'infobox

**Osservato.** L'occhio funziona sulle label: restano percentuali e grafiche, come
richiesto. Ma sul grafico della crescita del portafoglio, **in modalità Abs** l'asse Y
mostra ancora i valori assoluti, e lo stesso vale per l'infobox. In `%` va bene. In **P&L**
il problema ritorna.

**Superficie.** `frontend/src/lib/components/dashboard/GrowthChart.svelte`
- `:1815` `yAxisFormatter` — ternario che distingue `pct`, da cui il `%` corretto
- `:1834` `fmtCurrency`
- `:2051` `axisLabel.formatter` — il canale che sfugge

**Principio deciso dal developer, da applicare qui**: *«il patrimonio entra in gioco quando
da quel numero si risale a quanto possiede l'utente»*. Un asse Y in valuta assoluta è
esattamente questo. Un asse in percentuale **no** — e infatti va già bene.

> 📌 **Il confine da rispettare**: la maschera copre **il numero, non la valuta**
> (`currencyFormat.ts:41-47` avvolge solo l'importo; simbolo, bandiera e codice sono
> aggiunti dopo). Sotto privacy l'output corretto è `••• € 🇪🇺 EUR`, non `•••`.
> Chi ripara l'asse deve mantenere questo comportamento, non reinventarlo.

**Owner: J** possiede il canale privacy; **I** possiede il grafico. Da coordinare: la
correzione tocca un file di I con una regola di J.

---

### R8 🟠 Candele — più bucket nello stesso mese

**Osservato.** Le candele si muovono secondo le aspettative e le linee orizzontali ora si
notano, permettendo di discriminare i bucket. Ma compaiono **casi in cui più bucket cadono
nello stesso mese**.

📷 `…/attachments/559272fc-f850-4bc2-9c36-fb169fd78692-92ff4458-d493-43f3-a0f5-7600980b5b89-clipboard.png`

**Non riprodotto staticamente.** Serve il dataset del developer: dipende dalla soglia di
aggregazione e dalla distribuzione reale delle transazioni importate. **Owner: I**, che ha
il modello dei bucket.

---

### R9 🟡 Frase sotto le candele

**Osservato.** La frase è **corretta nel contenuto**. Richieste: (a) sintetizzarla,
(b) aggiungere la proprietà CSS che la fa **scorrere** se non entra nello schermo — più per
mobile che desktop.

📷 stesso screenshot di R8.

---

### R10 🟠 · R11 🟠 Income — larghezza barre e composizione dello stack

**Osservato.** *«Il lavoro di base è ottimo»*, e piace la distinzione nuovo capitale /
reinvestito. Due problemi:

**R10 — barre troppo sottili.** Non sfruttano la larghezza disponibile, specie con bucket
larghi. Zoomando appena si ricalcolano e si vedono: quindi la larghezza è calcolata, ma con
un riferimento sbagliato al primo render.

📷 `…/attachments/aa813611-0654-4713-901c-c054590325be-80de0cde-d769-49c4-ae5f-7ba1cb667f55-clipboard.png`

**R11 — manca il valore di acquisto.** Nelle barre non c'è la voce *«quanti soldi sono stati
spesi per acquistare asset»*. L'aspettativa dichiarata: **il reinvestito deve colorare la
parte alta di quella barra**, non essere una serie impilata a sé.

📷 tooltip attuale (Dividendo / Interesse / Costi e tasse / Deposito / Nuovo capitale /
Reinvestito): `…/attachments/6f707866-cd32-40e8-a756-1f490b39ae21-bad9c3a2-58ba-4aa9-a63f-30738872467a-clipboard.png`

> 📐 R11 è una **decisione di modello**, non un bug: cambia cosa la barra rappresenta.
> Va progettata con te prima di implementarla.

---

### R12 🟠 Torta allocazione — un livello invece di due

**Osservato.** Un ETF salvato come **ETF azionario** viene mostrato **a parte**, non dentro
la torta a due livelli concordata con Risk.

📷 `…/attachments/45c752d3-bcdb-4f81-b90c-ab2517b4584f-5b83de79-7b2d-4812-a8af-45ba68fb737d-clipboard.png`
(ETF / Crowdfunding / Obbligazioni, tutti allo stesso livello)

**Owner: Risk**, che possiede la tassonomia a due livelli e il suo disegno.

> **Esito (24/09, tempo ② di Risk col developer)**: la prima torta a due anelli **non ha passato la
> review**. Da fuori sembrava un anello solo, l'icona del membro copriva la fascia esterna e il
> tooltip cambiava a seconda della fascia. Su due mockup costruiti coi suoi numeri, il developer ha
> scelto **B, per veicolo**: «ETF» è la famiglia dell'anello interno, i sottotipi stanno
> sull'anello esterno (*«la proposta B è quello che mi aspettavo»*). ~~per contenuto: `ETF_STOCK`
> sotto «Azione»~~. Nel modello il principio non cambia: il sottotipo dice che cosa contiene.
> Cambia il raggruppamento della torta, con un modulo nuovo di Risk (`charts/allocationFamily.ts`).
> Registrato da Risk in `04` (D72) e `REGISTRO` (R2-158). Conseguenze: Allocazione storica (I)
> raggruppa ancora per contenuto; per `CROWDFUND_REAL_ESTATE` il veicolo verrà dalla famiglia
> esposta da K.

---

### R13 🟠 "CSV" non trova "Generic CSV" — **la causa NON è dove sembra**

**Osservato.** Creando il broker Recrowd: scrivendo `generic` l'opzione compare subito;
scrivendo `CSV` **no**. Ipotesi del developer: il filtro è passato da `contains` a
`startsWith`.

🔴 **Ipotesi falsificata per esecuzione.** Il filtro reale è
`frontend/src/lib/components/ui/select/optionFilter.ts:15-17`, ed è un `includes` su tre
campi:

```js
option.value.toLowerCase().includes(query)
|| option.label.toLowerCase().includes(query)
|| (!!option.searchText && option.searchText.toLowerCase().includes(query))
|| iconMatches(option.icon, rawQuery)
```

Ho eseguito quella funzione — copiata verbatim, tipi strippati — sulle opzioni **come
`ImportPluginSelect.svelte:62-70` le costruisce davvero** (`value: 'broker_generic_csv'`,
`label: 'Generic CSV'`, `searchText:` la descrizione del provider):

| query | risultato |
|---|---|
| `generic` | `[Generic CSV]` ✅ |
| `CSV` | `[Generic CSV]` ✅ |
| `csv` | `[Generic CSV]` ✅ |
| `sv` | `[Generic CSV]` ✅ |

Il filtro trova `CSV`, maiuscolo e parziale. Il componente in gioco è
`BrokerForm.svelte:238` → `ImportPluginSelect` → `SearchSelect` con `inlineSearch={true}`.

> ⚠️ **Il difetto è reale — l'hai visto — ma non è nel filtro.** Chi lo prende deve partire
> dalla riproduzione, non da `optionFilter.ts`, o perde il giro. Piste: lo stato di
> `searchQuery` in modalità `inlineSearch`, un reset dell'input, oppure il caso in cui la
> riga c'è ma la lista non scrolla fino a lei — che a schermo è indistinguibile da "non
> trova". Questa terza pista spiegherebbe perché `generic` (primo match in cima) funziona
> e `CSV` no.

> ✅ **Riprodotto da K il 23/09 — era la terza pista, e la mia misura era il difetto.** Ho
> eseguito il filtro su **una** opzione; K l'ha eseguito sulle **30 reali**, nell'ordine del
> backend: `CSV` ne trova 30, perché **29 descrizioni su 30 contengono «CSV»**. «Generic CSV»
> è la **16ª**, se ne vedono circa 6, ed è evidenziata Avanza. Il filtro abbina bene: è
> l'**ordinamento** che perde, perché un match sul nome vale quanto uno sulla descrizione.
> Cura proposta da K: prima i match sul nome, poi quelli sulla descrizione, dentro le
> sezioni. `optionFilter.ts` è condiviso da tutti i `SearchSelect`: in questo round ne è
> **unico scrittore K**. È il campione scelto dal fenomeno di 09 §3.6, commesso da chi l'ha
> scritto.

---

### R14 💡 · R15 🟠 · R16 🟠 · R17 💡 Select del tipo transazione

✅ **Il primo livello è come concordato.** Quattro richieste sopra:

- **R14** — evolvere il select a `SearchSelect.svelte` (ora che le opzioni sono molte)
- **R15** — la lista è **tutta a un livello**: serve la struttura a **due livelli**, come il
  selettore degli indici nel pannello segnali (che è il modello da copiare)
- **R16** — i tipi di ETF mostrano **solo l'icona ETF**: manca la **seconda icona piccola,
  leggermente sovrapposta** alla principale. Il "come" è già dettagliato nei piani di Risk
- **R17** — aggiungere **crowdfunding immobiliare** fra le tipologie composite

> 📌 R14, R15 e R16 toccano lo stesso componente e lo stesso render di opzione: vanno a **un
> solo owner, in un solo passaggio**. Separarle significa riscrivere due volte lo stesso file.

✅ **Nota positiva registrata**: Borsa Italiana rileva correttamente il titolo di stato come
tipo di transazione.

---

### R18 🔴 Doppia modale ISIN nell'import wizard

**Osservato.** Aggiungendo il BTP Più: prima compare la modale «ISIN del report ≠ ISIN del
provider» — **corretta**. Un secondo dopo le si apre **sopra** la modale «confronto dati
provider», che chiede **la stessa cosa**.

**Causa ipotizzata dal developer** (plausibile): il campo si pre-popola, e nel tempo in cui
il provider risponde le due richieste corrono in parallelo.

**Comportamento desiderato, dichiarato:**
> Se la modale di conferma è aperta, il confronto dati **resta carico ma in attesa**; in base
> alla risposta della prima si **toglie la riga che chiede la stessa cosa**; e **se non resta
> nulla, la seconda modale si annulla**.

📐 È una regola di **sequenziamento**, non un fix di z-index: la seconda modale deve
conoscere l'esito della prima prima di decidere se esistere.

---

### R19 🟡 Onboarding — un testo di troppo

✅ **«La guida di benvenuto è perfetta.»** Unica correzione: in Transazioni c'è un messaggio
che dice che l'import ha una sua guida — **da togliere come testo**.

**Owner: J**, che possiede l'onboarding.

---

## 3 · Ciò che **non** è un difetto

Tre cose sono state notate come sospette e non lo sono. Valgono quanto i difetti: evitano
una riparazione che romperebbe un comportamento voluto.

### 3.1 Il PAC senza interfaccia — stato modellato, non regressione

**Osservato.** Strumenti mostra *«Interfacce non disponibili in questa build: 1»*, un toast
di warning, e sotto l'Allocatore PAC: *«Backend/API 2.0.0 · UI 2.0.0 — lo strumento backend
è installato, ma la sua interfaccia non è inclusa in questa build frontend. Nessun calcolo è
stato avviato.»*

**Non è un guasto.** `frontend/src/lib/features/tools/registry.ts:240-250` lo dichiara:

> *«No compiled renderers. The P1 UIs for `pac_allocator` and `portfolio_rebalancer` were
> removed on 2026-09-21 together with their backend services. The backend now exposes
> `pac_allocator` with `operation="plan"` (planner v2), which has no UI yet. **This is a
> modelled state, not a gap**: `resolveToolRenderer` returns the `renderer_missing`
> unavailable code, which `presentation.ts` maps to `tools.availability.rendererMissing` —
> translated in all four locales and explicit that no calculation was started.»*

Il messaggio che hai letto è **il comportamento progettato**: lo strumento resta in catalogo
e si spiega da solo finché la UI v2 non esiste.

> 🔴 **Ma è il reperto più importante della tua review, e la domanda è per te.**
> D ha consegnato il planner v2 **backend-only**. La feature-faro del round, aperta
> dall'interfaccia, dice di non avere interfaccia. Due cose da decidere:
>
> 1. **La UI del PAC v2 è pianificata in questo round?** Se sì, manca un workstream
>    frontend che oggi non esiste. Se no, va detto, perché tu te la aspettavi funzionante.
> 2. Uno stato **atteso e voluto** produce un **toast di warning**. Un avviso per una
>    condizione normale addestra a ignorare gli avvisi: questo sì merita una correzione.

### 3.2 La privacy non nasconde la valuta — ~~già corretto~~ → 🔴 **falso in due siti** *(23/09)*

> 🔴 **Vero solo per `currencyFormat.ts`.** Due siti aggirano le primitive D8 e restituiscono
> `•••` al posto dell'intera stringa, valuta compresa: `riskAnalysisHelpers.ts:160` (livelli
> di rischio L1 e L4, Asset Global) e `LotComparisonChart.svelte:261` (analisi lotti). È
> esattamente ciò che il tuo principio chiama errore, ed è **protetto da un verde**: sette
> asserzioni in `riskAnalysisHelpers.test.ts` fissano il `•••` nudo. → **J** (09 §9.8).
> Il paragrafo sotto è il ragionamento giusto applicato al pezzo che non decide.

Il tuo principio (*«il privacy deve nascondere il numero, non la valuta»*) **è già il
comportamento del codice**. `currencyFormat.ts:41-47`: la maschera avvolge **solo**
l'importo; simbolo, bandiera e codice valuta sono concatenati **dopo**, fuori. Output sotto
privacy: `••• € 🇪🇺 EUR`.

⚠️ Avevo riportato il contrario in una nota precedente, sulla fiducia di un'affermazione che
non avevo eseguito. Corretto leggendo il formatter.

### 3.3 Benchmark MSCI World

✅ Editato come benchmark, salvato, riaperto: persiste. Nessuna azione.

---

## 4 · Stato delle pagine di rischio

**Osservato.** Dashboard → Rischio e Asset Global → Rischio: *«l'estetica e i numeri devono
essere ricontrollati sicuramente, ma grosso modo mi pare che le cose ci siano e funzionino
con le giuste traduzioni.»*

📌 Registrato come **impressione, non come verdetto**: non genera task finché non c'è un
numero specifico contestato. Le voci concrete emerse da quelle pagine sono R1 e R12.

---

## 5 · Screenshot — percorsi completi

Utilizzabili da qualunque agente di questo progetto.

| # | Contenuto | Percorso |
|---|---|---|
| 1 | Candele: più bucket nello stesso mese, frase lunga sotto | `/Users/ea_enel/.copilot/workspaces/12a0954d-0fbe-42da-b687-979e798a50c6/attachments/559272fc-f850-4bc2-9c36-fb169fd78692-92ff4458-d493-43f3-a0f5-7600980b5b89-clipboard.png` |
| 2 | Income: barre troppo sottili | `/Users/ea_enel/.copilot/workspaces/12a0954d-0fbe-42da-b687-979e798a50c6/attachments/aa813611-0654-4713-901c-c054590325be-80de0cde-d769-49c4-ae5f-7ba1cb667f55-clipboard.png` |
| 3 | Income: tooltip con le sei voci attuali | `/Users/ea_enel/.copilot/workspaces/12a0954d-0fbe-42da-b687-979e798a50c6/attachments/6f707866-cd32-40e8-a756-1f490b39ae21-bad9c3a2-58ba-4aa9-a63f-30738872467a-clipboard.png` |
| 4 | Torta allocazione a un livello | `/Users/ea_enel/.copilot/workspaces/12a0954d-0fbe-42da-b687-979e798a50c6/attachments/45c752d3-bcdb-4f81-b90c-ab2517b4584f-5b83de79-7b2d-4812-a8af-45ba68fb737d-clipboard.png` |

---

## 6 · Distribuzione per owner

| Owner | Voci | Note |
|---|---|---|
| **I** — grafici performance | R8, R9, R10, R11, (R5/R6 con J) | Il blocco più grande; R11 richiede una tua decisione di modello prima |
| **J** — privacy / onboarding | R5, R6, R7, R19, **R20** | R5/R6 toccano un file di I: coordinare per non scrivere in due. R20 è la stessa famiglia |
| **A** — asset global | R1 | Una riga per catalogo; se il file risulta di F, passa a F |
| **Risk** | R12, R16 | Entrambe discendono dalla tassonomia a due livelli |
| **D** — PAC | §3.1 | Non un difetto: serve la tua decisione sulla UI v2 |
| **Da assegnare** | R2, R3, R4, R13, R14, R15, R17, R18 | Nessun workstream attivo le copre |

> 📌 **Le otto voci non assegnate non sono un residuo**: sono un perimetro coerente —
> versione/update, select, wizard di import. Nessuno dei sette workstream attuali possiede
> quelle superfici. Se le distribuisci fra gli owner esistenti, scriveranno in file che non
> conoscono; se apri un workstream nuovo, ha un tema e un confine propri.

---

## 7 · Note per l'esecuzione

- **Nessuna voce è stata riparata.** Questo foglio è una raccolta verificata, non un
  intervento: i sette alberi restano `FROZEN` su `e4a46e9e0`.
- **R2 ha un'azione immediata** che non richiede un agente: `rm VERSION` sulla tua macchina.
- **R3/R4 vanno dopo R2**, altrimenti si collaudano sullo scenario sbagliato.
- **R13 non ha ancora una causa**: chi la prende parte dalla riproduzione.
- **R11, R15, R17 sono decisioni di progetto** prima che implementazioni.

---

## 8 · Secondo passaggio — 22/09/2026, 16:23

Il developer ha ripercorso le aree segnalate come non coperte. Questo passaggio **chiude
cinque sospetti**, ne **apre uno nuovo**, e fissa **tre decisioni di perimetro** sulla privacy.

### 8.1 Chiuso: i numeri

> *«Quelli che riconosco sono tutti corretti. I dubbi sono in risk, ma li rivedremo nel
> dettaglio finita questa parte di review.»*

✅ Il controllo che avevo indicato come il buco più grande **è stato fatto** sulle cifre
riconoscibili. Resta aperto **solo il perimetro risk**, rinviato di proposito a dopo questa
review. Non genera task ora.

### 8.2 Chiuso: Abs/% nel tab correlazione — **non è un difetto**

Il toggle Abs/% era nella mia lista dei sospetti («il click non produce effetti»). La
verifica d'uso lo ribalta:

- compare **solo in modalità griglia** — dettaglio che andava specificato e non lo era;
- nella pagina Asset **funziona**;
- in correlazione il click non produce effetti **su quella pagina**, ma premendolo lì e
  tornando su Asset **l'effetto è vivo**.

> 📌 Il toggle non è morto: è **globale**, e la pagina correlazione semplicemente non lo
> consuma. Quello che sembrava un controllo rotto è un controllo che agisce altrove.
> **Nessuna riparazione.** Semmai una nota d'uso: il controllo appare in una modalità sola.

### 8.3 Chiuso: rendimento a N giorni

> *«Mi pare funzioni MOOOLTO bene.»* ✅ Nessuna azione.

### 8.4 Chiuso: il replay ripiegato

Parte ripiegato **ed è corretto così**. La valutazione del suo *output* è rinviata all'owner
del componente quando si arriverà a rifinirlo. Non è un difetto di stato iniziale.

### 8.5 Chiuso: il valore di acquisto esiste già

> *«Il valore di acquisto complessivo è sicuramente calcolato, altrimenti non potremmo
> mostrarlo nella card KPI di PATRIMONIO NETTO.»*

✅ La domanda aperta in R11 («il dato esiste nel backend?») ha risposta: **sì**. Quindi R11 è
un lavoro di **rendering e modello del grafico**, non di calcolo mancante. Il developer
autorizza esplicitamente un adeguamento backend se serve a esporlo nella forma giusta:
*«potrebbe servire aggiornare il backend, non sarebbe un problema.»* → decisione a **I**.

### 8.6 🔴 Aperto: R20 — la privacy dei broker non si riscopre

**Osservato.** In **Broker Global** i valori si nascondono, ma poi **non si riscoprono**. In
**Broker Detail** e in **Transazioni** il toggle funziona in entrambe le direzioni.

> ⚠️ **È un difetto peggiore di quello che sembra, e va detto a chi lo ripara.** Un toggle
> che non torna indietro non è "metà funzionante": è **irreversibile senza ricaricare**, e
> l'utente che ha attivato la privacy per un momento resta cieco sui propri dati. Il fatto
> che le altre due pagine funzionino dice che il canale è giusto e il difetto è locale allo
> stato di quella pagina — probabilmente una condizione che sa spegnere e non riaccendere.

**Owner: J.** Stessa famiglia di R5/R6/R7.

### 8.7 Decisioni di perimetro sulla privacy

Tre domande poste dal developer, risolte con il criterio che lui stesso ha fissato:

> **Il criterio**: *«il patrimonio entra in gioco quando da quel numero si risale a quanto
> possiede l'utente, e generalmente ha a che fare con le transazioni e le quantità
> possedute.»*

#### ① Numero di movimenti in Asset → **si mostra**

Coerente con la decisione già presa sul prezzo unitario WAC. Da *«12 movimenti»* non si
risale a quanto possiedi: è una **cardinalità**, non una quantità, e non è moltiplicabile per
un prezzo. Dice **quanto spesso** hai agito, non **quanto** possiedi.

Il caso di composizione regge: numero di movimenti + WAC unitario non danno la quantità;
per arrivarci servirebbe comunque una quantità o un controvalore, che restano mascherati.

#### ② Pagina FX → **niente da nascondere**

Verificato nel codice: la pagina FX espone **tassi di mercato**, non importi dell'utente.
`frontend/src/routes/(app)/fx/[pair]/+page.svelte:795` chiede sempre
`from_amount: {amount: '1'}` — cioè la conversione di **una unità**, che è la definizione di
tasso. Un cambio EUR/USD è un dato pubblico: non dice nulla su di te.

#### ③ Tools → **niente oggi, molto domani**

Oggi la pagina non ha nulla da nascondere, per una ragione accidentale: **l'unico strumento
non ha UI** (§3.1).

> 🔑 **Ma il PAC è il caso peggiore di tutta l'applicazione**, e sta per nascere. Prende in
> input *«quanta liquidità investibile ho»* e produce *«quanto metto su ciascun ETF»*:
> **entrambi patrimonio puro**, non un prezzo di mercato. Se il perimetro privacy viene
> dichiarato chiuso adesso, la UI del PAC nascerà **fuori** dal perimetro — e sarà scoperta
> dal primo giorno, in una pagina che oggi risulta legittimamente "pulita".
>
> 📌 Questa è una decisione da prendere **prima** che la superficie esista, non dopo.

### 8.8 Nuovo task: `risk-lab.spec.ts` va riallineato a fine review

> *«Mi torna che risk-lab come test non sia mai stato eseguito. Alla fine della review
> dobbiamo riaggiornarlo, che è rimasto super indietro. Appuntiamoci che è sicuramente uno
> dei test che al termine della review va aggiornato per essere coerente con il nuovo
> sistema.»*

> ⚠️ **Rettifica del 23/09 — la premessa era falsa, e l'avevo data io.** `risk-lab` **è
> stato eseguito**: ✅ 6/6 (`daa03c0f2`) e ✅ 11/11 (`032b86959`) sul ramo di A il 21/09, e da
> allora lo spec è byte-identico. Non è mai girato **sull'albero integrato**, che è una cosa
> diversa. E «rimasto super indietro» non trova appoggio nella misura statica: distanza zero
> su testid, tipi e rotte (misura di F). La tua istruzione resta giusta — **farlo girare
> prima di aggiornarlo** — ma parte da un rosso ignoto, non da un test abbandonato.
> ✅ **Poi misurato (F-1, 23/09 16:15)**: **11/11 verdi sull'albero integrato** `f1047f766`.
> Nessun rosso di partenza: «super indietro» significa copertura mancante del sistema nuovo.
> Dettaglio: 09 §2.1. Owner: **F**; la test list passa da te, non da `test-author`.

📌 **Registrato come task di chiusura della review**, non del round. Due vincoli per chi
lo riprende:

1. Il file è **2057 righe scritte da due mandati diversi** e mai eseguito: prima di
   aggiornarlo va **fatto girare** per sapere da che rosso si parte.
2. ~~Una delle sue tre asserzioni privacy è cieca sotto maschera, le altre due sopravvivono.~~
   🔴 **Falso su questa pagina** *(rettificato il 23/09, 09 §9.8)*: il denaro dei livelli di
   rischio passa da `riskAnalysisHelpers.formatCurrencyAmount`, che sotto privacy restituisce
   `•••` senza valuta, quindi le tre asserzioni sono cieche **tutte**. E `.currency-symbol`
   lì non compare mai, nemmeno a privacy spenta. Il pin si riscrive dopo la riparazione di
   J, contro il comportamento riparato.

### 8.9 Correzione a mio carico: i 61 file di `custom-uploads`

Avevo scritto che erano **orfani sopravvissuti** al `create-clean`. **Falso, e rovesciato.**

```
.avatars_seeded  →  "Seeded 30 avatars at 2026-09-22T11:11:03Z"   (13:11 locali)
un .json         →  "description": "Default avatar: men_04",  "uploaded_by_user_id": 0
                     30 png + 30 json + 1 sentinella = 61
```

Sono gli **avatar di default**, creati **dal** `create-clean` di oggi. Non sono sopravvissuti
al reset: sono il suo prodotto. La frase *«il reset azzera il DB, non il disco»* era esatta
al contrario — il reset **popola** il disco.

> ⚠️ **La forma dell'errore, perché è la terza identica in un giorno.** Ho visto *61 file in
> una cartella di upload* + *DB azzerato* e ho dedotto l'orfanità **dalla sequenza degli
> eventi**. Non ho aperto un file. Il primo `.json` diceva `Default avatar`. Le altre due
> occorrenze: un exit code letto da un comando che non lo usa per segnalare presenza (§R2), e
> un'affermazione altrui accettata senza eseguirla (§3.2).
>
> Tutte e tre sono **deduzioni corrette su un frammento**, che non lasciano residuo: il
> ragionamento fila, e l'unica differenza rispetto al vero è **quanto si è guardato**.

### 8.10 🟡 R21 — Crescita e Allocazione non ricordano la vista scelta

**Osservato.** *«Se cambio pagina e poi ritorno, si riaprono sempre alla prima vista.
Potremmo aggiungere una memoria locale, così che quando ci si torna si riapre il grafico
giusto?»* — vale per **Crescita del portafoglio** e **Allocazione patrimoniale**.

✅ **Il pattern esiste già, e il vicino di casa lo usa.** Nella stessa dashboard:

| componente | persistenza |
|---|---|
| `PositionsPanel.svelte:68-69, 88-89, 96, 104` | ✅ **due** modalità (`semantic`, `visual`) |
| `GrowthChart.svelte` | ❌ zero occorrenze di `localStorage` |
| `AllocationHistoryChart.svelte` | ❌ zero occorrenze di `localStorage` |

Il modello da copiare, per intero:

```ts
const STORAGE_KEY_SEMANTIC = getUserStorageKey('dashboard-positions-semantic');
const STORAGE_KEY_VISUAL   = getUserStorageKey('dashboard-positions-visual');
let semanticMode = $state(normalizeSemanticMode(loadPref(STORAGE_KEY_SEMANTIC, 'holdings')));
```

> 📌 **Il dettaglio da non perdere è `getUserStorageKey()`**: la chiave è **per utente**, così
> due account sulla stessa macchina non si sovrascrivono le preferenze. Chi implementa con un
> `localStorage.setItem('growth-mode', …)` nudo introduce una fuga di preferenze fra utenti —
> piccola, ma è esattamente la classe di difetto che questo helper esiste per impedire.
>
> E c'è un `normalizeSemanticMode()` nel caricamento: un valore salvato da una versione
> precedente non deve poter mettere il componente in uno stato che non sa più rendere.

**Owner: I** (possiede entrambi i grafici). Costo: basso — è un'applicazione del pattern, non
un progetto.

---

## 9 · Terzo passaggio — 22/09/2026, 18:20 · nasce il workstream K

Le otto voci senza owner sono state risolte **guardando i file, non i numeri**. Il risultato
non è una lista sola: sono tre famiglie con tre proprietari diversi.

### 9.1 Chi ha generato la tassonomia

`git log -S "is_benchmark" -- backend/app/db/models.py` dà un solo commit:

```
00d8c735b 2026-09-18  feat(assets): add benchmark flag and risk taxonomy
   entrato con → 25d2d138b  merge(risk): taxonomy (B)
   ramo        → e-alfy-legendary-succotash
```

La sessione si presentava come *«il mandato **B — Tassonomia degli asset e catalogo dei
benchmark** della ripianificazione del sottosistema di rischio»*. Quindi R14–R17 discendono da
una commessa **della famiglia risk, ma chiusa**. Risk-attuale non è il suo erede naturale: ha
già davanti la review puntuale componente per componente, concordata col developer nella sua
chat, e caricarla di backlog UI la ritarda.

> ⚠️ **Rettifica del 23/09.** «Commessa chiusa della famiglia risk» era incompleto: il
> kickoff di B dice *«Il coordinatore della campagna, che gira sul branch
> `e-alfy-risk-management-replan` nel worktree `e-alfy-ideal-eureka`»* — cioè **Risk**. È
> Risk che ha deciso il passo 10 di B (vedi R15 sotto). La scelta di K resta valida per le
> ragioni dette, ma K **riapre una decisione di Risk**, e Risk ne è stato informato.

### 9.2 Le tre famiglie, per file

| famiglia | voci | file che si tocca | owner |
|---|---|---|---|
| Versione | R3 R4 | `onboarding/DeferredAppPopups.svelte`, `auth/UpdateAvailableModal.svelte` | **J** |
| Tassonomia | R14 R15 R16 R17 | `utils/assetTypes.ts` — *una sola funzione* | **K** |
| Select / Import | R13 R18 | `ui/select/optionFilter.ts`, `ImportWizardModal.svelte` | **K** |

**R3/R4 non erano orfane.** `DeferredAppPopups.svelte` nasce da `8a8e686f0 feat(onboarding):
add modular guide foundation` — è J che l'ha scritto, ed è *esattamente* il componente che
conta `data-modal-scroll-lock-count` per non accavallare i popup. Ha fallito il compito per
cui esiste. Darlo a un agente nuovo significa metterlo a correggere codice vivo di J.

**R16 si sposta da Risk a K.** Non per tema, per riga: `getAssetTypeIconUrl()` e
`buildAssetTypeOptions()` sono nello stesso file, adiacenti, e R14/R15 le riscrivono. Due
owner sullo stesso file è la collisione che il protocollo vieta per prima.

### 9.3 Tre rettifiche emerse verificando

> ⚠️ **R14 era un equivoco di superficie.** `TransactionTypeSearchSelect.svelte` **esiste già**
> ed è un `SearchSelect` (lo usano `TransactionFormModal`, `TransactionBulkModal`,
> `FixFlaggedStep`). Il select piatto osservato è quello dei **tipi asset** — ETF e
> crowdfunding sono asset, non transazioni. La voce si restringe a quel select.

> 🔴 **R15 riapre una decisione, e il registro non la conosce.** *(rettificato il 23/09 — il
> 22/09 questa voce diceva «è il disegno di B, non una svista», ed era incompleto.)* Tre
> documenti, tre versioni:
>
> - `Phase_0/02_riskfolioIntegration/04-decisioni-e-questioni-aperte.md`, **D62** (17/09):
>   l'albero a due livelli è `SignalTreeSelect`, da generalizzare in `ui/select/`. Nel
>   registro è **ancora vigente**.
> - `Phase_0/02_riskfolioIntegration/implementation/progress/B-esecuzione.md`, passo 10: il
>   coordinatore di B (**Risk**) ha respinto la promozione dopo F27 *(⚠️ F27 è citata e **mai
>   scritta**: nel registro di B i Fuori pista saltano da F26 a F28 — Risk, 23/09)* — le due forme divergono
>   su tre assi — e B ha scelto le sezioni piatte su `SimpleSelect`. Il docstring di
>   `buildAssetTypeOptions()` è quella scelta. La correzione di D62 **non è mai stata
>   scritta nel registro**.
> - La review del 22/09 chiede l'albero «come il selettore degli indici nel pannello
>   segnali»: cioè D62 com'era.
>
> Rivalutazione: **K**, con le opzioni al developer prima del codice. Risk annota D62.

> 🔴 **R16: la pastiglia di D52 non è mai stata consegnata.** *(misurato il 23/09)* D52
> prescrive icona grande del contenitore + icona piccola sovrapposta del tipo base, con una
> costante accanto a `PNG_MAP`: in `assetTypes.ts` non c'è, e nessun componente la rende.
> `B-esecuzione.md` la dà per presente perché usa «pastiglia» per due cose diverse: la
> classe colore del badge (`assetTypeBadgeClass`, consegnata) e l'icona sovrapposta (mai).

> ✅ **R17 non richiede una migrazione.** `assets.asset_type` è un `VARCHAR` **senza CHECK
> constraint**: l'enum vive in Python e allargarlo è un cambio di codice. Non tocca il divieto
> di nuove migrazioni dato ai figli.

### 9.4 Larghezze di colonna — deciso e applicato dal coordinator

Verificando R17 è emerso che `assets.asset_type` era dichiarata `VARCHAR(14)` mentre
`ETF_REAL_ESTATE` è **15**: la dichiarazione era già sfondata. Misurate allora *tutte* le 27
colonne con larghezza dichiarata contro il massimo che i rispettivi enum possono produrre:

| colonna | dichiarata | massimo possibile | esito |
|---|---|---|---|
| `assets.asset_type` | 14 | **15** `ETF_REAL_ESTATE` | 🔴 sfondata |
| `transactions.type` | 14 | 13 `FX_CONVERSION` | 🟠 un carattere di margine |
| `alembic_version.version_num` | 32 | 24 `004_release_1_2_0_schema` | 🟠 tetto ai nomi futuri |
| le altre 24 | — | — | ✅ ampie |

Entrambe portate a **32** nel DDL di `001_initial.py`, su decisione del developer. 32 e non 24
perché è lo stesso numero che Alembic usa per sé, e perché `CROWDFUND_REAL_ESTATE` (R17) è 21.

**Nessuna ricostruzione di tabella sugli installati.** Provato che su SQLite la larghezza è
avvisoria — 30 caratteri accettati in una `VARCHAR(14)` — quindi rifare `assets` e
`transactions` su ogni installazione rilasciata costerebbe un rischio reale per zero effetto.
La divergenza che resta (installati a 14, nuovi a 32) è invisibile su SQLite e sparisce il
giorno in cui lo schema viene costruito su un motore che applica il vincolo, perché quel
giorno lo costruiscono queste migrazioni.

Il docstring della 004 **argomentava il contrario** ed è stato riscritto: era la stessa classe
di difetto — una doc che resta indietro — che questo round ha già pagato una volta.

Aggiunto infine alla regola di naming (`backend-db.instructions.md`) il tetto mancante: un
revision id deve stare in **32 caratteri**, perché `alembic_version.version_num` è
`VARCHAR(32)` e su Postgres il vincolo è applicato davvero.

**Gate:** `db_schema_validate.py` **17/17 verdi** su DB di test ricreato dalla catena, con
`VARCHAR(32)` su entrambe le colonne; DB già installato (`VARCHAR(14)`) portato a head senza
DDL, `integrity_check ok`, 15 asset intatti.

---

## 10 · Quarto passaggio — 23/09/2026, pomeriggio · le proprietà incrociate

I piani dei sette workstream, letti insieme, hanno fatto emergere voci che nessun piano
possedeva, o che due piani possedevano insieme. Decisioni del coordinator:

| voce | cosa | owner | nota |
|---|---|---|---|
| 🔴 stress uniforme | `RiskAnalysisPanel.svelte:115` elenca 9 tipi su 17; a `:472` lo stress costruisce i secchi solo da lì → 8 tipi con shock 0.0 in silenzio | **Risk** | trovato da K, verificato |
| 🔴 privacy e valuta | `riskAnalysisHelpers.ts:160` maschera anche la valuta (09 §9.8) | **J** | Risk non tocca quelle righe |
| R2-128 | accesso al sync FX dal laboratorio, perso smontando il monolite (`implementation_2/REGISTRO.md:360`) | **F** | proprietario del guscio; il developer può rinviarlo |
| §1.6 · pin privacy `risk-lab` | riparazione del gate | **F** | variante ON dopo J |
| filtro broker | `risk-analysis.spec.ts:1335` → `risk-lab.spec.ts` | **F** aggiunge, **Risk** rimuove | **ordine**: F aggiunge e lo porta verde, poi manda il nome al coordinator, che dà il via a Risk (14 → 13); `desc=` del catalogo: F solo per aggiunta, Risk solo per sottrazione. **Integrazione**: F non dopo Risk, altrimenti nel target si apre una finestra senza copertura |
| `panelTitle` | chiave orfana `risk.assetSet.panelTitle` | **F**, a fine round | introdotta da F (`f2ad97dd4`); non si cancella prima |
| §2.6 | commenti `formatScopedCurrencyAmount:163` in `L4Replay:47`, `L4Shock:46` | **Risk** | file della famiglia Risk (E → S4), non di F |
| citazioni derivate | `AssetSetRiskPanel.svelte:42` cita `:874` (ora `RiskAnalysisPanel:879`); `AssetSetReplaySection.svelte:31` cita `service.py:840` (ora `:873`) | **F** | segnalate da A, verificate; stesso rimedio di §2.6: citare il simbolo |
| R17 · scenari | righe CROWDFUND_REAL_ESTATE in `equity_crash.yml`, `global_risk_off.yml` | **K**, nello stesso commit dell'enum | valore al developer; Risk non tocca i due YAML fino a R17 |
| R13 · `optionFilter.ts` | ordinamento condiviso da tutti i `SearchSelect` | **K**, unico scrittore | test list con tutti i consumatori |
| registro privacy | righe del grafico di crescita | **I**, nello stesso commit | file di J; al merge si sommano |
| emoji `AllocationHistoryChart` | mancano COMMODITY, REAL_ESTATE, ETF_MONETARY | **I** | segnalato da K, da verificare |
| indice `financial-theory/asset-types` | 8 tipi mancanti, HOLD etichettato «Commodities» | **K**, con R17 | EN via `docs-writer`; traduzioni su richiesta del developer |

**Aggiunte del 23/09, ~16:00** (dal messaggio di J, verificate):

| voce | cosa | owner | nota |
|---|---|---|---|
| 🔴 privacy e valuta, secondo sito | `LotComparisonChart.svelte:261` | **J** | stesso difetto di `riskAnalysisHelpers:160` |
| `riskAnalysisHelpers.ts` + test | file interi, per tutto il round | **J**, unico scrittore | nessuna finestra: Risk non li tocca |
| 🔴 P4-11, secondo grafico | `PerformanceChart.svelte:161` (`shortMoney`, P&L per posizione), `:170` (`axisTickAmount`, asse dei valori) — nessun riferimento alla privacy nel file | **I** | piano di I rimandato per aggiungerlo |
| ~~D1 di I, precisato~~ → **D1 rifatto** *(J, 16:00)* | «al merge si sommano» era sbagliato: `moneyRenderSites.test.ts:276` usa PerformanceChart come esemplare del controllo positivo, e mascherarlo lo manda rosso; le 4 voci di I vanno cancellate; le liste `:272-273` le toccano sia I sia J | **J** gate-prep (checkpoint separato, solo il file del gate) → merge **J → I** → **S2 di I** | dipendenza tra workstream, gestita con un merge figlio → figlio; `compact` dentro la maschera; nessuna primitiva nuova per I |
| ancore della guida import | `ImportWizardModal` `import.action.*` `:4586–4770`, 5 del Bulk, step-sync `:164–178`, `:1279` | **K** le preserva | per l'analisi di K R18 non tocca quel file |
| §1.3, §1.5 di 09 | ritirate | — | barrate, non cancellate |
| 🟡 **C2 — latente** *(era 🔴 candidato; rettifica di Risk, 17:40)* — orizzonte del bootstrap | `simulation.py:403` passa `horizon_days` senza conversione; il bootstrap conta osservazioni, il GBM converte. ~~sui dati del developer la griglia congiunta è fatta di giorni di borsa (0,69 per giorno di calendario), quindi «365 giorni» ≈ 17 mesi di mercato: cono ~+20%, deriva ~+45%, in modalità di default~~ → **premessa falsa**: la griglia è l'**unione** delle date con una quotazione fresca (`series_preparation.py:236`), poi tiene quelle in cui ogni asset ha un valore, anche riportato (`:287`). Non è l'intersezione. Con un asset justETF nel perimetro è **giornaliera di calendario**: f = 365, e «365 giorni» sono un anno. Il difetto morde solo dove nessun asset scrive i weekend | **Risk**, nel tempo ② col developer | la correzione dentro `simulation.py` resta consigliata. Premessa presa da una frase della doc (`observed-annualization.en.md:95`) invece che dal codice. Verificato dal coordinator nel codice, sulla snapshot e con la misura di A (riga «griglia di calendario» qui sotto) |
| 🔴 **candidato F2** — asset senza prezzi = liquidità allo 0% | `service.py:608-687`, `usable_cash_weight = 1 − Σ pesi utilizzabili`. Verificato sulla snapshot: i 4 crowdfunding (id 12-15) hanno **0 righe** in `price_history` e pesano il **30,5%** | **Risk**, nel tempo ② col developer | limite del modello, non un bug; tocca correlazione, contributi, N_eff, backtest, simulazione e replay **nel perimetro di portafoglio**. ⚠️ *Rettifica del 16:58, misura di A sulla copia*: nel perimetro `asset_set` l'asset senza prezzi viene **escluso** (`missing_price`, avviso `assets_excluded`; `[1,3,8]` e `[1,3,8,12]` danno entrambi 574 osservazioni) e non convertito in liquidità. C2 non compare su Asset Global, perché lì la simulazione non è annunciata |
| 🔴 **replay inerte** | il polling di `POST /api/v1/assets/prices/current` (Asset Global, due volte a caricamento e ogni 30 s; ogni chiamata scrive) passa da `zodios-client.ts:123` → `notifyPortfolioMutation` → `riskStore.svelte.ts:195` `invalidateRisk`; il `queryRisk` in volo torna `null` e `runGuarded` lo scrive come risultato: niente spinner, niente errore | **Risk** (`runGuarded`: richiedere una volta, poi dirlo, come `loadBase`) | trovato da F (C15 rosso), catena verificata. **R2-66 aveva la diagnosi sbagliata**: la corsa d'identità è irraggiungibile, la causa è il polling; va riscritta nel ramo di scarto di `loadBase` e nel test `riskStore.test.ts`. F ha già corretto lo stesso difetto nel suo `applyBrokerPreset`. **Portata** (misura di Risk): il polling c'è in Asset Global (`assets/+page.svelte:401`) e in Asset Detail (`assets/[id]/+page.svelte:1468`, `:2034`), non in Dashboard né in Broker Detail; `portfolioMutation.ts` conta come mutazione ogni `POST` sotto `/api/v1/assets/prices` tranne `/query`. La riparazione va comunque in `runGuarded`, per tutti. Risk verificherà da sé la nuova diagnosi di R2-66 prima di riscriverla |
| sostituto promesso | `risk.levels.l4.replayNeedsChoice` promette «give it a stand-in», ma `L4Replay.svelte:101` scrive `proxyAssets: []` fisso | **Risk** + decisione del developer | togliere la promessa o costruire il sostituto; vale su ogni pagina con L4 |
| `CorrelationHeatmap` condivisa | «By name» ordinava per id → ora per nome (testid `risk-correlation-ordering-name`, il vecchio era usato solo da `risk-lab.spec.ts` di F); colori della lista coppie allineati alla heatmap | **F** · Risk informato: **cambia anche la Dashboard** | la polarità dei colori è una decisione del developer (F-3): una riga nel `visualMap`, che sposta anche la Dashboard |
| 🔴 polling di `/assets` a raffica | l'effetto legge `assets.length` e riparte a ogni riassegnazione di `assets`; `fetchAllPriceData` la riassegna fino a 4 volte → fino a 4 `POST /prices/current` per caricamento, ognuno con 14 righe scritte e un'invalidazione **globale** di report e rischio | **F** (unico scrittore di `assets/+page.svelte` in questo round) | l'effetto deve dipendere dall'elenco degli id; riduce la frequenza del replay inerte, senza sostituire la riparazione di Risk in `runGuarded` |
| motore di correlazione (per il tempo ②) | `min_coverage` non può scattare (copertura 1,0 per costruzione, `low_pair_coverage` morto); `min_observations = 2` del plugin non si applica (agisce il parametro, default 20); riempimento in avanti senza limite di età che da solo rende `partial`; `data-quality.en.md` §Alignment falso per un asset che parte tardi; `en.json:3228` «Some correlation pairs…» per una condizione su tutte le celle | **Risk**, col developer | trovati da `docs-writer` di F eseguendo `RiskService.execute`. ~~il coordinator non li ha misurati~~ → **due verificati dal coordinator nel codice** (17:45). *`min_coverage`*: per l'avviso regge. La copertura di cella è `osservazioni / n_observations` sulla stessa griglia densa (`metrics.py:583`, `correlation.py:64-75`), quindi vale 1,0. La copertura **del risultato**, invece, è `calendar_coverage` (`correlation.py:133`) e scende sotto 1: su `[1,3,8]` dal 2024-01-01 vale 574/995 = **0,577**, sotto il default 0,6, e nessun avviso scatta. Il controesempio di Risk (asset tardivo, `series_preparation.py:344-345`) riguarda questa seconda copertura, non quella che la soglia confronta. *Riempimento in avanti*: confermato, perché `CARRIED_FORWARD` (`schemas/portfolio.py:244`) ≠ `OK` dà `partial` (`service.py:803`) |
| ⑥ | test di F verde (16/16), nome esatto a `risk-lab.spec.ts:2478` | via a Risk **dopo** il commit del suo checkpoint | la correzione di ⑥ tocca due file del commit 6. *24/09*: tempo ① committato (`a5f6776aa`…`de55b5346`), via dato alle 09:31. ⑥ fatto: il vecchio test tolto per titolo, `risk` 13/13, checkpoint 7 pronto (3 percorsi). 🔴 Da qui l'**ordine d'integrazione è vincolante**: il ramo di F entra prima di quello di Risk, oppure nello stesso merge |
| colori D71 tra i due grafici | lo storico (`AllocationHistoryChart`) ordina le famiglie per **peso medio del periodo**, la torta per **peso di oggi**: la stessa famiglia può uscire con colori diversi | **Risk** con il developer, nel tempo ② · **I** coinvolto | non è un difetto: si decide in review se la regola di ordinamento va condivisa |
| 🟠 **il gate privacy non gira** | 5 test di J orfani del runner: `privacyStore`, `privacyStoreSsr`, `currencyFormat`, `maskable` (`b66e93003`) e **`moneyRenderSites`** (`9a6dd2015`), cioè il gate dei punti di resa non registrati, che non è registrato lui stesso. Nessun workflow CI lancia vitest | **J** registra, e sceglie l'azione | trovato da Risk con `check-orphans`, verificato: 0 citazioni nel catalogo. Finché non si registra, il verde esiste solo per chi lancia il gate a mano, e le verifiche del gate-prep e dell'S2-pre di I lo devono eseguire esplicitamente |
| R2-128 · la riga in A (D9 di F) | `AssetSetComparisonLevels.svelte:90` deve ricevere il nuovo `refreshVersion` | **F** la scrive | prop opzionale con default che lascia invariato il comportamento; A non tocca il file finché R2-128 è aperto; se il developer rinvia R2-128, D9 decade |
| R2-128 · la pagina | `routes/(app)/assets/+page.svelte:1510` (montaggio del guscio), una riga | **F** | non interagisce con §2.5 di I: quello è `assets/[id]/+page.svelte:2174`, altra pagina |
| citazioni derivate, precisazione | `{#if scope.kind === 'asset'}` compare due volte in `RiskAnalysisPanel` (`:742`, `:879`) | **F** | «cita il simbolo» non basta: va citato per contenimento; F rende simboliche tutte e 8 le citazioni dei suoi componenti, più una terza nata sbagliata (`AssetSetReplaySection:44` → `L4Replay:238`) |
| 🟠 **griglia di calendario sui dati del developer** *(17:45)* | justETF scrive sabato e domenica con la chiusura del venerdì. Nella snapshot ci sono **14 448** righe di weekend sui 10 asset justETF, e **il 100 %** è uguale al venerdì. Il provider le passa come arrivano, con `backward_fill_info=None` (`justetf.py:373-387`): contano come fresche (`series_preparation.py:123-125`). Il BTP (id 8, `borsa_italiana`) ha 399 righe, **nessuna** nel weekend | **Risk** con il developer, nel tempo ② | Conseguenze verificate: **(1)** con un justETF nel perimetro f = 365, e *Mese storto* (21 osservazioni, `asset_set_var.py:83`, `historical_var.py:71`) dura **3 settimane**, come sul portafoglio. Sul portafoglio lo è per costruzione: la serie TWRR del report ha un punto per ogni giorno di calendario (`service.py:932-941` la legge da `report.history`; `portfolio_engine.py:870-871` emette uno stato per giorno di calendario, e i giorni fermi riusano quello precedente; `portfolio_service.py:1305-1425` ne ricava la storia senza campionarla), quindi togliere le righe del weekend di justETF non basta a farne di nuovo un mese. Resta da decidere l'unità dell'orizzonte. Fa eccezione il BTP da solo, su giorni di borsa, dove 21 osservazioni sono circa un mese. L'insieme preparato include anche gli asset di confronto (`service.py:170-171`), quindi un benchmark justETF cambia griglia anche al BTP. **(2)** Ogni asset justETF ha un rendimento **esattamente zero** nei weekend, in ogni VaR e in ogni correlazione. *Misura di Risk del 24/09, fatta sulla copia su 3 asset justETF per 730 giorni, non riverificata dal coordinator*: la volatilità annualizzata **non** è distorta, perché il fattore osservato compensa la diluizione (rapporto 1,00). Sono sottostimati i quantili per osservazione: *Giornata storta* dell'8-13 %, *Mese storto* del 9-19 %. Vale per ogni ambito sulla griglia di calendario. **(3)** Se nel perimetro c'è un justETF, il BTP viene riportato in avanti ogni weekend, e il risultato è `partial`. È la causa del `partial` di A su `[1,3,8]`: 574 osservazioni sono 574 giorni di calendario (baseline 2025-02-25, prima quotazione del BTP) e i punti riportati sono 176. `[1,2,3,4]`, tutti justETF, danno `ok` |
| doc · la griglia descritta come intersezione | `observed-annualization.en.md:95` («intersected across the assets in scope») e `historical-replay.en.md:95` («over the intersection of the calendars») contraddicono il codice e `data-quality.en.md:60`, che l'unione la descrive giusta. La stessa premessa, di A, è nella sua pagina utente `user/assets/correlation.en.md` (:99 «about a month», :138, :150, :182) e nel suo piano (:138-143, :197, :211, :454-455) | **Risk** per le due pagine di teoria, come unico scrittore, dopo il suo checkpoint · **A** per la sua pagina e il suo piano, in un commit **dopo** il checkpoint | Le pagine di teoria vengono da `b35a8581e`, e oggi nessun ramo le tocca. `data-quality.en.md` e la `correlation.en.md` di teoria restano di **F**. Deciso *dopo* e non *prima* (17:58): il piano va corretto comunque dopo, e scongelare adesso invaliderebbe un checkpoint già verificato. A ha già corretto il messaggio del suo commit 2, e l'ho riverificato |
| 🟠 **E2E già rossi sul target** *(misurati da I, 24/09)* | su `f1047f766`: `front-portfolio dashboard` 5 falliti su 15 (`:577` ×3, il selettore zoom-window tolto; `:607`, legge un badge non più montato; `:534`) e `front-broker detail` 1 fallito su 28 (`:710`). Per `:534` e `:710` la causa è misurata: da `e7773a143` lo zero non ha segno, e i test cercano «≥3 importi con segno». È un'assunzione del test, non un difetto del prodotto. In più, da unit: `chartCoreHelpers.test.ts` 12 falliti su 162 (P4-9) | **I**, in S10, perché li ha rotti una sua slice | l'inventario del 22/09 misurava solo gli unit, quindi il «12» valeva per quel perimetro, non per il ramo. In questo round `dashboard.spec.ts` e `brokers-detail.spec.ts` li scrive solo I. J avvisato: confronta i risultati per nome del test |

**Aggiunte del 24/09, pomeriggio**:

| voce | cosa | owner | nota |
|---|---|---|---|
| 🟠 **lampo della shell** (privacy) | `(app)/+layout.svelte` è legacy: le sue `$:` leggevano `appBootstrap.ready`, uno stato runes che non tracciano. Quando serviva un redirect (benvenuto pendente, replay del benvenuto armata), la pagina richiesta si disegnava per 1-5 frame, e il segnaposto `onboarding-redirecting` non si montava mai (0 su 40 giri). In 1 giro su 8 dello scenario B sono comparsi 9 importi, gli zeri di un portafoglio vuoto: quindi il contenuto può arrivare dentro quella finestra | **J**, unico scrittore del layout, di `vitest.config.ts` e del mock `$app/stores` | ✅ `cc20b8288`: `toStore(() => appBootstrap.ready)`. Dopo la correzione: 0 frame, segnaposto montato 5 volte su 5 in ogni scenario. Test di regressione `layout.gate.test.ts`, rosso con le `$:` di prima (controllo negativo). Vincolo, scritto nel test: il template legacy segue `appBootstrap` solo attraverso i suoi getter enumerabili, quindi se `appBootstrap` diventasse una classe resterebbe fermo sul caricamento il layout vero |
| `risk.eligibility.*` | chiavi dei motivi di idoneità nel «+» del laboratorio | **F** fino a F → Risk, poi **Risk** | i 5 motivi di `14c334d85`. `no_price_history` (checkpoint C di Risk) lo scrive chi per primo ha nello stesso ramo sia l'enum sia la mappatura di F: oggi Risk, a F → Risk. Nessun riuso con `risk.warnings.historical_replay_excluded_*`, che appartiene a un altro enum |
| ordine d'integrazione F/Risk | Risk `14c334d85` fuso nel ramo di F: `2c02ff070` (24/09, 16:00), senza conflitti | — | la finestra senza copertura broker (riga ⑥) si chiude **dentro** il ramo di F. Da qui il caso «preset broker» di `risk-lab` è l'unica copertura broker, e F-6 lo deve tenere |
| ancora della guida nascosta | la gestione degli stalli del Round 7 non copre un'ancora **montata ma non disegnata**: con `display:none` il rettangolo è 0×0 e stabile, e il coachmark si aggancia a (0,0) | **J** (C6) | nel ramo di F l'ancora `asset.page.filters` sta dentro `{#if activeTab !== 'correlation'}`: è smontata, quindi lo stallo la copre già. J estende a tutte le pagine la regola «non disegnata = assente». Per chi scrive le pagine: `use:guideAnchor` solo sull'elemento visibile |
| sovra-mascheratura | `TransactionsTable.svelte` (`eventTooltipText`) e `transactions/wac/WacPreviewSection.svelte` (costo unitario, WAC progressivo) | **J** (C6), unico scrittore | regola D5′: un valore unitario è `public`, un totale `personal` |
| etichette dell'header | `PrivacyToggle`, `ThemeToggle`: testo inglese fisso | **J** (C6), unico scrittore dei due file | chiavi nuove, 4 lingue via `dev.py i18n` |
| doc della dashboard | `user/dashboard/index.en.md` dice tre schede, ma sono quattro | **I**, in S11-finale | trovato da J |

> ⚠️ **Errore del coordinator nel kickoff di J**: gli ho scritto che il piano Round 4 «resta
> valido e va cucito». È chiuso dall'11/09, e il **Round 5** (12/09) ne ha rovesciato lo
> split Bulk — *«Import/Bulk tornano a un flow ciascuno»*. Cucirlo avrebbe reintrodotto una
> decisione che il developer aveva annullato. La prosecuzione è OB-8 → OB-9 del piano Round 7.

### Il blocco che ho creato io

La procedura di copia del 23 mattina leggeva `backend/data/prod` del **main checkout**, e
l'agente dei figli lo vieta (`coordinated-workstream.agent.md:63`, *«Never read the main
checkout»*). A si è fermato lì, e gli altri sei si sarebbero fermati nello stesso punto.
Decisione del developer: **una snapshot sola, in sola lettura**, `/tmp/librefolio-r2-prod-snapshot`,
creata dal coordinator; ogni figlio copia da lì. Provata: la copia è scrivibile e accettata dal
guardiano, la snapshot rifiuta le scritture (*«attempt to write a readonly database»*) e il prod
resta byte-identico.

> 📌 **Una regola scritta in un file che il destinatario legge non basta: va letta anche da chi
> scrive l'ordine.** Avevo letto l'agente dei figli per il kickoff di K e non l'ho riletto
> scrivendo la procedura.

### Credenziali

La password di `alfy` non era cambiata: l'avevo troncata io, leggendo il punto finale come
punteggiatura. Verificata col login reale su una copia (200, 15 asset; senza punto 401). Il
reset via CLI è sicuro solo così: `LIBREFOLIO_TEST_DATA_DIR=<copia> … dev.py user --test-db`,
con `list` prima di `reset`. `dev.py user` **non ha `--data-dir`**: senza `--test-db` mira al
prod del checkout da cui lo si lancia — dal checkout principale, sono i dati del developer.
