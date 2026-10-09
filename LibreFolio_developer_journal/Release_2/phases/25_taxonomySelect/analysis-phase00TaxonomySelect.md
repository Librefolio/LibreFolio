# Analisi — K / Tassonomia e select (R13–R18)

> **Origine.** Workstream **K** del round di Release 2, nato il 22/09 dal terzo passaggio della review
> d'uso ([`09_feedbackJobs/08_review_visiva_20260922.md` §9](../../Phase_0/09_feedbackJobs/08_review_visiva_20260922.md)).
> Copre R13, R14, R15, R16, R17 e R18 dello stesso foglio. Il piano eseguibile è
> [`plan-phase00TaxonomySelect.prompt.md`](./plan-phase00TaxonomySelect.prompt.md).
>
> Ogni affermazione qui sotto è stata **verificata sul codice** della baseline, non ripresa dai
> numeri di riga dei documenti. Dove un documento del journal diceva altro, è scritto.

| | |
|---|---|
| **Workstream** | K — tassonomia e select |
| **Branch** | `e-alfy-k-tassonomia-e-select` (rinominato dall'app; nato come `e-alfy-improved-memory`) |
| **Baseline** | `f1047f766` (`fix(db): widen enum columns to VARCHAR(32)`) su `dev_release2` |
| **Lane** | suite `6155` + `/tmp/librefolio-r2-k` · copia prod `6165` + `/tmp/librefolio-r2-k-prodcopy` |
| **Coordinator** | «Release 2 backlog analysis» (`c8328a01-…`) |
| **Decisioni** | tutte prese dal developer (§2); piano approvato il 24/09 |
| **Creato** | 2026-09-24 |

---

## §1 — Stato reale verificato

### R18 🔴 Doppia modale ISIN — causa esatta, e non è nel wizard

La corsa vive in `components/assets/AssetModal.svelte`, non in `ImportWizardModal`:

```
applySearchResult()                                   :770
  ├─ askIdentifierPrimary(...)  → chooser APERTO sync  :787   (identifierChoiceOpen = true)
  ├─ handleAskProvider()        → probe ASINCRONO      :818
  └─ void maybePromptReuse()    → list ASINCRONO       :822   (terza modale possibile)
fetchAndCompareMetadata('all')                        :1005
  └─ compareStringField('identifier_isin', …)         → la riga ISIN c'è ancora: il chooser
                                                        non ha ancora scritto nulla
  └─ showComparisonModal = true                        :1156  ← nessun controllo sul chooser
```

Tre modali allo **stesso** `zIndex + 20` (chooser `:2239`, riuso `:2294`, confronto `:2424`): vince
l'ordine nel DOM, quindi il confronto finisce sopra. `ProviderComparisonModal` monta un chooser inline
per le righe `identifier_*`: «chiede la stessa cosa», letteralmente.

**Seconda metà dello stesso difetto, non vista a schermo.** Se l'utente risponde al chooser *prima*
che arrivi il probe e sceglie il codice del report, il confronto arriva dopo e ripropone la riga ISIN
(`current` = report ≠ provider). Non basta «aspettare»: la domanda già risolta va ricordata.

Verificato che il prompt post-creazione del wizard (`checkAndPromptIdentifier`,
`ImportWizardModal.svelte:1112`) **non** ri-chiede: `pendingIdentifier()` (`utils/assetIdentifiers.ts:65`)
salta i codici già in `identifier_other`. `ImportWizardModal` e `ProviderComparisonModal` restano intatti.
Nessun test copre il chooser di `AssetModal` (`asset-modal-primary-*` non compare in nessuno spec).

### R13 🟠 «CSV» non trova «Generic CSV» — riprodotto per esecuzione

Eseguito il **vero** `optionFilter.ts` (import diretto, Node 26) sulle **30** opzioni reali,
nell'ordine del backend (`provider_registry.py:124` → `sorted(glob("*.py"))`), costruite come
`ImportPluginSelect.svelte:62-70` (`value` = codice, `label` = nome, `searchText` = descrizione):

| query | risultati | match su nome/codice | posizione di «Generic CSV» | prime righe |
|---|---|---|---|---|
| `generic` | 1 | 1 | 0 | Generic CSV |
| `CSV` | **30** | **1** | **15** (16ª) | Avanza · Bitvavo · BUX |
| `csv` / `sv` | 30 | 1 | 15 | idem |
| `crypto` | 6 | 1 | — | Bitvavo · Coinbase · CoinTracking |

Controllo positivo: «Generic CSV» presente nella lista sorgente.

**Causa.** Il filtro è un `includes` corretto — ed è proprio questo il problema: **29 descrizioni su
30** dicono «…CSV export…» (`searchText: p.description`, `:66`), quindi «CSV» restituisce l'intero
elenco nell'ordine del disco. «Generic CSV» è 16ª, la tendina ne mostra circa 6 (righe da ~56 px,
`maxVisibleItems` 8 × 44 px), l'evidenziazione resta sulla prima: **Invio sceglierebbe Avanza**.
È la terza pista del foglio 08 («la riga c'è ma non si vede»), con la causa sotto.

> ⚠️ **Nota di metodo.** La misura del 22/09 girava sulla **sola** opzione «Generic CSV»: con una
> sola opzione il risultato è `[Generic CSV]` per costruzione — il campione scelto dal fenomeno
> ([09 §3.6](../../Phase_0/09_feedbackJobs/09_reperti_analisi_statica_20260922.md)). Il filtro non era rotto: mancava l'ordinamento.

È la **stessa famiglia** già curata due volte: le icone-URL (`optionFilter.ts:19-28`, «una query corta
trovava tutto») e D74 (valuta e tipo esclusi da `AssetSelect`). Qui il testo condiviso è la descrizione.

**Audit degli altri select** (chiesto dal developer), per `searchText` che porta testo condiviso:

| select | `searchText` | rischio | nota |
|---|---|---|---|
| `ImportPluginSelect` | descrizione | 🔴 misurato | sopra |
| `CurrencySearchSelect` | codice, nome, simbolo, **codici e nomi paese** | 🟠 probabile | nomi paese condivisi (`us` → Australia, Russia, Cipro…) — misura al passo 3 |
| `CountrySearchSelect`, `SectorSearchSelect`, `TransactionTypeSearchSelect`, `Broker/UserSearchSelect` | codice/nome = etichetta | 🟢 | |
| `AssetSelect`, `ImportAssetPicker` (archivio) | soli identificativi (D74) | 🟢 | |
| `AiExportOptionsPanel` | descrizioni | 🟢 | usa `SimpleSelect`: nessuna ricerca |
| `SignalTreeSelect` (segnali) | nome + sottotitolo + dati | 🟠 | filtro proprio, fuori perimetro: solo segnalato |
| `FxProviderSelect`, `DataTableColumnFilter`, `FilesTable` | filtri propri | 🟢 | non passano da `optionFilter` |

### R14 💡 / R15 🟠 — il select dei tipi asset

- `AssetModal.svelte:1799`: `SimpleSelect` (nessuna ricerca, **nessun `testId`**) su
  `buildAssetTypeOptions()` (`utils/assetTypes.ts:229`): 17 righe + un header `__section:ETF`, famiglia
  ETF in coda (`ASSET_TYPE_MENU_ORDER`, `:191`). Icone da 16 px.
- `TransactionTypeSearchSelect` è già un `SearchSelect`: **non si tocca** (R14 era un equivoco di superficie).

**F27 non esiste** (confermato da Risk il 23/09): la numerazione dei *Fuori pista* di
`B-esecuzione.md` salta da F26 a F28, e l'unico file che nomina F27 è quello che la cita (`:271`,
«contenuto dell'opzione, prefisso dei testid, modello dati»). La ricostruzione qui sotto, fatta sul
codice di `charts/SignalTreeSelect.svelte`, è quindi **il record completo**, con un quarto asse che la
citazione non nomina:

| asse | `SignalTreeSelect` | il select dei tipi richiede |
|---|---|---|
| 1 contenuto | `SignalOptionContent` cablato: emoji testuale + KaTeX | PNG + pastiglia |
| 2 testid | `signal-tree-option-*` / `-group-*` **fissi**, usati da `gallery.spec.ts` (F8), `asset-detail.spec.ts`, `fx-detail.spec.ts`, `ChartSignalsSection.test.ts` | un prefisso proprio |
| 3 modello | `groups[].items[]`: gruppi mai selezionabili, nessuna voce alla radice | 9 voci alla radice + famiglie; `ETF` generico selezionabile |
| 4 trigger | **selettore d'azione**: mostra sempre il placeholder, mai il valore | campo di form: deve mostrare icona ed etichetta scelte |

Il resto rintracciabile: (d) contro (b) — un componente dedicato avrebbe duplicato la meccanica di
tendina, cioè la mossa di D73; F28 — `SelectOption.header` e la regola di `optionFilter.ts:39-40`;
F29 — il selettore di `AssetModal` è già `SimpleSelect` con intestazioni. Risk annota D62 nel suo
registro: corretta al passo 10 di B, riaperta da R15, owner K.

### R16 🟠 Pastiglia di D52 — confermato: mai consegnata

- In `assetTypes.ts` esistono `PNG_MAP` (`:20`), `BADGE_CLASS_MAP` (`:59`), `PRIMARY_TYPE_MAP` (`:108`):
  nessuna costante per l'icona sovrapposta. I sei sottotipi ETF puntano a `etf.png` (`:36-41`).
- `B-esecuzione.md:286` usa «pastiglia» per il **colore del badge** (consegnato) e per l'icona
  sovrapposta (mai): stessa parola, due oggetti.
- Il modello indicato da D52 («lo schema che l'altro worktree applica a broker + asset») **non esiste
  nel codice**. `LotCustodyModal.svelte` compone `AssetIcon` (`:261`, intestazione) e `BrokerBadge`
  (`:428`, `:450`, righe) **affiancati**, non sovrapposti. Nessun componente del repo sovrappone due icone.
- `AssetIcon.svelte:53` disegna un solo `<img>` in un cerchio `overflow-hidden`, che taglierebbe
  qualunque sovrapposizione fatta a runtime.
- Le icone servono già tutte: contenuti `stock bond commodity real-estate crypto liquidity` e
  contenitori `etf crowdfunding`, in `frontend/static/icons/asset-types/`. Nessun disegno nuovo.
- L'icona di tipo è disegnata da **~20 siti** con tre tecnologie (`<img>` Svelte, stringhe HTML delle
  tabelle, rich text di ECharts), e **tutti** passano da `getAssetTypeIconUrl()`.

### R17 💡 Crowdfunding immobiliare — nessuna migrazione, ma non è solo frontend

- `assets.asset_type` è un `VARCHAR` senza CHECK, `VARCHAR(32)` nei build nuovi:
  `CROWDFUND_REAL_ESTATE` (21) ci sta anche su un motore che applica la lunghezza.
- Il gate backend `test_risk_scenario_catalog.py:295-316` è **bidirezionale**: un valore d'enum senza
  secchio in `equity_crash.yml` e `global_risk_off.yml` lo rende rosso → vanno toccati due YAML di Risk.
- Tabelle frontend scritte a mano: `PNG_MAP`, `BADGE_CLASS_MAP`, `PRIMARY_TYPE_MAP`,
  `ASSET_TYPE_MENU_ORDER`, i18n ×4, `AssetTable.svelte:179` (`enumOptions`),
  `routes/(app)/assets/+page.svelte:227` (`ALL_ASSET_TYPES`, **non** coperta dal gate).
- Nessun plugin BRIM, provider o componente AI Export vincola l'enum (stringa libera).
- Doc: `financial-theory/instruments/asset-types/real-estate.*.md` dice già «Code: `CROWDFUND`» per il
  crowdfunding immobiliare; l'indice è **già stantio** (mancano `COMMODITY`, `REAL_ESTATE` e i
  sottotipi; `HOLD` etichettato «Commodities»). `backend-db.instructions.md:42` elenca i valori di `AssetType`.

---

## §2 — Decisioni del developer

### D-K1 · R15 — A: generalizzare `SignalTreeSelect` in `ui/select/` (D62 com'è scritta)

Opzioni valutate: **A** (scelta), C2 — le sezioni di B rese comprimibili dentro `SearchSelect`
(era la raccomandazione di K), C1 — come C2 con `ETF` genitore selezionabile, D — sola ricerca.
Come si fa A senza cambiare nulla per i segnali (F8), trasformando i quattro assi in parametri:

| asse | parametro | default = segnali di oggi |
|---|---|---|
| 1 contenuto | snippet `item` (+ `groupLabel` opzionale); `ui/select` non importa `SignalOptionContent` | l'adattatore passa `SignalOptionContent` |
| 2 testid | `testIdPrefix` → `${prefix}-option-{value}`, `${prefix}-group-{key}`; trigger `${testId}-button` invariato | `signal-tree` |
| 3 modello | gruppi con flag opzionale `inline` (voci alla radice, senza intestazione, sempre visibili). I gruppi restano **non selezionabili**: `ETF` generico è la prima voce della famiglia, un'opzione normale — l'argomento di B regge | nessun gruppo `inline` |
| 4 trigger | `showSelected` + snippet `selectedItem`: un campo di form mostra il valore | selettore d'azione, placeholder |

Più `searchPlaceholder`/`noMatchesText` (l'adattatore passa `signals.selector.*`),
`defaultExpanded: 'first' | 'selected' | 'none'` (segnali `'first'`: il helper di `gallery.spec.ts`
conta su questo), `minDropdownWidth` (390).

- **Nuovo** `components/ui/select/TreeSelect.svelte`: la meccanica di `SignalTreeSelect` spostata così
  com'è, poi parametrizzata.
- `components/charts/SignalTreeSelect.svelte` resta un **adattatore sottile**, stesso path, stesse prop,
  stessi tipi esportati → `ChartSignalsSection` e il suo test non cambiano di una riga.
- **Nuovo** `components/ui/select/AssetTypeSelect.svelte`: wrapper di dominio (prefisso `asset-type-tree`,
  `showSelected`, `defaultExpanded: 'selected'`).
- **Rete di sicurezza scritta per prima**: caratterizzazione di `SignalTreeSelect` sulla baseline,
  verde prima e dopo lo spostamento, senza ritocchi.
- Conseguenze: R14 è soddisfatta (il `TreeSelect` ha la ricerca); `SearchSelect` non riceve una
  modalità albero; `SelectOption` non cambia. Il costo dichiarato da B resta vero e lo paghiamo:
  `SignalTreeSelect` cambia file. La caratterizzazione è ciò che lo rende sicuro.

### D-K2 · R16 — pastiglia ovunque, badge da 14 px, tabelle HTML e legende comprese

Realizzata con **icone composite statiche**, non con un overlay a runtime:

- 7 PNG in `frontend/static/icons/asset-types/` — `etf-stock`, `etf-bond`, `etf-commodity`,
  `etf-real-estate`, `etf-crypto`, `etf-liquidity`, `crowdfunding-real-estate`: contenitore intero +
  pastiglia in basso a destra (disco bianco, bordo slate, icona del contenuto);
- in `assetTypes.ts` la «seconda costante accanto a `PNG_MAP`» di D52 (`ASSET_TYPE_CONTENT_ICON`), e le
  voci dei sottotipi in `PNG_MAP` puntano alle composite;
- uno script riproducibile, `scripts/compose_asset_type_icons.py` (Pillow, già nel Pipfile), legge le
  mappe da `assetTypes.ts` come testo e rigenera le PNG, anche le copie della doc.

Effetto: la pastiglia arriva **in ogni sito senza toccarlo** — celle HTML di `ImportWizardModal`
(ancore di J), legende di `AllocationPieChart` (R12 di Risk), tabelle e treemap della dashboard (I).
`AssetIcon` non cambia. Un prototipo del 23/09 (7 composite a 14–64 px, tema chiaro e scuro) le mostra
leggibili da ~24 px; a 14–16 px la pastiglia è un punto, come atteso. Le icone personalizzate
(`icon_url`) restano come sono: la pastiglia appartiene all'icona di tipo.

### D-K3 · R17 — `CROWDFUND` è una famiglia generica, come `ETF`

Parole del developer: *«`REAL_ESTATE` (immobiliare) è un tipo primario, `CROWDFUND` è un altro
primario, ma generico, come gli ETF: una sua specializzazione è il crowdfunding immobiliare.»*

Lettura applicata, da confermare in review: `CROWDFUND` resta il residuo generico e si risolve in sé
stesso; `CROWDFUND_REAL_ESTATE` ne è la specializzazione e, come `ETF_REAL_ESTATE`, dice cosa contiene →
`primaryAssetType('CROWDFUND_REAL_ESTATE') = 'REAL_ESTATE'`. Conseguenze: pastiglia immobiliare
coerente con D61, badge teal (invariante `badge(x) = badge(primario(x))`), nella torta sta dentro
Immobiliare (primo gruppo a 3 membri: Risk informato), codominio di `primaryAssetType` fermo a 12.
Nessuna riclassificazione automatica degli asset esistenti: è un gesto dell'utente (D52).

### D-K4 · R17 — shock come `CROWDFUND`: −0.10 / −0.10

Chi riclassifica un Recrowd non vede cambiare nessuno stress. Parere di Risk, identico: è un prestito
illiquido, non marcato a mercato, il cui rischio è il default, che arriva tardi; −0.20 sovrastimerebbe
la perdita di breve periodo. **Limite dichiarato da Risk**, da scrivere nei due YAML: sottostima il
rischio di credito in una crisi immobiliare prolungata, che però questi due scenari — shock istantanei —
non modellano. Le righe le scrive K nel commit dell'enum (decisione del coordinator).

### D-K5 · R13 — ordinamento a livelli nel filtro condiviso

In `optionFilter.filterOptions`: prefisso di nome/codice → inizio parola → sottostringa → solo
`searchText`; stabile; **dentro** ogni sezione (header e contratto K3 intatti); senza query l'ordine non
cambia. In `SearchSelect`, a ogni cambio di query l'evidenziazione torna sulla prima riga e la lista in
cima. Scartata: togliere la descrizione dal solo `ImportPluginSelect` (perdeva «crypto», «Swiss
pension», «UK stocks»). Il `TreeSelect` ha un filtro proprio: il ranking non lo tocca.

### Contratto degli export di `assetTypes.ts` (chiesto da I)

Restano stabili — nome, path, firma e semantica: `ASSET_TYPES`, `ETF_SUBTYPES`, `isEtfSubtype` (vero
solo per i sei `ETF_*`), `primaryAssetType` (K2), `getAssetTypeIconUrl`, `assetTypeBadgeClass`,
`IDENTIFIER_TYPES`, `buildIdentifiersList`, `getSectorKeysList`, `sectorI18nKey`. Cambiano solo:
`buildAssetTypeOptions()` → `buildAssetTypeTree()` (unico consumatore `AssetModal`); il **valore** di
`getAssetTypeIconUrl()` per i sottotipi (le composite); si aggiungono `ASSET_TYPE_FAMILY`,
`ASSET_TYPE_CONTENT_ICON`, `assetTypeFamily()`.

---

## §3 — Superfici

| file | voce | proprietà |
|---|---|---|
| `frontend/src/lib/utils/assetTypes.ts` | R15 R16 R17 | K in esclusiva |
| `frontend/src/lib/utils/__tests__/assetTypeTables.test.ts` | gate | K |
| `frontend/src/lib/components/ui/select/optionFilter.ts`, `SearchSelect.svelte` | R13 | condivisi; K unico scrittore di `optionFilter.ts` nel round. Gli helper di navigazione, usati anche da `SimpleSelect`, non cambiano |
| `frontend/src/lib/components/ui/select/TreeSelect.svelte` (nuovo) | R15 | K |
| `frontend/src/lib/components/charts/SignalTreeSelect.svelte` | R15 | diventa adattatore; riserva chiesta al coordinator |
| `frontend/src/lib/components/ui/select/AssetTypeSelect.svelte` (nuovo), `index.ts` | R14 R15 | K |
| `frontend/static/icons/asset-types/` (7 PNG nuove) + `mkdocs_src/docs/static/icons/asset-types/` | R16 R17 | K — binari sorgente, committati di proposito |
| `scripts/compose_asset_type_icons.py` (nuovo) | R16 | K |
| `frontend/src/lib/components/assets/AssetModal.svelte` | R15 (`:1795-1813`), R18 (`:770-890`, `:1005-1160`) | condiviso (J: ancora `asset.identity` a `:1717`) |
| `frontend/src/lib/components/assets/providerComparisonQueue.ts` (nuovo, puro) | R18 | K |
| `backend/app/db/models.py` (`AssetType`) | R17 | condiviso |
| `backend/app/services/risk/scenario_catalog/built_in/hypothetical/{equity_crash,global_risk_off}.yml` | R17 | Risk — una riga ciascuno, scritta da K |
| `frontend/src/lib/components/assets/AssetTable.svelte:179`, `routes/(app)/assets/+page.svelte:227` | R17 | condivisi — una voce in un array |
| cataloghi i18n ×4 (via `dev.py i18n add`) | R15 R17 | condivisi, additivi |
| `scripts/test_runner/_frontend_utility.py`, `_frontend_asset.py` | test nuovi | condivisi, additivi |
| `frontend/e2e/select-components.spec.ts`, `assets/asset-modal.spec.ts`, `assets/asset-list.spec.ts` | E2E | `asset-list` forse anche di F |
| `mkdocs_src/docs/developer/frontend/components/core-ui/select.md`, `…/features/asset-identity.md` | doc | docs-writer, EN-only per disegno |
| `mkdocs_src/docs/financial-theory/instruments/asset-types/{index,real-estate}.en.md` | R17 + indice stantio | docs-writer, solo EN; IT/FR/ES restano debito per la pipeline |
| `.github/instructions/backend-db.instructions.md:42` | R17 | autorizzato dal coordinator |

**Non si toccano**: `ChartSignalsSection`, `SignalOptionContent`, `gallery.spec.ts`,
`TransactionTypeSearchSelect`, `ImportWizardModal`, `ProviderComparisonModal`, `AssetIcon`, `AssetCard`,
`LotCustodyModal` (di J nel round: maschera le quantità dei lotti), pannelli di rischio. Se
`ImportWizardModal` entrasse nel perimetro, prima si avvisa il coordinator e si preservano le ancore
della guida import di J (`import.action.*` a `:4586–4770`, le 5 del Bulk, lo step-sync a `:164–178` e `:1279`).

**Chiavi i18n nuove**

| chiave | en | it | fr | es |
|---|---|---|---|---|
| `assets.types.CROWDFUND_REAL_ESTATE` | Real estate crowdfunding | Crowdfunding immobiliare | Crowdfunding immobilier | Crowdfunding inmobiliario |
| `assets.typeSections.CROWDFUND` | Crowdfunding | Crowdfunding | Crowdfunding | Crowdfunding |
| `assets.typeHints.ETF` | Mixed or unstated content | Contenuto misto o non dichiarato | Contenu mixte ou non précisé | Contenido mixto o no declarado |
| `assets.typeHints.CROWDFUND` | P2P and business lending | Prestiti P2P e alle imprese | Prêts P2P et aux entreprises | Préstamos P2P y a empresas |
| `assets.typeSelect.searchPlaceholder` | Search types | Cerca un tipo | Rechercher un type | Buscar un tipo |
| `assets.typeSelect.noMatches` | No matching types | Nessun tipo corrispondente | Aucun type correspondant | Ningún tipo coincidente |

I due `typeHints` sono il sottotitolo della voce generica dentro la sua famiglia: «ETF» sotto «ETF»,
da solo, non dice che significa «misto». `assets.typeSections.ETF` esiste già e diventa l'etichetta del gruppo.

---

## §4 — Previsione dei conflitti

| con | dove | tipo | mitigazione |
|---|---|---|---|
| **Risk** (R12) | `primaryAssetType` → `allocationHierarchy.ts` | semantico: Immobiliare diventa il primo gruppo a 3 membri | K2 invariato; `assetTypeFamily()` è la vista **contenitore**, una relazione diversa da `primaryAssetType` (contenuto). Risk informato: la ciambella D72 deve reggere gruppi di N membri |
| **Risk** | i due YAML | testuale | scritti da K nel commit dell'enum; Risk non li tocca fino all'integrazione di R17 |
| **A / I** | `charts/SignalTreeSelect.svelte` diventa adattatore | testuale se altri lo modificano; semantico per `gallery.spec.ts` (F8) | riserva del file; contratto F8 fissato dalla caratterizzazione; `ChartSignalsSection` diff zero |
| **J** | `AssetModal` (ancora `asset.identity` che contiene il select) | testuale possibile | J avvisato; `AssetCard`, `LotCustodyModal` e `ImportWizardModal` non si toccano |
| **Risk / I / J** | legende e tabelle che disegnano icone di tipo | **visivo** soltanto | nessuna modifica ai loro file; da mettere nelle loro review |
| **I** | modulo emoji di Allocazione storica: importa `ASSET_TYPES` e `isEtfSubtype` | nessuno testuale (export stabili). All'integrazione il test «ogni valore d'enum ha un'emoji» scatterà su `CROWDFUND_REAL_ESTATE` | nella lista d'integrazione del coordinator |
| **A / F / J** | `assets/+page.svelte:227`, `AssetTable.svelte:179`, `asset-list.spec.ts` | testuale, una voce | modifica additiva dichiarata nell'handoff |
| **D / F / A** | ogni `SearchSelect` con ricerca | semantico: l'ordine dei risultati cambia quando c'è una query | senza query ordine identico; sezioni e K3 intatti; nessun E2E dipende dall'ordine con query (verificato) |
| tutti | i18n ×4, catalogo del runner | additivo | nessun riordino, elencati nell'handoff |
| catena Alembic | — | nessuno | zero migrazioni |

---

## §5 — Reperti fuori perimetro (instradati dal coordinator)

1. 🔴 **Risk** — `RiskAnalysisPanel.svelte:115`: `stressAssetClasses` ha i 9 tipi pre-tassonomia; lo
   stress uniforme di portafoglio (`:472`) costruisce i secchi solo da lì, quindi `COMMODITY`,
   `REAL_ESTATE` e i sei `ETF_*` prendono shock 0 in silenzio (`UNCONFIGURED_ZERO`, la classe di D70).
2. 🟡 **I** — `AllocationHistoryChart.svelte:165-180`: mappa emoji senza `COMMODITY`, `REAL_ESTATE`,
   `ETF_MONETARY` (ricadono su 📊).
3. 🟡 **K** — l'indice `financial-theory/asset-types` stantio: assegnato a K insieme a R17.

---

## §6 — CHANGELOG proposto (lo scrive il coordinator)

- 🐛 La ricerca nei select mette prima chi corrisponde nel **nome**: «CSV» trova «Generic CSV».
- 🐛 Creando un asset, il confronto col provider non si apre più sopra la scelta dell'ISIN: aspetta la
  risposta e non ripete la domanda.
- ✨ Il tipo asset si sceglie da un menu **cercabile a due livelli** (famiglie ETF e Crowdfunding).
- ✨ ETF e crowdfunding specializzati mostrano l'icona del contenuto sovrapposta, ovunque compaia il tipo.
- ✨ Nuovo tipo **Crowdfunding immobiliare**.
