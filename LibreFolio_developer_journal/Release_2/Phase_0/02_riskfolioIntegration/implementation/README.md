# Implementation — mappa di coordinamento

**Data**: 17 Settembre 2026
**Presupposto**: [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) approvato.

> Questa cartella contiene **i mandati**, uno per flusso. Ogni file è scritto per
> essere consegnato a un sotto-agente `coordinated-workstream` come prompt di avvio,
> senza bisogno di altre spiegazioni oltre ai link che contiene.
>
> Questo README è l'unico documento che i sotto-agenti **non** possiedono: è del
> coordinatore. Contiene le lane, la proprietà dei file e l'ordine di lancio.

---

## 1. Il modello di esecuzione

Il piano ha dodici flussi ([`07`](../07-piano-esecutivo.md) §2). Qui diventano **undici
mandati**, perché W0 e W1 vanno allo stesso agente: chi scrive l'oracolo è chi poi
migra sotto la sua protezione, e sono lo stesso file.

| Mandato | Flussi | Dominio | Taglia | File |
|---|---|---|:---:|---|
| **A** | W0 + W1 | backend matematica | L | [`A-backend-oracolo-e-migrazione.md`](./A-backend-oracolo-e-migrazione.md) |
| **B** | W2 | DB + backend + frontend | L | [`B-tassonomia-e-benchmark.md`](./B-tassonomia-e-benchmark.md) |
| **C** | W3 | backend scope | M | [`C-backend-affettamento-portafoglio.md`](./C-backend-affettamento-portafoglio.md) |
| **D** | W4 | frontend primitive | M | [`D-frontend-primitive-e-card.md`](./D-frontend-primitive-e-card.md) |
| **E** | W5 | frontend | **XL** | [`E-frontend-quattro-livelli.md`](./E-frontend-quattro-livelli.md) |
| **F** | W6 | frontend | L | [`F-frontend-laboratorio.md`](./F-frontend-laboratorio.md) |
| **G** | W7 | frontend dashboard | M | [`G-frontend-colori-allocazione.md`](./G-frontend-colori-allocazione.md) |
| **H** | W8 | backend simulazione | **XL** | [`H-backend-montecarlo.md`](./H-backend-montecarlo.md) |
| **I** | W9 | documentazione | M | [`I-documentazione.md`](./I-documentazione.md) |
| **J** | W10 | chiusura | S | [`J-chiusura-e-rilascio.md`](./J-chiusura-e-rilascio.md) |
| **N** | W11 | backend acquisizioni | M | [`N-backend-acquisizioni.md`](./N-backend-acquisizioni.md) |

> ⚠️ **Perché N si chiama N e non K.** Le lettere `K1`-`K8` sono i **contratti** (§4).
> Un mandato «K» sarebbe indistinguibile da un contratto in ogni messaggio fra sessioni.
> Stessa ragione per cui si saltano `L` (i livelli L1-L4) e `M` (le migrazioni M1-M6).

### 1.0 N è nato dopo, e va detto perché

Il mandato **N** non era nel piano originale: è emerso dalla **verifica dei dieci
mandati**, ed era il difetto più grave che quella verifica ha trovato.

Le decisioni **D38** (NEA e diversification ratio), **D45** (WR) e **D56** (la famiglia
drawdown) erano **decise e assegnate a nessuno**: il mandato A le espelle
esplicitamente come «acquisizioni, non migrazione», mentre il mandato E le assume già
presenti nel payload. Verificato con `grep` su tutto `backend/app`: `diversification`
zero occorrenze, `worst_realization` zero, `herfindahl` solo dentro AI Export.

**D39** (`Sharpe(rm=…)`) **resta ad A**, perché richiede la stessa idraulica di M5 — la
matrice dei rendimenti che oggi non arriva a quel livello.

### 1.1 Un worktree per mandato, non un worktree per tutti

⚠️ **Il punto che decide se la parallelizzazione funziona o produce danni.**

Sotto-agenti lanciati nella *stessa* cartella di lavoro condividono il filesystem: due
che scrivono nello stesso momento si sovrascrivono senza che Git se ne accorga, perché
non c'è ancora nulla da fondere. La parallelizzazione richiede **isolamento vero**:

> Ogni mandato gira in una **sessione worktree propria**, creata dal coordinatore, con
> la propria lane. Lo strumento del progetto per questo è l'agente
> `coordinated-workstream`, e il coordinatore è `release-coordinator`.

Un mandato **non** legge il checkout principale né il worktree di un altro mandato. Se
gli serve qualcosa che un altro sta producendo, lo riceve come **contratto scritto**
tramite il coordinatore (§4), non andandoselo a prendere.

### 1.2 Lane assegnate — banda 6240

L'altro worktree attivo occupa la banda `6150+`. Questa ripianificazione parte da
**6240**. Porta e data directory sono **una coppia**: non se ne scambia una sola.

| Mandato | `--test-port` | `--data-dir` |
|---|---:|---|
| **A** | `6240` | `backend/data/test-risk-a` |
| **B** | `6241` | `backend/data/test-risk-b` |
| **C** | `6242` | `backend/data/test-risk-c` |
| **D** | `6243` | `backend/data/test-risk-d` |
| **E** | `6244` | `backend/data/test-risk-e` |
| **F** | `6245` | `backend/data/test-risk-f` |
| **G** | `6246` | `backend/data/test-risk-g` |
| **H** | `6247` | `backend/data/test-risk-h` |
| **N** | `6248` | `backend/data/test-risk-n` |
| **J** | `6249` | `backend/data/test-risk-j` |
| **coordinatore** | `6250` | `backend/data/test-risk-coord` |
| **I** | — | — (documentazione: nessun server) |

Il coordinatore ha una lane **sua**, e la usa **solo** per i gate trasversali e la
revisione combinata: non gira mai la suite di un figlio.

Forma canonica di ogni comando, da nessuna eccezione:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test \
  --test-port <PORTA> --data-dir <DIR> \
  <CATEGORIA> <AZIONE>
```

Due guardie esistono già e vanno conosciute per non confonderle con un bug:
`configure_test_runtime` (`scripts/cli_base.py:219`) rifiuta una porta di test uguale
alla porta di produzione; `validate_test_data_dir` (`backend/app/config.py:228`)
rifiuta una data directory che si sovrapponga a quella di produzione o che sia dentro
una cartella marcata come tale. **Nessuna delle due sa che `6150` è di qualcun altro**:
quella distanza la tiene questo documento.

### 1.3 Tre fatti verificati sul bootstrap di un worktree

Vanno conosciuti, perché un agente che trova un ambiente incompleto e **non sa che è
normale** comincia a «ripararlo» — ed è il modo più rapido di rompere una lane.

| Fatto | Verifica eseguita | Conseguenza |
|---|---|---|
| **I data dir sono già isolati per worktree** | `get_project_root()` è `Path(__file__).parent.parent`, cioè **relativo al file**: in ogni worktree risolve il proprio | `backend/data/test-risk-*` è worktree-locale. **La porta è l'unica risorsa davvero globale** |
| **`.env` non serve, e la sua assenza è corretta** | Nessuno dei cinque worktree attivi ne ha uno: solo il checkout principale | Non si copia **mai** un `.env` da un altro checkout |
| **Le lane non toccano la produzione** | `DEFAULT_PROD_DATA_DIR = backend/data/prod`, **non** `backend/data` | `backend/data/test-risk-*` non si sovrappone: la guardia passa |

### 1.4 ⚠️ `node_modules` — l'unico bootstrap che serve davvero

**Misurato**: `frontend/node_modules` pesa **636 MB**, è in `.gitignore`, e **un
worktree nuovo nasce senza**.

I mandati **B, D, E, F, G, J** eseguono `lint`, `svelte-check`, Vitest o Playwright:
senza, **non possono chiudere la propria definizione di finito**. I mandati **A, C, H,
N** non ne hanno bisogno, e **I** non avvia nemmeno un server.

> ## 🔑 Lo installa il **coordinatore**, una volta per worktree frontend.
>
> `npm ci` dal lock esistente, **uno per volta**, mai `install`, mai `update`, mai
> `audit fix`. Il figlio non lo esegue: se manca, **riporta l'errore esatto**.

Il costo va dichiarato invece che scoperto: sei worktree frontend sono ~**3,8 GB**, su
un disco misurato al **90%** con 42 GiB liberi. Sostenibile, ma non gratuito — e va
verificato **prima** di lanciare l'ondata 2.

⚠️ `dev.py mkdocs serve` usa la porta fissa `6042`, fuori dal modello di lane: il
mandato **I** valida con `build` e `check-links`, mai con `serve`.

---

## 2. Proprietà dei file — la regola che evita i conflitti

Il principio è uno solo:

> ## 🔑 Un file ha un solo scrittore.
> Chi ne ha bisogno e non lo possiede, **chiede**.

### 2.1 Superfici esclusive

| Superficie | Scrittore | Nota |
|---|---|---|
| `backend/app/services/risk/metrics.py` | **A** | 661 righe, cuore della migrazione |
| `backend/app/services/risk/signal_helpers.py` | **A** | M1 |
| `backend/test_scripts/test_services/test_risk_metrics*.py` | **A** | oracolo incluso |
| `backend/app/db/models.py` + migrazione Alembic | **B** | **una sola** migrazione per tutta la campagna |
| `frontend/src/lib/utils/assetTypes.ts` | **B** | vedi §2.3 |
| `backend/app/services/risk/scenario_catalog/built_in/**` | **B** | i due YAML da riscrivere |
| `backend/app/schemas/risk.py` → classi di **scope** | **C** | |
| `backend/app/schemas/risk.py` → classi di **output** VaR/drawdown | **A** | vedi §2.2 |
| `backend/app/schemas/risk.py` → `RiskKpiOutput`, `RiskContributionOutput` | **N** | vedi §2.2 |
| `backend/app/services/risk/acquired.py` (**nuovo**) | **N** | mai `metrics.py` |
| `risk_plugins/historical_kpi.py`, `risk_plugins/risk_contribution.py` | **N** | solo aggiunte additive |
| `frontend/src/lib/components/ui/**` (primitive promosse) | **D** | |
| `frontend/src/lib/components/risk/**` | **E** | compreso sostituire `RiskAnalysisPanel` |
| `frontend/src/routes/(app)/assets/+page.svelte` | **F** | |
| `frontend/src/lib/components/risk/CorrelationHeatmap.svelte` | **F** | eccezione dichiarata dentro `risk/`, concordata con E |
| `frontend/src/lib/components/charts/AllocationPieChart.svelte` | **G** | |
| `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte` | **G** | |
| `frontend/src/lib/utils/colors.ts` | **G** | aggiunge `hexToHsl` |
| worker QuantLib + `risk_plugins/simulation.py` | **H** | |
| `mkdocs_src/**` e `mkdocs.yml` | **I** | |
| `CHANGELOG.md` | **J** | **nessun altro**, mai |

### 2.2 `schemas/risk.py` — tre scrittori, e dove collidono davvero

1 126 righe, e **tre** mandati devono toccarlo. Le regioni sono state **misurate**, non
stimate:

| Regione | Scrittore | Righe |
|---|---|---|
| `RiskScopeKind` | — | `:46` |
| Classi di **scope** | **C** | `:537-585` |
| `RiskKpiOutput` — famiglia scalare di L1 | **N** | `:640-647` |
| `RiskContributionOutput` — concentrazione L2 | **N** | `:676-680` |
| `RiskVarCvarOutput` — bin dell'istogramma | **A** | `:820-835` |
| `RiskDrawdownOutput` — serie underwater | **A** | `:945-1018` |
| **`__all__`** | 🔴 **tutti e tre** | **`:1067-1126`** |

Le regioni di classe sono **lontane**: N sta fra `:640` e `:680`, A fra `:820` e
`:1018`, C fra `:537` e `:585`. Nessuna confina con un'altra, quindi Git fonde senza
attrito.

> ## 🔑 Il conflitto vero è `__all__`, non le classi.
>
> Il file **finisce** con una lista `__all__` di sessanta nomi **ordinata
> alfabeticamente**. Chi aggiunge una classe deve inserire un nome **in mezzo** a quella
> lista, quindi tre scrittori si ritrovano nello stesso blocco.
>
> Appendere in coda al file — di solito il pattern multi-scrittore più sicuro — **qui
> non funziona**, perché in coda c'è `__all__`.

**Regola di risoluzione**, e vale **solo** qui:

> `__all__` è **l'unica regione dell'intera campagna** dove una risoluzione meccanica
> del conflitto è autorizzata: **unione dei nomi + riordino alfabetico**. È
> semanticamente sempre corretta, perché è una lista ordinata di nomi esportati e
> nessuno dei tre ne rimuove uno.

**Ma il testo che si fonde non è la semantica che regge.** Ovunque altro vale la regola
opposta: mai «ours», mai «theirs», mai un merge meccanico. E la regola operativa resta:
nessuno dei tre riformatta il file, nessuno riordina gli import, nessuno tocca una
classe che non gli appartiene. Chi la viola produce un conflitto che Git risolve male
proprio perché sembra facile.

### 2.3 `assetTypes.ts` — scrittore unico per scelta

124 righe che **B** e **G** vorrebbero entrambi: B per `PNG_MAP` e le pastiglie
(**D52**), G per la mappa sottotipo → primario (**D71**).

**Assegnato interamente a B**, e non per comodità: quella mappa *è* tassonomia, e la
tassonomia è il mandato di B. G la **consuma**, non la scrive. Così sparisce l'unico
conflitto frontend davvero pericoloso, e il contratto fra i due si riduce a una firma
di funzione (§4).

### 2.4 Le quattro lingue — misurato, non temuto

`frontend/src/lib/i18n/{en,it,fr,es}.json`, **3 416 righe ciascuno**, toccati da B
(etichette dei tipi), E (stringhe dei quattro livelli), F (laboratorio), G (nulla),
H (modalità di simulazione).

Sembra la superficie condivisa peggiore. **Misurate le posizioni, non lo è**:

| Namespace | Righe in `en.json` | Chi scrive |
|---|---|---|
| `assets` | 70-360 | **B** |
| `dashboard` | 1 316-1 458 | E |
| `risk` | 2 889-3 125 | **E**, F, H |

I blocchi sono **contigui e distanti**: B scrive intorno a riga 200, E intorno a
2 900. Git non ha nulla da fondere. Le due regole che lo mantengono vero:

1. si scrive **solo dentro il proprio namespace**, mai una chiave fuori;
2. **non si riordina e non si riformatta** il file, mai, per nessun motivo.

Dentro `risk` convivono tre mandati: E possiede il namespace e apre i sotto-blocchi
`risk.simulation.*` per H e `risk.lab.*` per F, che scrivono solo lì dentro.

### 2.5 Il catalogo dei test

`scripts/test_runner/_backend_services.py` riceve almeno un selettore nuovo da **A**
(`risk-oracle`) e forse uno da **H** o da **N**. Scrittore: **A**. Gli altri chiedono, A
registra.

### 2.6 `risk_plugins/` — un solo scrittore, ed è N

⚠️ **Va detto chiaro perché tre mandati lo dichiarano «fuori»**: A, C e G escludono
tutti `risk_plugins/` dai propri confini, e questo potrebbe far credere che nessuno lo
tocchi. Non è vero: **N** aggiunge campi additivi a `historical_kpi.py` e
`risk_contribution.py`.

Conseguenza pratica per chi verifica: la definizione di finito di **C** chiede che
`git diff` su `risk_plugins/` sia **vuoto**, e resta corretta — C lavora nel proprio
worktree e non tocca alcun plugin. Ma **dopo l'integrazione** quella cartella *avrà* le
modifiche di N. Chi verifica in **J** deve saperlo, o scambierà un lavoro previsto per
una violazione.

L'unica eccezione storica resta il doppio ciclo di `correlation.py:72`, che è di **A**
per ragioni di migrazione (M3).

### 2.7 ⚠️ Gli spec di test hanno proprietari, e uno va diviso prima di cominciare

**Il buco che la prima stesura aveva lasciato**: i file *sorgente* erano mappati, i file
di *test* no. Ma un difetto sugli spec produce lo stesso conflitto — con l'aggravante
che due agenti lo scoprono quando entrambi hanno già scritto.

| Spec | Righe | Chi lo tocca | Esito |
|---|---:|---|---|
| `e2e/portfolio/risk-analysis.spec.ts` | **817** | **E** *e* **F** | 🔴 va **diviso** — vedi sotto |
| `e2e/portfolio/dashboard.spec.ts` | 210 | **G** (grafici) · **E** (punto di montaggio) · **D** (solo non regressione) | 🟠 coordinare |
| `e2e/assets/asset-list.spec.ts` | 692 | **B** (filtro tipi) · **F** (colonne di rischio) | 🟠 coordinare |
| `e2e/assets/asset-modal.spec.ts` | 640 | **B** | ✅ scrittore unico |
| `src/lib/stores/risk/riskStore.test.ts` | — | **E** | ✅ scrittore unico |
| `e2e/gallery.spec.ts` | — | nessuno **scrive**, ma **G** lo invalida | ⚠️ vedi §2.8 |

#### `risk-analysis.spec.ts` — perché non basta «coordinarsi»

817 righe, **un solo `test.describe`**, e la struttura spiega il problema:

```text
:140-579   ~580 righe di impalcatura condivisa
           installRiskMocks · resultFor · definition · metadata
           openDashboardRisk · openFirstBrokerRisk · brokerWithHoldings
:587       dashboard renders base analytics…              → E
:619       per-analytic unavailable state…                → E
:628       asset global maps broker holdings…             → F
:687       broker tab sends a single-broker subset…       → E
:698       asset detail preserves Overview…               → 🚫 nessuno: Asset Detail è parcheggiato
:719       asset Risk runs typed scenarios…               → 🚫 nessuno: idem
```

Due dei sei test coprono **Asset Detail**, che è fuori ambito per **D8** e **D47**:
non vanno riscritti, vanno **tenuti verdi**. Sono la rete che dimostra che E ed F non
hanno rotto la pagina che hanno promesso di non toccare.

> ## 🔑 Lo divide **D**, prima che E ed F comincino.
>
> | File | Contenuto | Proprietario |
> |---|---|---|
> | `portfolio/risk-mocks.ts` | l'impalcatura condivisa (~580 righe) | **E** scrive, **F** consuma |
> | `portfolio/risk-analysis.spec.ts` | i tre test di portafoglio | **E** |
> | `portfolio/risk-lab.spec.ts` | il test di Asset Global | **F** |
> | `portfolio/risk-asset-detail.spec.ts` | i due test parcheggiati | 🚫 **nessuno li riscrive** |
>
> Perché D: è il mandato che **esiste per preparare il terreno a E ed F** ed è l'unico
> che gira prima di entrambi. La divisione entra nel contratto **K5**.

I selettori nuovi vanno registrati nel catalogo (`_frontend_portfolio.py`), dove oggi
`portfolio risk` punta al file unico.

### 2.8 ⚠️ L'effetto che nessuno vede: la galleria

`e2e/gallery.spec.ts:605` genera *«dashboard allocation charts — all languages and
themes»*, cioè gli screenshot della documentazione.

Il mandato **G** cambia i colori di quei due grafici. Quindi **G invalida degli
screenshot che non possiede e che non sa di toccare**, e la documentazione resta con
immagini che mostrano una tavolozza che il prodotto non usa più.

Non è un conflitto — nessuno scrive lo stesso file — è una **dipendenza invisibile**.
Va rigenerata a valle: la rigenerazione appartiene a **J**, dopo che G è integrato,
perché prima produrrebbe immagini di uno stato intermedio.

---

## 3. Ordine di lancio

```text
ondata 1  — subito, in parallelo:      A   B   D   H   I
ondata 1.5 — analisi di ondata 1 firmate:   C   N
ondata 2  — appena D consegna K5:      E   F
            appena B consegna K2:      G
ondata 3  — a catena completa:         J
```

Gli innesti non sono ondate: E **costruisce lasciando il posto** e collega K1 (A), K4
(C), K6 (H), K7 (I) e K8 (N) quando arrivano, senza aspettarli.

| # | Lancio | Perché non prima |
|---|---|---|
| 1 | **A, B, D, H, I** | Nessuna dipendenza in ingresso, e sono esattamente i mandati **il cui ritardo si propaga**: A è il gate di W1 e consegna K1; B consegna K2 e K3; D **blocca E ed F**; H è un XL che non blocca nessuno e quindi diventa il percorso critico se parte tardi; I deve consegnare i mock d'indice prima che E scriva un `DocsLink` |
| 2 | **C, N** | Nessuna dipendenza tecnica: potrebbero partire col gruppo 1. Messi dopo per una ragione che non è la macchina — vedi §3.1 |
| 3 | **E, F** | Aspettano **D** ([`07`](../07-piano-esecutivo.md) §3): costruire sopra le primitive vecchie riprodurrebbe i difetti in disposizione nuova |
| 4 | **G** | Aspetta **B**: senza sottotipi nell'enum non c'è nulla da sfumare |
| 5 | **J** | Aspetta tutti: si rilascia a catena completa (**D46**) |

### 3.1 Il vincolo che decide la dimensione di un'ondata non è la macchina

Verificato: le porte della banda 6240 sono **libere**, e i data dir sono
**worktree-locali** (§1.3). Dieci backend simultanei girerebbero.

> ## 🔑 Il collo di bottiglia è il **cancello analisi-prima**.
>
> Ogni figlio consegna un'analisi che il **developer** deve firmare prima che scriva
> codice. Cinque analisi da revisionare insieme sono già molte; dieci sono una coda che
> annulla il vantaggio di averli lanciati tutti.

Per questo l'ondata 1 contiene **cinque** mandati, scelti con un criterio esplicito —
*chi blocca qualcuno, o è XL* — e non «i primi cinque dell'alfabeto».

**H e I andrebbero lanciati per primi** anche se sembrano secondari. H è un XL che non
aspetta nessuno e non blocca nessuno: se parte tardi diventa lui il percorso critico. I
deve produrre i mock d'indice **all'inizio** (**D55**), o E si ritrova a scrivere link
verso pagine che non esistono.

---

## 4. I contratti fra mandati

Un contratto è ciò che un mandato promette a un altro **prima** di averlo costruito,
così che il secondo possa lavorare contro una firma invece che aspettare.

| # | Da | A | Contratto |
|---|---|---|---|
| **K1** | A | E | I due campi di output: serie underwater (**D14**) e bin dell'istogramma (**D21**). Nome, tipo e unità concordati **prima** di scrivere il codice |
| **K2** | B | G | `primaryAssetType(type: string): string` esportata da `assetTypes.ts`, **mappa esplicita** mai divisione su `_` (Q12) |
| **K3** | B | E, F | Il selettore benchmark ordinato a sezioni (**D50**), con la sua firma |
| **K4** | C | E | Il campo di filtro su `PortfolioRiskScope` e la regola dei pesi rinormalizzati (**D59**) |
| **K5** | D | E, F | I nomi e le props delle primitive promosse in `components/ui/` |
| **K6** | H | E | La forma del selettore di modalità e del payload del cono |
| **K7** | I | E, F, H | Gli slug delle pagine di documentazione, per i `DocsLink` |
| **K8** | N | E | I campi nuovi su `RiskKpiOutput` e `RiskContributionOutput`: nomi, **convenzione di segno**, unità di NEA, se `WR` porta la data, e la convenzione sulla cassa. Più il vincolo che **NEA e diversification ratio si mostrano insieme** |

**Regola**: un contratto si concorda **per scritto tramite il coordinatore**, prima che
il consumatore inizi. Un contratto cambiato a metà strada è la cosa che questa
struttura esiste per rendere visibile.

### 4.1 ⚠️ Un contratto che vive solo in chat non esiste

I mandati girano in **worktree separati**: il file che A scrive nel suo worktree **non
è visibile a E**. Quindi un contratto non può essere consegnato «mettendolo in un file»
— e se resta solo dentro un messaggio fra sessioni, **sparisce al primo azzeramento di
contesto**, esattamente quando serve.

> ## 🔑 I contratti vivono in [`contracts/`](./contracts/), e sono del **coordinatore**.
>
> Il produttore **comunica** il contratto; il coordinatore lo **scrive** nel proprio
> worktree e lo **relaya** al consumatore. Un file per contratto, `K1.md` … `K8.md`.

È anche l'unico modo perché un contratto **cambiato** sia visibile: la differenza fra
la versione scritta e quella nuova è un diff, non un ricordo.

---

## 5. Cosa vale per ogni mandato, senza ripeterlo undici volte

Ogni file di mandato dà per noti questi vincoli. Sono le regole del progetto, non
invenzioni di questo piano.

### 5.1 Git

> **Mai** `git commit`, `git push`, `git merge`, `git rebase`, `git reset`,
> `git cherry-pick`, cancellazione o forzatura di branch.
>
> Consentiti: comandi Git in sola lettura. `git add` **solo** per una risoluzione di
> conflitto richiesta esplicitamente dal coordinatore.

I messaggi di commit si **propongono**, non si eseguono. Il developer committa a mano.

### 5.2 Runtime

- Solo la lane assegnata in §1.2, e mai due comandi in parallelo dentro la stessa lane.
- Mai `server --force`, mai uccidere un processo in ascolto.
- Mai `./dev.py` nudo: sempre `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py`.
- Mai `pipenv install`, `npm install`, `npm update`, `npm audit fix`, `./dev.py install`.
  Se manca una dipendenza si **riporta l'errore esatto**, non si installa.
  ⚠️ `node_modules` è l'eccezione **già prevista e già autorizzata**, e la installa il
  coordinatore: vedi §1.4. Trovarlo assente **non è un guasto**.
- A fine lavoro, provare che la porta è libera:
  ```bash
  lsof -nP -iTCP:<PORTA> -sTCP:LISTEN
  ```

### 5.3 Dopo aver modificato…

| Se tocchi | Devi |
|---|---|
| uno schema o una rotta API | `./dev.py api sync` — rigenera il client TypeScript |
| un modello DB | una migrazione Alembic **incrementale** (mai `001_initial.py`) |
| una stringa UI | tutte e quattro le lingue, dentro il proprio namespace |

### 5.4 Test

L'agente `test-author` scrive i test; il mandato gli passa la lane e i file consentiti.
Vale la regola del progetto: nel medesimo runtime ogni test condivide un database e un
backend con i vicini, quindi **niente posizioni fisse, niente conteggi globali, niente
attese sull'orologio, niente selettori su testo tradotto**.

Prima di dichiarare «flaky» un rosso, si usa `test-triage`.

### 5.5 Il piano vive — ma **non** sopra il mandato

> ## ⚠️ Il file di mandato è un **brief in sola lettura**. Non si spunta, non si modifica.
>
> Contiene le istruzioni dell'agente ed è **l'unica copia** che l'agente ha di esse.
> Spuntarci sopra i passi le distrugge, e le distrugge proprio nel momento in cui
> servirebbero di più: dopo un azzeramento di contesto.

Il piano vivo è un **file nuovo**, che l'agente crea al primo passo:

```text
implementation/progress/<LETTERA>-esecuzione.md
```

Si aggiorna **dopo ogni passo**, non alla fine: passo spuntato con data, una riga
`Note implementazione`, e una riga `Fuori pista` per ogni deviazione — comando fallito,
problema d'ambiente, rischio scoperto. È il punto di ripristino se il contesto si
azzera.

Indice e convenzioni in [`progress/README.md`](./progress/README.md).

### 5.6 Cosa non si mette mai in un checkpoint

Database, upload, report broker, log, cache, `.testLog`, risultati Playwright, file di
coverage, `node_modules`, output di build, `.svelte-kit`, client API e codec generati,
CSV privati, valori finanziari reali.

---

## 6. La definizione di finito, comune

Un mandato è finito quando **tutte** queste sono vere. Non alcune.

1. Il cancello scritto nella sua scheda di [`07`](../07-piano-esecutivo.md) §8 è
   soddisfatto, e l'evidenza è nel piano.
2. I selettori di test più piccoli che coprono il cambiamento sono verdi, con il
   comando esatto registrato.
3. Il gate di integrazione del suo dominio è verde (`services risk-all` per il backend,
   lint + type-check + gli spec toccati per il frontend).
4. Nessun server resta in ascolto sulla sua porta.
5. I contratti promessi in §4 sono consegnati e comunicati.
6. È proposto un messaggio di commit in forma Conventional Commit.
7. Lo stato dichiarato è `FROZEN`: nessuna altra modifica, nessun test, nessun server.

---

## 7. Indice dei mandati

| | Mandato | Dipende da | Consegna a |
|---|---|---|---|
| **A** | [Oracolo e migrazione matematica](./A-backend-oracolo-e-migrazione.md) | — | E (K1) |
| **B** | [Tassonomia e catalogo benchmark](./B-tassonomia-e-benchmark.md) | — | G (K2), E/F (K3) |
| **C** | [Affettamento del portafoglio](./C-backend-affettamento-portafoglio.md) | — | E (K4) |
| **D** | [Primitive e card del rischio](./D-frontend-primitive-e-card.md) | — | E/F (K5) |
| **E** | [I quattro livelli](./E-frontend-quattro-livelli.md) | D, + innesti A/C/H/I/N | J |
| **F** | [Il laboratorio](./F-frontend-laboratorio.md) | D | J |
| **G** | [Gerarchia cromatica](./G-frontend-colori-allocazione.md) | B | J |
| **H** | [Monte Carlo](./H-backend-montecarlo.md) | — | E (K6) |
| **I** | [Documentazione](./I-documentazione.md) | — | tutti (K7) |
| **N** | [Acquisizioni backend L1/L2](./N-backend-acquisizioni.md) | — | E (K8) |
| **J** | [Chiusura e rilascio](./J-chiusura-e-rilascio.md) | tutti | — |

### 7.1 Documenti del coordinatore

Non appartengono a nessun mandato e **nessun figlio li modifica**:

- questo `README.md` — lane, proprietà dei file, ordine, contratti;
- [`kickoff/`](./kickoff/) — i prompt di avvio delle sessioni e il cancello del commit;
- [`contracts/`](./contracts/) — i contratti K1-K8 materializzati (§4.1);
- [`progress/`](./progress/) — l'indice dei piani vivi; i singoli file dentro sono
  invece del rispettivo mandato (§5.5).
