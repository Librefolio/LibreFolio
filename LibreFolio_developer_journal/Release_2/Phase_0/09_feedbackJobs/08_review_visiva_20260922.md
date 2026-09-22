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
| R3 | Versione | Modale nuova versione sotto quella corrente (z-index) | 🟠 | da assegnare | ⚠️ superficie |
| R4 | Versione | Nessun banner "sei aggiornato" a schermo | 🟠 | da assegnare | ⚠️ superficie |
| R5 | Privacy | Asse Y in **Abs** mostra valori assoluti | 🔴 | **J** + **I** | ✅ P4-11 |
| R6 | Privacy | Asse Y in **P&L** stesso problema | 🔴 | **J** + **I** | ✅ P4-11 |
| R7 | Privacy | Infobox mostra valori assoluti | 🔴 | **J** | ⚠️ superficie |
| R8 | Grafici | Candele: più bucket nello stesso mese | 🟠 | **I** | ❓ riprodurre |
| R9 | Grafici | Frase sotto le candele: sintetizzare + scroll CSS | 🟡 | **I** | ✅ superficie |
| R10 | Grafici | Income: barre troppo sottili | 🟠 | **I** | ❓ riprodurre |
| R11 | Grafici | Income: manca il valore di acquisto nello stack | 🟠 | **I** | 📐 progetto |
| R12 | Allocazione | Torta a 1 livello, non 2 come concordato | 🟠 | **Risk** | ❓ riprodurre |
| R13 | Select | "CSV" non trova "Generic CSV" | 🟠 | da assegnare | 🔴 **non è optionFilter** |
| R14 | Select | Tipo transazione: evolvere a `SearchSelect` | 💡 | da assegnare | ✅ superficie |
| R15 | Select | Tipo transazione: 2 livelli come pannello segnali | 🟠 | da assegnare | 📐 progetto |
| R16 | Select | ETF: manca la seconda icona sovrapposta | 🟠 | **Risk** | 📐 nei piani risk |
| R17 | Tipologie | Aggiungere crowdfunding immobiliare | 💡 | da assegnare | 📐 progetto |
| R18 | Import | Doppia modale ISIN (race condition) | 🔴 | da assegnare | ⚠️ superficie |
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

### R3 🟠 · R4 🟠 Modali update — z-index e banner assente

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

### 3.2 La privacy non nasconde la valuta — già corretto

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

📌 **Registrato come task di chiusura della review**, non del round. Da affidare a
`test-author`. Due vincoli da portargli:

1. Il file è **2057 righe scritte da due mandati diversi** e mai eseguito: prima di
   aggiornarlo va **fatto girare** per sapere da che rosso si parte.
2. Una delle sue tre asserzioni privacy (`:1356`, `.not.toMatch(MONEY_PATTERN)`) è **cieca
   sotto maschera** — cerca il *valore*, che la privacy cancella. Le altre due cercano il
   *canale* (`'€'`, `.currency-symbol`) e sopravvivono. Chi riscrive deve sapere quale delle
   tre lo stava davvero proteggendo.

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
