# 08 — Stato & API frontend — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/08_frontend_state_api.md)
> Metodo: analisi statica read-only; nessun test eseguito (run full in corso).
> Strumenti: `grep`/`find`/`git log --no-pager` + `npx knip --no-progress` (analisi
> statica, nessun server avviato; config `frontend/knip.json` invariata dal 2026-08-05,
> commit `b10449b6`). Working tree incluse le modifiche beta NON committate del 02/09.

---

## Sintesi esecutiva

Il grosso della pulizia S1–S3 (commit `be8394bb`, 2026-08-05) **ha tenuto**: zero barrel
morti rinati, zero bandiere `isXLoaded` rinate, le 6 dipendenze npm non sono tornate.
Riproducendo knip oggi: **0 file inutilizzati** (erano 20), **60 export inutilizzati**
(erano 79), **86 tipi esportati inutilizzati** (erano 84), **4 devDependency** segnalate
(falso positivo, vedi sotto).

Restano aperti i reperti di fondo che l'esecuzione S1–S3 aveva esplicitamente rimandato:
i 4 accessori `txStoreGet*` (H2), le 4 funzioni di ciclo di vita dei registry (H3), i 3
export di presentazione lingua (H4), `ApiError`/default/`downloadFxBackup` (H5) e i 43
tipi orfani di `lib/types/` (H7) sono **tutti ancora lì, immutati**. In compenso sono nati
**nuovi orfani** negli store (`dateRangeStore`, `notify`, `navigationStore`) e in
`version.ts`/`debug.ts`, e knip segnala 2 export duplicati.

| Metrica | Audit 2026-08-07 | Oggi 2026-09-02 | Comando |
|---|---:|---:|---|
| File inutilizzati (frontend) | 20 | **0** | `cd frontend && npx knip --no-progress` (nessuna sezione "Unused files") |
| Export inutilizzati | 79 | **60** | sezione "Unused exports (60)" |
| Tipi esportati inutilizzati | 84 | **86** | sezione "Unused exported types (86)" |
| Dipendenze npm inutilizzate | 6 | **4** (falso positivo, vedi Nuovi rilievi) | sezione "Unused devDependencies (4)" |
| `lib/stores/` (no test) | 43 file / 6 665 righe | 33 file / 5 236 righe | `find src/lib/stores -type f \( -name '*.ts' -o -name '*.svelte' \) ! -name '*.test.ts' ! -path '*__tests__*'` |
| `lib/utils/` (no test) | 49 / 5 604 | 73 / 7 727 | idem su `src/lib/utils` |
| `lib/api/` | 4 / 17 050 | 4 / 17 727 | idem su `src/lib/api` |

> Nota metriche: i conteggi 2026-08 includevano i test secondo una metodologia non
> interamente riproducibile (l'output grezzo di knip non fu archiviato). Da allora sono
> stati aggiunti molti test (commit `fecd5949` 30/08, `7ae1ef46`/`ce8db7af` 31/08) e
> l'esecuzione S1–S3 ha estratto `utils/core/`: i delta di file/righe sono quindi
> indicativi, non segnali di regressione. I confronti affidabili sono quelli knip
> (stessa config, stesso tool).

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| H1 — 8 bandiere `isXLoaded`/`isXLoading` morte | 🟡 aperto | **FATTO** | `grep -rn "is(Assets\|Brokers\|Countries\|Currencies\|FxRoutes\|Sectors)(Loaded\|Loading)" src/` → unica superstite `isCurrenciesLoaded` (`stores/reference/currencyStore.ts:133`), **ora usata** da `stores/currencyGraphStore.ts:18` (import) e `:69` (uso). Il doc S1–S3 (`15_esecuzione_s1_s3.md:159,351-355`) conferma: il numero vero era **9** bandiere (l'8° era un predicato di autenticazione finito nell'elenco per errore), tutte rimosse | nessuna; sorveglianza anti-rinascita |
| H2 — 4 accessori `txStoreGet*` mai usati | 🟡 aperto | **ANCORA VALIDO** | `txStore.svelte.ts:49` (`txStoreGetPartner`), `:62` (`txStoreGetMain`), `:67` (`txStoreGetFiltered`), `:97` (`txStoreGetVersion`); `grep -rn "txStoreGet…" src/` fuori dallo store → 0 risultati; knip 2026-09-02 li conferma tutti e 4 | decidere con chi conosce il modello main/partner (task T1) |
| H3 — 4 funzioni lifecycle registry orfane | 🟡 aperto | **ANCORA VALIDO** (uso produttivo = 0) | `removeAssetPriceStore` (`assetPriceStoreRegistry.ts:64`) e `invalidateCurrencyGraph` (`currencyGraphStore.ts:135`) mai chiamate, knip conferma. `getFxStoreByPair` (`fxStoreRegistry.ts:132`) e `ensureFxRangeLoadedBulk` (`:266`) **non più segnalate da knip perché importate dai test** (`stores/__tests__/fxStoreRegistry.test.ts:29,31`) — ma in produzione nessun chiamante (`grep` fuori da test: 0) | cablare o rimuovere (task T2, T3) |
| H3 — rischio crescita cache store per asset | 🟡 aperto | **ANCORA VALIDO** | `assetPriceStoreRegistry.ts`: unica scrittura di cancellazione è `stores.delete(key)` a `:68`, **dentro** `removeAssetPriceStore` che nessuno chiama; nessuna logica LRU/TTL (`grep "maxSize\|LRU\|evict"` → solo quel `delete`) | verifica empirica + cablaggio (task T2) |
| H4 — `availableLanguages`/`currentLanguageFlag`/`currentLanguageName` DRY orfano | 🟢 aperto | **ANCORA VALIDO** | Definiti a `stores/app/language.ts:105,110,116`; il selettore `components/layout/LanguageSelector.svelte:8` importa `LANGUAGE_OPTIONS` da `$lib/i18n` e ricava bandiera/nome per conto proprio (`:15` `$derived`, `:53,66,67`). knip conferma i 3 export orfani | adottare o rimuovere (task T4) |
| H5 — `ApiError` mai importata | 🟢 aperto | **ANCORA VALIDO** | `api/zodios-client.ts:181` (classe), ri-esportata `api/index.ts:26`; i consumatori importano solo `zodiosApi` (85 import da `$lib/api`), `schemas` (16), `axiosInstance` (7) — `grep -o` su `import {…} from '$lib/api'`. Nei test è mockata come classe locale (es. `PreferencesTab.test.ts:86`), mai importata quella vera. knip conferma | adottare nella gestione errori o rimuovere (task T5) |
| H5 — default export `zodios-client` | 🟢 aperto | **ANCORA VALIDO** | `api/zodios-client.ts:210` `export default zodiosApi`; `grep "import zodiosApi from\|import api from"` → 0. knip: `default` orfano + export duplicato `zodiosApi\|default` | rimuovere il default (task T5) |
| H5 — `downloadFxBackup` senza chiamante | 🟢 aperto | **ANCORA VALIDO** | `api/backupDownload.ts:82`; `grep -rn "downloadFxBackup" src/` → solo la definizione. knip conferma | ripristinare il pulsante o rimuovere (task T5) |
| H6 — `cleanUrlParams`/`hasActiveFilters` orfani | 🟢 aperto | **ANCORA VALIDO in produzione**, mitigato | `utils/urlFilters.ts:216` e `:191`; uso produttivo 0, ma ora importati da `utils/__tests__/urlFilters.test.ts:21` (test aggiunto 31/08, commit `7ae1ef46`) → knip non li segnala più | decidere la policy "test che congelano codice morto" (task T6) |
| H6 — 3 helper `imageCrop.ts` orfani | 🟢 aperto | **ANCORA VALIDO in produzione**, mitigato | `createImageEditConfig` (`imageCrop.ts:136`), `isSupportedImageType` (`:197`), `getDefaultOutputFileName` (`:204`): uso produttivo 0, importati solo da `imageCrop.test.ts:18` (30/08, `fecd5949`). Il resto del modulo è vivo: `blobToFile`/`getCroppedImageFromCropper`/`IMAGE_PRESETS` usati da `ui/media/ImageEditModal.svelte:19`, `isImageFile` da `FileUploader.svelte:14`; `cropperjs` usato a runtime da `ImageCropper.svelte:9` | task T6 |
| H6 — `uploadBrimFile` orfano | 🟢 aperto | **ANCORA VALIDO** | `utils/files/upload.ts:45`; `grep` → solo la definizione, nessun test. knip conferma. L'upload BRIM passa da altra via (come ipotizzato) | tracciare la via viva e rimuovere (task T7) |
| H6 — `destroyPriceProcessingPool` mai chiamata | 🟢 aperto | **ANCORA VALIDO** | `workers/priceProcessingPool.ts:97`; `grep` → solo la definizione. knip conferma | cablare a teardown o rimuovere (task T2) |
| H7 — 43 tipi orfani in `lib/types/` | 🟢 aperto | **ANCORA VALIDO** (stesso numero) | knip 2026-09-02: 43 tipi orfani in `lib/types/` (`asset.ts` 7, `broker.ts` 6, `common.ts` 8, `files.ts` 6, `settings.ts` 4, `transaction.ts` 5, `user.ts` 7) su 86 totali. Nessun campionamento contro `generated.ts` è stato fatto | campionare 10 nomi vs `generated.ts` (task T8) |
| H8 — 6 dipendenze npm inutilizzate | 🟢 aperto | **FATTO** | `grep "tanstack\|topojson\|cropperjs\|date-fns\|katex" package.json` → solo `cropperjs` (^2.1.0, **usata** a runtime) e `katex` (^0.16.38, **usata**: `Tooltip.svelte`, `SignalOptionContent.svelte`, `FilePreviewModal.svelte`, `inlineMath.ts`). Le 6 segnalate (`@tanstack/table-core`, `topojson-client`, `@types/topojson-client`, `@types/cropperjs`, `date-fns`, `@types/katex`) rimosse; `grep -rn "date-fns\|topojson\|@tanstack" src/ e2e/` → 0 import residui | nessuna |
| `generated.ts` escluso dagli scan | costruzione | **ANCORA VALIDO** | `knip.json` `ignore` contiene ancora `src/lib/api/generated.ts` | — |

---

## Dettaglio reperti ancora aperti / regrediti

### H2 — `txStoreGet*`: immutati, sempre senza consumatori

Le 4 funzioni sono rimaste parola per parola dove erano. La raccomandazione originale
(non rimuovere a scatola chiusa perché toccano il modello main/partner) resta corretta:
`txStoreGetPartner`/`txStoreGetMain` esprimono logica di dominio. Ma un anno di
runes-reattività ha reso l'accessore manuale ridondante di fatto — i componenti leggono
lo store direttamente. Decisione ancora da prendere.

### H3 — la cache cresce ancora senza limiti, e c'è una mezza novità

Nessuna eviction è stata aggiunta: il rischio "memoria monotona in sessioni lunghe" è
intatto. Novità in `currencyGraphStore.ts`: esiste ora `cachedProvidersHash` (scritto a
`:96`, azzerato a `:137`) con commento *"(for invalidation)"* a `:35-36` — **ma l'hash
non viene mai confrontato** (`grep cachedProvidersHash` → 3 sole occorrenze: dichiarazione,
scrittura, reset). È un meccanismo di invalidazione costruito a metà: o si completa
(confronto hash a ogni accesso → rebuild automatico al cambio provider) o si rimuove il
campo. `invalidateCurrencyGraph` stessa reca ora il commento *"Normally not needed — the
graph is stable for the session"* (`:130-133`): la decisione implicita è "non serve", e
allora la funzione + l'hash sono entrambi residui.

### Regressione lieve: nuovi orfani nati negli store e dintorni

knip 2026-09-02 segnala orfani che il vecchio report non elencava (esso dettagliava 19
dei 26 export store; questi potrebbero essere i 7 non dettagliati, ma senza l'output grezzo
archiviato non è dimostrabile — trattarli come **nuovi rilievi**):

- `getResolvedStart` / `getResolvedEnd` — `stores/dateRangeStore.svelte.ts:162,166`
- `eventsSince` / `currentSeq` / `resetEvents` — `stores/app/notify.svelte.ts:87,91,96`
- `_debugStack` — `stores/app/navigationStore.ts:100`
- `debugAssert` — `src/lib/debug.ts:84`
- `isReleaseVersion` / `isDirtyVersion` — `src/lib/version.ts:19,27`
- `date` / `time` / `number` — ri-export da svelte-i18n in `i18n/index.ts:108`
  (`locale`, `t`, `_`, `i18nLoading` dallo stesso statement sono invece usati)

### Export duplicati (nuova categoria knip)

- `zodiosApi|default` — `api/zodios-client.ts` (il default è il vecchio H5, confermato)
- `getTypeIconUrl|getTransactionTypeIconUrl` — `stores/transactions/transactionTypeStore.ts:183,195`:
  `getTransactionTypeIconUrl` è un alias (`export const … = getTypeIconUrl`). Entrambi i
  nomi hanno usi esterni (1 vs 29): convergere su un solo nome e aggiornare l'unico
  consumatore dell'altro.

---

## Task riesumati

| # | Task | Evidenza | Stima |
|---|---|---|---|
| T1 | Decidere `txStoreGet×4` (rimozione o adozione) con chi conosce il modello main/partner | `txStore.svelte.ts:49,62,67,97`; 0 usi | **S** |
| T2 | Verificare empiricamente la crescita della cache degli store per asset; se confermata, cablare `removeAssetPriceStore` a un punto di uscita (es. chiusura pagina dettaglio). Stessa decisione per `destroyPriceProcessingPool` | `assetPriceStoreRegistry.ts:64-68`; `priceProcessingPool.ts:97` | **M** (misura + cablaggio) |
| T3 | Risolvere la mezza invalidazione del grafo valute: completare il confronto di `cachedProvidersHash` **oppure** rimuovere campo + `invalidateCurrencyGraph` | `currencyGraphStore.ts:35-36,96,135-139` | **S** |
| T4 | Far usare `availableLanguages`/`currentLanguageFlag`/`currentLanguageName` a `LanguageSelector.svelte` o rimuoverli | `language.ts:105,110,116` vs `LanguageSelector.svelte:8,15` | **S** |
| T5 | Famiglia `api/`: adottare `ApiError` nella gestione errori dei componenti **o** rimuoverla; rimuovere il `export default` di `zodios-client.ts:210`; decidere `downloadFxBackup` (pulsante UI o rimozione) | `zodios-client.ts:181,210`; `api/index.ts:26`; `backupDownload.ts:82` | **S** (M se si adotta `ApiError` ovunque) |
| T6 | Decidere la policy per gli helper orfani **coperti da test** (`cleanUrlParams`, `hasActiveFilters`, 3× `imageCrop`): i test aggiunti il 30–31/08 congelano codice che la produzione non chiama. O si cablano in produzione o si rimuovono codice+test | `urlFilters.ts:191,216`; `imageCrop.ts:136,197,204` | **S** |
| T7 | Tracciare la via viva dell'upload BRIM e rimuovere `uploadBrimFile` | `upload.ts:45` | **S** |
| T8 | Campionare 10 dei 43 tipi orfani di `lib/types/` contro `api/generated.ts`: se duplicano lo schema generato → rimozione; la domanda aperta dell'audit è immutata | lista knip sezione "Unused exported types" | **S** (il campione), poi **M** se si rimuovono |
| T9 | Rimuovere i nuovi orfani: `getResolvedStart/End`, `eventsSince/currentSeq/resetEvents`, `_debugStack`, `debugAssert`, `isReleaseVersion/isDirtyVersion`, ri-export `date/time/number`; convergere l'alias `getTransactionTypeIconUrl` | righe in "Dettaglio" sopra | **S** |

---

## Nuovi rilievi

1. **Falso positivo knip: 4 devDependency istanbul.** knip 2026-09-02 segnala
   `istanbul-lib-coverage`, `istanbul-lib-report`, `istanbul-lib-source-maps`,
   `istanbul-reports` (`package.json:41-44`) come inutilizzate. **Falso positivo**: sono
   importate da `frontend/scripts/js-coverage-report.js:25-28`, che knip non vede perché
   gli entry pattern coprono `scripts/*.{ts,mjs}` ma **non** `*.js`. Rimedi possibili:
   aggiungere `scripts/*.js` agli entry di `knip.json` (preferibile) o rinominare lo
   script in `.mjs`. **Non rimuovere le dipendenze.**
2. **"Unlisted binary" `pipenv`** in `e2e/global-setup.ts` — nota knip, coerente con il
   monorepo Python+Node; nessuna azione.
3. I reperti knip su **componenti, barrel e i18n** (22 ri-esportazioni morte in barrel
   vivi, tipi `components/table`, fixture e2e orfane) sono trattati nel report
   [09](09_frontend_components.md) perché ricadono nel suo perimetro.

---

## Cross-reference

- Fonte: [08_frontend_state_api.md archiviato](../../phases/05_cleanAudit/08_frontend_state_api.md)
- Esecuzione S1–S3 (contesto rimozioni): [15_esecuzione_s1_s3.md](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md)
- Report gemelli di questa tornata: [09 — Componenti](09_frontend_components.md), [10 — Grafici](10_frontend_charts.md)
- Vecchio crosscutting `$:`/knip: [11_crosscutting.md](../../phases/05_cleanAudit/11_crosscutting.md) (verifica di competenza di un'altra tornata; qui solo il dato frontend per area nel report 10)
