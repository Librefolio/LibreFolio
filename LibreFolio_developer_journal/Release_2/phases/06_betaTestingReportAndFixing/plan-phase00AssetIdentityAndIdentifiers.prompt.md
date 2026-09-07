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
| **D11** | Lo step «Unifica asset» sta **prima** dello step di riparazione (`analyze → assets → fix`), non dopo | Richiesta del committente (08/08/2026): *«quando bisogna scegliere l'asset si sceglie già tra quelli agglomerati»*. Non è una preferenza di comodo — vedi la prova qui sotto |

### Perché l'unificazione deve precedere la riparazione (D11)

`fixAnalysisAssets` (`ImportWizardModal.svelte:2326-2332`) è derivato **direttamente** da
`assetResolutions`, e alimenta la tendina asset di `FixFlaggedStep` (`:3788` → `:150`):

```ts
let fixAnalysisAssets = $derived(
    assetResolutions.map((r) => ({ id: r.fakeAssetId, label: …, detail: … })),
);
```

Poiché `fakeRemap` è **per-file** (`:776`), oggi lo stesso BTP presente in due file produce **due**
`AssetResolution` → **due voci identiche nella tendina**, con due `fakeAssetId` diversi.
Un utente che deve tipizzare una tassa e assegnarle l'asset vede due «BTP Più» e ne sceglie uno:
la riga finisce su **metà strumento**, e l'errore è invisibile perché le due voci sono
indistinguibili.

Invertendo l'ordine — riparazione prima, unificazione dopo — quella scelta andrebbe **rifatta o
migrata** dopo l'unione, cioè si chiederebbe due volte la stessa cosa.

> **Conseguenza di progetto**: il gruppo **non** è una struttura parallela affiancata a
> `assetResolutions` — **è** `assetResolutions`. C‑02 riscrive quella lista in modo che ogni
> elemento sia un gruppo. Così `fixAnalysisAssets`, la sezione di risoluzione di `review`, il
> dedup e tutto il resto ricevono i gruppi **senza una riga di lavoro aggiuntivo**, perché
> derivano già da lì.

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

## 2‑bis. Convivenza con l'agente P1 — ✅ **RISOLTA** (08/08/2026)

> ## ⚠️ Sezione storica — vincoli non più attivi
>
> P1 ha **committato la Fase A** (`571bcde0`, *«feat(import): asset identity, CA trades and import
> wizard rework»*): la working tree è pulita e il partizionamento dei file qui sotto **non serve
> più**. In Fase B P1 lavora solo su `broker_credit_agricole.py`, le sue fixture e
> `schemas/brim.py` — **nessun file in comune con P3**.
>
> Resta valida **una sola regola** di questa sezione, ora per il motivo opposto: P3 **non tocca**
> `backend/app/schemas/brim.py` né il plugin Crédit Agricole. Se serve un campo nel contratto
> BRIM, si chiede.
>
> Conservata perché documenta come è stata gestita la concorrenza e perché la matrice di
> collisione spiega alcune scelte dell'Onda 1 (p.es. l'i18n modificata solo con `edit` chirurgici).

> **Contesto verificato**: nessun worktree separato — P1 e P3 scrivono nella **stessa cartella**
> `/Users/ea_enel/Documents/00_My/LibreFolio`, ramo `dev_release2`. P1 ha la **Fase A consegnata
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

#### B‑02 · Innesco 1 — assegnazione nel wizard ✅ **COMPLETATO** (08/08/2026)
`ImportWizardModal.svelte` — **righe ricalibrate dopo il commit `571bcde0`**:
`checkAndPromptIdentifier()` **`:1082-1116`** · stato `identifierPrompt*` **`:648-657`** ·
`reuseExistingForCreate()` **`:1015-1034`** · `createNamesFor()` **`:1005`** ·
`clearResolution()` **`:1000`**.

Sostituisce l'attuale modale a tre bottoni. Chiude in un colpo **quattro rilievi**:

| Rilievo | Come viene chiuso | Verificato sul codice |
|---|---|---|
| **A2** — modale spuria se l'ISIN è già negli alternativi | Corto circuito prima di aprire: `if (info.identifier_other?.some(v => v.toUpperCase() === res.extractedIsin?.toUpperCase())) return;` — idem per il ticker. **Non c'è nulla da decidere se è già noto** | ✅ chiuso in `pendingIdentifier()` |
| **A3** — testo di conflitto senza conflitto | `identifierPromptIsConflict = existingValue !== null` (`:1109`) è `true` anche con `identifier_isin === ""`. Normalizzare (`|| null`). Nel nuovo componente il problema svanisce: con un solo valore non c'è scelta da fare | ✅ chiuso in `normIdentifier()` |
| **A4** — «aggiungi come alternativo» | È l'esito naturale del selettore: tutto ciò che non è primario **è** alternativo | ✅ chiuso: ISIN/ticker estratti ora attraversano il prompt |
| **W6** — Annulla non riporta l'asset a neutro | Il bottone «Annulla» chiama `clearResolution(fakeAssetId)` (esiste già, `:1000`) | ✅ chiuso in `cancelAddIdentifier()` |

> ⚠️ **A4 va completato secondo D10, non nel modo ovvio.** Oggi `reuseExistingForCreate` unisce in
> `identifier_other` solo `createNamesFor(res)` — i **nomi**. L'ISIN e il ticker estratti si
> perdono. La tentazione è aggiungerli a `other` e chiuderla lì; sarebbe sbagliato:
>
> - se l'asset esistente **non ha** `identifier_isin` → l'ISIN estratto ne diventa il **primario**
>   (altrimenti si lascia non quotabile un asset che potrebbe esserlo);
> - se ce l'ha ed è **diverso** → è un conflitto di stadio 2 → `IdentifierPrimaryChooser`;
> - se ce l'ha ed è **uguale** → non si chiede nulla.
>
> Stessa scala per il ticker. I nomi, che non sono identificativi strutturati, vanno sempre in
> `other` come già fanno.

Al termine: PATCH con `identifier_isin` + `identifier_other` (unione lato client — il PATCH
**sostituisce** la lista, quindi va inviato l'insieme completo, come già fa
`reuseExistingForCreate` `:1027`), poi `refreshAllAssets()` + `refreshCandidates()`.

##### Esito di implementazione

**Nuovo modulo puro** `frontend/src/lib/utils/assetIdentifiers.ts` — `normIdentifier`,
`otherContains`, `pendingIdentifier`, `mergeOther`, `demotedValues`.
A2 e A3 erano **errori di pura logica sepolti dentro il wizard**, dove nessun test poteva
raggiungerli: estrarli è ciò che impedisce di reintrodurli in silenzio. **21 test** in
`__tests__/assetIdentifiers.test.ts`, tutti verdi.

**Comportamento della modale — due forme, un percorso**

| Situazione | Cosa vede l'utente |
|---|---|
| L'asset non ha codice di quel tipo | Testo semplice: «vuoi salvarlo come principale?» — nessun selettore, **nessuna parola «sostituisci»** |
| L'asset ne ha già uno diverso | `IdentifierPrimaryChooser` con i due valori e la loro origine (`già salvato` / `dal report`) + nota BTP |

**Default del primario = quello già memorizzato.** Retrocederlo senza chiedere è esattamente il
gesto distruttivo che questo lavoro elimina. Chi vuole promuovere il codice del report lo fa in un
click.

**I tre bottoni, con semantica finalmente distinta**

| Bottone | Effetto |
|---|---|
| **Annulla** | Chiude e — se l'utente era arrivato scegliendo un asset dalla lista — **azzera la risoluzione** (W6). Arrivando invece dalla *creazione* di un asset non azzera nulla: l'asset esiste, slegarlo lo lascerebbe orfano (`clearOnCancel`) |
| **Solo assegna / Non salvare** | Tiene il legame, non scrive identificativi, **ma scrive comunque le chiavi di ricerca**: erano state acconsentite a parte, rifiutare una domanda non è rifiutarle entrambe |
| **Conferma** | Un **solo** PATCH scrive primario + lista alternativi completa |

**Catena ISIN → ticker.** Un report può portare entrambi; prima si decideva solo il primo e il
secondo spariva. Ora dopo la conferma il controllo rigira con l'elenco dei campi già risolti
(`settled`), quindi chiede il ticker e **non può** riproporre l'ISIN: il ciclo termina per
costruzione.

**Chiavi i18n**: nasce `importWizard.addIdentifier.alsoKeys` (4 lingue); spariscono
`titleConflict`, `bodyConflict`, `confirmConflict` — codificavano la semantica «sostituisci» che
non esiste più. Le tre chiavi `primaryChooser.{confirm,cancel,skip}`, prima segnalate inutilizzate,
ora hanno il loro chiamante.

> ⚠️ **Trappola trovata**: l'audit i18n non vede le chiavi annidate in un ternario dentro `$t(...)`
> (il pattern richiede `$t('chiave')` letterale, `frontend/scripts/i18n-audit.py:94`). Le etichette
> sono state estratte in un `$derived` con chiamate `$t` esplicite — più leggibile e tracciabile.

**Verifiche**: `./dev.py front check` **0/0** · `vitest assetIdentifiers` **21 passed** ·
`./dev.py i18n audit` **2416/2416 complete, 0 incomplete** (inutilizzate 114 → 111).

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

#### C‑05 · Innesto negli step ✅ *semplificato dalla riscrittura di P1*
- **Non serve rinumerare nulla.** Gli step sono una macchina a stati condizionale
  (`type StepId`, `:100`). L'innesto è: una riga in `STEP_DEFS` (`:102-109`), un ramo in
  `stepIsActive()` (`:2488`), un ramo in `goNext()` (`:2559`).
- **Posizione: fra `analyze` e `fix`** — è **D11**, richiesta esplicita del committente, e
  coincide con l'indicazione lasciata da P1 nel commento a `:97-99`. Vale anche per **D10**:
  lo stadio 1 precede tutto ciò che confronta col DB.
- ⚠️ **Verifica obbligatoria dopo C‑05**: la tendina asset di `FixFlaggedStep` deve mostrare
  **un'unica voce per gruppo**. Se ne mostra due per lo stesso titolo, `assetResolutions` non è
  stato riscritto per gruppi (C‑02) e D11 non è soddisfatta.
- **Auto-skip (D5) gratis**: `stepIsActive('assets')` ritorna `false` se ogni gruppo è `single` e
  non c'è alcun legame proposto. `enterNextActiveStep()` (`:2547`) fa già il salto in avanti.
- `resetDownstreamState()` (`:2517`) va esteso con lo stato dei gruppi.
- ⚠️ `goToStep()` (`:2534`) consente solo il ritorno indietro (`isStepBeforeCurrent`): lo step
  resta raggiungibile all'indietro senza lavoro aggiuntivo.

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

#### D‑03 · A5 ✨ — modifica asset dalle card ✅ *già in casa, da replicare*
**Il pattern esiste**: `openInspectAsset()` (`ImportWizardModal.svelte:2392-2418`) apre
`AssetModal` in `editMode` con `editData` costruito come fa `assets/[id]/+page.svelte`
(`buildEditData()`), a z-index 90. È renderizzato a `:4511-4522`, e la matita è a `:4040-4053`
(`data-testid="import-wizard-inspect-asset-{fakeAssetId}"`).

D‑03 diventa quindi: **riusare la stessa funzione** sulle card del nuovo Step «Unifica asset»,
non inventarne una seconda. `onupdated` → `refreshAllAssets()` + `refreshCandidates()`.

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

### 🟢 Onda 2 — SBLOCCATA (08/08/2026)

> **Condizione soddisfatta**: P1 ha **committato** (`571bcde0`) e ha lasciato l'area. Working tree
> pulita, `./dev.py front check` **0 errori / 0 warning**. P1 ora lavora solo su
> `broker_credit_agricole.py` + fixture + `schemas/brim.py` (Fase B): **nessun file in comune**.
>
> ⚠️ **Il wizard è stato riscritto.** Tutti i numeri di riga citati qui sotto vengono dalla
> rilettura del codice reale post-commit; quelli delle versioni precedenti del piano sono da
> buttare.

#### Cosa è cambiato nel wizard, e cosa significa per P3

**1. Gli step non sono più indici numerici ma una macchina a stati condizionale**
(`ImportWizardModal.svelte:100-111`):

```ts
type StepId = 'upload' | 'select' | 'analyze' | 'fix' | 'duplicates' | 'review';
```

`fix` e `duplicates` compaiono **solo se hanno qualcosa da fare** (`stepIsActive`, `:2488`);
`enterNextActiveStep()` (`:2547`) cammina in avanti e atterra sul primo step non vuoto.

> ✅ **C‑05 si semplifica moltissimo**: l'auto-skip che il piano prevedeva di costruire **esiste
> già come infrastruttura**. Aggiungere lo step «Unifica asset» significa una riga in `STEP_DEFS`,
> un ramo in `stepIsActive`, un ramo in `goNext`. Niente rinumerazione, niente `target <= 3`.

**2. P1 ha lasciato l'aggancio esplicito** (`:97-99`, commento nel codice):

> *«An `assets` step ("Unifica asset") belongs between `analyze` and `fix`; add it to STEP_DEFS
> and to `stepIsActive` when it lands.»*

**Ed è la collocazione giusta anche per D10**: `analyze` produce i dati → **`assets` unifica
(stadio 1)** → `fix` corregge → `duplicates` arbitra → `review` risolve contro il DB (stadio 2).

**3. La risoluzione asset è una sezione dentro `review`**, non uno step (`:3967-3970`,
`import-wizard-resolve-section`). Quindi **stadio 1 e stadio 2 restano separati** come vuole D10,
ma il secondo vive in fondo al percorso.

**4. Il buco W2 è intatto e confermato sul codice.** `fakeRemap` è dichiarata **dentro** il ciclo
sui file (`:776`, commento *«Per-file map»*): ogni file genera i propri `globalFakeId` e **nessuno
consolida fra file**. Lo stesso BTP in due file resta due `AssetResolution`. È esattamente ciò che
WS‑C deve chiudere.

**5. `checkAndPromptIdentifier` non è stata toccata** (`:1082-1116`). Verificato riga per riga:

| Rilievo | Stato reale | Prova |
|---|---|---|
| **A2** — modale spuria se l'ISIN è già negli alternativi | ❌ **aperto** | Il confronto guarda solo `info.identifier_isin`; `identifier_other` non è mai consultato (`:1093`) |
| **A3** — testo di conflitto senza conflitto | ❌ **aperto** | `identifierPromptIsConflict = existingValue !== null` (`:1109`) con `existingValue = info.identifier_isin ?? null`: una stringa vuota è `!== null` → conflitto fantasma |
| **A4** — salvare l'identificativo del report | 🟡 **mezzo fatto** | `reuseExistingForCreate(id, addKeys)` (`:1015`) esiste, ma unisce in `identifier_other` **solo i nomi** (`createNamesFor`, `:1005`): l'ISIN e il ticker estratti **non vengono salvati** |
| **W6** — Annulla non azzera l'asset | ❌ **aperto** | `clearResolution` (`:1000`) esiste ma il bottone Annulla non la chiama |

> **A4 è la correzione più economica del lotto** e va fatta con la testa di D10: se l'asset
> esistente **non ha** `identifier_isin`, l'ISIN estratto ne diventa il **primario**, non un
> alternativo. Se ce l'ha ed è diverso → `IdentifierPrimaryChooser`. Aggiungerlo sempre a
> `other` sarebbe comodo e sbagliato: lascerebbe non quotabile un asset che potrebbe esserlo.

**6. La matita di ispezione esiste già** (`:2392-2418` + `:4040-4053`): apre `AssetModal` in
`editMode` con `editData` costruito come `assets/[id]/+page.svelte`, z-index 90.

> ✅ **D‑03 (A5) da costruire diventa D‑03 da replicare.** Il pattern è in casa: si riusa
> `openInspectAsset()` sulle card del nuovo Step «Unifica asset». Costo quasi nullo.

#### Componenti condivisi di P1 — usare, non reinventare

| File | Obbligo per P3 |
|---|---|
| `lib/actions/numericArrows.ts` | **ogni** input numerico nuovo → `use:numericArrows` |
| `SingleDatePicker` / `DateRangePicker` | ogni campo data nuovo. Il range picker pubblica **solo** a Invio/chiusura/blur |
| `lib/utils/core/parseDecimalInput.ts` | normalizzazione decimali locale-safe |
| `BrimNoticeList` / `BrimEvidenceTable` | se P3 deve mostrare avvisi o righe di origine |

> **W8 di P2 è superato** dal contratto `BRIMNotice` a 4 livelli: non reimplementarlo.

#### Ordine di esecuzione dell'Onda 2

```
B-02 ✅ ──▶ B-03 ✅          prompt identificativi (chiude A2, A3, A4, W6)
  │                       ✅ 08/08 — + modulo puro assetIdentifiers.ts (29 test)
  ▼
C-02 ✅ ─▶ C-03 ✅ ─▶ C-04 ✅ ─▶ C-05 ✅   Step «Unifica asset» fra analyze e fix (chiude W2)
  ▼
D-03 ✅                    A5 — riusa openAssetInspector()
E-02 ✅                    aggancio fusione dal wizard
B-05 ✅                    i18n, 4 lingue (2440/2440)
api sync                  non necessario: nessun cambio di contratto
F-02 ──▶ F-03             documentazione + validazione        ⏳ residui
F-01                      E2E — IN CODA, dopo il via libera estetico del committente
```

### Esito Onda 2 — WS‑C, B‑03, E‑02 (08/08/2026)

**Il fold vive dentro `mergeAllTransactions()`, non accanto.** `applyAssetGrouping()` gira dopo il
ciclo sui file e **prima** di `rebuildDuplicateGroups()`. Piega i membri sul rappresentante,
riscrive `tx.asset_id` e cancella le voci assorbite da `assetMap`. Tre conseguenze, tutte gratuite:

| Effetto | Perché |
|---|---|
| La tendina di `FixFlaggedStep` mostra **una voce per titolo** | `fixAnalysisAssets` deriva da `assetResolutions`, che ora **è** l'elenco dei gruppi (D11) |
| I duplicati **fra file diversi** finalmente si riconoscono | `rebuildDuplicateGroups` confronta anche l'asset: prima due file davano due `fakeAssetId` e nessuna coppia poteva combaciare |
| L'import finale non ha bisogno di tabelle di traduzione | i legami sono già riscritti sulle transazioni |

**L'invariante è pinnata da un test, non solo dal codice.** `representativeMap()` (modulo puro,
3 test dedicati) è la funzione che il wizard usa davvero per riscrivere i legami: *«ogni membro
di un gruppo finisce su un unico sopravvissuto»* è una proprietà di quella mappa, quindi la
verifica obbligatoria di C‑05 non dipende da un'ispezione a mano della UI.

**L'override è una partizione intera, non un delta.** La partizione automatica viene ricalcolata
da zero a ogni re‑merge e i `fakeAssetId` sono riallocati, quindi un delta non sarebbe
riproducibile. Le chiavi dei membri sono **derivate dal contenuto** (`fileId|isin|symbol|nome`):
per questo l'override **sopravvive** a un re‑parse degli stessi file e viene azzerato **solo** dal
reset totale. Un membro che l'override non nomina — un file aggiunto dopo — torna singolo invece
di sparire.

**`refreshCandidates` interroga tutti i codici del gruppo.** Girava sul solo rappresentante: dopo
l'unificazione avrebbe **ristretto** l'unione che l'unificazione aveva appena costruito. Ora cicla
su `groupIsins`/`groupSymbols` e deduplica per `asset_id` tenendo la confidenza più forte.

**B‑03 chiede prima, non dopo.** Se il gruppo porta più ISIN, il selettore del primario si apre
**prima** del form di creazione: il form arriva già corretto (primario in `identifier_isin`, il
resto in `identifier_other` insieme ai nomi) invece di essere corretto a cose fatte. Due click.

**E‑02 è un avviso, non un automatismo.** Due candidati di grado identificativo (`EXACT` + `HIGH`)
sulla stessa estrazione sono quasi sempre il duplicato creato da un import precedente: la card
mostra un avviso ambrato con «Unisci» che apre `AssetMergeModal` sul candidato **non** legato.
I match per **nome** sono esclusi di proposito — due fondi dello stesso emittente si somigliano
legittimamente, e proporne la fusione sarebbe un consiglio pericoloso.

**File nuovi**: `lib/utils/assetGrouping.ts` (30 test), `components/transactions/import/AssetGroupStep.svelte`.

**Verifiche**: `./dev.py front check` **0/0** · `vitest src/lib/utils/__tests__/` **224 passed
(11 file)** · `./dev.py i18n audit` **2440/2440 complete, 0 incomplete**, inutilizzate ferme a 111.

> ⚠️ **Residuo noto**: gli archi SVG di C‑03 sono resi come **righe di spiegazione testuale** sotto
> i chip («stesso nome, cambia solo il suffisso · somiglianza 94%») anziché come overlay
> disegnato. Il contenuto informativo è identico e la forma è più leggibile su schermi stretti;
> se il committente vuole il tratto grafico si aggiunge sopra, senza toccare la logica.

---

### Primo collaudo estetico — correzioni (08/08/2026)

Il committente ha provato lo step su un import reale di più report Crédit Agricole. Sette
rilievi, uno dei quali era un difetto vero e non un gusto.

| # | Rilievo | Risposta |
|---|---|---|
| 1 | 🔴 «non ci sono transazioni selezionate», impossibile proseguire | Lo step `assets` **non aveva un ramo di footer** e cadeva nel `{:else}` finale, che è quello della revisione: giudicava *transazioni* su uno step che non ne ha, e disabilitava l'unica via d'uscita. Ramo dedicato con conteggio dei gruppi da confermare |
| 2 | Riordino per numero di elementi a ogni unione | Ora **ordine di estrazione**, preso dalla posizione nell'array in ingresso e non dal `fakeAssetId` (che il wizard alloca **a scendere**: `Math.min` avrebbe dato l'ultimo, non il primo). Due test lo fissano, uno dei quali con id negativi decrescenti |
| 3 | «stesso nome · somiglianza 100%» non dice *a cosa* si riferisce | La riga nomina entrambi i lati: `IT0005612345 ↔ IT0005634792 · stesso nome`. Il lato è etichettato con **codice o file, mai col nome**: quando il motivo *è* «stesso nome», scrivere `BTP X ↔ BTP X` non spiega niente |
| 4 | Manca un ripristino dell'unione automatica | Bottone in cima, attivo solo se qualcosa è stato deciso a mano. Serve perché la partizione è memorizzata **intera**: dopo il primo gesto il motore smette di dare forma al layout, e qualche trascinamento sbagliato lascia un disordine che nessun singolo annullamento ripulisce |
| 5 | Rettangoli disuguali, nomi file troncati | Griglia di card **della stessa misura** (`items-stretch` + altezza minima), gruppi e singoli nello stesso flusso; nomi file e intestazione con `use:scrollOnOverflow`, la marquee già usata in tabelle e card |
| 6 | Badge tutti grigi | Una tinta per genere: **ISIN azzurro · ticker viola · nome ardesia** |
| 7 | I badge mostravano solo gli ISIN | Ora **tutti** gli identificativi, nome compreso |

**L'elezione del primario si sposta qui.** Era il punto 7 del committente ed è più di un
dettaglio grafico: i codici sono *su questa pagina*, accanto ai file che li portavano, quindi è
qui che si sceglie quale guida. Un click su un badge lo promuove; la stella marca quello con cui
il titolo verrà quotato — che per un BTP retail **non** è il codice CUM di collocamento.

Il modello sta nel modulo puro (`GroupPrimary`, `electPrimary`, `orderedIdentifiers`, 8 test
nuovi) e sceglie di **riordinare** anziché marcare: ogni consumatore a valle legge già
`groupIsins[0]` come «il codice da usare», quindi la scelta raggiunge il form di creazione, i
suggerimenti di ricerca e il prompt degli identificativi senza che nessuno di loro impari un
concetto nuovo. Le chiavi sono le **firme di cluster**, non i `groupId`: sopravvivono al
ricalcolo. Un'elezione che nomina un valore che il gruppo non ha più — la scheggia è stata
estratta dopo la scelta — è semplicemente inerte, ed è questo che rende innocue le voci stantie.

Il selettore di B‑03 **resta**, ma solo per chi passa oltre lo step senza decidere:
`startCreateAsset` non richiede una scelta già fatta (`groupPrimaryIsin`/`groupPrimarySymbol`).

**Verifiche dopo le correzioni**: `front check` **0/0** · `vitest utils/` **233 passed (11 file)**
· `i18n audit` **2455/2455 complete, 0 incomplete**, inutilizzate ferme a 111 · `front build` ok.

> ⏳ **In attesa del committente**: secondo giro di prova estetica. F‑01 (E2E) e F‑03 restano in
> coda come concordato; F‑02 (documentazione) è chiusa.

**B‑02 per primo, non C‑02.** Tre motivi: chiude quattro rilievi da solo, è il più piccolo, e
soprattutto **C‑02 gli cambia il tipo sotto i piedi** (`extractedIsin: string | null` →
`extractedIsins: string[]`). Fare prima il prompt su un tipo singolo e poi adeguarlo al plurale
costa meno che costruirlo due volte.

---

### Vincoli operativi concordati con P1 (dal suo messaggio dell'08/08/2026)

- **Non toccare** `broker_credit_agricole.py`, le sue fixture, `backend/app/schemas/brim.py`.
- Serve un campo nuovo nel contratto BRIM? **Si chiede**, non si aggiunge in parallelo.
- `./dev.py front check` deve restare **0/0**; `./dev.py i18n audit` **0 incomplete** su 4 lingue.
- Niente E2E se non richiesti dall'utente. Niente `git commit` / `git push`.

### Politica di verifica dell'Onda 2 (decisa dal committente, 08/08/2026)

| Ambito | Cosa fa l'agente | Cosa fa il committente |
|---|---|---|
| **Backend** | Test completi come sempre: `./dev.py test db …`, unit, integrazione | — |
| **Frontend — logica pura** | Unit test dove il codice è puro e testabile (`assetSimilarity.ts` e simili) | — |
| **Frontend — build & tipi** | `./dev.py front check` (0/0), `i18n audit`, build | — |
| **Frontend — UI/estetica** | ❌ **niente E2E, niente test di interfaccia durante lo sviluppo** | ✅ **prova a mano** e detta l'estetica giusta |
| **E2E finali (F‑01)** | Si scrivono **solo alla fine**, sull'aspetto già approvato | approva prima |

> **Motivo**: scrivere gli E2E su una UI non ancora approvata significa doverli riscrivere a ogni
> aggiustamento estetico. Si formalizzano quando la forma è ferma. **F‑01 slitta in coda**, dopo
> il via libera del committente sull'aspetto.

---

## 5. Rischi e attenzioni

| Rischio | Mitigazione |
|---|---|
| ~~**Collisione con P1 su `ImportWizardModal.svelte`**~~ | ✅ **Risolto 08/08/2026**: P1 ha committato (`571bcde0`) e lavora ora solo su `broker_credit_agricole.py` + fixture + `schemas/brim.py`. Nessun file in comune |
| **I numeri di riga dei piani sono sfalsati** dopo la riscrittura del wizard | Tutti quelli dell'Onda 2 sono stati riverificati sul codice post-commit. Per qualunque punto nuovo: **cercare per nome di funzione**, mai per riga |
| **Regressione su ciò che P1 ha appena costruito** (step condizionali, `FixFlaggedStep`, dedup con asset NULL) | Lo step nuovo si **aggiunge** a `STEP_DEFS`/`stepIsActive` senza toccare i rami esistenti. `./dev.py front check` deve restare **0/0** — è il baseline misurato oggi |
| **Contratto BRIM conteso** | P3 non tocca `schemas/brim.py`. Se servisse un campo, si chiede a P1 |
| Collisione con P2 su `identifierPrompt*` | W6 già marcato «assorbito da P3» nell'INDEX |
| Il nuovo step allunga il percorso per tutti | Auto-skip: `stepIsActive` esiste già, lo step non compare se non c'è nulla da unire |
| Il DnD non è testabile a fondo in Playwright | Il menu `⋮` è la strada primaria per gli E2E; il DnD è un'aggiunta |
| Unione sbagliata → transazioni sull'asset sbagliato | Solo i segnali forti uniscono da soli; i deboli **propongono** e basta. `userTouched` impedisce che un ricalcolo sovrascriva una decisione dell'utente |
| La fusione è **distruttiva** | Anteprima obbligatoria di tutto ciò che si sposta + conferma esplicita; transazione unica lato DB |
| `AssetResolution` da singolo a plurale tocca molto codice | Cambiamento di tipo guidato dal compilatore: `svelte-check` elenca ogni punto da adeguare. **B‑02 va fatto prima di C‑02**, altrimenti il prompt si costruisce due volte |

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
- **Da chiedere all'agente P1** — ✅ **tutte risolte 08/08/2026**:
  1. ~~La **Fase A può essere committata**?~~ → **Sì, fatto** (`571bcde0`). Working tree pulita.
  2. ~~Il **punto 5 del checkpoint** (pannello di revisione nello Step 3)?~~ → **Superato dai
     fatti**: il pannello è stato costruito ed è diventato uno step proprio (`FixFlaggedStep`,
     `stepIsActive('fix')`). Gli step ora sono condizionali, quindi non c'è più nulla da
     rinumerare.
  3. ~~**B5** atterra anche nel wizard?~~ → **Domanda decaduta**: P1 dichiara di lavorare in
     Fase B solo su `broker_credit_agricole.py`, le sue fixture e `schemas/brim.py`.
- **Nuovo punto da tenere d'occhio**: P1 in Fase B potrebbe emettere `field_todos` con
  `severity: "blocker"` legati all'**asset mancante**. Se succede, il ramo di riparazione
  `FixFlaggedStep` e il nuovo Step «Unifica asset» si sfiorano — non collidono, ma la stessa
  riga potrebbe comparire in entrambi. Da verificare a Fase B consegnata.

---

### Secondo collaudo estetico — correzioni (08/08/2026)

Cinque rilievi. Uno era un difetto vero — il selettore delle correzioni mostrava ancora le
etichette pre-unificazione — e uno ha aperto un buco di progetto che nessuno aveva visto.

| # | Rilievo | Risposta |
|---|---|---|
| 1 | La stella e l'evidenziazione piacciono ma non si capisce cosa siano, né **come si cambia l'ISIN principale** | Il badge non primario ora porta una **stella vuota** invece di niente: l'affordance c'era solo per chi già sapeva. Sopra i badge una didascalia dice cosa fa il click; in cima alla pagina una legenda decodifica bordi e stella. Il tooltip smette di dire «verrà quotato» per i **nomi**, dove sarebbe falso: `primaryIsCode` e `primaryIsName` sono ora due frasi distinte |
| 2 | Con 4 file la spiegazione si ripete parola per parola | `summariseLinks()` (modulo puro, 4 test): **una riga per motivo**, non per coppia. Se il motivo copre tutti i membri il testo diventa *«stesso ISIN · tutte e 4 le estrazioni»* e non nomina nessuno — quando tutto combacia, dire *chi* non aggiunge nulla. Il punteggio compare **solo** sotto il 100% |
| 3 | Il ripristino accorcia il banner | Banner a tutta larghezza sulla sua riga; sotto, una riga con la legenda a sinistra e il ripristino a destra |
| 4 | 🔴 Allo step 5 il selettore mostra ancora gli asset «fake» | L'elenco era **giusto** (una voce per gruppo), l'etichetta no: veniva da `extractedName`, cioè il nome grezzo del file capofila. Nasce `resolutionLabel()`, **una sola funzione** usata da `fixAnalysisAssets`, dalle etichette dei duplicati e dai filtri: nome d'archivio se il gruppo è legato → nome eletto/rinominato → estrazione grezza |
| 5 | Per i gruppi **senza** corrispondente in DB serve poter rinominare o scegliere fra i nomi dei report | Intestazione della card **rinominabile in linea** (matita → invio) quando il gruppo non è legato; se è legato mostra il badge «in archivio» e il nome dell'archivio, non modificabile lì (c'è già la matita che apre l'editor dell'asset). I nomi dei report restano badge cliccabili, quindi *scegliere* costa un click e *scrivere* è la via d'uscita quando nessuno dei due va bene |

**La rinomina ha richiesto un'eccezione nel modello, e vale la pena dirla.** `leadWith()` scartava
per costruzione un valore eletto che il gruppo non possedeva — è la regola che rende inerti le
elezioni stantie. Ma un nome che nessun file porta **non** è un residuo: è esattamente ciò che
l'utente ha appena scritto. Quindi i **nomi** accettano un valore nuovo (`allowNew`), i **codici**
no: inventare un ISIN sarebbe un errore, inventare un nome è la funzione richiesta.

**E la rinomina doveva anche arrivare da qualche parte.** Il form di creazione usava
`display_name: extractedName`: il nome scelto sullo step non lo raggiungeva. Ora legge
`groupNames[0]`, e `createNamesFor()` include tutti i nomi del gruppo — così il nome nuovo diventa
il titolo dell'asset e quelli dei report restano chiavi di ricerca in `identifier_other`.

**Verifiche**: `front check` **0/0** · `vitest utils/` **241 passed (11 file)** · `i18n audit`
**2466/2466 complete, 0 incomplete**, inutilizzate ferme a **111** · `front build` ok ·
prettier pulito.

> ⏳ **In attesa del committente**: terzo giro di prova estetica. F‑01 (E2E) e F‑03 restano in coda.

---

## Onda 3 — Un campo solo per scegliere lo strumento (progetto, 08/08/2026)

### Il rilievo

> «non mi convince il nome "asset già catalogati" e poi da lì, se non si trova, fare aggiungi
> asset, non mi pare intuitivo, il lavoro è corretto, ma poco chiaro»

### La diagnosi

Due difetti, una radice sola.

**«Asset già catalogati» è un'opzione che non è una cosa.** Tutte le altre righe della lista sono
strumenti; quella è un *posto dove andare a cercare*. Una lista che mescola sostantivi e verbi va
letta due volte. **E «crea» sta a profondità 2**: lo si trova solo dopo aver fallito due volte —
prima non trovando il titolo fra quelli dell'import, poi passando all'archivio e scoprendo il
footer.

La radice: **chiediamo di scegliere una provenienza quando l'utente vuole solo nominare una cosa.**
La provenienza — id finti dell'import contro id veri dell'archivio — è contabilità nostra che
trasuda nell'interfaccia. E dopo lo step di unificazione non è nemmeno una distinzione vera: molti
strumenti dell'import sono *già legati* all'archivio, i due insiemi si sovrappongono.

### La soluzione

Un campo solo, una lista sola, **sezioni al posto delle modalità**:

```
┌─ cerca: "btp nov" ──────────────────────────┐
│  IN QUESTO IMPORT           ← intestazione  │
│    BTP 17-11-28  [in archivio]   12 mov.    │
│  IN ARCHIVIO                                │
│    BTP 1/3/32 1,65%   IT0005094088          │
├─────────────────────────────────────────────┤
│  ➕ Crea «BTP Nov 28»       ← footer fisso   │
└─────────────────────────────────────────────┘
```

- **L'intestazione risponde a «perché è qui»** senza che l'utente debba sceglierlo. La sezione
  dell'import viene prima perché ha ragione quasi sempre: le righe da correggere vengono da lì.
- **Il footer è sempre visibile e porta il testo digitato.** Creare non è più qualcosa da
  *trovare*: è l'ultima cosa che si vede, ogni volta, già compilata. Profondità 2 → 0.
- **Uno strumento già legato all'archivio compare una volta sola**, nella sezione import, col badge
  «in archivio». Mostrarlo anche sotto sarebbe una trappola: due righe, stesso titolo, esiti diversi.
- Vocabolario: via «catalogati» (gergo). **«In questo import» / «In archivio»** — e *archivio* è
  già la parola del badge dello step di unificazione, così il lessico resta uno.

### Il costo vero non è la UI

I componenti erano **già costruiti per questo**: `AssetSelect` è un involucro di `SearchSelect`
alimentato da `getAllAssets()` (**l'archivio è già tutto in memoria**: nessuna ricerca asincrona,
nessun lavoro di API), `SearchSelect` ha già il footer `createLabel`/`onCreateNew`, e `AssetSelect`
ha già `suggestedIds` — *«elementi prioritari in cima alla lista con un badge»*.

L'ostacolo è lo **spazio degli id**: è *questo* che ha generato due componenti. In una lista sola il
`value` deve codificare la provenienza (`import:-9993` / `db:412`). `FixFlaggedStep` fa già
esattamente questa traduzione per `__db__`/`__none__`.

### Ordine dei passi — dettato dalla collisione

`FixFlaggedStep.svelte` **contiene il codice dei tassi nominali ed è in staging**: l'altro agente
ce l'ha aperto. È il file che mi servirebbe. Quindi il lavoro va rovesciato, e il rovesciamento
produce per conto suo un progetto migliore:

| Passo | File | Collisione | Contenuto |
|---|---|---|---|
| **C‑01** | `ui/select/types.ts`, `SearchSelect.svelte` | nessuna | `SelectOption.header?: boolean` — riga non selezionabile, saltata da filtro e navigazione da tastiera; footer «crea» che riceve il testo digitato |
| **C‑02** | `import/ImportAssetPicker.svelte` (**nuovo**) | nessuna | Incapsula tutta la lista fusa: sezioni, dedup archivio↔import, codifica `import:`/`db:`, footer. Espone `value: {source, id} \| null` |
| **C‑03** | `FixFlaggedStep.svelte` | 🔴 **attendere** | Sostituire `SearchSelect` + `AssetSelect` con `<ImportAssetPicker>` |

**Perché un componente nuovo e non modifiche dirette**: incapsulando la lista fusa, la modifica
dentro `FixFlaggedStep` si riduce a *sostituire due elementi con uno*. La superficie di collisione
col lavoro sui tassi nominali passa da un centinaio di righe a una manciata — che è esattamente
quello che serve quando un altro agente ha il file aperto.

> ⏳ C‑03 parte solo a pagina libera.

### C‑01 ✅ — Intestazioni di sezione in `SearchSelect` (08/08/2026)

> **Note implementazione**: `SelectOption.header?: boolean` — riga non selezionabile, saltata da
> Invio, dalle frecce e dal filtro. `onCreateNew` riceve ora il **testo digitato**, e il nuovo
> `createLabelFor(query)` fa dire al footer *cosa* verrà creato invece di un verbo generico.

**La regola interessante non è la ricerca, è cosa succede a un'intestazione rimasta senza sezione.**
Un titolo che sopravvive al filtro mentre le sue voci spariscono rivendica una categoria che la
lista non ha più — ed è invisibile nel caso comune, quindi è esattamente il difetto che va in
produzione. I titoli non corrispondono mai a una query (sono arredo, non contenuto): vengono
tenuti in blocco al primo passaggio e scartati al secondo, quando non hanno più nulla dietro. Una
sezione svuotata lascia una di due forme sole: **due titoli di fila**, o **un titolo per ultimo**.

Per questo la logica non è rimasta dentro il componente: `ui/select/optionFilter.ts` (modulo puro)
+ **15 test**, compresi i due casi degeneri e la traversata da tastiera che scavalca i titoli senza
avvolgersi in fondo alla lista.

Compatibilità: senza `header` il filtro è **identico** a prima (il secondo passaggio non scarta
nulla), e `() => void` resta assegnabile a `(query: string) => void` — nessuno dei chiamanti
esistenti va toccato.

### C‑02 ✅ — `ImportAssetPicker.svelte` (08/08/2026)

> **Note implementazione**: un campo solo con sezioni «In questo import» / «In archivio», dedup
> archivio↔import, badge «in archivio», footer «Crea «…»» col testo digitato dentro.

**Due decisioni che valgono più del componente.**

*Il valore non è `number | null` ma una scelta discriminata* — `{kind:'asset',id}` | `{kind:'none'}`
| `null`. «Non appartiene a nessuno strumento» (la spesa del broker) e «non ho ancora risposto»
sono risposte diverse che un `null` nudo non distingue: è l'ambiguità che aveva costretto
`FixFlaggedStep` a tenere due `Set` paralleli (`noAssetRows`, `dbSearchRows`). A C‑03 spariscono
entrambi.

*Non esiste `allowNone`* — la presenza di `noneLabel` abilita la riga. Offrire la risposta senza
saperla scrivere è uno stato che non dev'essere esprimibile, e così non c'è un flag che possa
contraddire l'etichetta. (Il fallback `$t('common.none')` che avevo scritto stampava la chiave
grezza: quella chiave non esiste. Lo stato impossibile ha eliminato anche il bug.)

Riconoscere la provenienza di un id si fa per **appartenenza alla lista dell'import**, non per
grandezza: oggi id finti e id veri non collidono, ma appoggiarsi a quel fatto farebbe sbagliare in
silenzio la selezione al primo cambio di schema.

**Verifiche**: `front check` **0/0** · vitest **575 passed (53 file)** · `i18n audit`
**2475/2475, 0 incomplete**, inutilizzate ferme a **111** · `front build` ok.

### Terzo collaudo estetico — e la diagnosi del «li vedo ancora doppi» (08/08/2026)

Tre rilievi. Due erano domande, il terzo sembrava un difetto del raggruppamento e non lo era.

**«Quando compare *da confermare*?»** — È la domanda giusta, perché quel bordo è l'unico posto in
cui il motore ammette di non sapere. Un gruppo è `proposed` **solo** finché l'evidenza è debole *e*
nessuno ha deciso (`resolveState`, `assetGrouping.ts:133`), e l'evidenza debole nasce in due punti
soli (`assetSimilarity.ts:227,232`): `nameSuffix`, stesso nome a meno di un suffisso neutro
(**CUM**/EX/ACC), e `nameNoIsin`, nomi vicinissimi ma uno dei due senza ISIN. Cioè **esattamente il
caso BTP e il caso W2**, i due che questo piano esiste per risolvere. Tutto il resto — stesso ISIN,
stesso ticker, nome identico — è forte e si unisce da solo; e **qualunque gesto dell'utente**
promuove il gruppo a `confirmed`, dove nessun ricalcolo lo tocca più.

**Placeholder** — «Scegli tra gli strumenti trovati in questi file» mandava a capo la cella:
ora «Scegli asset» in 4 lingue.

#### Il doppione non era nel raggruppamento: era la coesistenza dei due selettori

Il dump HTML del committente conteneva **due** combobox, non uno:

| testid | stato | contenuto |
|---|---|---|
| `fix-step-asset` | chiuso, placeholder | gli strumenti dell'import, **già unificati** |
| `fix-step-asset-db` | **aperto, 28 voci** | l'archivio **intero**, id reali `1…48` |

Le voci che sembravano duplicate erano **asset del database**, non estrazioni: lo stesso titolo
compariva una volta come gruppo unificato e una volta come voce d'archivio. Nessuna unificazione
all'import può chiudere quel doppione, perché non è dentro l'import — **è fra l'import e
l'archivio**. Ed è precisamente ciò che l'Onda 3 era stata progettata per eliminare: mancava solo
il collegamento.

(Nota a margine: `BTP 05/26 0.55FOICUM` e `BTP 20-25 1.40FOICUM` sono due CUM rimasti in archivio
dai test precedenti. Quelli sono duplicati **veri** e si chiudono con `AssetMergeModal` — E‑01 —
non con l'unificazione.)

### C‑03 ✅ — Un campo solo in `FixFlaggedStep` (08/08/2026)

> **Note implementazione**: `SearchSelect` + `AssetSelect` → un solo `<ImportAssetPicker>`.
> `AnalysisAsset` guadagna `archiveId`, alimentato da `resolvedAssetId`: è il dato che permette al
> picker di **cancellare dall'archivio ciò che l'import ha già legato**, cioè di chiudere il
> doppione alla radice invece di nasconderlo.

**Due `Set` paralleli diventano una mappa di risposte.** `dbSearchRows` e `noAssetRows` esistevano
perché `asset_id: null` significava insieme «non appartiene a nessuno strumento» e «non ho ancora
risposto». Con `PickedAsset` la risposta è una sola cosa (`assetPicks`), e i due insiemi — con i
loro tre punti di sincronizzazione, ognuno un'occasione di divergere — spariscono.

**Un id d'archivio già legato seleziona il *gruppo*, non se stesso.** È la trappola che il dedup
crea per conto suo: se l'asset #42 è nascosto perché il gruppo lo rappresenta, selezionare #42
lascerebbe il campo apparentemente vuoto **subito dopo aver risposto**. `selectedValue` risale
quindi da `archiveId` al gruppo. Il dedup senza questo passaggio non è un'ottimizzazione: è un bug.

**Il testo digitato arriva fino alla creazione.** `oncreateasset(index, query)` porta la query nel
form (`display_name` e ricerca provider preseminati): il footer «Crea «…»» non promette più
qualcosa che poi va riscritto a mano.

**Due chiavi i18n muoiono qui**: `importWizard.fixStep.assetFromDb` — cioè letteralmente
«Asset già catalogati», la voce-luogo in mezzo alle voci-cosa — e `fixStep.assetCreate`.

**Verifiche**: `front check` **0/0** · vitest **575 passed (53 file)** · `i18n audit`
**2473/2473 complete, 0 incomplete**, inutilizzate ferme a **111** · `front build` ok ·
prettier pulito.

### Quarto collaudo — la ricerca che parte dalla quarta lettera (10/08/2026)

**Sintomo**: nel selettore asset la ricerca sembrava attivarsi solo dal quarto carattere.
**Causa**: due campi che matchavano *qualcosa che l'utente non vede*.

1. `searchText` degli asset conteneva **valuta e tipo** (`… a.currency, a.asset_type`). In un
   archivio interamente in EUR, `eur` matcha **tutte** le righe: cercando «Eurizon» la lista non si
   restringeva fino a `euri`. Una valuta non *nomina* uno strumento, lo *descrive*: è un filtro
   travestito da ricerca, e l'utente non ha modo di sapere in quale delle due modalità si trova.
2. `matches()` confrontava la query con `option.icon`, che per gli asset è un **percorso**
   (`/icons/asset-types/bond.png`). Qualsiasi query di 1–2 lettere presente nel percorso — `s`,
   `o`, `n`, `png` — matchava l'intero elenco. L'icona torna cercabile **solo quando è il simbolo
   stesso** (una bandiera incollata nella casella): niente `/`, niente `.`.

Correzione in `AssetSelect` e `ImportAssetPicker` (identificativi sì — ISIN, ticker,
`identifier_other` col CUM — valuta e tipo no) e in `optionFilter.ts` (+3 test).

### «Tieni com'è» diceva una cosa e la riga ne faceva un'altra (10/08/2026)

Due difetti dello stesso tipo: **lo stato dichiarato e lo stato reale divergevano.**

*Accettare non annullava la correzione già applicata.* `acceptPluginFallback` marcava `kept`
lasciando intatta la transazione riscritta e le sue gambe: la riga conservava una correzione sotto
un'etichetta che nega di averla. Ora accettare **ripristina prima** (`resetFixRow`, che su una riga
mai applicata è un no-op) e poi dichiara. Lato UI `accept()` scarta anche le bozze locali,
altrimenti la modifica sarebbe riapparsa alla riapertura della riga.

*Toccare una riga già decisa la lasciava decisa.* Un badge «mantenuta come letta» sopra un form che
mostra altro è un'affermazione che lo schermo stesso smentisce. `onreopen` fa decadere la decisione
al primo cambiamento di campo (`setDraft`, `setSplitLines`): icona, colore e messaggio d'allarme
tornano quelli d'origine perché derivano tutti da `decision` e da `fixTodoSnapshot`, che sopravvive.
La transazione **non** viene ripristinata: la bozza in corso è stata letta da lì, e riportarla
indietro sposterebbe i valori sotto le dita dell'utente.

**Verifiche**: `front check` **0/0** · vitest **579 passed (53 file)** · `front build` ok ·
prettier pulito.

> ⏳ **In attesa del committente**: prova estetica sul selettore fuso e sui due comportamenti.
> Aperta la domanda sul **lessico dei suffissi neutri** (frontend vs backend) — vedi sotto.
> F‑01 (E2E) e F‑03 restano in coda.

---

### Quinto collaudo — il lessico che non serviva e l'elezione che non c'era (10/08/2026)

Due rilievi. Il primo tocca il motore di similarità, il secondo è **il buco più importante
dell'intero P3**: il caso BTP CUM si rompeva proprio nell'ultimo metro.

#### 1. Via il dizionario dei suffissi neutri

> «toglierei quella parte hardcodata e lavorerei solo di similitudini»

`NEUTRAL_SUFFIX_TOKENS` era una lista di venti parole (`CUM`, `EX`, `ACC`, `HDG`, le lettere di
classe, e — sbagliando — anche `EUR`/`USD`/`GBP`/`CHF`). Riconosceva **solo i marcatori che
qualcuno aveva pensato**: un `PTF`, un `TF`, un `SR` di un altro broker venivano rifiutati in
silenzio, e la regola generale si riduceva a un dizionario privato da mantenere.

Il giudizio ora è **strutturale**: `onlyNeutralSuffixDiff` diventa `onlyMinorTokenDiff` e chiede
*«i token che differiscono sono pochi e corti?»* — al massimo **2**, al massimo **4 caratteri**,
tutti alfabetici, su un nome per il resto identico.

**Perché la regola regge senza lista.** Quando il flag viene consultato in `compareAssets`, la
guardia numerica è **già passata**: date, cedole e scadenze combaciano tutte. Quel che resta non
può essere una scadenza diversa — è un marcatore. La guardia `!isNumericToken` è comunque scritta
esplicitamente dentro `compareAssetNames`, perché il flag è **esportato** e deve reggere da solo,
non appoggiarsi ai controlli di chi lo chiama.

**Il costo, detto senza girarci intorno**: una regola strutturale non distingue `CUM` da `ESG`.
`Amundi S&P 500` e `Amundi S&P 500 ESG` diventeranno una **proposta**. È più permissiva, quindi
produce più proposte sbagliate — ognuna costa un click su «Separa». Non produce **mai** un'unione
automatica: i segnali deboli propongono e basta. Il rischio vero non è l'unione errata, è
l'abitudine a confermare senza guardare.

Cinque test nuovi fissano i due lati: un suffisso mai visto (`Ptf`) ora è accettato; `World` vs
`Emerging` no (token lungo); tre differenze no (troppe); `Ag30` vs `St27` no (numerico).

> La domanda «il lessico appartiene al frontend o al backend?» **decade**: non c'è più un lessico.

#### 2. 🔴 L'elezione del primario spariva all'ultimo passo

> «ho fatto il cerca e mi ha trovato un isin diverso […] non mi è stato chiesto quale dei 2
> eleggere a principale e quale mettere in other, me lo aspettavo a questo step»

Aveva ragione, ed è esattamente lo scenario per cui questo piano esiste: report con l'ISIN **CUM**
`IT0005466344`, provider con l'ISIN **quotato**. Il codice di collocamento è sparito senza una
domanda.

**Dove si perdeva.** `AssetModal.applySearchResult` (`:702-707` pre-fix):

```ts
const existing = identifierRows.find((r) => r.type === idType);
if (existing) identifierRows = identifierRows.map((r) => (r.type === idType ? {...r, value: result.identifier} : r));
```

Una `map` che **sovrascrive**. Il valore precedente non veniva demandato a `OTHER`, non veniva
confrontato: cessava di esistere. E la sola guardia presente (`:684`) era condizionata a
`editMode`, cioè **spenta proprio nel percorso di creazione dal wizard**.

Il prompt di B‑02 (`checkAndPromptIdentifier`) scattava sì dopo il salvataggio — ma su un asset i
cui identificativi il provider aveva già ripulito, e comunque **dopo**, in una modale separata,
quando i due valori non erano più affiancati. La domanda arrivava fuori tempo e senza il confronto
che la rende rispondibile.

**La correzione.** Una ricerca provider è una **fonte di informazione, non un'autorità**: non può
cancellare un codice che l'utente ha preso da un documento suo. Quando il provider restituisce un
identificativo dello stesso tipo con **valore diverso** e il campo è già pieno, la sovrascrittura
non avviene: si apre `IdentifierPrimaryChooser` con i due valori affiancati e le loro provenienze —
**«dal provider»** contro **«dal report»** — e la nota BTP, che qui è finalmente nel punto giusto.
Chi non è eletto scende fra gli alternativi.

Tre dettagli che valgono più del codice:

| Scelta | Motivo |
|---|---|
| Il **collegamento al provider si stabilisce comunque**, subito | La ricerca ha fatto il suo lavoro: `provider_code`, `provider_identifier`, parametri. È solo la domanda di *identità* a essere differita. Bloccare anche il resto punirebbe l'utente per aver cercato |
| La provenienza «dal report» non è indovinata | `prefilledIdentifiers` registra alla sorgente i codici arrivati da `prefillData`. Senza, l'unico modo di etichettarli sarebbe una supposizione — e un badge che sbaglia l'origine è peggio di nessun badge, perché è **sull'origine** che l'utente decide (D3) |
| **Annullare non distrugge nulla** | Chiudendo la modale il codice del report resta principale e quello del provider vive comunque nell'assegnazione provider, che porta il proprio `identifier`. Nessuno dei due esiti perde un dato |

Il default preselezionato resta il valore **del provider**: è l'unico che un provider di prezzo
possa indicizzare — che per un BTP retail è precisamente *non* il codice CUM.

**Verifiche**: `front check` **0/0** · vitest **583 passed (53 file)** · `i18n audit`
**2477/2477 complete, 0 incomplete**, inutilizzate ferme a **111** · `front build` ok ·
prettier pulito. Nessuna chiave i18n nuova: `assets.identifiers.primaryChooser.*` esisteva già ed
è ora usata anche qui.

#### 3. Rifiniture del chooser (stesso collaudo)

Quattro correzioni sulla modale appena nata, più una risposta.

**Una riga d'apertura prima della domanda.** La modale chiedeva quale codice fosse il principale
senza dire *perché* ci fosse qualcosa da decidere. Ora una riga fattuale precede la domanda —
«*Yahoo Finance riporta per questo titolo un ISIN diverso da quello letto nei report*» — con il
nome vero del provider (`getAssetProviderName`, non il codice) e due varianti a seconda di cosa
sta dall'altra parte, report o valore già salvato. Compare **solo** quando un valore del provider
si trova davvero di fronte a un'altra fonte: altrimenti descriverebbe un disaccordo inesistente.

**La nota non parla più solo di Italia.** Diceva «BTP», «premio fedeltà», «CUM»: precisa per chi
compra titoli di Stato italiani, muta per tutti gli altri. Il meccanismo però non è italiano — è
la forma generale di *qualunque* titolo collocato con un codice dedicato che dà un bonus a chi lo
tiene fino alla scadenza e che, proprio perché non deve essere scambiato, non ha un prezzo di
mercato. La nota ora descrive **il meccanismo**, non il paese; la chiave si chiama `issuanceNote`
e non più `btpNote`, perché il nome di una chiave è documentazione anche lui.

**I colori dicevano il contrario di quel che conta.** Il badge del report era blu acceso, quello
del provider verde smorto: l'occhio andava alla fonte meno autorevole. Invertiti. Il criterio ora
è esplicito — il colore misura l'**autorità** della fonte, non la sua novità:

| Origine | Badge | Perché |
|---|---|---|
| provider | blu | È l'unica fonte con un feed di prezzo dietro: se un codice deve quotare, è il suo |
| già salvato | verde LibreFolio | È roba tua, già in archivio |
| report | grigio | Un documento: informativo, ma muto |

Gli identificativi nella riga «Restano come alternativi» erano testo monospace grigio; ora sono
badge colorati con l'origine di provenienza, così la riga si legge con lo stesso alfabeto del
resto della modale.

**Uscire senza scegliere non è un non-evento.** Cliccare fuori, premere Esc o Annulla chiudeva la
modale in silenzio: il codice del provider veniva scartato e l'asset restava sull'identificativo
di partenza — una conseguenza reale, invisibile finché al prossimo import il titolo non viene
riconosciuto. Ora una conferma la enuncia *prima* che accada, che è l'unico momento in cui costa
poco rimediare.

**E se gli identificativi in conflitto fossero più di uno?** Già gestito, ma da un'altra strada.
Un risultato di ricerca porta **un solo** `identifier_type`, quindi da lì può nascere un solo
conflitto. L'arricchimento successivo (`handleAskProvider`) confronta invece **tutti** i tipi e
manda le differenze a `ProviderComparisonModal`, che monta un `IdentifierPrimaryChooser`
**per ciascun tipo** in conflitto (`isIdentifierField`). La stessa domanda, lo stesso componente,
tante volte quante servono.

**Verifiche**: `front check` **0/0** · vitest **583 passed (53 file)** · `i18n audit`
**2484/2484 complete, 0 incomplete**, inutilizzate ferme a **111** · `front build` ok ·
prettier pulito.

---

## P‑01 — Import in parallelo: la concorrenza che non c'era (10/08/2026)

> Rilievo del committente, fuori da P3 in senso stretto: *«ho l'impressione che upload e parsing
> avvengano sequenzialmente e non parallelamente»*. Aveva ragione **due volte**, e la seconda era
> quella che conta.

### Diagnosi — tre problemi indipendenti

**1. I due cicli del wizard erano `for … await`.** Un file per volta, entrambi.

**2. E renderli paralleli lato browser sarebbe stato teatro.** Sia `upload_file`
(`brokers.py`) sia `parse_file` erano `async def` che chiamavano **lavoro sincrono bloccante
direttamente nel loop**. Finché è così, richieste concorrenti dal browser vengono comunque
**serializzate dal server**, e per tutta la durata di un parse l'intera applicazione — prezzi, FX,
navigazione — resta ferma. È la regola di async I/O del progetto, documentata **in quello stesso
file** (`brokers.py:97-98`) e rispettata altrove, ma non nei due percorsi più caldi.

**3. Un terzo problema che nessuno aveva visto**: dentro `parse_file` c'era un
`await search_asset_candidates(...)` **per ogni asset estratto**, e ogni chiamata emette fino a
**cinque** query. Un report da trenta strumenti spendeva ~150 round-trip sequenziali dentro una
sola richiesta.

### Cosa è stato fatto

| Livello | Intervento |
|---|---|
| **Upload** | `save_uploaded_file` va in `asyncio.to_thread`. Un thread basta: il trasferimento vero è lavoro del sistema operativo, noi scriviamo e rileggiamo il file per fiutare i plugin compatibili |
| **Parse** | Nuovo modulo `backend/app/services/brim_parse_pool.py`: `ProcessPoolExecutor` **pigro**, `min(cpu_count, 4)` worker, `forkserver` se disponibile altrimenti `spawn` — **mai** `fork`, perché questo processo ha un event loop e un thread pool e forkarli è il modo classico di produrre deadlock che compaiono solo in produzione. Un parse è lavoro **CPU**: un thread lo lascerebbe serializzato dal GIL |
| **Candidati** | `search_asset_candidates_bulk`: **una** query per l'intero file, poi le stesse cinque priorità applicate in memoria |
| **Frontend** | `lib/utils/core/requestConcurrency.ts` + `mapWithConcurrency`, applicato a `uploadAllPendingFiles` e `doParseAll` |
| **Shutdown** | `shutdown_pool()` agganciato al `lifespan` di `main.py`, accanto agli altri pool |

### Le tre decisioni che valgono più del codice

**Il fallback è permanente, e a ragione.** Se il pool non parte — o un worker muore portandosi
dietro un parser C che segfaulta — si ripiega su un thread **per il resto della vita del
processo**. Un parse degradato è un parse lento; un parse fallito è un import perso. E un
ambiente che non riesce ad avviare worker non comincerà a riuscirci a metà import: riprovare a
ogni file pagherebbe di nuovo il costo di avvio per nulla.

**Un errore del parser non è un pool rotto.** La distinzione è netta e testata: un fallimento
**al submit** è sempre roba nostra; in attesa, **solo** `BrokenProcessPool` conta. Tutto il resto
— `ValueError` per plugin sbagliato, `FileNotFoundError`, `BRIMParseError` — risale intatto.
Trattare un `OSError` come pool rotto avrebbe disabilitato il pool per sempre al primo file
mancante, e trasformato l'unico messaggio utile che l'utente riceve («questo layout non è
supportato») in un silenzio con la rotella che gira.

**Il `%` nei nomi delle obbligazioni.** La ricerca in blocco riproduce in Python predicati che
prima erano SQL, e `LIKE` legge `%` come **jolly**. I nomi dei titoli ne sono pieni
(`BTP Valore 3,35%`): un ingenuo `in` di Python avrebbe reso la ricerca *più stretta* di prima,
perdendo candidati in silenzio. `_like_to_regex` traduce `%`→`.*` e `_`→`.` con tutto il resto
sotto escape. È il modo più probabile in cui le due strade possono divergere, e per questo è il
caso centrale del test di equivalenza.

### Il limite di connessioni del browser — la risposta

Non esiste **nessuna API web** che esponga il numero massimo di connessioni per host.
`navigator.connection` descrive la *qualità* del collegamento (solo Chromium), mai i conteggi;
`navigator.hardwareConcurrency` conta i **core della CPU**, che è tutt'altra cosa. Il tetto è un
dettaglio interno: HTTP/1.1 si assesta per convenzione su **6 per host**, HTTP/2 multiplexa su una
sola connessione e il limite pratico è molto più alto.

Quindi il numero è un'**euristica dichiarata, non una misura**, costruita sul caso pessimistico:

```
max(2, min(6 - 1, navigator.hardwareConcurrency ?? 4))
```

→ **5** su una macchina multi-core, **4** quando il browser non lo dice, **2** su un dual-core.
Uno slot resta sempre libero: un import che affama di connessioni il resto dell'applicazione
sembra un blocco, e l'utente non ha modo di distinguere «occupato» da «rotto».

### Cosa è stato messo sotto test

| Test | Cosa fissa |
|---|---|
| `test db brim-bulk` (**4**) | La ricerca in blocco restituisce **esattamente** ciò che restituisce quella per-asset: stessi id, stesse confidenze, stesso ordine. Copre il doppio ISIN col CUM negli alternati, un nome con `%`, il solo ticker, e l'estrazione ripetuta che deve collassare |
| `test services brim-parse-pool` (**8**) | Un parse **reale** attraverso il pool torna identico a quello inline; `BRIMParseOutput` e `BRIMParseError` (con `details`) sopravvivono al pickle; errori del parser e file mancanti **non** disabilitano il pool; il fallback a thread produce comunque il risultato |
| `requestConcurrency.test.ts` (**12**) | L'ordine dei risultati segue l'input anche quando i task finiscono al contrario — il wizard indicizza `parseResults` per posizione, quindi un runner che consegnasse in ordine di completamento attaccherebbe le transazioni al file sbagliato. Più: il tetto non viene mai superato, l'abort non avvia nuovi task, l'euristica sui core |

**Verifiche**: `dev.py lint` pulito sui file toccati · `test db brim` **17 passed** (nessuna
regressione) · `test db brim-bulk` **4 passed** · `test services brim-parse-pool` **8 passed** ·
`front check` **0/0** · vitest **595 passed (54 file)** · `i18n audit` **2484/2484, 0 incomplete**,
inutilizzate ferme a **111** · `front build` ok · prettier pulito.

> Nessuna chiave i18n nuova, nessun cambio di contratto API: `api sync` non serve.

---

## F‑02 bis — La documentazione delle modali nuove (10/08/2026)

> Richiesta del committente: aggiornare `mkdocs_src` **solo in inglese** — developer guide e
> guida utente all'import — descrivendo le modali e i componenti nati con P3, con gli **step
> opzionali in pannelli richiudibili** il cui titolo dica il nome dello step **e quando compare**.

### Il difetto che la documentazione nascondeva

La guida utente prometteva *«5 step operativi»*. Il wizard ne ha **sette**, e tre non ci sono
quasi mai. Un elenco fisso descrive un percorso che nessun utente vede: chi importa un file
pulito conta quattro schermate e cerca le altre; chi ne importa quattro ne vede sette e non
trova la spiegazione. E lo **Step 2** era intitolato *«Parser Configuration»*, mentre è la
scelta di **quali file** del broker parsare — compresi quelli caricati in sessioni precedenti —
con il plugin scelto **per file**.

Nessuno dei componenti nuovi (`AssetGroupStep`, `ImportAssetPicker`, `FixFlaggedStep`,
`IdentifierPrimaryChooser`, `AssetMergeModal`, il motore di similarità, l'endpoint di merge)
compariva in una sola riga di documentazione.

### Cosa è stato scritto

| File | Intervento |
|---|---|
| `user/transactions/import/how-to.en.md` | Riscritta la sezione degli step: **4 sempre presenti + 3 in pannelli `???`**, ognuno intitolato *nome — quando compare*. Corretto lo Step 2. Il vecchio «Step 4» (risoluzione asset, data di apertura, avvisi, duplicati contro il DB) confluisce nel nuovo **Step 4 · Review & Import**, che è dove quel lavoro avviene davvero |
| `user/assets/create-edit.en.md` | Nuova sezione **🧲 Merging duplicate assets**: i due tempi, la tabella di ciò che migra, l'avviso che l'operazione è distruttiva, e l'aggancio dal wizard |
| `developer/frontend/components/features/import-wizard.md` | Sostituita la tabella di flusso **a 4 righe, stantia da mesi**, con il modello a 7 step, il predicato `stepIsActive` verbatim, e la spiegazione del perché `assets` precede `fix`. Nuova sezione sui tre componenti di step |
| `developer/frontend/components/features/asset-identity.md` | **Nuova pagina**: motore di similarità, override come partizione intera, elezione del primario con le sue quattro inneschi, endpoint di merge con le due trappole d'ordine trovate dai test, e la scala di priorità dei candidati |
| `developer/backend/brim/architecture.md` | Nuova sezione **⚡ Concurrency & off-loading**: `to_thread` per l'upload, il process pool per il parse, la ricerca in blocco, l'euristica del frontend |
| `mkdocs.yml` | Voce di nav *Asset Identity* accanto a *Import Wizard* |

### Due scelte di forma che hanno sostanza

**Il titolo del pannello porta la condizione, non solo il nome.** «🧬 Unify Assets» da solo
lascia il lettore a chiedersi perché lui non l'abbia mai visto; *«— appears when the same
security was found under more than one name or code»* glielo dice **prima** che apra il
pannello. È l'unica forma in cui un indice di step condizionali resta leggibile da chi ne vede
un sottoinsieme.

**I pannelli sono `???` e non `!!!`.** Collassati di default: chi legge la guida per importare un
file Degiro pulito scorre quattro step e non incontra un muro di casi che non lo riguardano;
chi ha il problema apre il pannello e trova tutto. La regola di indentazione a 4 spazi
(`mkdocs.instructions.md`) è rispettata anche nelle admonition annidate — le nested `!!! tip` /
`!!! danger` dentro i `???` sono state verificate nel sito generato, non solo nel sorgente.

### Verifiche

`./dev.py mkdocs build` **pulito** — 0 warning, 0 link rotti, 4 lingue costruite in 22.9s ·
`./dev.py mkdocs check-links` **18/18 validi** (l'unico rosso, `${lang`, è un falso positivo
preesistente su `AboutTab.svelte:145`, file non toccato) · i tre `<details>` verificati nel sito
generato con le admonition annidate intatte.

> Le versioni `.it/.fr/.es` restano indietro **per progetto**: la pipeline Aphra le rigenera
> dall'inglese (`./dev.py mkdocs translate`), e la consegna richiesta era «solo la parte inglese».

---

# 🏁 Riepilogo finale di P3 — consegna e passaggio di consegne

> **Documento di handoff.** Scritto per l'agente che coordinerà la chiusura di P1 e P3.
> Contiene: cosa è stato consegnato, i fuori pista (che sono la parte più istruttiva),
> e i **task residui — tutti e soli di test**.
> Ultimo aggiornamento: **12/08/2026**.

---

## 1. Stato in una riga

**Il codice di P3 è completo e accettato dal committente.** Ciò che resta è **esclusivamente la
formalizzazione dei test E2E**, deliberatamente rinviata: durante lo sviluppo il committente ha
provato a mano e dettato l'estetica, con la regola esplicita di non scrivere test UI finché
l'interfaccia non fosse approvata. Ora lo è.

---

## 2. Il problema che P3 doveva risolvere

Un titolo può presentarsi a LibreFolio sotto più nomi e più codici. Il caso che ha rotto il
beta-test sono i **BTP retail a doppio ISIN**: si sottoscrivono con un codice ("CUM", che dà
diritto al premio fedeltà ma **non è negoziabile**) e si scambiano con un altro, **l'unico
quotato**. Per LibreFolio sono lo stesso strumento, e il premio finale è un `INTEREST` sull'asset
il giorno in cui arriva.

L'invariante che ne discende governa tutto il resto:

> `identifier_isin` contiene **solo il codice quotato**. Tutto il resto vive in
> `identifier_other`, dove non quota ma **riconosce**.
> Un prezzo è il valore dell'ultimo scambio: un codice che non si può scambiare non può avere un
> prezzo, e metterlo nel campo principale rende l'asset silenziosamente non prezzabile.

---

## 3. Cosa è stato consegnato

### 3.1 Il motore di identità (logica pura, testabile senza UI)

| File | Ruolo | Test |
|---|---|---|
| `lib/utils/assetSimilarity.ts` | Pesa l'evidenza che due estrazioni siano lo stesso titolo | **31** |
| `lib/utils/assetGrouping.ts` | Union-find sui link, override, elezione del primario | **47** |
| `lib/utils/assetIdentifiers.ts` | Quando un identificativo va chiesto invece che sovrascritto | **29** |
| `lib/utils/core/requestConcurrency.ts` | Concorrenza limitata e ordinata per i loop di rete | **12** |

La regola cardine di `compareAssets`: **solo i link `strong` uniscono da soli**; i `weak`
uniscono *e marcano il gruppo `proposed`*, così la UI chiede invece di assumere. E un
**disaccordo su un token numerico è un no definitivo** — è ciò che distingue `BTP 1/3/32` da
`BTP 1/3/35` per quanto simili appaiano.

### 3.2 I componenti

| Componente | Cosa risolve |
|---|---|
| `import/AssetGroupStep.svelte` | Lo step «Unifica strumenti»: tre stati visivi (verde pieno = certo, ambra tratteggiato = proposta, grigio = da solo), unione/separazione da menu `⋮` **e** da drag, elezione del codice principale con la ⭐, rinomina, ripristino totale |
| `import/ImportAssetPicker.svelte` | **Un solo campo** al posto di due select: sezioni invece di modalità, footer «Crea» sempre visibile che porta con sé il testo digitato |
| `assets/IdentifierPrimaryChooser.svelte` | Elezione a N vie con badge di provenienza (provider / già salvato / dal report), preambolo che nomina il provider, nota sull'emissione generalizzata, avviso se si annulla |
| `assets/AssetMergeModal.svelte` | Fusione in due tempi di duplicati **già in archivio**, con conteggi reali da dry-run |
| `ui/select/optionFilter.ts` | Intestazioni di sezione come primitiva di `SearchSelect`: non matchano mai la query, saltate da tastiera, e **cadono se il filtro ha svuotato la loro sezione** |

### 3.3 Il backend

- **`POST /api/v1/assets/merge`** (`asset_source.py:4223`) — `dry_run` + esecuzione, transazione
  unica. Gestisce tutte e quattro le FK verso `assets.id`; `identifier_other` del sopravvissuto
  diventa l'**unione**, non una sostituzione.
- **`search_asset_candidates`** — le priorità 1 e 2 (ISIN primario + ISIN in `identifier_other`)
  ora girano **insieme** e si fondono, invece di essere in cascata.

### 3.4 Fuori pista che hanno prodotto lavoro reale

Nessuno di questi era nel piano iniziale; ognuno è nato da una prova del committente.

| # | Fuori pista | Esito |
|---|---|---|
| **1** | **Il raggruppamento andava spostato *prima* delle correzioni** | Riordinati gli step. Il picker dello step correzioni deriva dalle risoluzioni: unificare dopo mostrava lo stesso titolo due volte, indistinguibile, e metà righe finivano su metà strumento |
| **2** | **Il suffisso "neutro" era un glossario privato** | Rimossa la lista hard-coded (`CUM`, `EX`, `ACC`…): riconosceva solo i marcatori a cui qualcuno aveva pensato. Ora il giudizio è **strutturale** — *pochi token, corti, non numerici* — e il prezzo è dichiarato: non distingue `CUM` da `ESG`, quindi propone e non decide mai |
| **3** | **La ricerca partiva dalla 4ª lettera** | Valuta e tipo asset erano nel testo cercabile: in una libreria tutta in EUR, `eur` matchava tutto. Stessa classe di bug su `option.icon`, che per gli asset è un *percorso* (`/icons/asset-types/bond.png`) |
| **4** | **«Tieni com'è» non resettava** | Accettare una riga senza prima azzerarla la lasciava con una correzione applicata sotto un'etichetta che la negava. E modificare una riga già decisa ora fa **decadere** la decisione |
| **5** | **Import sequenziale** (P‑01) | Upload e parse erano `for … await`, e i due endpoint facevano I/O sincrono dentro `async def`, violando la regola del progetto **documentata nello stesso file**. Aggiunti `brim_parse_pool` (process pool), `to_thread` per l'upload, `search_asset_candidates_bulk` (una query per file invece di ~150), e concorrenza limitata sul frontend |
| **6** | **Domande di architettura sulla ricerca provider** | Verificato sul codice: la ricerca è **già parallela** (SSE, un task per provider); il link-finder web è un fallback **per-provider**, non un ultimo appello globale, e **solo Borsa Italiana** lo dichiara. *Segnalato e non deciso*: la cache di 15 minuti memorizza **anche i risultati vuoti** |
| **7** | **Documentazione** (F‑02 bis) | 5 pagine mkdocs, di cui una nuova (`asset-identity.md`). La guida utente prometteva «5 step»: il wizard ne ha **7**, e tre non ci sono quasi mai |
| **8** | **Immagini della doc invisibili nella nightly** (I2 di P6) | Il fallback puntava a `alfystar.github.io`, residuo pre-migrazione all'organizzazione → **404 sistematico**. Ora l'URL è **derivato da `site_url`** via `overrides/main.html`, così non può più divergere. Verificato in Chromium riproducendo la nightly: **11/11 immagini** recuperate da Pages |

> Il fuori pista **8** ha anche corretto la diagnosi del piano P6, che attribuiva il guasto al
> build Docker locale: la nightly nasce da `release.yml`, dove il passo screenshot è
> `continue-on-error` su `dev` **per scelta**. È esattamente lo scenario per cui il fallback
> esiste — ed era l'unica rete, col buco.

---

## 4. Verifiche già eseguite (tutte verdi)

| Comando | Esito |
|---|---|
| `./dev.py test db asset-merge` | **12** passati |
| `./dev.py test db brim-bulk` | **4** passati |
| `./dev.py test services brim-parse-pool` | **8** passati |
| `./dev.py test db brim` | **17** passati (nessuna regressione) |
| `./dev.py front check` | **0 errori / 0 warning** |
| vitest | **595** passati su 54 file |
| `./dev.py i18n audit` | **2484/2484**, 0 incomplete su 4 lingue |
| `./dev.py front build` | ok |
| `./dev.py mkdocs build` | 0 warning, 0 link rotti |

---

## 5. ⏳ Task residui — sono **tutti** di test

> **Nessun task di produzione è aperto.** Quanto segue è la formalizzazione rinviata per
> decisione del committente (08/08/2026): niente test UI durante lo sviluppo, il committente
> prova a mano e detta l'estetica; gli E2E si scrivono alla fine, sulla UI già approvata.
> Quel momento è adesso.

### ⚠️ Vincolo di coordinamento — perché questo richiede un piano condiviso con P1

Gli E2E **non possono girare in parallelo** tra i due agenti: condividono la porta backend di
test **6041**, la **5173** del frontend e **lo stesso database di test**. Due suite in
contemporanea si corrompono i dati a vicenda. Serve un solo esecutore per volta, o una sola
suite unificata.

Inoltre P1 e P3 attraversano **lo stesso wizard**: un E2E che copre l'import Crédit Agricole
passa necessariamente per lo step di unificazione asset, e uno che copre l'unificazione ha
bisogno di un file parsato. **Conviene una suite sola, non due che si sovrappongono.**

### F‑01 — Il percorso end-to-end del BTP CUM

Il test che chiude il problema d'origine, da scrivere per intero:

1. Import di un report con un titolo sotto il **codice CUM**.
2. Secondo import dello stesso titolo sotto il **codice di mercato**.
3. Lo step **Unifica strumenti** li propone insieme (link `weak`, gruppo `proposed`).
4. Si elegge come principale il **codice quotato**; il CUM finisce fra gli alternativi.
5. Un terzo import che porta **solo** il CUM riconosce l'asset esistente (priorità 2).
6. Il **premio fedeltà** si registra come `INTEREST` sull'asset **anche dopo la disattivazione**.

### F‑03 — Validazione finale congiunta

`./dev.py front check` · test backend `--filter brim` e `--filter asset` · test frontend
`--filter import` · `i18n audit` · **`./dev.py api sync` una volta sola**, concordata fra i due
agenti (sono modifiche API di entrambi).

### Copertura E2E mancante — misurata, non stimata

Nessuno dei `data-testid` dei componenti nuovi compare negli E2E esistenti:

| `data-testid` | Spec che lo usano |
|---|---|
| `import-wizard-step-assets` | **0** |
| `asset-group-reset` | **0** |
| `fix-step-asset-trigger` | **0** |
| `asset-modal-primary-chooser` | **0** |
| `asset-merge-modal` | **0** |

Gli spec da estendere sono `frontend/e2e/transactions/tx-brim-import.spec.ts` (321 righe) e
`tx-import-resolution.spec.ts` (643 righe) — quest'ultimo descrive **il flusso a 5 step, ormai
superato**: prima di aggiungervi casi va riallineato ai 7 step condizionali, altrimenti si
costruisce sopra un modello che non esiste più.

### Casi che meritano un test perché sono già stati sbagliati una volta

Non sono ipotesi: ognuno corrisponde a un difetto realmente trovato e corretto.

1. **Gli step condizionali compaiono solo quando servono** — `assets`, `fix` e `duplicates`
   hanno tre predicati distinti; un import pulito non deve vederne nessuno.
2. **`assets` precede `fix`** — con lo stesso titolo in due file, il picker delle correzioni
   deve mostrarne **uno**.
3. **Le collisioni col database non aprono lo step duplicati** — arrivano deselezionate alla
   revisione.
4. **L'override di raggruppamento sopravvive a un re-parse** — è chiavato sul *contenuto*, non
   sul `fakeAssetId`, che viene riallocato.
5. **Il chooser non si chiude in silenzio** — click fuori o annulla mostrano l'avviso.
6. **La fusione non perde identificativi** — `identifier_other` del sopravvissuto è l'*unione*.
7. **Un asset disattivato resta selezionabile** — senza questo, il premio fedeltà è
   irregistrabile: è il caso d'uso che ha fatto nascere il piano.

---

## 6. Punti lasciati aperti di proposito

| Punto | Stato |
|---|---|
| La cache L2 della ricerca provider memorizza **anche i risultati vuoti** del link-finder | Segnalato al committente, **nessuna decisione presa**. Non tocca P3 |
| `AssetModal.svelte:668/788` usa `toLowerCase()` grezzo invece di `normalizeAssetName` per la collisione di nome | Deriva nota, non corretta: è nel percorso di P1 |
| Le traduzioni `.it/.fr/.es` della documentazione sono indietro | **Per progetto**: la pipeline Aphra le rigenera dall'inglese |
| Gli screenshot dei nuovi step non esistono su GitHub Pages | `gh-deploy` gira solo da `main`/release. Il fallback copre le immagini esistenti, non quelle nuove |

---

## Chiusura — blindatura a test (08/08/2026) ✅

UI approvata dal committente ⇒ si formalizzano i test rinviati.

### Test scritti

| Livello | File | Test | Cosa fissa |
|---|---|---|---|
| Backend | `test_api/test_asset_merge_api.py` *(nuovo)* | **7** | `POST /assets/merge` aveva 12 test di servizio e **zero** test HTTP: dry‑run che non scrive, migrazione di transazioni/prezzi/eventi/assegnazioni, `identifier_other` come **unione** e non sostituzione, asset altrui ⇒ 403 (non 404: non deve rivelare l'esistenza), sorgente = destinazione ⇒ 400 |
| E2E | `tx-import-asset-identity.spec.ts` *(nuovo)* | **7** | AID‑001…007 sullo step «Unifica strumenti»: i tre stati (certo/proposto/solo), conferma e separazione, ripristino, elezione del codice principale, rinomina, unione ed estrazione manuale dal menu ⋮, e la **sopravvivenza dell'override a un giro avanti/indietro** |
| E2E | `assets/asset-merge.spec.ts` *(nuovo)* | **3** | AM‑001…003 sulla fusione di due asset già in archivio: anteprima da dry‑run, conferma che sposta la storia e ritira il duplicato, sopravvissuto che eredita entrambi gli ISIN |

### La fixture del doppio ISIN

Il caso che ha fatto nascere P3 — lo stesso BTP sotto codice di collocamento e codice quotato —
**non è producibile** con il plugin generico: porta un solo identificativo per riga. Serve un
formato che porti nome **e** ISIN insieme: **Fineco** (`Titolo,Isin`). Da qui due fixture nuove,
`fineco_btp_placement.csv` e `fineco_btp_market.csv`, sondate direttamente sul provider **prima**
di scrivere lo spec, per non inseguire un fallimento di fixture dentro Playwright.

Insieme accendono i tre stati in un colpo solo: `BTP 20‑25 1.40% CUM` (IT0005410912) e
`BTP 20‑25 1.40%` (IT0005416570) ⇒ gruppo **proposto**; lo stesso iShares in entrambi i file ⇒
gruppo **certo**; il covered bond in uno solo ⇒ **singolo**.

### Difetto trovato **dal test**

> **⚠️ Fuori pista** — `AssetMergeModal` passava `allowOverflow={true}` a `ModalBase` per far
> uscire il menu a tendina del bersaglio. Ma `allowOverflow` mette `overflow: visible` sul
> contenitore, e con `overflow: visible` il `max-height: 90vh` **non genera scroll**: al secondo
> step, che è lungo (anteprima + scelta dell'ISIN primario + spiegazione + avviso distruttivo),
> i pulsanti «Indietro / Annulla / Unisci ed elimina» finivano **fuori dal viewport e
> irraggiungibili**. Playwright lo ha detto senza ambiguità: *element is outside of the
> viewport*, 222 tentativi di click. Corretto rendendo l'overflow condizionale allo step
> (`allowOverflow={step === 1}`) e dando al corpo del secondo step
> `max-h-[85vh] overflow-y-auto`.
>
> È un difetto che a mano si vede solo su schermi bassi o con zoom alto — esattamente la classe
> di problemi per cui gli E2E valgono il loro costo.

### Note per chi tornerà su questi spec

- `POST /transactions/commit` risponde **200 anche quando rifiuta**: l'esito vero è
  `committed: true/false` con le ragioni in `issues`. Un `expect(res.ok())` da solo non prova
  niente — la fixture della fusione sembrava creata e invece l'acquisto era stato respinto per
  saldo cassa negativo, e il dry‑run mostrava `transactions: 0`.
- Non esiste `GET /assets/{id}`: l'esistenza si legge da `GET /assets?asset_ids=…`, ma **gli
  identificativi no** — quelli stanno solo in `GET /assets/all`.

---

## Seguito — P7, coverage JavaScript

Questo piano ha prodotto un rilievo che va oltre il proprio ambito: **quasi tutti i difetti si
nascondevano in codice frontend che nessuna misura sorvegliava**. Da lì nasce
[`plan-phase00FrontendCoverage.prompt.md`](plan-phase00FrontendCoverage.prompt.md) (P7), che
introduce la coverage di `.svelte`/`.ts` accanto a quella Python.

La misura che lo giustifica: gli oltre 60 spec E2E aggiungono **15 statement Python su 37.331**
(lo 0,04 %) alla copertura del backend, mentre le **134.051 righe di frontend** su cui agiscono
davvero non venivano registrate in alcun modo.

Onestà del bilancio: sui difetti effettivamente trovati qui, la coverage ne avrebbe segnalati
**circa la metà** — quelli dovuti a codice mai eseguito. Sugli altri (ricerca dalla 4ª lettera,
ordine del raggruppamento, dizionario di suffissi hard-coded) non avrebbe detto niente, perché
quel codice girava: era sbagliato, non morto.
