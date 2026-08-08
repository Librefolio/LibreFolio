# P3 — Identità dell'asset: unificazione, identificativi, ciclo di vita

> **Sostituisce** `plan-phase00AssetLifecycleAndIdentifiers.prompt.md` (P3 originale, rilievi A1–A5).
>
> **Stato**: 🟢 **Onda 1 completata** (05/08/2026) — D‑01, D‑02, A‑01, A‑02, A‑03, B‑01, B‑04,
> C‑01, E‑01. ⏸️ **Onda 2 in attesa** che P1 committi la Fase A (vedi §4).
>
> **Ambito allargato** rispetto al P3 originale: oltre ad A1–A5, il piano prende in carico
> **l'identità dell'asset** nel suo complesso — unificazione degli asset tra report diversi,
> scelta dell'identificativo primario, e fusione dei duplicati già presenti in DB.

---

## 0. Il problema centrale — i titoli a doppio ISIN (BTP "CUM")

Alcuni titoli di Stato italiani a collocamento retail (BTP Valore, BTP Più, BTP Italia)
vivono con **due codici ISIN** distinti:

| Fase | ISIN | Caratteristiche |
|---|---|---|
| **Collocamento** ("CUM") | es. `IT0005634792` | Assegnato a chi sottoscrive all'emissione. Dà diritto al **premio fedeltà** se detenuto fino a scadenza. **Non negoziabile** sul mercato → nessuna quotazione, nessun provider lo indicizza |
| **Mercato** ("EX") | ISIN diverso | Liberamente scambiabile e **quotato**. È l'unico su cui esiste un prezzo, perché il prezzo *è* il valore dell'ultima compravendita |

Per vendere prima della scadenza il titolo va "trasformato" nell'ISIN di mercato.

### Il modello LibreFolio (decisione dell'utente)

- **Un solo Asset.** I due ISIN sono lo stesso strumento in due fasi della sua vita.
- **`identifier_isin` = l'ISIN di mercato** — è l'unico indicizzabile, ed è quello che il
  provider di prezzo restituisce.
- **L'ISIN CUM va in `identifier_other`** — così ogni reimport che lo cita ritrova l'asset.
- **Il premio fedeltà** è una transazione `INTEREST` legata all'asset, alla data di pagamento.

Il costo sul lato prezzi è **zero**: `AssetProviderAssignment` è 1‑a‑1 con l'asset e porta il
proprio `identifier` (`backend/app/db/models.py:962-978`), completamente separato da
`Asset.identifier_isin`. La scelta del primario è quindi una decisione di *identità*, non di
*pricing*.

### Perché è stato il problema più grosso del beta test

Il tester ha incontrato, sullo stesso titolo, **quattro ostacoli in fila**:

1. Il report cita l'ISIN CUM, il provider quello di mercato → la ricerca candidati non li
   collega, perché il match su `identifier_other` gira solo **come ultima spiaggia**, dopo un
   match per nome che può restituire candidati spuri e bloccarlo
   (`backend/app/services/brim_provider.py:1166-1188`).
2. La modale offre solo *"sostituisci"* o *"solo assegna"* → l'unico modo di tenere entrambi
   gli ISIN era **perdere** l'altro (`ImportWizardModal.svelte:3814-3862`).
3. Digitando l'ISIN CUM nel selettore asset non si trova nulla, perché
   `AssetSelect.searchText` **non include `identifier_other`** (`AssetSelect.svelte:72`).
4. A titolo scaduto e disattivato, l'asset **non è selezionabile**
   (`AssetSelect.svelte:73` → `SearchSelect.svelte:241`) → l'unica via d'uscita è creare un
   asset duplicato.

Ognuno dei quattro, da solo, è un fastidio. In fila costringono a sporcare il database.

### Il quinto ostacolo, emerso in analisi

Lo stesso titolo compare in **file diversi con identificativi diversi**: il layout
*Deposito Titoli* di Crédit Agricole produce il titolo **senza** ISIN, il layout *Movimenti
Conto* **con** ISIN (rilievo W2). Oggi arrivano allo step di revisione come **due asset
distinti** da risolvere due volte. È lo stesso problema di identità, un livello più a monte:
prima di chiedere all'utente *"a quale asset del DB corrisponde?"* bisogna sapere *"quanti
asset diversi ci sono davvero nei report?"*.

---

## 1. Decisioni di progetto

| # | Decisione | Motivazione |
|---|---|---|
| **D1** | `identifier_other` resta il **contenitore generico**. Nessun campo tipizzato nuovo (`identifier_isin_alt` e simili) | *"Oggi è ISIN, domani ticker e poi chissà"* — la lista soft esiste apposta ed è già additiva, normalizzata e cercabile |
| **D2** | Quando due identificativi **dello stesso tipo strutturato** entrano in conflitto, l'utente **sceglie il primario**; gli altri scendono in `other`. Mai una sostituzione distruttiva silenziosa | È il gesto che risolve il caso CUM/EX in un click, ed è generico per qualunque tipo futuro |
| **D3** | La provenienza di ogni valore è **sempre visibile**: «dal provider» vs «dal report» | Senza l'origine l'utente non ha modo di decidere quale sia il primario |
| **D4** | Asset inattivi **selezionabili ovunque**, marcati con badge e ordinati in fondo | Serve anche fuori dall'import: cedola finale, rimborso e premio fedeltà di un BTP scaduto si inseriscono a mano |
| **D5** | **Nuovo Step 4 «Unifica asset»**; *Review & Import* diventa **Step 5**. Lo step si auto-salta quando non c'è nulla da decidere | L'identità dell'asset è un lavoro distinto dalla risoluzione e va **prima**: il gruppo unificato è ciò che deve guidare la ricerca candidati |
| **D6** | Grammatica visiva a tre stati: **bordo pieno** = gruppo confermato (automatico, segnale forte) · **bordo tratteggiato** = gruppo proposto (Conferma/Separa, segnale debole) · **chip nudo** = singolo. Archi SVG **solo dentro i riquadri** | Non lascia mai separato ciò che è correlato → gli archi collegano solo elementi già adiacenti, niente incroci |
| **D7** | Superficie DOM (chip trascinabili + overlay SVG), **non** canvas ECharts | La serie `graph` di ECharts disegna su canvas: niente nodi DOM, niente `data-testid`, e il drag sposta la posizione del layout, non l'appartenenza al gruppo → incompatibile con le regole E2E del progetto |
| **D8** | Similarità **token-aware**: differenze su token **numerici** (date, tassi) = segnale **negativo forte**; differenze su token **alfabetici di coda** (`CUM`, `EX`, `ACC`, `DIST`, classi) = neutre | Discrimina `BTP 1/3/32` da `BTP 1/3/35` (mai proporre) senza perdere `… CUM` ↔ `…` (proporre) |
| **D9** | La fusione dei duplicati **già in DB** entra in P3 | A1 ferma l'emorragia, ma i duplicati creati dal tester restano; senza merge il debito è permanente |
| **D10** | La fusione ha **due stadi distinti e ordinati**: prima fra gli asset *dell'import*, poi fra il gruppo risultante e gli asset *già in DB*. La scelta del **primario** appartiene **solo al secondo stadio** | Precisazione del committente (07/08/2026). Nel primo stadio non c'è nulla da eleggere: si sta solo dicendo «queste righe sono lo stesso titolo». L'identità contesa nasce quando il gruppo incontra un asset che ha già i propri identificativi |

### I due stadi della fusione (D10)

```
                    ┌─────────── STADIO 1 ───────────┐   ┌────────── STADIO 2 ──────────┐
                    │  import ↔ import               │   │  gruppo ↔ asset in DB        │
                    │  «sono lo stesso titolo?»      │   │  «è questo, in archivio?»    │
                    └────────────────────────────────┘   └──────────────────────────────┘

  file A ─ BTP … CUM   ┐
                       ├──▶  gruppo {IT…792, IT…8xx}  ──▶  asset #42  ──▶  primario: IT…8xx
  file B ─ BTP …       ┘            ▲                            ▲              other: IT…792
                                    │                            │                    ▲
                              Step 4 · WS‑C                B‑02 / B‑03          IdentifierPrimaryChooser
                           similarità + gruppi          ricerca candidati              (WS‑B)
                          NESSUNA elezione qui           su TUTTI gli ISIN        elezione SOLO qui
```

**Cosa cambia in pratica**, e perché l'ordine non è invertibile:

1. **Stadio 1 non elegge nulla.** Un gruppo porta con sé *tutti* gli identificativi dei suoi membri
   (`extractedIsins: string[]`, C‑02). Non serve decidere quale comandi: nessuno dei due è ancora
   confrontato con l'archivio.
2. **Lo stadio 1 alimenta la ricerca dello stadio 2.** È il motivo per cui deve venire prima: la
   ricerca candidati gira sull'**unione** degli ISIN del gruppo, non su quello del primo file
   incontrato. Con l'ordine invertito, un gruppo CUM+quotato cercherebbe con un solo ISIN e
   troverebbe — o peggio, *creerebbe* — l'asset sbagliato.
3. **L'elezione del primario è un evento di stadio 2**, e ha tre inneschi (WS‑B): assegnazione a un
   asset esistente (B‑02), creazione di un asset nuovo da un gruppo con più ISIN (B‑03), conflitto
   col provider dentro `AssetModal` (B‑04). In tutti e tre vale la stessa regola: **uno primario,
   gli altri in `other`, nessuno scartato**.
4. **La fusione di due asset già in DB (WS‑E) è uno stadio 2 fuori dall'import** — stessa domanda,
   stesso componente, stessa regola. Per questo riusa `IdentifierPrimaryChooser` invece di avere
   una logica propria.

> **Invariante**: `identifier_isin` contiene **sempre e solo** l'ISIN quotato — l'unico su cui un
> provider possa restituire un prezzo. Tutto il resto vive in `identifier_other`, dove non serve a
> quotare ma a **riconoscere**. È la ragione per cui A‑01 (match su `other` a priorità `HIGH`) e
> D‑02 (ricerca dentro `other`) sono i due pilastri della prevenzione.

---

## 2. Confini con gli altri piani

| Piano | Cosa resta suo | Punto di contatto |
|---|---|---|
| **P1** — plugin Crédit Agricole *(in corso, altro agente)* | Estrazione di ISIN/nominale/ritenute dalle righe, `field_todos`, warning | P3 **consuma** ciò che il parser emette; nessun file in comune. Da P1 può arrivare la causale del **premio fedeltà** (`CEDOLE, DIVIDENDI, PREMI ESTRATTI`) → in LibreFolio è un `INTEREST` con `asset_id` |
| **P2** — wizard di import | Conteggi (W1), riepilogo (W3), copy/i18n (W4, W5), auto-selezione (W7), livello INFO (W8), parallelismo (W9, W10), **pannelli duplicati per broker** | **W2** (merge asset tra file) **passa a P3**: è identità, non conteggio. **W6** (Annulla → `clearResolution`) viene assorbito da P3 perché la modale che lo contiene viene riscritta → in P2 resta solo come verifica |
| **P4/P5/P6** | Nessun contatto | — |

> ⚠️ **Nota di coordinamento**: P3 riscrive `identifierPrompt*` in `ImportWizardModal.svelte`.
> Se P2 partisse in parallelo su W6, i due lavori collidono sullo stesso blocco. W6 va marcato
> come *"assorbito da P3"* nell'INDEX prima di iniziare.

---

## 2‑bis. Convivenza con l'agente P1 (in corso, stessa working tree)

> **Contesto verificato**: nessun worktree separato — P1 e P3 scrivono nella **stessa cartella**
> `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio`, ramo `dev_release2`. P1 ha la **Fase A consegnata
> ma non committata** e la **Fase B ferma al checkpoint UI**.

### File con modifiche non committate di P1

```
 M backend/app/schemas/brim.py
 M backend/app/services/brim_providers/broker_credit_agricole.py
 M backend/test_scripts/test_external/test_brim_providers.py
 M frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte   ← unico contatto
 M frontend/src/lib/components/transactions/modals/ParseDetailModal.svelte
 M frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte
 M frontend/src/lib/i18n/{en,it,fr,es}.json
 M frontend/src/lib/types/files.ts
 M frontend/src/lib/utils/transactions/txPayloadHelpers.ts
?? frontend/src/lib/components/transactions/import/
```

### Matrice di collisione

| Risorsa | P1 | P3 | Rischio |
|---|---|---|---|
| `ImportWizardModal.svelte` | Fase A: **56 righe** su ~10 hunk (13, 50, 719, 1944‑1956, **3675‑3742**) | `AssetResolution` (255), prompt (585‑594, 905‑965, 3814‑3862), step (2030‑2078, 2870‑2915), template step 4 (3332‑3450), create (3750‑3792) | 🔴 **Stesso file, regioni disgiunte.** Nessuna riga in comune, ma numerazione già slittata di +16 e vista potenzialmente stantia |
| Struttura degli step | Checkpoint punto 5: *«pannello di revisione nello Step 3: serve davvero?»* ⏳ | Rinumera 4 → 5 step | 🔴 **Semantico**: se P1 aggiunge un pannello allo Step 3 mentre P3 rinumera, si litiga sullo stesso stepper |
| `i18n/{en,it,fr,es}.json` | Fase A: **3 chiavi** (5 righe/lingua). Fase B: altre | `assets.identifiers.primaryChooser.*`, `importWizard.assetUnify.*`, rimozione `addIdentifier.*` | 🟠 Sottoalberi disgiunti → fondibili, ma una **riscrittura integrale** del file perde il lavoro altrui |
| `api/generated.ts` | `./dev.py api sync` dopo `brim.py` (Fase B) | `./dev.py api sync` dopo l'endpoint di merge (A‑02) | ✅ **Nessuno — verificato.** `frontend/src/lib/api/generated.ts` e `openapi.json` sono **gitignored** (`frontend/.gitignore:12-13`): non compaiono in `git status`, quindi nessuna delle due parti può sovrascrivere lavoro dell'altra. `api sync` legge lo schema **dal codice** (nessun server), quindi rigenera sempre l'unione di ciò che è su disco. Eseguibile liberamente da entrambi |
| Runtime condiviso (DB di test, porte 6041/5173) | `./dev.py test external brim-providers` | `./dev.py test frontend`, `test backend` | 🟡 E2E simultanei → conflitto di porte e DB di test condiviso |
| `brim_provider.py` *(framework)* | — *(P1 tocca `brim_providers/broker_credit_agricole.py`, file diverso)* | A‑01 priorità candidati | ✅ Nessuno |
| `test_db/test_brim_db.py` | — *(P1 usa `test_external/test_brim_providers.py`)* | A‑01 test | ✅ Nessuno |
| `AssetSelect` · `SearchSelect` · `AssetModal` · `ProviderComparisonModal` | — | D‑01, D‑02, B‑04 | ✅ Nessuno |
| `api/v1/assets.py` · `asset_source.py` · `schemas/assets.py` | — | A‑02 | ✅ Nessuno |
| File nuovi (`assetSimilarity.ts`, `IdentifierPrimaryChooser.svelte`, modale di merge) | — | C‑01, B‑01, E‑01 | ✅ Nessuno |

### Regole operative

1. **Mai `git commit`, `stash`, `reset --hard`, `checkout -- …`, `rebase`.** Oltre alla regola di
   progetto, qui distruggerebbero il lavoro non committato di P1. Solo `status`/`diff`/`log`.
2. **Su file condivisi, solo modifiche chirurgiche** (sostituzione di stringa mirata). Mai
   riscrivere un file intero — è l'unico gesto che fa sparire il lavoro dell'altro agente.
3. **`./dev.py api sync` è libero** — `generated.ts` e `openapi.json` sono gitignored e
   rigenerati dal codice su disco, quindi non c'è nulla da sovrascrivere (§ matrice).
4. **Niente E2E o server in parallelo**: `./dev.py test frontend` occupa 6041/5173 e il DB di test.
5. **Rilettura prima di ogni modifica** ai file condivisi: le righe slittano.

---

## 3. Piano di lavoro

### WS‑A — Backend: identità e matching

#### A‑01 · Priorità del match su identificativo soft
`backend/app/services/brim_provider.py:1120-1195`

Oggi l'ordine è: ISIN esatto → ticker → **nome** → `identifier_other`. Il match su
`identifier_other` gira solo `if not candidates`, quindi **un match per nome vagamente
plausibile lo esclude**. Ma un ISIN salvato in `identifier_other` è un'asserzione *deliberata*
dell'utente: vale molto più di una somiglianza di nome.

Nuovo ordine:

| Priorità | Criterio | Confidenza |
|---|---|---|
| 1 | `identifier_isin` esatto | `EXACT` |
| 2 | ISIN presente in `identifier_other` | `HIGH` |
| 3 | `identifier_ticker` esatto | `MEDIUM` |
| 4 | nome (parziale, poi `display_name`) | `LOW` |
| 5 | nome presente in `identifier_other` | `LOW` |

Le priorità 1 e 2 girano **entrambe** e si uniscono (dedup per `asset_id`): se l'ISIN CUM è
primario su un asset duplicato e alternativo su quello buono, l'utente **vede tutti e due** e
può fondere. È il ponte con WS‑E.

> `BRIMMatchConfidence.HIGH` è già previsto dallo schema e già gestito dal frontend
> (`CONF_ORDER`, `ImportWizardModal.svelte:861`) — nessun cambio di contratto.

#### A‑02 · Endpoint di fusione asset
Nuovo: `POST /api/v1/assets/merge` — `{source_asset_id, target_asset_id}`.

Le referenze a `assets.id` sono **quattro**, tutte censite:

| Tabella | Riga | Vincolo | Politica di fusione |
|---|---|---|---|
| `Transaction.asset_id` | `models.py:610` | nullable, nessun unique | Riassegna al target |
| `PriceHistory.asset_id` | `models.py:734` | `uq_price_history_asset_date` | Riassegna; **in collisione (stessa data) vince il target**, la riga sorgente viene scartata |
| `AssetEvent.asset_id` | `models.py:779` | nessun unique *(volutamente, `models.py:766`)* | Riassegna; deduplica per `(date, type, amount)` e **rimappa `Transaction.asset_event_id`** sugli eventi scartati |
| `AssetProviderAssignment.asset_id` | `models.py:963` | `uq_asset_provider_asset_id` | Se il target ne ha già uno → elimina quello sorgente; altrimenti spostalo |

Inoltre: `identifier_other` del target = unione di *(other sorgente + other target + tutti gli
identificativi strutturati della sorgente che il target non ha come primari)* — nessun
identificativo va perso. Poi l'asset sorgente viene **eliminato**.

Nessuna referenza "morbida" (JSON/settings) esiste: verificato su `schemas/signals.py`,
`schemas/settings.py` e sui modelli. Operazione in **una sola transazione**; su conflitto di
`display_name` (`uq_assets_display_name`) non c'è problema perché la sorgente sparisce.

> Il target è **sempre** l'asset che l'utente vuole tenere. L'endpoint non sceglie da sé.

#### A‑03 · Test backend
`backend/test_scripts/` — priorità dei candidati (ISIN soft prima del nome), fusione con
collisione prezzi, fusione con evento condiviso e rimappatura di `asset_event_id`, fusione con
doppio provider assignment.

---

### WS‑B — Il selettore «primario vs alternativo»

> **Stadio 2** (D10). Tutto ciò che segue scatta **solo** quando un gruppo — o un asset — incontra
> un asset **già in archivio**. Nello stadio 1 non si elegge nulla.

Cuore della decisione **D2**. Un unico componente riusato in **tre** punti di innesco.

#### B‑01 · Componente condiviso `IdentifierPrimaryChooser.svelte`
Nuovo, in `frontend/src/lib/components/assets/`.

Riceve: il tipo di identificativo, i valori in gioco **con la loro origine**, e il nome
dell'asset. Restituisce quale valore è primario e quali finiscono in `other`.

```
┌──────────────────────────────────────────────────────────────┐
│  Quale ISIN è il principale per «Btp Piu' Sc Fb33 Eur»?      │
│                                                              │
│  ⦿  IT00056348xx    [dal provider]   ← preselezionato        │
│  ○  IT0005634792    [dal report]                             │
│                                                              │
│  Gli altri vanno negli identificativi alternativi e          │
│  serviranno a riconoscere l'asset nei prossimi import.       │
│                                                              │
│  ℹ️  I BTP italiani comprati all'emissione ("CUM") hanno un   │
│     ISIN diverso da quello negoziabile sul mercato: il       │
│     primo dà diritto al premio fedeltà ma non è quotato.     │
│     Tieni come principale quello **quotato** — è l'unico     │
│     su cui esiste un prezzo.                                 │
│                                                              │
│           [ Non salvare ]  [ Annulla ]  [ Conferma ]         │
└──────────────────────────────────────────────────────────────┘
```

- **Default**: primario = il valore **del provider** se presente (è quello quotato), altrimenti
  il valore già memorizzato sull'asset. Nel caso tipico bastano **due click** (apri → conferma).
- Regge **N valori**, non solo due: un gruppo unificato può portarne diversi.
- La nota BTP compare solo quando è pertinente (tipo ISIN, ≥ 2 valori) — non è un muro di testo
  permanente.
- Tutto DOM con `data-testid` per riga.

#### B‑02 · Innesco 1 — assegnazione nel wizard
`ImportWizardModal.svelte:905-965` + `3814-3862`

Sostituisce l'attuale modale a tre bottoni. Chiude in un colpo **quattro rilievi**:

| Rilievo | Come viene chiuso |
|---|---|
| **A2** — modale spuria se l'ISIN è già negli alternativi | Corto circuito prima di aprire: `if (info.identifier_other?.includes(res.extractedIsin)) return;` — idem per il ticker. **Non c'è nulla da decidere se è già noto** |
| **A3** — testo di conflitto senza conflitto | `identifierPromptIsConflict = existingValue !== null` (`:932`) è `true` anche con `identifier_isin === ""`. Normalizzare (`|| null`). Nel nuovo componente il problema svanisce: con un solo valore non c'è scelta da fare |
| **A4** — «aggiungi come alternativo» | È l'esito naturale del selettore: tutto ciò che non è primario **è** alternativo |
| **W6** — Annulla non riporta l'asset a neutro | Il bottone «Annulla» chiama `clearResolution(fakeAssetId)` (esiste già, `:823-825`) |

Al termine: PATCH con `identifier_isin` + `identifier_other` (unione lato client — il PATCH
**sostituisce** la lista, quindi va inviato l'insieme completo, come già fa
`reuseExistingForCreate` `:848-850`), poi `refreshAllAssets()` + `refreshCandidates()`.

#### B‑03 · Innesco 2 — creazione asset dal wizard
`ImportWizardModal.svelte:3750-3792` → `AssetModal`

Quando il gruppo unificato porta **più ISIN** (caso CUM/EX su due report), il prefill deve
proporre il selettore invece di scegliere da sé. Il primario va in `identifier_isin`, il resto
in `identifier_other` **insieme** ai nomi identificati già raccolti (`createNamesFor`, `:829`).

#### B‑04 · Innesco 3 — conflitto con il provider in `AssetModal`
`AssetModal.svelte:909-928` → `ProviderComparisonModal.svelte`

Oggi un ISIN diverso dal provider è un diff **binario**: tieni il tuo *oppure* prendi il suo
(`DiffItem.selected`, `ProviderComparisonModal.svelte:28-35`). Manca esattamente il terzo esito
— *tienili entrambi, scegli il primario*.

`DiffItem` prende un campo opzionale `resolution` valorizzato **solo** per i campi
`identifier_*`; le righe identificative rendono il selettore inline invece della spunta. Gli
altri campi (settore, area, descrizione) restano binari — nessuna regressione.

#### B‑05 · i18n
Chiavi nuove in `en/it/fr/es.json` sotto `assets.identifiers.primaryChooser.*`. Le chiavi
`importWizard.addIdentifier.*` obsolete vengono rimosse in tutte e quattro le lingue.
Verifica con `./dev.py i18n audit`.

---

### WS‑C — Nuovo Step 4 «Unifica asset»

> **Stadio 1** (D10): fusione **import ↔ import**. Qui si risponde a una sola domanda — *«queste
> righe, che vengono da file diversi, sono lo stesso titolo?»*. **Nessuna elezione di primario**:
> il gruppo raccoglie tutti gli identificativi dei membri e li porta interi allo stadio 2.

#### C‑01 · Motore di similarità
Nuovo modulo `frontend/src/lib/utils/assetSimilarity.ts` (puro, testabile a unità).

Normalizzazione: maiuscole, accenti, punteggiatura, spazi collassati; poi tokenizzazione con
distinzione fra token **numerici** (`25-2-33`, `1/3/32`, `1,65%`, `3,35`) e **alfabetici**.

| Segnale | Forza | Effetto |
|---|---|---|
| `identifier_isin` identico | **Forte** | Gruppo confermato (bordo pieno) |
| `identifier_ticker` identico | **Forte** | Gruppo confermato |
| Nome normalizzato identico | **Forte** | Gruppo confermato |
| Uno dei due **non ha ISIN**, nomi molto simili | Debole | Gruppo proposto — *è il caso W2 dei due layout CA* |
| ISIN **diversi**, differenza solo su token **alfabetici di coda** (`CUM`, `EX`, `ACC`, `DIST`…) | Debole | Gruppo proposto — *è il caso BTP CUM* |
| ISIN diversi, differenza su token **numerici** | **Negativo** | **Mai** proposto — `BTP 1/3/32` ≠ `BTP 1/3/35` |
| ISIN diversi, nomi lontani | Nessuno | Chip singoli |

> **D8 in una riga**: le date e i tassi *identificano* un'obbligazione, i suffissi alfabetici ne
> descrivono la *fase o la classe*. Trattarli allo stesso modo è l'errore da evitare.

#### C‑02 · Modello dati dei gruppi
Stato **locale del wizard** — nessuna tabella, nessuna migrazione. Il gruppo è un raggruppamento
di `fake_asset_id` provenienti da file diversi:

```ts
interface AssetGroup {
    groupId: string;
    members: Array<{fileId: string; fakeAssetId: number; name; isin; symbol}>;
    state: 'confirmed' | 'proposed' | 'single';
    links: Array<{from: number; to: number; reason: 'isin' | 'ticker' | 'name' | 'nameSuffix'; score: number}>;
    userTouched: boolean;   // l'utente ha deciso → nessun ricalcolo automatico sovrascrive
}
```

`AssetResolution` (`ImportWizardModal.svelte:255-265`) diventa **la proiezione di un gruppo**:
`extractedIsin: string | null` → `extractedIsins: string[]`, idem per simbolo e nome;
`sourceFiles` diventa l'elenco reale dei file che contengono il gruppo; `txCount` somma tutti i
membri. Risolvendo il gruppo, l'asset viene assegnato a **tutte** le transazioni dei membri.

#### C‑03 · UI — insiemi, chip, archi
- Riquadro **pieno** = confermato · **tratteggiato** = proposto (con `[Conferma] [Separa]`) ·
  chip nudo = singolo, nell'area «Singoli».
- Ogni chip: nome, badge identificativi, file di provenienza, menu `⋮`.
- Ogni gruppo: unione degli identificativi in intestazione + numero di transazioni + elenco file.
- **Archi**: overlay `<svg>` in posizione assoluta sopra il riquadro, tratteggiati, etichettati
  col motivo (*«nome ~94% · differisce solo per CUM»*). Solo **dentro** i riquadri → mai
  incroci. Ricalcolo su resize via `ResizeObserver`.
- Hover su un chip → i suoi archi si evidenziano.

#### C‑04 · Interazione
- **Drag & drop** HTML5 sul modello di `OrderableList.svelte:127-129` (precedente già in casa):
  chip su chip → nasce il gruppo; chip dentro un gruppo → entra; chip fuori → esce.
- **Fallback obbligatorio** via menu `⋮`: «Unisci con…» (elenco degli altri chip/gruppi) e
  «Estrai dal gruppo». È la strada per tastiera **e** per gli E2E — il DnD è un di più.
- Ogni gesto marca `userTouched = true`.

#### C‑05 · Innesto negli step
- `STEPS` passa da 4 a 5; `goNext()`/`goToStep()` (`:2030-2078`) aggiornati; il reset dello
  stato di risoluzione scatta ora a `target <= 3`.
- **Auto-skip** (D5): se ogni gruppo è `single` e non esiste alcun legame → lo step viene
  saltato in avanti automaticamente. Un import da file singolo **non guadagna nessun click**.
- Lo step resta raggiungibile all'indietro dallo stepper.

---

### WS‑D — Ciclo di vita dell'asset

#### D‑01 · A1 🔴 — asset inattivi selezionabili
`AssetSelect.svelte:73` · `SearchSelect.svelte:241`

Rimuovere `disabled: a.active === false`. L'inattivo resta **ordinato in fondo**
(`:65-68`, già così) e riceve un badge «inattivo» + testo attenuato.

`AssetSelect` è usato in soli **tre** punti — wizard step 4 (`:3393`) e `TransactionFormModal`
(`:1546`, `:1920`) — e in tutti e tre selezionare un titolo scaduto è legittimo: l'import è
retroattivo per natura, e cedola finale, rimborso e **premio fedeltà** si inseriscono a mano su
un titolo ormai disattivato. Nessuna prop nuova, nessun punto d'uso da adeguare.

> **Scelta di prodotto**: selezionare un asset inattivo **non lo riattiva**. Importare la storia
> di un titolo scaduto non deve farlo riapparire tra le posizioni correnti; la riattivazione
> resta un gesto esplicito nella `AssetModal`.

#### D‑02 · A6 ➕ — la ricerca non vede gli identificativi alternativi
`AssetSelect.svelte:72` *(scoperto in analisi, non nel report)*

```ts
searchText: [a.identifier_isin, a.identifier_ticker, a.currency, a.asset_type]  // ← manca identifier_other
```

Digitando l'ISIN CUM nel selettore **non si trova nulla**, pur essendo salvato. Con A2 che
sopprime la modale e A1 che sblocca la selezione, questo resterebbe l'ultimo ostacolo del
percorso CUM. `SignalAssetParamControl.svelte:27` include già `identifier_other`:
`AssetSelect` è l'unico fuori riga.

#### D‑03 · A5 ✨ — modifica asset dalle card dello step 5
Pulsante «modifica» su ogni card risolta → `AssetModal` in `editMode` sopra il wizard
(`zIndex + 40`), `onupdated` → `refreshAllAssets()` + `refreshCandidates()`.

Permette di sistemare gli identificativi **senza uscire dal wizard** — cioè senza perdere il
contesto di import, che è esattamente ciò che è costato tempo al tester.

---

### WS‑E — Fusione dei duplicati già in DB (D9)

> **Stadio 2 fuori dall'import** (D10): stessa domanda del wizard — *«quale identificativo
> comanda?»* — posta su due asset che sono **entrambi** già in archivio. Per questo riusa
> `IdentifierPrimaryChooser` invece di avere una logica propria.

#### E‑01 · UI di fusione ✅ *(Onda 1)*
Azione «Unisci con…» nella lista asset (`routes/(app)/assets/+page.svelte`) e nella pagina di
dettaglio. Modale in due tempi:

1. **Scegli il target** (l'asset da tenere) via `AssetSelect`.
2. **Anteprima** di ciò che verrà spostato: N transazioni, N prezzi, N eventi, provider
   assignment, e l'**unione risultante degli identificativi** — con il selettore di WS‑B per
   decidere i primari quando i due asset hanno ISIN o ticker diversi.

Conferma esplicita: l'operazione **elimina** l'asset sorgente.

#### E‑02 · Aggancio dal wizard
Quando A‑01 fa emergere **due candidati** per lo stesso identificativo (uno `EXACT`, uno
`HIGH`) è quasi sempre un duplicato: un avviso discreto sulla card offre «Unisci».
È il punto in cui l'utente li vede affiancati, quindi il punto in cui il gesto costa meno.

---

### WS‑F — Verifica

#### F‑01 · Percorso end-to-end del BTP CUM
Non un test astratto: **il caso reale del beta test**, dall'inizio alla fine.

| # | Scenario | Asserzione |
|---|---|---|
| 1 | Asset disattivato nell'elenco | è **selezionabile**, mostra il badge «inattivo», e **resta inattivo** dopo l'assegnazione |
| 2 | Ricerca per ISIN presente in `identifier_other` | l'asset **compare** nel selettore |
| 3 | ISIN già in `identifier_other` | la modale **non** compare |
| 4 | `identifier_isin === ""` | nessun testo di conflitto |
| 5 | Selettore primario: report vs provider | il primario va in `identifier_isin`, l'altro in `identifier_other`, **nulla si perde** |
| 6 | Reimport dopo il #5 | nessuna modale + candidato `HIGH` — *chiusura del ciclo A2 ↔ A4* |
| 7 | Due file, stesso titolo, uno con ISIN e uno senza | **un solo** gruppo proposto, **una sola** card allo step 5 (W2) |
| 8 | `BTP 1/3/32` e `BTP 1/3/35` nello stesso import | **mai** proposti insieme (D8) |
| 9 | Import da file singolo | lo Step 4 viene **saltato** |
| 10 | Fusione di due asset duplicati | transazioni, prezzi ed eventi migrano; identificativi uniti; sorgente eliminata |
| 11 | `INTEREST` (premio fedeltà) su asset a posizione zero | l'importo risulta nel reddito dell'asset |

Lo scenario 11 verifica anche l'ipotesi alternativa su **X2** (*"anche export AI è disattivo"*):
il sospetto in analisi è che l'asset sparisse per **posizione zero**, non perché disattivato
(`runtime_service.py:586` non filtra su `Asset.active`). Il premio fedeltà è per definizione un
incasso a posizione zero → è il banco di prova naturale. Se lo scenario passa, X2 va cercato
altrove; se fallisce, X2 è spiegato.

#### F‑02 · Documentazione
`mkdocs_src/docs/user/assets/create-edit.*.md` — sezione «identificativi alternativi» con la
ricetta dei BTP CUM (quale ISIN tenere primario e perché, dove finisce l'altro, come si modella
il premio fedeltà). In 4 lingue.

#### F‑03 · Comandi
```bash
./dev.py front check                     # lint + format + svelte-check
./dev.py test backend --filter brim      # A-01, A-03
./dev.py test backend --filter asset     # A-02
./dev.py test frontend --filter import   # F-01
./dev.py i18n audit                      # B-05
./dev.py api sync                        # dopo A-02 (endpoint nuovo)
```

---

## 4. Ordine di esecuzione — due onde

L'ordine non è più solo tecnico: è **partizionato per convivenza con P1** (§2‑bis).

### 🟢 Onda 1 — parallela a P1, zero contatti — ✅ **COMPLETATA**

Nessuno di questi tocca `ImportWizardModal.svelte` né la struttura degli step.

```
D-01 ✅ ──▶ D-02 ✅       AssetSelect.svelte · SearchSelect.svelte
  «ferma l'emorragia di duplicati» — piccoli, indipendenti, urgenti

A-01 ✅ ──▶ A-03 ✅       brim_provider.py · test_db/test_brim_db.py
  priorità del match su identificativo soft

B-01 ✅ ──▶ B-04 ✅       IdentifierPrimaryChooser.svelte (nuovo)
  componente          ──▶ AssetModal.svelte · ProviderComparisonModal.svelte

C-01 ✅                   assetSimilarity.ts (nuovo, puro, testabile a unità)

A-02 ✅ ──▶ E-01 ✅       api/v1/assets.py · schemas/assets.py · asset_source.py
  endpoint di merge   ──▶ routes/(app)/assets/ + AssetMergeModal.svelte
                          `api sync` eseguito (gitignored → nessun rischio)
```

> **Esito Onda 1** — 9/9 punti chiusi e verificati:
>
> | Verifica | Esito |
> |---|---|
> | `./dev.py test db asset-merge` | **12 passed** |
> | `./dev.py test db brim` | **15 passed** |
> | `vitest assetSimilarity.test.ts` | **27 passed** |
> | `npm run check` (svelte-check) | **0 errori** sui file P3 |
> | `ruff` + `black --line-length 300` | pulito |
> | Chiavi i18n di P1 | intatte in en/it/fr/es |
>
> **Trappole trovate e chiuse durante l'implementazione** (documentate nei test):
> 1. `IdentifierType.OTHER` → `identifier_other`, che è la **lista JSON**, non una colonna
>    stringa: qualunque codice che enumera le colonne identificative deve escluderla.
> 2. `AssetEvent.provider_assignment_id` è `ondelete=CASCADE` → eliminare il provider
>    assignment della sorgente **distruggeva silenziosamente** gli eventi appena migrati.
>    Gli eventi vanno ripuntati **prima** della delete (test AM‑009).
> 3. `Transaction.asset_event_id` è `ondelete=RESTRICT` → gli eventi duplicati non si possono
>    scartare finché le transazioni non sono rimappate (test AM‑006).
> 4. `openapi-zod-client` **non fa l'escape delle virgolette** nelle description → mai mettere
>    `"` in un `Field(description=…)`, genera TypeScript sintatticamente invalido.

**D‑01 e D‑02 per primi**: sono piccoli, indipendenti, e ogni giorno che passa senza di loro il
database accumula asset doppi. Tutto il resto può attendere; questo no. E sono anche i due file
che P1 non tocca mai — quindi non c'è motivo di rimandarli.

**A‑01 prima di WS‑B**: il selettore ha senso solo se poi il match sull'identificativo salvato
funziona davvero — altrimenti l'utente fa la scelta giusta e al reimport non se ne accorge nessuno.

> **i18n nell'Onda 1**: D‑01 (badge «inattivo»), B‑01 e B‑04 hanno bisogno di chiavi. Vanno
> aggiunte **con `edit` chirurgico** nel sottoalbero `assets.*`, mai riscrivendo il file, e
> verificando con `git diff` che le chiavi di P1 siano ancora al loro posto.
>
> ✅ *Esito*: `./dev.py i18n audit` → **2377/2377 complete, 0 incomplete, 0 backend mancanti**.
> Restano segnalate come inutilizzate `assets.identifiers.primaryChooser.{confirm,cancel,skip}`:
> sono i bottoni della **modale autonoma** del wizard, che nasce in **B‑02** (Onda 2). Nei due
> innesti dell'Onda 1 il selettore è *inline* dentro modali che hanno già il proprio footer,
> quindi le tre chiavi non hanno ancora un chiamante. **Non rimuoverle** — B‑05 le riprende.

### 🔴 Onda 2 — richiede la serializzazione su `ImportWizardModal.svelte`

```
B-02 ──▶ B-03             prompt identificativi nel wizard (chiude A2, A3, A4, W6)
C-02 ──▶ C-03 ──▶ C-04 ──▶ C-05    Step 4 «Unifica asset» (chiude W2)
D-03                      A5 — modifica asset dalle card
B-05                      i18n, in un'unica passata finale
api sync                  generated.ts, un colpo solo
F-01 ──▶ F-02             E2E + documentazione
```

**Condizione di ingresso all'Onda 2** — una delle due:

- **(a) preferibile** — P1 committa la Fase A. Il file torna pulito e la Fase B lo tocca
  pochissimo (solo B5, e il piano lo colloca nel bulk modal, non nel wizard);
- **(b)** — P1 dichiara chiuso il checkpoint UI, in particolare il **punto 5** (*pannello di
  revisione nello Step 3*): finché è aperto, la struttura degli step è contesa e rinumerarla
  significa lavorare su fondamenta che possono muoversi.

---

## 5. Rischi e attenzioni

| Rischio | Mitigazione |
|---|---|
| **Collisione con P1 su `ImportWizardModal.svelte`** (stessa working tree, Fase A non committata) | Onda 1 non tocca il file. L'Onda 2 parte solo dopo commit della Fase A o chiusura del checkpoint UI (§2‑bis) |
| **Perdita del lavoro non committato di P1** | Nessun comando git che muta la storia o l'albero. Solo modifiche chirurgiche, mai riscritture integrali |
| Collisione con P2 su `identifierPrompt*` | W6 marcato «assorbito da P3» nell'INDEX prima di iniziare |
| Il nuovo step allunga il percorso per tutti | Auto-skip (C‑05): chi importa un file solo non vede alcuna differenza |
| Il DnD non è testabile a fondo in Playwright | Il menu `⋮` è la strada primaria per gli E2E; il DnD è un'aggiunta |
| Unione sbagliata → transazioni sull'asset sbagliato | Solo i segnali forti uniscono da soli; i deboli **propongono** e basta. `userTouched` impedisce che un ricalcolo sovrascriva una decisione dell'utente |
| La fusione è **distruttiva** | Anteprima obbligatoria di tutto ciò che si sposta + conferma esplicita; transazione unica lato DB |
| `AssetResolution` da singolo a plurale tocca molto codice | Cambiamento di tipo guidato dal compilatore: `svelte-check` elenca ogni punto da adeguare |

---

## 6. Punti aperti

- **X1** (*"non posso riportare attivo un asset disattivato dal modifica"*) resta **sospeso**:
  il toggle esiste ed è sempre renderizzato (`AssetModal.svelte:1860-1873`). Ipotesi da
  verificare per prima: è nel **footer** della modale e su viewport ridotti finisce fuori
  dall'area visibile — sarebbe un difetto reale, ma di layout, non di logica. Serve una
  riproduzione col tester.
- **Premio fedeltà lato plugin**: il riconoscimento della causale nel report Crédit Agricole
  appartiene a P1. P3 garantisce che, una volta prodotta, la transazione `INTEREST` si agganci
  all'asset giusto anche se scaduto e disattivato (D‑01) e a posizione zero (F‑01 #11).
- **Da chiedere all'agente P1** (nessuna sessione app disponibile per messaggiarlo → passa
  dall'utente):
  1. La **Fase A può essere committata** prima che P3 tocchi `ImportWizardModal.svelte`?
  2. Il **punto 5 del checkpoint** (pannello di revisione nello Step 3) è confermato o scartato?
     Da questo dipende se P3 rinumera gli step su fondamenta stabili.
  3. **B5** (*suddivisione in più transazioni*) atterra solo in `TransactionBulkModal.svelte`
     o anche nel wizard?
