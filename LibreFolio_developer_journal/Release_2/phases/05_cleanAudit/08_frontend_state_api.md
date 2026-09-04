# 08 — Frontend: Store & API

> `src/lib/stores/` (43 file, 6 665 righe), `src/lib/api/` (4 file, 17 050),
> `src/lib/workers/`, `src/lib/utils/`
> Gravità massima: 🟡

---

## Sintesi

Il livello di stato del frontend concentra **26 export inutilizzati su 79** — un terzo del
totale, sul 5 % delle righe. Ma anche qui il numero grezzo nasconde la struttura reale:
le 26 rilevazioni si riducono a **quattro famiglie**, tre delle quali sono lo stesso
errore ripetuto.

La famiglia più numerosa è quella delle **bandiere di caricamento** (`isXLoaded`,
`isXLoading`): otto export generati da un pattern applicato uniformemente a tutti gli
store di riferimento, che nessun componente consuma. Non è codice sbagliato — è un
contratto che i consumatori hanno scelto di non usare.

`src/lib/api/` è il file più grande del frontend (17 050 righe in 4 file), ma è quasi
tutto generato: `generated.ts` è escluso dagli scan per costruzione.

---

## Metriche

| Area | File | Righe | Export inutilizzati |
|---|---:|---:|---:|
| `lib/stores/` | 43 | 6 665 | **26** |
| `lib/utils/` | 49 | 5 604 | 6 |
| `lib/api/` | 4 | 17 050 | 3 |
| `lib/workers/` | — | — | 1 |

Tipi esportati inutilizzati: 43 in `lib/types/`, 3 in `lib/stores/`, 1 in `lib/api/`.

---

## Reperti

### 🟡 H1 — 8 bandiere di caricamento mai consumate

```
isAssetsLoaded       (reference/assetStore.ts)
isBrokersLoaded      (reference/brokerStore.ts)
isCountriesLoaded    (reference/countryStore.ts)
isCountriesLoading   (reference/countryStore.ts)
isCurrenciesLoading  (reference/currencyStore.ts)
isFxRoutesLoaded     (reference/fxRoutesStore.ts)
isFxRoutesLoading    (reference/fxRoutesStore.ts)
isSectorsLoaded      (reference/sectorStore.ts)
```

Ogni store di riferimento espone la propria coppia `isXLoaded` / `isXLoading`. Nessuna è
importata da alcun componente.

> **Tracciatura della logica**: la logica **non è persa**. I componenti gestiscono il
> caricamento in altro modo — tipicamente attendendo la promise di `fetchX()` o
> controllando direttamente se la collezione è vuota. Le bandiere sono un'API alternativa
> che è stata costruita per simmetria e mai adottata.

L'asimmetria è indicativa: `countryStore` e `fxRoutesStore` espongono **entrambe** le
bandiere, `assetStore`, `brokerStore` e `sectorStore` solo `isXLoaded`, `currencyStore`
solo `isXLoading`. Se fossero parte di un contratto vivo, sarebbero uniformi. La forma
irregolare dice che sono state aggiunte per riflesso, copiando lo store precedente.

**Rimedio**: rimuoverle tutte e otto. È la rimozione più sicura del frontend — sono
derivazioni di stato interno già esposto, senza effetti collaterali, e non c'è nulla da
assorbire perché nulla le chiama.

Se invece si vuole standardizzare la gestione del caricamento, allora vanno rese uniformi
**e** adottate nei componenti. Ma è una scelta di design da fare esplicitamente, non da
lasciare a metà.

---

### 🟡 H2 — 4 accessori `txStore` mai usati

```
txStoreGetFiltered   (transactions/txStore.svelte.ts)
txStoreGetMain       (transactions/txStore.svelte.ts)
txStoreGetPartner    (transactions/txStore.svelte.ts)
txStoreGetVersion    (transactions/txStore.svelte.ts)
```

Quattro funzioni di accesso allo store delle transazioni — la parte più complessa dello
stato del frontend — nessuna consumata.

> **Tracciatura**: da verificare caso per caso. Il nome `txStoreGetVersion` suggerisce un
> meccanismo di invalidazione basato su versione; se il resto del codice usa un altro
> meccanismo (per esempio la reattività diretta delle Runes), l'accessore è residuo di un
> approccio precedente.

Diversamente da H1, qui **non consiglio la rimozione a scatola chiusa**. Lo store delle
transazioni ha una nozione di record "main" e "partner" (le transazioni collegate) che è
logica di dominio, non infrastruttura. Va guardato da chi conosce quel modello prima di
cancellare.

---

### 🟡 H3 — Registry di store: 4 funzioni orfane

```
ensureFxRangeLoadedBulk   (fxStoreRegistry.ts)
getFxStoreByPair          (fxStoreRegistry.ts)
removeAssetPriceStore     (assetPriceStoreRegistry.ts)
invalidateCurrencyGraph   (currencyGraphStore.ts)
```

I registry di store creano istanze per chiave (coppia FX, asset) e le mantengono in
cache. Le funzioni orfane sono quelle di **ciclo di vita**: recupero puntuale
(`getFxStoreByPair`), rimozione (`removeAssetPriceStore`), invalidazione
(`invalidateCurrencyGraph`), precaricamento bulk (`ensureFxRangeLoadedBulk`).

> **Tracciatura**: la creazione e la lettura degli store funzionano (altrimenti
> l'applicazione non mostrerebbe grafici). Manca la **rimozione**: nessuno chiama
> `removeAssetPriceStore`.

Questo merita attenzione, perché ha una conseguenza osservabile: se gli store per asset
si accumulano senza mai essere rimossi, una sessione lunga in cui l'utente apre molti
asset diversi fa crescere la memoria in modo monotono. Non è un difetto di correttezza,
ma è il tipo di problema che si manifesta solo dopo ore di uso.

**Rimedio**: verificare empiricamente se la cache degli store cresce senza limiti (basta
ispezionarne la dimensione dopo aver navigato fra molti asset). Se cresce, `removeAssetPriceStore`
va cablata a un punto di uscita — non rimossa.

`invalidateCurrencyGraph` è nella stessa categoria: se il grafo delle valute è memorizzato
e le rotte FX cambiano, senza invalidazione l'utente vede dati stantii fino al reload.

---

### 🟢 H4 — `language.ts`: 3 export di presentazione inutilizzati

```
availableLanguages   (app/language.ts)
currentLanguageFlag  (app/language.ts)
currentLanguageName  (app/language.ts)
```

> **Tracciatura**: il selettore di lingua nell'interfaccia costruisce l'elenco e mostra
> bandiera e nome **per conto proprio**. Stessa forma del *DRY orfano* già visto nel
> backend (report [07](07_schemas_utils.md), reperto G1): l'astrazione esiste, il
> consumatore la reimplementa.

**Rimedio**: farle usare al selettore di lingua. Sono tre righe da spostare e riducono a
uno i punti in cui è definita la lista delle lingue supportate — che con quattro lingue
(EN/IT/FR/ES) e possibili aggiunte future è un vantaggio concreto.

---

### 🟢 H5 — `api/`: `ApiError` e il default export di `zodios-client`

```
ApiError   (src/lib/api/index.ts)
default    (src/lib/api/zodios-client.ts)
```

`ApiError` non importata da nessuno: la gestione errori nei componenti si basa su
controlli generici invece che sul tipo dedicato. È l'occasione mancata di avere una
gestione errori tipizzata, coerente con la scelta di Zodios.

Il `default` di `zodios-client.ts` è probabilmente un falso positivo o un residuo: i
consumatori importano l'export nominale. Da verificare prima di toccarlo.

`downloadFxBackup` (`api/backupDownload.ts`) è invece un caso concreto: esiste il
download del backup FX ma nessun pulsante lo invoca. Da capire se la funzionalità è stata
rimossa dall'interfaccia o non ci è mai arrivata.

---

### 🟢 H6 — `utils/`: 6 export orfani, di cui 3 dello stesso modulo

```
cleanUrlParams            (utils/urlFilters.ts)
hasActiveFilters          (utils/urlFilters.ts)
createImageEditConfig     (utils/files/imageCrop.ts)
getDefaultOutputFileName  (utils/files/imageCrop.ts)
isSupportedImageType      (utils/files/imageCrop.ts)
uploadBrimFile            (utils/files/upload.ts)
```

Tre su sei vengono da `imageCrop.ts`. Correlato: `@types/cropperjs` risulta fra le
dipendenze npm inutilizzate (vedi H8). L'ipotesi più probabile è che il ritaglio immagini
sia stato sostituito da un altro approccio e siano rimasti gli helper.

`uploadBrimFile` merita una verifica a parte: l'upload dei file BRIM è una funzionalità
centrale e funzionante, quindi o passa da un'altra funzione (duplicazione) o questo helper
è la versione vecchia. Da tracciare prima di rimuovere.

`destroyPriceProcessingPool` (`workers/priceProcessingPool.ts`) è nella stessa famiglia di
H3: la funzione di distruzione del pool di worker non viene mai chiamata.

---

### 🟢 H7 — 43 tipi esportati inutilizzati in `lib/types/`

Su 84 tipi esportati inutilizzati totali, 43 vivono in `lib/types/`.

> **Tracciatura**: i tipi non contengono logica. Il rischio della rimozione è nullo dal
> punto di vista funzionale.

Il punto è **perché** ce ne sono così tanti. Due cause plausibili, con risposte opposte:

- Sono tipi scritti a mano che **duplicano** quelli generati da OpenAPI in
  `api/generated.ts`. In questo caso vanno rimossi: la fonte di verità è lo schema
  backend, e mantenere una seconda definizione a mano garantisce che prima o poi
  divergano.
- Sono tipi di dominio **frontend** che descrivono strutture interne, e semplicemente non
  hanno ancora consumatori.

Un campione di dieci nomi confrontati con `generated.ts` risolve la questione. La
raccomandazione dipende dall'esito, ma la prima ipotesi è la più probabile, ed è anche la
più importante da correggere: la tipizzazione end-to-end del progetto perde valore se
esiste una definizione parallela scritta a mano.

---

### 🟢 H8 — 6 dipendenze npm inutilizzate

| Pacchetto | Tipo |
|---|---|
| `@tanstack/table-core` | dependency |
| `topojson-client` | dependency |
| `@types/topojson-client` | dependency |
| `@types/cropperjs` | dependency |
| `date-fns` | dependency |
| `@types/katex` | devDependency |

`@tanstack/table-core` è legato all'intera directory `src/lib/tanstack-table/` risultata
inutilizzata (vedi report [09](09_frontend_components.md), reperto I2): rimuovendo quella,
cade anche la dipendenza.

`date-fns` è il caso più interessante: una libreria di manipolazione date non usata
significa che le date vengono gestite altrimenti — probabilmente con `Date` nativo o con
helper interni. Va confermato che non ci siano import residui prima di rimuoverla.

I tre `@types/*` sono dichiarazioni di tipo per librerie non più usate: rimozione sicura.

**Rimedio**: rimuoverle riduce il tempo di `npm install`, la dimensione di
`node_modules` e la superficie di aggiornamenti di sicurezza da monitorare. Va fatto
**dopo** aver deciso su `tanstack-table`, per non doverlo fare due volte.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Verificare la crescita della cache degli store per asset (H3) | basso | — |
| 2 | Rimuovere le 8 bandiere `isXLoaded`/`isXLoading` | basso | nullo |
| 3 | Campionare i 43 tipi orfani contro `generated.ts` | basso | — |
| 4 | Far usare `availableLanguages`/`currentLanguageFlag`/`Name` al selettore lingua | basso | basso |
| 5 | Tracciare `uploadBrimFile` e `downloadFxBackup` | basso | — |
| 6 | Rimuovere le 6 dipendenze npm inutilizzate | basso | basso |
| 7 | Decidere su `txStoreGet*` con chi conosce il modello main/partner | — | — |

L'intervento 1 è l'unico che potrebbe rivelare un difetto reale — una perdita di memoria
lenta. Gli altri sono pulizia.

L'intervento 3 è quello che può cambiare di più il quadro: se i 43 tipi duplicano lo
schema generato, il problema non è che sono inutilizzati, è che **esistono**.
