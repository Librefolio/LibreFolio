# 09 — Frontend: Componenti & Feature

> `src/lib/components/` (219 file, 80 515 righe), `src/routes/` (22 file, 11 553)
> — esclusa `features/ai-export/`
> Gravità massima: 🟡

---

## Sintesi

I componenti sono il 60 % del frontend e producono **20 file inutilizzati**, di cui 4
componenti reali e una libreria interna completa.

Ma la scoperta più significativa non è il codice morto in sé: è che **11 dei 20 file
inutilizzati sono file `index.ts` di barrel export**. Il progetto ha adottato il pattern
dei barrel, poi ha smesso di usarlo — i componenti si importano per percorso diretto — e
i barrel sono rimasti a marcire.

Questo spiega anche perché knip segnala 25 export di componenti come inutilizzati: sono
in gran parte ri-esportazioni dentro barrel che nessuno importa. Il conteggio si sgonfia
appena si capisce la causa.

Fra i quattro componenti realmente morti, tre hanno una storia chiara di sostituzione;
uno no.

---

## Metriche

| Area | File | Righe |
|---|---:|---:|
| `lib/components/` | 219 | 80 515 |
| `routes/` | 22 | 11 553 |

| Categoria | N |
|---|---:|
| File inutilizzati | **20** |
| — di cui barrel `index.ts` | 11 |
| — di cui componenti reali | 4 |
| — di cui libreria interna | 3 |
| — di cui helper e2e | 1 |
| Export di componenti inutilizzati | 25 |
| Tipi di componenti inutilizzati | 32 |

Righe di codice nei 4 componenti morti + `tanstack-table`: **1 106**.

---

## Reperti

### 🟡 I1 — 4 componenti morti, 918 righe

| Componente | Righe | Stato |
|---|---:|---|
| `fx/FxProviderConfig.svelte` | 314 | superato? — da verificare |
| `layout/LiveTicker.svelte` | 233 | rimosso dall'interfaccia |
| `brokers/BrokerImportFiles.svelte` | 223 | **superato** |
| `dashboard/HoldingsPanel.svelte` | 148 | **superato** |

#### `HoldingsPanel.svelte` — assorbito, rimozione sicura

```
HoldingsPanel — Compact read-only list of current portfolio holdings.
Shows a summary table of holdings from portfolioStore.fetchSummary().
Columns: Asset (icon + name), Current Price, Value, Gain%.
```

> **Tracciatura**: `PositionsPanel.svelte` — vivo e usato in
> `brokers/[id]/+page.svelte:577` — dichiara nel proprio docstring quattro viste, la prima
> delle quali è *"Holdings / Table: snapshot of open positions at date_to (weights,
> unrealized P&L, PMC)"*. **La logica è assorbita e ampliata**: il sostituto mostra più
> colonne (pesi, PMC) e aggiunge tre viste ulteriori (treemap, performance, attribuzione).

Zero riferimenti nel codebase, nemmeno in un barrel. Rimozione sicura.

#### `BrokerImportFiles.svelte` — assorbito, rimozione sicura

> **Tracciatura**: esiste `BrokerImportFilesModal.svelte`, vivo e usato in
> `brokers/[id]/+page.svelte:759`. È la stessa funzionalità riconfezionata come modale. Il
> commento in `ModalBase.svelte:15` conferma che il modale è parte dell'architettura
> corrente (*"60 = second-level modals (e.g. FileEditModal over BrokerImportFilesModal)"*).

La versione non-modale è il predecessore. Rimozione sicura.

#### `LiveTicker.svelte` — rimosso dall'interfaccia, logica non riassorbita

Referenziato solo dal barrel `layout/index.ts:6` (a sua volta morto) e da **commenti** in
tre file diversi:

- `stores/reference/assetStore.ts:9` — *"matching the existing pattern used by
  `/assets/+page.svelte` and `LiveTicker`"*
- `components/assets/AssetModal.svelte:1158` — *"(transactions cell, AssetCard,
  LiveTicker, …) reflect the entry"*
- `components/assets/AssetModal.svelte:1297` — *"every consumer (transactions cell,
  AssetCard, LiveTicker, …) sees"*

> **Tracciatura**: i commenti descrivono `LiveTicker` come **consumatore attivo** della
> propagazione dei prezzi. Non esiste un sostituto: la funzionalità "striscia di prezzi in
> tempo reale" **non c'è più nell'interfaccia**.

Questo è un caso da discutere, non da risolvere con uno scan. Il componente è stato tolto
dall'interfaccia — deliberatamente o durante un rifacimento del layout — ma nessuno ha
aggiornato i commenti che lo citano. Le opzioni:

- **Era una funzionalità voluta e va ripristinata** → il codice c'è, serve rimetterlo nel
  layout;
- **È stata abbandonata** → rimuovere il componente **e correggere i tre commenti**, che
  altrimenti continueranno a indicare un consumatore inesistente a chi legge il codice fra
  sei mesi.

#### `FxProviderConfig.svelte` — da verificare

314 righe, il più grande dei quattro. Referenziato solo dal barrel `fx/index.ts:7` e da un
commento in `OrderableList.svelte:14` (*"Used by: FxProviderConfig, DataTableToolbar
(future), etc."*) che quindi è **anch'esso obsoleto**.

Contiene la logica di visualizzazione delle catene di conversione FX — la stessa che
`FxPairAddModal.svelte` e `fx/[pair]/+page.svelte` reimplementano inline (vedi report
[06](06_db_models.md), reperto F1).

> **Tracciatura**: parzialmente assorbita. La configurazione delle rotte FX esiste ancora
> nell'interfaccia, ma passa da altri componenti. Se questo era il pannello di
> configurazione completo e ora è frammentato in più modali, allora è superato. Se invece
> offriva una vista d'insieme che oggi manca, è una regressione funzionale.

Da verificare aprendo l'applicazione: esiste ancora una schermata che mostra tutte le
rotte FX configurate con il loro ordine di priorità?

---

### 🟡 I2 — `src/lib/tanstack-table/`: libreria interna mai usata

| File | Righe |
|---|---:|
| `createSvelteTable.svelte.ts` | 98 |
| `index.ts` | 64 |
| `FlexRender.svelte` | 26 |
| **Totale** | **188** |

Un adattatore Svelte 5 per TanStack Table, scritto a mano (l'adattatore ufficiale per
Svelte 5 non era disponibile al tempo). Nessun consumatore.

> **Tracciatura**: le tabelle dell'applicazione usano un'implementazione propria — il
> progetto ha `DataTable` e componenti correlati sotto `components/ui/`. **La
> funzionalità esiste, per altra via.**

Trascina con sé la dipendenza npm `@tanstack/table-core` (vedi report
[08](08_frontend_state_api.md), reperto H8).

**Rimedio**: rimuovere directory e dipendenza insieme. 188 righe di codice e una
dipendenza esterna in meno, senza alcun impatto — è la rimozione con il miglior rapporto
valore/rischio del frontend.

L'unica cautela: se l'intenzione era migrare a TanStack Table in futuro, va detto
esplicitamente prima di cancellare. Ma un adattatore scritto e mai usato per un anno è
più probabilmente un esperimento concluso.

---

### 🟡 I3 — 11 barrel `index.ts` morti: un pattern abbandonato a metà

```
src/lib/index.ts
src/lib/components/assets/index.ts
src/lib/components/charts/index.ts
src/lib/components/fx/index.ts
src/lib/components/layout/index.ts
src/lib/components/settings/tabs/index.ts
src/lib/components/ui/index.ts
src/lib/components/ui/data-editor/index.ts
src/lib/components/ui/date/index.ts
src/lib/components/ui/display/index.ts
src/lib/components/ui/input/index.ts
src/lib/components/ui/modals/index.ts
```

> **Tracciatura**: nessuna logica — sono solo ri-esportazioni. Ma hanno **due effetti
> collaterali negativi concreti**:
>
> 1. **Falsano l'analisi del codice morto.** `FxProviderConfig`, `LiveTicker` e
>    `BrokerImportFiles` sono referenziati *solo* dai rispettivi barrel. Se knip non
>    avesse rilevato che i barrel stessi sono morti, quei tre componenti sarebbero
>    apparsi vivi. Un barrel morto è un **conservante per il codice morto**.
> 2. **Generano rumore.** Gran parte dei 25 "export di componenti inutilizzati" sono
>    ri-esportazioni dentro questi file.

La conclusione è netta: il pattern dei barrel è stato adottato, poi abbandonato in favore
degli import per percorso diretto, e i file sono rimasti.

**Rimedio**: rimuovere tutti e 12 (11 sotto `components/` più `src/lib/index.ts`). Prima
però va **rieseguito knip**: eliminati i barrel, alcuni componenti oggi "vivi solo grazie
al barrel" emergeranno come morti. È il motivo per cui questa rimozione va fatta *presto*
— ogni altra analisi di codice morto sul frontend è distorta finché i barrel esistono.

Se invece si vuole tornare ai barrel come stile, allora vanno usati davvero: import da
`$lib/components/ui` invece che da `$lib/components/ui/Button.svelte`. Mezza adozione è
peggio di entrambe le scelte.

---

### 🟢 I4 — 32 tipi di componenti inutilizzati

Distribuiti su tutta la gerarchia dei componenti. Come per i 43 tipi di `lib/types/`
(report [08](08_frontend_state_api.md), reperto H7), non contengono logica e la rimozione
è priva di rischio funzionale.

Sospetto che una quota significativa siano tipi di prop esportati per essere riusati da
componenti figli, che poi hanno definito i propri. Vale la stessa raccomandazione: prima
un campione, poi la decisione.

---

### 🟢 I5 — `e2e/fixtures/db-helpers.ts` inutilizzato

Unico file di test fra i 20. Helper per la manipolazione diretta del database nei test
end-to-end, mai importato.

> **Tracciatura**: i test e2e preparano lo stato tramite API o fixture applicative, non
> toccando il DB. È l'approccio più robusto, quindi l'abbandono di questi helper è
> probabilmente **deliberato**.

Rimozione sicura. Se invece serviva per scenari che oggi non si riescono a preparare via
API, va detto — ma allora andrebbe usato.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Rimuovere i 12 barrel morti, poi **rieseguire knip** | basso | basso |
| 2 | Rimuovere `src/lib/tanstack-table/` + `@tanstack/table-core` | basso | nullo |
| 3 | Rimuovere `HoldingsPanel.svelte` e `BrokerImportFiles.svelte` (assorbiti) | basso | nullo |
| 4 | **Decidere su `LiveTicker`**: ripristinare o rimuovere + correggere 3 commenti | — | — |
| 5 | **Verificare `FxProviderConfig`**: esiste ancora una vista d'insieme delle rotte FX? | basso | — |
| 6 | Rimuovere `e2e/fixtures/db-helpers.ts` | basso | nullo |
| 7 | Campionare i 32 tipi orfani prima di decidere | basso | — |

L'ordine conta. L'intervento 1 va **prima** di tutti gli altri, perché finché i barrel
morti esistono l'analisi del codice morto sul frontend non è attendibile: stanno tenendo
in vita simboli che nessuno usa davvero.

Gli interventi 4 e 5 sono i due che richiedono una decisione umana. Entrambi riguardano
funzionalità che *sembrano* essere sparite dall'interfaccia senza che il codice sia stato
rimosso — e in entrambi i casi il codebase contiene ancora commenti che le descrivono
come vive.
