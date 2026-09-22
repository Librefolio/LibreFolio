# B — piano di esecuzione

| | |
|---|---|
| Mandato | [`../B-tassonomia-e-benchmark.md`](../B-tassonomia-e-benchmark.md) — 🚫 sola lettura |
| Branch | `e-alfy-risk-taxonomy-benchmark` |
| Baseline | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` ✅ verificata |
| Lane | porta `6241` · data dir `backend/data/test-risk-b` |
| Autorizzazione | coordinatore, sotto delega generale del developer (*«Work autonomously and make good decisions»*) |

---

## Decisioni che governano questo piano

| # | Decisione | Origine |
|---|---|---|
| **Naming** | **`ETF_STOCK`**, non `ETF_EQUITY` — `ETF_EQUITY` nominerebbe un tipo base inesistente, cioè la trappola del genitore che K2 esiste per vietare. L'uso finanziario vive nell'**etichetta** | B, confermata dal coordinatore |
| **17 valori** | 9 attuali + `COMMODITY` `REAL_ESTATE` + `ETF_STOCK` `ETF_BOND` `ETF_COMMODITY` `ETF_REAL_ESTATE` `ETF_CRYPTO` `ETF_MONETARY` | D52/D61/D67 |
| **K2** | `primaryAssetType` → **contenuto** (`ETF_STOCK` → `STOCK`). **Una funzione sola** | D85 |
| **`VARCHAR(14)`** | resta, **advisory**, col precedente di `002` e la nota Postgres | B-Q2 |
| **`ETF_MONETARY`** | → **sé stesso** (non ha tipo base, D67) — vedi *Fuori pista* al passo 6 | B-Q9, proposta B |

---

## Passi

- [x] **0. `api sync` (bootstrap)** — ✅ 18 Set 2026
  > **Note implementazione**: `generated.ts` era **assente** nel worktree e resta
  > gitignorato (`frontend/.gitignore:13`), mentre `assetTypes.ts:11` lo importa: senza
  > questo passo `svelte-check` e Vitest non collegano. Eseguito
  > `pipenv run python dev.py api sync` → rigenerati `openapi.json`,
  > `tool-contracts.openapi.json`, `generated.ts` e il client dei tool. Verificato
  > lane-safe: importa l'app FastAPI **in processo**, non apre porte.
  > **Fuori pista**: il brief lo collocava al passo 3; è dovuto salire a 0 perché è
  > **precondizione di qualunque verifica frontend**, non una conseguenza del backend.
  > ⚠️ Trappola d'integrazione per i mandati a valle (F7): essendo ignorato,
  > `generated.ts` **non viaggia nei commit** — chiunque consumi i nuovi tipi dovrà
  > rieseguire `api sync` nel proprio worktree dopo l'integrazione di B, o userà un
  > client che i sottotipi non conosce. Segnalata al coordinatore per J.

- [x] **1. Il test del cancello, scritto per primo** — ✅ 18 Set 2026 · **rosso come doveva**
  > **Note implementazione**: delegato a `test-author`. Due file, ognuno nella sua lingua.
  > **Backend**: esteso `test_risk_scenario_catalog.py` (+4 test) invece di crearne uno
  > nuovo — quel file è **già** nell'elenco di `_backend_services.py:76` sotto `risk-all`,
  > quindi il cancello entra in funzione **senza toccare il runner**, che è di **A**.
  > Conflitto evitato per costruzione. Verifica bidirezionale: ogni `AssetType` ha un
  > secchio in ogni scenario `asset_class`, **e** ogni chiave di secchio è un `AssetType`
  > valido (prende i refusi e le chiavi rimaste indietro dopo un rename).
  > **Frontend**: nuovo `src/lib/utils/__tests__/assetTypeTables.test.ts`, 9 test,
  > registrato in `_frontend_asset.py` (elenco esplicito, non glob). L'enum è letto **da
  > `backend/app/db/models.py` via regex**, non da `generated.ts`: quest'ultimo è
  > gitignorato e rigenerato da `api sync`, quindi un valore aggiunto senza risync
  > avrebbe fatto **passare** il test — cioè esattamente la desincronizzazione che il
  > cancello esiste per scoprire. Ogni scrape è protetto da un'asserzione di non-vuoto
  > con valori d'ancora: una regex che non aggancia nulla renderebbe ogni ciclo
  > «per ogni tipo» un no-op verde, che è il modo peggiore di fallire. Nessuna
  > asserzione sul **numero** dei tipi: l'insieme deve poter crescere.
  >
  > **Il rosso ha nominato sei buchi, non cinque**:
  > `equity_crash` senza `BOND` `CRYPTO` `CROWDFUND` `HOLD`; `AssetTable` senza `INDEX`
  > nel filtro; e **`OTHER` senza colore pastiglia** — quest'ultimo non era nella mia
  > previsione. Puliti invece: `global_risk_off` (tutti e 9), il senso inverso (nessuna
  > chiave spuria), `PNG_MAP` (9 su 9, e ogni PNG esiste davvero su disco), i18n ×4.
  >
  > **Fuori pista — tre scoperte nuove**:
  > ⚠️ **F16 — il loader degli scenari non è ricorsivo.** `loader.py:116-117` e `:169-170`
  > iterano **due sottocartelle scritte a mano**, `historical/` e `hypothetical/`. Un YAML
  > messo altrove sotto `built_in/` non viene rifiutato: viene **ignorato in silenzio**.
  > È la stessa modalità di fallimento silenzioso di D70, in un punto che nessuno aveva
  > guardato. `test-author` ha aggiunto un guardiano
  > (`test_every_built_in_scenario_file_is_reachable_by_the_loader`) che oggi è **verde**
  > ed è ciò che impedisce al cancello di diventare vacuo domani. File di **N** →
  > segnalato al coordinatore, non corretto da me.
  > ⚠️ **F17 — il filtro per tipo della tabella è disattivato.** `AssetTable.svelte:183`
  > ha `filterable: false`, proprio sotto l'elenco `enumOptions` di `:181`. Quindi il
  > buco `INDEX` è reale come **dato**, ma il sintomo «`INDEX` non è filtrabile» vale
  > oggi per **tutti** i tipi. Correggo l'elenco e **non tocco il flag**: accenderlo è una
  > decisione di prodotto fuori mandato e cambierebbe il comportamento su cui **F**
  > costruirà `asset-list.spec.ts`. Segnalato.
  > ⚠️ **F18 — il selettore del brief §10 è sbagliato una seconda volta.** Non `front
  > asset-unit` ma **`front-asset asset-unit`**: la categoria è `front-asset`.
  > ⚠️ **F19 — le tabelle frontend sono già *avanti* all'enum**: `PNG_MAP` e le quattro
  > lingue portano già `LIQUIDITY` (orfano innocuo e documentato, D61/D63). Il cancello
  > frontend è quindi **monodirezionale** per scelta, mentre quello backend è
  > bidirezionale: il senso inverso nominerebbe `LIQUIDITY` e produrrebbe un rosso non
  > richiesto. Asimmetria deliberata, scritta qui perché non si scopra come una svista.
  >
  > **Decisione presa**: `OTHER` **va aggiunto esplicitamente** alla mappa dei colori al
  > passo 9. Che il ripiego grigio sia per caso giusto proprio per `OTHER` è ciò che
  > rende invisibile il fatto che domani anche `COMMODITY` sarà grigio.
- [x] **2. `models.py`: 8 valori nuovi, docstring corretto, `Asset.is_benchmark`** — ✅ 18 Set 2026
  > **Note implementazione**: `AssetType` passa da 9 a **17** valori. Ordine scelto per
  > minima perturbazione: `COMMODITY` e `REAL_ESTATE` inseriti dopo `HOLD`, così `INDEX`
  > e `OTHER` restano in coda dov'erano (l'ordine dell'enum guida `schemas.AssetType.options`
  > e quindi l'ordine nei menù); i sei sottotipi ETF in un blocco a parte.
  > Docstring riscritto: sparito il blocco **«Affects default valuation_model»**, che
  > descriveva una macchina inesistente — `valuation_model` non compare in nessun punto
  > del backend fuori da quel testo. Al suo posto quello che `asset_type` fa **davvero**:
  > `INDEX` vieta le transazioni, il resto è inerte; alimenta la ripartizione di
  > portafoglio; fornisce i secchi `asset_class` degli scenari, **con la nota che
  > l'assenza da un secchio vale zero in silenzio**; sceglie icona ed etichetta.
  > `is_benchmark` documentato come **condiviso** (la tabella non ha colonna di proprietà)
  > e **indipendente da `asset_type`**: essere benchmark è un ruolo, non una natura.
  > **Fuori pista**: nessuno. Verificato in `001_initial.py` che `asset_type` sia un
  > `VARCHAR` **senza alcun `CHECK`** → i valori nuovi non richiedono DDL.

- [x] **3. Migrazione `003` — unica della campagna** — ✅ 18 Set 2026
  > **Note implementazione**: `003_asset_benchmark_flag_and_taxonomy`,
  > `down_revision = "5b1333fa6b07"`. Stile di casa: SQL grezzo via `conn.execute(sa.text(...))`,
  > guardie di idempotenza su `PRAGMA table_info`, `downgrade()` esplicito. Il backfill
  > `INDEX → is_benchmark = 1` gira **solo alla creazione della colonna**: una
  > ri-esecuzione non deve resuscitare un flag che l'utente ha tolto.
  > Nel docstring è scritta l'archeologia del `VARCHAR(14)` — **14 = `CROWDFUND_LOAN`**,
  > valore che non esiste più — la decisione di lasciarlo advisory, e l'obbligo esplicito
  > di allargarlo su un futuro Postgres, dove `ETF_REAL_ESTATE` (15) verrebbe **rifiutato**.
  >
  > **La prova, perché `db validate` non basta**: quel controllo è dinamico su tabelle,
  > unique, FK e indici, e **non confronta le colonne** — una colonna dimenticata nella
  > migrazione sarebbe passata liscia. Quindi giro completo su DB **popolato**:
  > `downgrade -1` (colonna via, revisione a `5b1333fa6b07`) → `upgrade head` → risultato
  > **`INDEX|2|2`**, cioè entrambi gli `INDEX` marcati e **nessun altro tipo toccato**;
  > poi `upgrade head` di nuovo → totale invariato, idempotenza dimostrata.
  > ⚠️ Nota verificata: `db populate --force --clean` migra un DB **vuoto**, quindi il
  > backfill non viene esercitato — con quello solo sarebbe rimasto non provato.
  >
  > **Fuori pista** — ⚠️ **F20: `dev.py db downgrade <path>` ignora la data dir.**
  > `cmd_db_downgrade` (`dev.py:485`) e `cmd_db_upgrade` (`:470`) passano il percorso solo
  > come variabile d'ambiente `DATABASE_URL`, ma `backend/alembic/env.py:36` legge
  > `settings.DATABASE_URL` dalla configurazione, non dall'ambiente: con `.env` assente
  > si risolve sulla data dir di **produzione**, che in un worktree non esiste →
  > `OperationalError: unable to open database file`, sia con percorso assoluto sia
  > relativo. `env.py:25` onora invece `-x sqlalchemy.url=`, che dev.py **non** passa.
  > Usata quella interfaccia documentata per la prova. `dev.py` è file condiviso →
  > **segnalato al coordinatore, non corretto**.

- [x] **3b. Verifica schema** — ✅ `db all` **10/10**
- [x] **4. Schemi + `asset_sources/crud.py`** — ✅ 2026-03-07
  > **Note implementazione**: `is_benchmark` aggiunto alle **quattro** classi di
  > `schemas/assets.py` con le semantiche che ciascuna richiede — `FAAssetCreateItem`
  > default `False`, `FAinfoResponse` default `False`, `FAAinfoFiltersRequest` **tri-stato**
  > (`None` = non filtrare), `FAAssetPatchItem` `None` = campo non toccato. In
  > `asset_sources/crud.py`: filtro tri-stato accanto a quello di `active` (`:183-189`),
  > propagazione in creazione (`:90`) e in risposta (`:280`).
  > La **patch non ha richiesto codice**: il ciclo `:574` itera `patch_dict` generato da
  > `model_dump(exclude_unset=True, exclude_none=True)` e applica `setattr(asset, field, value)`
  > (`:611`) senza lista bianca → il campo passa da solo, e `exclude_none` conserva
  > `is_benchmark=False` perché `False` non è `None`. Verificato leggendo il ciclo, non assunto.
  >
  > **Fuori pista** — ⚠️ **il filtro `asset_type` resta a uguaglianza esatta, per scelta.**
  > Il censimento Q12 elencava `crud.py:180-181` fra i punti da riallineare, lasciando
  > intendere un roll-up (`asset_type=ETF` che pesca anche `ETF_STOCK`). **Non l'ho fatto**,
  > per tre ragioni verificate sul codice: (a) non è un ripiego silenzioso — il campo è
  > tipizzato `AssetType`, quindi un valore inesistente lo rifiuta Pydantic, non il DB;
  > (b) il filtro della vista a schede **non passa di qui**: costruisce un `Set` lato client
  > e filtra nel browser (`+page.svelte:297`); (c) lo stesso filtro è usato da BRIM per
  > l'identificazione esatta degli asset, e un roll-up silenzioso ne cambierebbe la
  > semantica senza che nessuno l'abbia chiesto. Se il roll-up servirà, va come
  > **parametro esplicito e separato**. Segnalato al coordinatore come non-modifica deliberata.

- [x] **5. `api sync` coi tipi nuovi** — ✅ 2026-03-07
  > **Note implementazione**: rigenerato; `generated.ts` contiene i sei sottotipi `ETF_*`,
  > `COMMODITY`, `REAL_ESTATE` e sei occorrenze di `is_benchmark`. Resta **ignorato da git**:
  > è F7, ogni mandato a valle dovrà rilanciarlo dopo l'integrazione di B.
- [x] **6. `assetTypes.ts` → K2** — ✅ 2026-03-07
  > **Note implementazione**: `PNG_MAP` completata (17 valori + `LIQUIDITY`), `ETF_SUBTYPES`,
  > `isEtfSubtype`, `PRIMARY_TYPE_MAP` (5 voci, solo quelle che *si muovono*) e
  > `primaryAssetType`. Ingresso ignoto → **sé stesso**, non `OTHER`: riscriverlo in `OTHER`
  > nasconderebbe un valore nuovo proprio nel secchio che nessuno ispeziona.
  > Solo `null`/vuoto ripiega su `OTHER`. Nessuno `split('_')`, mai.
  >
  > **Fuori pista** — ⚠️ **F21: `commodity.png` e `real-estate.png` erano già su disco**
  > (`frontend/static/icons/asset-types/`) ma **assenti da `PNG_MAP`**: icone pronte da
  > tempo per due tipi che l'enum non aveva. Nessun file nuovo da produrre. Attenzione al
  > nome col trattino — `real-estate`, non `real_estate`.
  >
  > **Fuori pista** — ⚠️ **F24: l'invariante di K2 è 12, non 13.** Verificato eseguendo la
  > mappa sull'enum (`/tmp/libreFolio_B_codomain.py`), non a mente.

- [x] **6b. `AssetCard.svelte`** — ✅ 2026-03-07
  > **Note implementazione**: `ASSET_TYPE_ICON_MAP` duplicata **rimossa** → usa
  > `getAssetTypeIconUrl`. Lo `switch` dei colori sostituito da `assetTypeBadgeClass`.
  >
  > **Fuori pista** — ⚠️ **le due mappe colori sono state unificate in `assetTypes.ts`**,
  > deviando dal mandato che le trattava come due punti separati (passi 6b e 9).
  > Ragione: erano **già divergenti** — la scheda non aveva `INDEX`, non aveva `OTHER`
  > esplicito ed era uno `switch` invece di una tabella. Tenerle separate avrebbe
  > richiesto di mantenerle allineate a mano per sempre con il cancello a guardia di
  > **una sola delle due**: esattamente la divergenza silenziosa che questo mandato
  > esiste per uccidere. Ora la mappa è una, i consumatori due, e il cancello legge
  > quella. Aggiunto un test che verifica che **entrambe** le viste la usino ancora,
  > perché controllare la mappa condivisa vale solo finché qualcuno la legge.

- [x] **7. i18n × 4** — ✅ 2026-03-07
  > **Note implementazione**: +8 etichette per lingua (10 → 18), solo dentro `assets.types`.
  > `ETF_STOCK` = "Equity ETF" / "ETF azionario" / "ETF actions" / "ETF de renta variable":
  > **la chiave resta coerente col tipo base, l'idioma finanziario vive nell'etichetta** —
  > che è l'unica cosa che l'utente vede. JSON riletto e validato in tutte e quattro.
  >
  > **Fuori pista** — ⚠️ **F22: `HOLD` è tradotto "Liquidità"/"Liquidité"/"Liquidez"**,
  > cioè **identico a `LIQUIDITY`**, in tre lingue su quattro. Ma `HOLD` significa
  > "bene senza prezzo di mercato automatico" (arte, collezionismo, società non quotate):
  > la traduzione è **sbagliata**, non solo collidente. **Non l'ho corretta**: è testo
  > visibile all'utente in tre lingue, quindi è una decisione di prodotto, non una svista
  > da sanare di straforo dentro un altro mandato. Segnalata al coordinatore.

- [x] **8. I due YAML `asset_class`** — ✅ 2026-03-07
  > **Note implementazione**: `equity_crash.yml` **5 → 17** bucket, `global_risk_off.yml`
  > **9 → 17**. Regola dichiarata nei file stessi: **shock(ETF_X) == shock(X)**, l'ETF è
  > shockato per quello che contiene; l'`ETF` generico conserva uno shock miscelato perché
  > il contenuto non è dichiarato — ed è precisamente il guadagno che la tassonomia compra.
  > I 4 buchi preesistenti di `equity_crash` (`BOND`, `CRYPTO`, `CROWDFUND`, `HOLD`) chiusi.
  > ⚠️ Verificato meccanicamente che **nessun valore già calibrato sia cambiato**:
  > `pre-existing values changed: none` su entrambi i file.

- [x] **9. `AssetTable`** — ✅ 2026-03-07
  > **Note implementazione**: `enumOptions` da 8 a **17** valori. `OTHER` ha ora un colore
  > **esplicito** (`slate`), distinto dal ripiego grigio: finché il ripiego era *per caso*
  > giusto per `OTHER`, nessuno poteva accorgersi che domani `COMMODITY` sarebbe stato grigio.
  > `filterable: false` **non toccato** (F17, decisione di prodotto su cui costruisce F).
  >
  > **Fuori pista** — ⚠️ **F23: `enumOptions` deve restare scritto a mano.** Derivarlo da
  > `schemas.AssetType.options` sembrava l'ovvio miglioramento — impossibile desincronizzarsi.
  > È **peggio**: `generated.ts` è gitignorato (F7) ed esiste solo dopo `api sync`, quindi su
  > un checkout non rigenerato la lista derivata si riempirebbe a metà **con il test verde**.
  > La lista letterale funziona senza client, e il cancello rende rosso dimenticarne uno.

- [x] **F16. `scenario_catalog/loader.py`** — ✅ 2026-03-07 (riga concessa dal coordinatore)
  > **Note implementazione**: ⚠️ **la diagnosi iniziale era imprecisa e il codice l'ha corretta.**
  > `_yaml_files` **usa già `rglob`**: l'annidamento dentro `historical/` e `hypothetical/`
  > funzionava. Il buco vero è un altro — le cartelle lette sono **tre** (`historical`,
  > `hypothetical`, **`geography`**, quest'ultima legittima e che avrei falsamente accusato)
  > e un YAML **fuori da tutte e tre** non veniva né caricato né rifiutato: spariva.
  > Aggiunto un insieme `visited` e un controllo finale che **solleva**
  > `RiskScenarioCatalogLoadError` elencando i file orfani. Rumoroso, perché il catalogo
  > built-in è nostro e ci viene spedito: un file fuori posto è un bug di impacchettamento.
  > **Metà host lasciata aperta**: lì il contenuto è dell'utente, quindi vorrebbe un
  > *warning*, non un'eccezione, e la concessione riguardava il built-in.

- [x] **13. Il cancello è verde** — ✅ 2026-03-07 (anticipato: i passi 6-9 lo chiudono)
- [x] **6c. `+page.svelte`** — ✅ 2026-03-07
  > **Note implementazione**: `ALL_ASSET_TYPES` da 9 a **17** valori. `availableTypes`
  > (`:245`) filtra già per conteggio > 0, quindi la tendina non si gonfia: mostra solo i
  > tipi che l'utente possiede davvero. Il rifiuto a `:297` ora accetta tutti e 17, cioè
  > i sottotipi smettono di essere **attivamente nascosti** da "seleziona tutto".
  >
  > **Fuori pista** — ⚠️ **F25: c'era una TERZA mappa icone duplicata**, `TYPE_ICON_MAP`
  > (`:220-230`), usata a `:1408` **dalla tendina stessa che stavo estendendo**. Conosceva
  > nove tipi: gli otto nuovi sarebbero usciti tutti come `other.png` — un guasto **causato
  > dalla mia stessa modifica**, non preesistente e indipendente. Rimossa, sostituita da
  > `getAssetTypeIconUrl`.
  > ⚠️ **Questo eccede il confine concesso** («solo la costante `ALL_ASSET_TYPES`»): sono
  > 12 righe in più nello stesso file, additive e banalmente reversibili. Segnalato al
  > coordinatore come eccezione esplicita, con offerta di ripristino se il proprietario
  > del file obietta. Le mappe icone duplicate erano **tre**, non due.
  >
  > **Fuori pista** — ⚠️ **F26: due PNG non tracciate in `mkdocs_src/`.**
  > `mkdocs_src/docs/static/icons/asset-types/{commodity,real-estate}.png` esistono su
  > disco, sono **byte-identiche** a quelle del frontend, **non sono ignorate da git** e
  > **non le ho create io**. Le gemelle nel frontend sono tracciate e arrivano da
  > **`cc33120eb`**, cioè dal commit di baseline della campagna: qualcuno le ha preparate
  > per questo mandato e ha dimenticato il `git add` sul lato documentazione.
  > **Conseguenza operativa**: al checkpoint un `git add -A` se le porterebbe dentro senza
  > che nessuno se ne accorga (65 KB + 54 KB di binari). Non le tocco — `mkdocs_src/` non è
  > mia — ma vanno nelle **esclusioni** dell'handoff. Debito residuo per la documentazione:
  > il set icone dei docs è ora incompleto in git, 10 tracciate contro 12 necessarie.
- [x] **10 → annullato. Decisione (d): nessun albero, sezioni su `SimpleSelect`** — ✅ 2026-03-07
  > **Note implementazione**: il passo 10 del mandato («promuovi `SignalTreeSelect` in
  > `ui/select/TreeSelect.svelte`») **non si fa**. Il coordinatore ha respinto la
  > promozione e ha corretto **D62**, che diceva «il selettore esiste già, va
  > generalizzato». Non era vero: avevo verificato che le due forme divergono su tre
  > assi (contenuto dell'opzione, prefisso dei testid, modello dati) — vedi **F27**.
  > Fra le tre uscite ho scelto **(d)**: sezioni non selezionabili invece di un albero.
  >
  > **Perché (d) e non (b) — un componente nuovo dedicato**, che era la mia proposta:
  > (b) avrebbe duplicato la meccanica di tendina (tastiera, ricerca, focus, ARIA), cioè
  > **la mossa che ha prodotto D73** — un picker ad hoc costruito accanto a uno che
  > esisteva già. La mia obiezione («lì il componente calzava, qui no») resta vera, ma il
  > rischio residuo è lo stesso: un secondo albero che diverge dal primo.
  >
  > **Fuori pista** — ✅ **F29: non c'è nessun componente da convertire.** Il selettore
  > di tipo del modale (`AssetModal.svelte:1778`) è **già `SimpleSelect`**, e
  > `SimpleSelect` rende **già** le intestazioni di sezione: markup a `:322-329` con
  > testid `{testId}-header-{value}`, tastiera delegata a `:11`
  > (`firstSelectable, isSelectable, lastSelectable, stepSelectable` — **le stesse
  > identiche funzioni** di `SearchSelect`), e `:205` `if (option.disabled || option.header) return;`.
  > Lo snippet `item` è invocato **solo** sul ramo `{:else}`: la pastiglia composita di
  > **D52 gira immutata**, è già lì oggi.
  > Quindi (d) non è «adotta un altro componente»: è **aggiungere due voci a un array**.
  > `SignalTreeSelect`, `ChartSignalsSection` e `gallery.spec.ts` **non si toccano**:
  > i tre zeri che mi facevano preferire (b), senza il componente in più.
  > **F2 sparisce davvero** — `ETF` diventa un'opzione normale sotto la propria
  > intestazione, non un gruppo costretto a comportarsi da foglia.
- [x] **12a. `assetStore.ts` — `is_benchmark` su `AssetInfo` (F13)** — ✅ 2026-03-07
  > **Note implementazione**: campo `is_benchmark?: boolean` aggiunto all'interfaccia e
  > propagato in `normalize` con `copyDirect('is_benchmark', false)`. Il default esplicito
  > non è cosmesi: `normalize` è chiamata anche con payload **parziali** di PATCH, e un
  > `undefined` renderebbe inaffidabile il predicato `match` di K3 proprio dopo una
  > modifica dell'asset.
- [x] **12b. `AssetSelect` a sezioni → K3 consegnato** — ✅ 2026-03-07
  > **Note implementazione**: due prop nuove, `sections` e `restLabel`, **retrocompatibili**
  > — senza di esse il comportamento è identico al byte a prima. Ogni asset entra nella
  > **prima** sezione che lo accetta, quindi l'ordine dell'array è l'ordine a schermo e
  > due predicati sovrapposti si risolvono invece di duplicare la riga. Una sezione vuota
  > non stampa il titolo. Il resto prende `restLabel` **solo se** qualcosa sopra è stato
  > titolato, altrimenti sarebbe un'unica intestazione sopra l'intera lista.
  > **Sezioni ⊥ pastiglie**: con `suggestedIds` insieme a `sections`, le sezioni decidono
  > l'ordine e la pastiglia viaggia con la sua opzione — i due meccanismi non confliggono.
  >
  > **Fuori pista** — ✅ **F28: la meccanica delle sezioni esisteva già.** `SelectOption.header`
  > è nel tipo condiviso, con la regola non ovvia in `optionFilter.ts:39-40` — un titolo
  > sopravvive solo se la riga successiva **non** è un altro titolo, quindi spariscono sia
  > la sezione svuotata dalla ricerca sia il titolo rimasto in coda. Non ho aggiunto
  > meccanica: l'ho consumata. È anche la ragione per cui (d) è coerente — nello stesso
  > mandato ora c'è **un paradigma solo**, sezioni via `SelectOption.header`, su entrambi
  > i selettori.
- [x] **11. `AssetModal` — sezioni nel selettore di tipo (d) + interruttore benchmark** — ✅ 2026-03-07
  > **Note implementazione**: `AssetModal.svelte` **non cambia di una riga** per il tipo.
  > Tutto lo step vive in `assetTypes.ts`: `ASSET_TYPE_MENU_ORDER` (17 valori, 10 primari
  > poi la famiglia ETF) e `buildAssetTypeOptions` che emette l'intestazione
  > `__section:ETF` prima del primo membro della famiglia. L'intestazione è cercata per
  > **appartenenza** (`isEtfFamily`), non per indice: riordinare la lista non sposta il
  > titolo dalla sua famiglia.
  >
  > **L'invariante promessa al coordinatore è nel cancello**: `ASSET_TYPE_MENU_ORDER`
  > raschiata testualmente e confrontata con l'enum di `models.py`. Qui il confronto è
  > **bidirezionale**, a differenza delle tabelle di lookup (F19): un valore di troppo in
  > una lookup è peso morto, un valore di troppo **qui** viene offerto all'utente e poi
  > rifiutato dall'API. Aggiunte anche: nessun duplicato, e **famiglia ETF contigua** —
  > una famiglia spezzata metterebbe il titolo sopra solo una parte di ciò che nomina.
  >
  > **Fuori pista** — ho **cambiato idea** sull'interruttore benchmark rispetto alla mia
  > stessa analisi, che lo voleva in sola lettura quando `asset_type === 'INDEX'`.
  > È sbagliato: il backfill della migrazione è uno **stato iniziale**, non un vincolo, e
  > renderlo immutabile impedirebbe per sempre di togliere la spunta a un indice. Niente
  > accoppiamento automatico tipo→benchmark nemmeno in creazione: sarebbe comportamento
  > invisibile in un modale che altrove distingue con cura l'automatico dal manuale
  > (`markManualField`). Interruttore piano, l'utente decide.
  >
  > `isBenchmark` propagato nei **sei** punti in cui vive `active` — stato, tupla di
  > dirty-check (`:436`), caricamento, reset, payload di creazione, payload di PATCH — più
  > `is_benchmark?: boolean` su `AssetData`, che `svelte-check` ha giustamente preteso.
  > i18n ×4: `assets.modal.benchmark` + `benchmarkTooltip`, e `assets.typeSections.ETF`.
  > La chiave della sezione sta **fuori** da `assets.types` di proposito: quel namespace è
  > una mappa enum→etichetta e il cancello ci si appoggia, un titolo lì dentro sarebbe
  > stato letto come un tipo.
- [x] **F22. `HOLD` tradotto «Liquidità» in 3 lingue su 4** — ✅ 2026-03-07 (correzione autorizzata)
  > **Note implementazione**: `HOLD` è un bene senza prezzo di mercato automatico — arte,
  > collezionismo, società non quotate. Chiamarlo «Liquidità»/«Liquidité»/«Liquidez» è
  > **falso**, e rendeva `HOLD` e `LIQUIDITY` **indistinguibili** proprio nel selettore
  > che stavo portando a 17 valori. Reso: *Held asset · Bene detenuto · Bien détenu ·
  > Bien en posesión*. `LIQUIDITY` invariato.
  > Corretto anche l'inglese, che non era falso ma solo brusco: «Hold» accanto a
  > «Stock»/«Bond» si legge come un verbo o un giudizio, non come il nome di una cosa —
  > e le etichette vicine sono tutte sostantivi che nominano la cosa.
  > **Nessun test si appoggiava a quelle stringhe** (verificato su `e2e/` e `src/`), come
  > dev'essere: asserire su testo tradotto è vietato dalle istruzioni di progetto.
  > ⚠️ Le quattro modifiche i18n sono state applicate via `json.dumps(indent=2)`: ho
  > verificato con `git diff --stat` che **non** riformattino il file (13 righe per
  > lingua, tutte mie). Un riformattamento silenzioso di un catalogo condiviso sarebbe
  > stato un incubo di merge per gli altri mandati.
- [x] **12c. `SignalAssetParamControl` → `AssetSelect`** — ✅ 2026-03-07
  > **Note implementazione**: **D73 confermata sul codice, e la causa è precisa.**
  > `SearchSelect.svelte:414` rende `selectedOption.value` come **riga principale** quando
  > il chiamante non passa lo snippet `selectedItem` — e qui `option.value` è
  > `String(asset.id)`. Non era una svista di rendering: era il prezzo di aver costruito
  > le opzioni a mano invece di riusare `AssetSelect`, che gli snippet ce li ha.
  > Il componente è ora un **adattatore sottile**: conserva il contratto dei parametri di
  > segnale e delega lista, ricerca e resa al picker condiviso. `excludeAssetIds` diventa
  > una `filter`, e la `sections` del benchmark rende **K3 usato**, non solo consegnato.
  >
  > **Props pubbliche identiche al byte** (F9): `value: unknown`, `onchange: (value: number) => void`,
  > `excludeAssetIds?: number[]`, `testId?: string`. `RiskAnalysisPanel.svelte`
  > **non compare nel diff** — verificato con `git diff --name-only`.
  >
  > **La ricerca migliora invece di peggiorare**: il controllo cercava anche sulla valuta,
  > `AssetSelect` no — e il commento in `AssetSelect` spiega perché (P3/A6): valuta e tipo
  > sono proprietà condivise da centinaia di righe, quindi `eur`, `bon`, `etf` facevano
  > corrispondere l'intera lista e la ricerca sembrava funzionare solo dalla quarta
  > lettera. Identificatori ISIN/ticker/`identifier_other` restano cercabili.
  >
  > **Fuori pista** — ⚠️ **F30: `AssetSelect` non inoltrava `testid` a `SearchSelect`.**
  > Migrare senza accorgersene avrebbe cancellato `{testId}-trigger` e rotto **due** spec
  > E2E — `e2e/assets/asset-detail.spec.ts:256` e `e2e/portfolio/risk-analysis.spec.ts:730`
  > — senza che Git mostrasse nulla, la stessa classe di guasto di F8. Inoltrato.
  > Verificato che sia **additivo**: i testid esistenti `asset-select` stanno sul div
  > contenitore e Playwright fa corrispondenza esatta, quindi i quattro spec di import che
  > ci si appoggiano non cambiano comportamento.
  >
  > **Fuori pista** — ⚠️ **F31: un fallimento di caricamento lasciava `AssetSelect` a
  > girare per sempre.** `onMount` faceva `await ensureAssetsLoaded(); loading = false;`:
  > se la promessa veniva rifiutata, `loading` non tornava mai `false` e il selettore
  > restava in caricamento, senza modo di dirlo. Ora `try/catch/finally` con
  > `onLoadError?.()`, che è anche ciò che permette al controllo di conservare il suo
  > messaggio d'errore. Guasto **preesistente**, trovato migrando: riguarda ogni
  > chiamante di `AssetSelect`, non solo il mio.
  > Aggiunti anche `dropdownPosition` e `dropdownMinWidth` in inoltro (F12), che il
  > controllo usava e che si sarebbero persi: il selettore vive in fondo a un pannello
  > grafico, dove `auto` è ciò che evita che la tendina esca dallo schermo.
- [x] **14. Gate finali e handoff** — ✅ 2026-03-07
  > **Note implementazione**: E2E scritti dall'agente `test-author` (corsia **non**
  > concessa: li ho eseguiti io). Due spec nuove, appese in coda ai rispettivi blocchi
  > per ridurre la superficie di conflitto: `asset-list.spec.ts` **692-825** (le righe
  > 1-691 restano identiche al byte per il **mandato F**, che deve appendere a 825) e
  > `asset-modal.spec.ts` **639-714**.
  > La prima prova che un asset di tipo nuovo sopravvive al giro completo — API, icona
  > sulla scheda, comparsa nel filtro dei tipi — e asserisce che l'icona **non** sia
  > `other.png`, cioè esattamente il guasto silenzioso per cui esiste questo mandato.
  >
  > **Fuori pista** — 🔴 **F32: la mia stessa modifica introduceva una perdita di dati.**
  > Il `test-author` ha tracciato che `is_benchmark` non arrivava mai al form di modifica:
  > `assetEditData.ts:33` e `routes/(app)/assets/[id]/+page.svelte:1765` copiano `active`
  > ma non `is_benchmark`, quindi l'interruttore si apriva **sempre spento**. E siccome il
  > PATCH che ho scritto io manda `is_benchmark` **sempre**, e la patch backend è un
  > `setattr` generico che preserva `False`, **modificare qualunque cosa di un asset
  > benchmark lo declassava in silenzio**. Non è un difetto preesistente: è un guasto
  > **causato dal mio stesso step 11**, quindi mio da chiudere. Una riga per file.
  > La spec del `test-author` era stata scritta per essere **rossa** su questo; dopo la
  > correzione è **verde**, il che è la prova che il test misura davvero ciò che dice.
  >
  > **Fuori pista** — ⚠️ **F33: il filtro benchmark era irraggiungibile via HTTP.**
  > Avevo aggiunto il filtro tri-stato in `crud.py` e il campo in `FAAinfoFiltersRequest`,
  > ma `GET /api/v1/assets/query` (`assets.py:234`) non esponeva il parametro: il filtro
  > funzionava **solo per un chiamante in-process**. Il mio step 4 era incompleto e non se
  > n'era accorto nessun test, perché nessun test lo chiamava via rete. Parametro aggiunto,
  > documentato nel docstring e inoltrato; terzo `api sync` — `generated.ts` passa da 6 a
  > **11** occorrenze. Senza questo, **E e F** non avrebbero potuto chiedere i benchmark
  > al backend.
  >
  > **Fuori pista** — ⚠️ **F34: terza eccezione di perimetro su `+page.svelte`.**
  > Le righe del filtro dei tipi non avevano **alcun** `data-testid`, e le alternative
  > erano entrambe precluse: l'etichetta è tradotta (vietato) e l'icona non distingue i
  > sottotipi ETF, che condividono `etf.png` di proposito. Aggiunto
  > `assets-type-filter-option-{typeVal}`, seguendo la convenzione già presente nel file
  > (`column-visibility-item-{id}`, `provider-option-{code}`). Additivo, nessun
  > comportamento cambia. Senza, l'asserzione sul filtro per `ETF_STOCK` non esisterebbe.
  > ⚠️ **F30 e F31** (vedi step 12c) toccano `AssetSelect`, che è mio, ma **F31 è un
  > guasto preesistente che riguarda ogni suo chiamante**, non solo il mio.

---

## Gate finali — evidenza completa

| Comando (tutti con `--test-port 6241 --data-dir backend/data/test-risk-b`) | Esito |
|---|---|
| `dev.py lint` | ✅ *All checks passed!* |
| `dev.py front check` | ✅ **0 errors**, 41 warnings in 2 file (nessuno mio) |
| `dev.py front format` | ✅ eseguito, poi check e unit **rieseguiti** |
| `… front-asset asset-unit` | ✅ **16 file, 256 passed** |
| `… schemas assets` | ✅ **70 passed** |
| `… api assets-crud` | ✅ **32 passed** |
| `… services risk-all` | ✅ **138 passed** |
| `… db all` | ✅ **10/10** |
| `… front-asset asset-list` | ✅ **25 passed** (include la spec nuova) |
| `… front-asset asset-modal` | ✅ **16 passed** (include la spec nuova) |
| `… front-asset asset-detail` | ✅ **25 passed** — consuma il controllo riscritto |
| `… front-portfolio risk` | ✅ **6 passed** — secondo consumatore del controllo |
| `lsof -nP -iTCP:6241 -sTCP:LISTEN` | ✅ **libera**, nessun listener |
| `git diff --check` | ✅ pulito |

---

## Evidenza

| Comando | Esito |
|---|---|
| `git rev-parse HEAD` | `cc33120e…` ✅ coincide con la baseline |
| `… api sync` | ✅ exit 0 — `generated.ts` creato, 1 tool contract |
| `… test --test-port 6241 --data-dir backend/data/test-risk-b services risk-all` | 🔴 **1 failed, 137 passed** (28.1s) — rosso **voluto**, identico su 2 esecuzioni |
| `… test --test-port 6241 --data-dir backend/data/test-risk-b front-asset asset-unit` | 🔴 **2 failed, 248 passed** · file: 1 failed, 15 passed — rosso **voluto**, identico su 3 esecuzioni |
| `… db all` (dopo la migrazione) | ✅ **10/10** |
| `… lint` (dopo i passi 2-4) | ✅ *All checks passed* |
| `… schemas assets` | ✅ **70 passed** (0.96s) |
| `… api assets-crud` | ✅ **32 passed** (19.25s) |
| `… front-asset asset-unit` (dopo i passi 6-9) | ✅ **16 file, 251 passed** — cancello frontend **verde** |
| `… lint` (dopo F16 e il passo 8) | ✅ *All checks passed* |
| `… services risk-all` (dopo il passo 8) | ✅ **138 passed** (27.81s) — cancello backend **verde** |
| `… front check` (dopo K3 e F13) | ✅ **0 errors**, 41 warnings in 2 file — nessuno dei due è mio |
| `… front-asset asset-unit` (dopo K3 e F13) | ✅ **16 file, 251 passed** |
| `… front-asset asset-unit` (dopo il passo 11) | ✅ **16 file, 256 passed** — +5 test di cancello |
| `… front check` (dopo il passo 11 e l'interruttore) | ✅ **0 errors**, 41 warnings in 2 file |
| `… front check` (dopo il passo 12c) | ✅ **0 errors**, 41 warnings in 2 file |
| `… front-asset asset-unit` (dopo il passo 12c) | ✅ **16 file, 256 passed** |

I tre rossi sono tutti del cancello. **Nessun test preesistente è caduto**: gli altri 15
file Vitest e gli altri 10 file risk restano verdi, e i conteggi sono identici fra
esecuzioni — i due test sono analisi statica pura, quindi il determinismo è strutturale.
Log in `/tmp/libreFolio_risk_all*.log` e `/tmp/libreFolio_front_asset_unit*.log`.

---

## Contratti

| # | Verso | Stato |
|---|---|---|
| K2 `primaryAssetType` | G | ✅ consegnato al coordinatore (passo 6) — invariante **12**, non 13 (F24) |
| K3 selettore a sezioni | E, F | ✅ consegnato al coordinatore (passo 12b) — `sections` + `restLabel` su `AssetSelect`, testid `search-select-header-__section:{key}` |

---

## Promesse vincolanti

- `RiskAnalysisPanel.svelte` **non deve comparire nel diff** (F9) — props pubbliche di
  `SignalAssetParamControl` identiche al byte.
- Nessun `data-testid` di `SignalTreeSelect` rinominato (F8) — `e2e/gallery.spec.ts` ci
  si appoggia e Git non mostrerebbe la rottura.
- Di `routes/(app)/assets/+page.svelte` si tocca **solo** `ALL_ASSET_TYPES` a `:231`.
- Nessun `git commit`: i messaggi si propongono.

---

## Passo 15 — tre asserzioni sul secchio di cassa (post-`FROZEN`, autorizzato)

✅ completato

> **Note implementazione**: unico scongelamento dopo il `FROZEN` delle 01:34, su
> autorizzazione esplicita del coordinatore. Nessuna modifica di prodotto: sei test in
> più in `assetTypeTables.test.ts`, **256 → 262**. Proteggono l'arrangiamento del
> secchio sintetico di cassa, che attraversa la UI per la stessa via delle chiavi enum
> senza essere un `AssetType`:
>
> 1. `LIQUIDITY` **non** è un `AssetType` — letto da `models.py` per regex, come tutto
>    il resto del file;
> 2. `primaryAssetType` **continua a maiuscolare** — se qualcuno lo «corregge» a
>    restituire l'ingresso verbatim, la fetta di cassa smette di corrispondere a ogni
>    tabella chiavata in maiuscolo, e il colore cade prima dell'etichetta;
> 3. `assets.types.LIQUIDITY` esiste in **tutte e quattro** le lingue (F36) — la chiave
>    non ha alcun riferimento letterale perché `AllocationHistoryChart` la costruisce
>    per concatenazione, quindi sembra morta, ed è l'ultima del blocco: la più facile
>    da amputare.

### Falsificazione (D100) — nessuna delle tre è nata verde senza prova

| rete | mutazione | esito |
|---|---|---|
| A — `LIQUIDITY` fuori enum | `LIQUIDITY = "LIQUIDITY"` dentro `class AssetType` | **3 failed / 259 passed** — la mia più *type filter* e *creation menu* |
| B — maiuscolazione | `.trim().toUpperCase()` → `.trim()` | **1 failed / 261 passed**, messaggio esatto |
| C — chiave i18n | chiave rimossa dal solo `en.json` | **1 failed / 261 passed** — **una sola lingua rossa**, tre verdi |

Ripristino provato per impronta `git status` (`b3d61fcd…` prima e dopo) e `diff` per file.
Log: `/tmp/libreFolio_B_falsify3{,b}.log`, `/tmp/libreFolio_B_f3_*.log`.

> **⚠️ Fuori pista — le prime due mutazioni non si sono applicate, e la suite è restata
> verde.** `OTHER = "OTHER"` compare **due volte** in `models.py` (righe 142 e 192) e
> `"LIQUIDITY"` è l'**ultima** chiave di `assets.types`, quindi senza virgola finale. I
> due `assert` dentro gli script di mutazione hanno rifiutato la modifica ambigua invece
> di applicarla al punto sbagliato. Senza quegli `assert` avrei letto «262 passed» e
> concluso **«la rete non scatta»** — o, peggio, «falsificata». È la stessa famiglia dei
> falsi positivi del verde di F20/F32/F33, applicata **alla falsificazione stessa**:
> anche la prova che una rete funziona ha bisogno della prova di essere stata eseguita.

> **⚠️ Fuori pista — F38, una pastiglia mia mai dichiarata.** Alla baseline `cc33120eb`
> `LIQUIDITY` aveva **solo** `PNG_MAP` (+ `liquidity.png`, 78 KB, su disco) e l'etichetta
> i18n nelle quattro lingue. **`BADGE_CLASS_MAP.LIQUIDITY` (verde) è mia**, e non
> compare fra le pastiglie che avevo dichiarato al coordinatore — avevo nominato solo
> `INDEX` e `OTHER`. Non cambia un pixel **oggi**: nessun bene ha tipo `LIQUIDITY`, quindi
> nessuna riga chiede mai quel colore. Ma è la voce che rende il secchio di cassa
> **completamente vestito** in tutte e tre le tabelle UI — icona, colore, etichetta —
> mentre l'enum continua a non contenerlo.

### Passo 15b — arricchimento del commento (richiesto dal coordinatore)

✅ completato · `asset-unit` **262 passed**, Prettier pulito

> **Note implementazione**: il coordinatore ha fornito il testo della motivazione «perché
> sopravviva a chi la leggerà senza contesto». Quattro dei cinque elementi c'erano già.
> Ho aggiunto il quinto, **l'espressione letterale** `assets.types.${rawName.toUpperCase()}`:
> è un'àncora verificabile con un grep, non un'affermazione da credere.

> **⚠️ Fuori pista — ho rifiutato un elemento su cinque.** Il testo proposto diceva
> «**l'unica delle 18 chiavi** senza valore enum corrispondente». Non ho scritto **18**:
> un numero nudo in un commento invecchia al primo tipo aggiunto, ed è esattamente la
> modalità di guasto che il coordinatore stesso ha codificato su K2 («baseline 24» senza
> dire in quale mondo) e su K7. La **relazione** — «l'unica voce senza `AssetType`
> corrispondente» — non invecchia **e il test la ricalcola a ogni corsa**.

---

## Passo 16 — riapertura dopo `FROZEN`: duplicazione di `data-testid` (F30 di ritorno)

✅ completato · trovato da **F**, verificato dal coordinatore sul mio worktree, riparato e misurato qui

> **Note implementazione.** La mia correzione F30 inoltrava `testId={testid}` a `SearchSelect`
> **senza togliere l'id al wrapper**: due elementi annidati con `data-testid="asset-select"`,
> cioè una violazione di strict mode per ogni spec che lo risolve senza `.first()`.
> Verificato sul codice, non sull'elenco ricevuto: la baseline `cc33120eb:AssetSelect.svelte:123`
> ha il wrapper **e nessun inoltro** (`git show … | grep testId` → nulla), quindi l'inoltro è mio.
> `SearchSelect.svelte:357` rende `data-testid={testId}` **nudo**, non suffissato.
>
> **Riparazione**: il wrapper torna un `<div>` spoglio con un commento che spiega perché non
> porta id; l'identità vive solo su `SearchSelect`. L'inoltro **resta** — due spec consumano
> `…-trigger` (`risk-analysis.spec.ts:730`, `asset-detail.spec.ts:256`), che era la ragione di F30.
> Il wrapper conteneva **solo** `<SearchSelect>` e nessuna classe: spostare l'id è senza effetti.

> **⚠️ Fuori pista — il raggio d'azione ricevuto era sbagliato in entrambi i versi.**
> Dei cinque spec elencati, **tre sono protetti da `.first()`** (`tx-import-ca-contract:455`,
> `tx-import-resolution` ×7, `gallery.spec.ts:3648`) e non potevano fallire. In compenso
> l'elenco **ometteva `e2e/assets/asset-merge.spec.ts:137`**, che risolve
> `asset-merge-target-select` senza `.first()` — ed è **l'unico rosso che ho osservato davvero**:
> `front-asset asset-merge` → **3 failed**, `strict mode violation: … resolved to 2 elements`,
> poi **3 passed** dopo la correzione. Il rosso l'ho **osservato prima di riparare**, per non
> ripetere F37 (una diagnosi senza il rosso corrispondente).
> `gallery.spec.ts:3648` verificato **per lettura, mai eseguendolo** (`EXCLUDED_SPECS`): ha `.first()`.

> **⚠️ Fuori pista — F39, la storia esiste ma non su un percorso che qualcuno percorre.**
> Avevo ripetuto che un ripristino all'ingrosso avrebbe cancellato le mie 13 righe in
> `scenario_catalog/loader.py` «senza lasciare traccia». **Falso**: `git log --all` su quella
> directory restituisce 15 commit, **tutti della mia stessa sessione**, in
> `refs/copilot/checkpoints/<session>/…`. La traccia c'è (`b4817544c`); quello che manca è un
> ref che un revisore pensi di guardare. La stessa verifica **conferma** la tesi del
> coordinatore per la via opposta alla sua: lui ha letto gli alberi di lavoro di N, A, H, C,
> io la storia — nessun altro scrittore.

### Cancelli dopo la correzione — comandi ed esiti, uno alla volta nella lane 6241

| comando | esito |
|---|---|
| `front-asset asset-unit` | **16 + 262 passed** |
| `front-asset asset-merge` | **3 passed** (erano 3 failed) |
| `front-asset asset-list` | **25 passed** |
| `front-asset asset-modal` | **16 passed** |
| `front-asset asset-detail` | **25 passed** |
| `front-portfolio risk` | **6 passed** |
| `front-transaction tx-import-matching` | **6 passed** |
| `front-transaction tx-import-resolution` | **12 passed** |
| `front-transaction tx-ca-contract` | **2 failed / 10 passed** → vedi sotto |
| `front-transaction tx-import-asset-inspector` | **1 failed / 4 passed** → vedi sotto |

> ⚠️ La categoria è **`front-transaction`** (singolare) e l'azione è **`tx-ca-contract`**, non
> `tx-import-ca-contract`. Entrambi gli `exit=2` incontrati erano **argparse**, non pytest.

---

## Passo 17 — i due rossi residui: **ritratta la mia attribuzione causale**

⚠️ **La scoperta di questo passo è un mio errore, non un difetto del prodotto.**

Avevo riferito al coordinatore che il rosso di `tx-import-asset-inspector` era
**«provato mio per esecuzione»**, sulla base di *una* misura: con `AssetModal.svelte` a
baseline lo spec dava 5 passed. **Quella misura era un verde singolo fortunato.**

### La matrice causale, costruita eseguendo

| `AssetModal` | `AssetSelect` | corse | esito |
|---|---|---|---|
| mio | mio | 2 | 2 × rosso |
| **senza il markup del toggle** (−21 righe) | mio | 1 | rosso |
| **senza le due righe di payload** | mio | 1 | rosso |
| **senza `isBenchmark` in `buildFormSnapshot`** | mio | 1 | rosso |
| **baseline** | mio | **5** | **1 verde, 4 rossi** |
| mio | **baseline** | 2 | 2 × rosso |
| *solo `E2-001`, isolato* | mio | 1 | **verde** |

`tx-ca-contract`: **2 failed / 10 passed** in tutte e tre le configurazioni provate,
inclusa quella con `AssetSelect` a baseline.

**Conclusione: né `AssetModal.svelte` né `AssetSelect.svelte` causano questi rossi.**
Nessuno dei due spec è nel mio diff; entrambi sono stati toccati l'ultima volta da
`916f12bdd feat(dev): isolate test runtime lanes`, e `tx-import-asset-inspector.spec.ts`
è nato il giorno prima (`ef722b552`, 2026-09-09).

### Il meccanismo, per quanto ho potuto vederlo

`E2-001` fallisce alla **seconda** chiamata di `blockedSave()` (spec:704), dentro
`chooseCurrency` (spec:476): `getByTestId('asset-modal-currency-group').getByRole('listbox')`
→ *element(s) not found*. Lo screenshot mostra il modale **aperto e regolare**, con la valuta
già su `USD` e il combobox **chiuso** — quindi il click non ha aperto la tendina, o l'ha chiusa.

`optionsClosed()` (`e2e/fixtures/probe.ts:46`) asserisce **zero opzioni**:

```ts
await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0);
```

Ma la tendina di `SearchSelect` rende il `listbox` con `aria-busy={loading}` **prima** delle
opzioni (`SearchSelect.svelte:452`). Una tendina **aperta ma ancora vuota** soddisfa
`optionsClosed`, e il `.click()` successivo sul combobox la **richiude** → nessun listbox.
Il docblock dell'helper dice di aver sostituito un `waitForTimeout(300)`: ha **ristretto** la
finestra, non l'ha chiusa. Che `E2-001` **passi da solo** e cada in sequenza è coerente con
questa lettura.

> **⚠️ Fuori pista — ho ripetuto F37 un livello più in basso.** Avevo *nominato* l'errore
> («non ripetere il fantasma di F37») e poi l'ho commesso: una singola esecuzione verde
> trasformata in una relazione causale, e riferita al coordinatore come **provata**.
> La bisezione non l'ha smentita rimuovendo la causa — l'ha smentita perché **ogni**
> rimozione restava rossa, che è la firma di una causa che non sta nel file.
> **Un verde non è una misura. È una misura con N = 1.**

---

## Passo 18 — F42: «la tredicesima chiave ha già un colore» è vero sul mio file e **falso per G**

Il coordinatore ha scritto, registrando F38: *«se G calcola la tavolozza **via** `assetTypeBadgeClass`, la tredicesima chiave **ha già un colore**»*.

Verificato eseguendo, tre fatti veri e una conclusione falsa:

| | |
|---|---|
| ✅ `BADGE_CLASS_MAP.LIQUIDITY` esiste | è mia (F38) |
| ✅ la mappa è **coperta dal cancello** | `assetTypeTables.test.ts:158` — enum ⊆ mappa |
| ✅ copre 18 chiavi | 17 valori enum + `LIQUIDITY` |
| 🔴 **ma i valori non sono colori** | sono **stringhe di classi Tailwind**: `'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'` — **zero `#` in tutta la mappa** |

`assetTypeBadgeClass()` restituisce una classe CSS. **ECharts vuole un valore di colore.**
G non può passare quella stringa a una serie: la fetta non prende il colore giusto — e
**non si rompe niente**, perché `BADGE_CLASS_FALLBACK` è una stringa valida come le altre.

> **È il ripiego silenzioso un'ultima volta, e stavolta travestito da buona notizia.** La
> raccomandazione instraderebbe G **verso** la funzione il cui ripiego è un grigio Tailwind,
> cioè dentro il difetto che G sta riparando. In più la mappa codifica i due temi **nella
> stessa stringa** (`dark:` inline): non è separabile in un colore chiaro e uno scuro.

**Cosa resta vero e utile per G**: l'**insieme** delle chiavi — 12 primari + `LIQUIDITY` = 13 — e
il fatto che quell'insieme è **già sorvegliato** contro l'enum. Una tavolozza *parallela*,
scritta a parte, **non lo sarebbe**: il cancello protegge `BADGE_CLASS_MAP`, non «i colori».

---

## Passo 19 — contratto K2 pinnato sul comportamento, non sul testo (richiesta di G)

✅ completato · `front-asset asset-unit` **262 → 264 passed**, Prettier pulito, entrambe falsificate

> **Note implementazione.** G ha chiesto due asserzioni «nel file di B, non nel mio», perché
> l'invariante è una proprietà **di K2** e da lui sarebbe *il secondo guardiano della stessa
> proprietà nel posto sbagliato*. Ha ragione, e la richiesta è più forte di come è arrivata.

### Prima ho verificato il presupposto, poi ho scritto

La seconda asserzione — *`null`/`undefined`/`''` → `'OTHER'`* — **sembrava falsa**: dalle due
righe di `primaryAssetType` che avevo in mente (`raw = (type ?? '').trim().toUpperCase()`,
`return PRIMARY_TYPE_MAP[raw] ?? raw`) l'input vuoto esce come `''`, non `'OTHER'`.
**Letto il codice, c'è una guardia** — `if (raw === '') return 'OTHER';` — e l'asserzione è vera.
Il difetto era nella mia versione riassunta, non nel prodotto.

### 🔑 La scoperta: la mia rete precedente su K2 è **testuale**, e non copre il caso

`keeps primaryAssetType upper-casing its input` legge il sorgente e verifica che
`.toUpperCase()` compaia nel corpo. **Cambiare l'ultima riga da `?? raw` a `?? type` lascia
quella chiamata intatta** e restituisce al chiamante la sua stessa grafia: il contratto è
morto e la rete resta verde.

**Falsificato eseguendo**, con `assert` di applicazione della mutazione (D136):

| mutazione | applicata? | esito | quale test |
|---|---|---|---|
| `?? raw` → `?? (type as string)` | ✅ n=1, `.toUpperCase()` ancora presente ×4 | **1 failed / 263** | `returns an upper-case value…` |
| rimossa `if (raw === '') return 'OTHER';` | ✅ guardia assente | **1 failed / 263** | `folds nullish and blank input…` |
| ripristino | `diff -q` identico | **264 passed** | — |

> ⚠️ **Nel primo caso il test testuale NON compare fra i rossi** (`grep -c` sul log → **0**).
> È la tesi di G provata per esecuzione: le due reti **non sono ridondanti**, e quella vecchia
> è verde esattamente sulla mutazione che distrugge il contratto.

> **⚠️ Fuori pista — l'import statico avrebbe avvelenato tutto il file.** `assetTypes.ts`
> importa `$lib/api/generated`, che è **gitignored**, e **nessun test del repo lo importa oggi**.
> Un `import` in testa avrebbe trascinato tutti e 18 i test di scraping in quella dipendenza,
> perché un import irrisolvibile fa fallire **l'intero modulo in fase di collection** — e il
> file esiste proprio per funzionare su un checkout dove `api sync` non è mai girato.
> Usato un **import dinamico locale ai due test** che devono *chiamare* la funzione, con
> `existsSync` che **fallisce invece di saltare**: in una riga di riepilogo un test saltato e
> uno soddisfatto sono la stessa assenza di rosso.

### Cancelli E2E non rilanciati, e perché

`git diff 590f32ae6` → **zero file di prodotto tracciati modificati**; `assetTypes.ts`
**byte-identico** al checkpoint dopo le mutazioni. Il delta è **un solo file, +68 righe, di soli
test Vitest**, che Playwright non carica. `asset-detail`, `front-portfolio risk` e i
`tx-import-*` misurerebbero **lo stesso albero di 40 minuti fa** — e i due rossi noti di
`tx-ca-contract` e `tx-import-asset-inspector` aggiungerebbero rumore, non segnale.

---

## Passo 20 — il cancello richiesto era già speso, e l'altro non esiste

✅ completato · `front-asset asset-merge` **3 passed (8.1s)**, misura fresca

Il coordinatore ha chiesto due cancelli aggiuntivi sostenendo che *«`tx-import-*` esercita
solo il DEFAULT: le due vie personalizzate — merge e risk-lab — non ci sono dentro»*.
**Il ragionamento è corretto; due dei suoi fatti no.**

### `asset-merge`: è la via personalizzata, e l'ho già esercitata — è quella che ha **trovato** il difetto

`AssetMergeModal:259` passa `testid="asset-merge-target-select"`, un id **personalizzato**.
È precisamente il percorso che distingue *inoltrare* da *inoltrare e togliere*. Cronologia:

| momento | esito |
|---|---|
| prima della correzione | **3 failed** — `resolved to 2 elements` |
| dopo la correzione | **3 passed** |
| rimisurato ora | **3 passed (8.1s)** |

### `risk-lab`: non è runnable, e non toccherebbe il mio codice nemmeno se lo fosse

Tre strati, tutti misurati:

1. **`AssetSetRiskPanel.svelte` non usa `AssetSelect`.** `grep -c AssetSelect` → **0**;
   usa **`SearchSelect` diretto** (`:135`). L'id `risk-asset-add-select` **non attraversa
   il mio componente**: la mia rimozione non può raggiungerlo.
2. **Il file è baseline, non mio** — `git status --porcelain` vuoto.
3. **Lo spec si chiama `risk-analysis.spec.ts`**, non `risk-lab.spec.ts`, e a `:652` risolve
   **`risk-asset-add-select-trigger` direttamente**: `role="combobox"` compare **0 volte**
   nel file. Lo helper citato è codice **nuovo di F, nel worktree di F**.
4. E l'azione `risk-lab` **non esiste nel runner**: `front-portfolio` espone
   `banners · broker-icons · dashboard · risk-unit · store-unit · risk · all`.
   Il comando sarebbe uscito con **exit=2** di argparse, senza eseguire nulla.

### 🔑 F44 — l'inoltro non ha attivato **un** testid, ne ha attivati **cinque**

`SearchSelect` **baseline** deriva cinque id da `testId`, tutti preesistenti:

```
:357  data-testid={testId}                    ← container   ⚠️ QUESTO collideva
:377  data-testid={`${testId}-trigger`}       ← combobox
:393  data-testid={`${testId}-search`}
:440  data-testid={`${testId}-search`}
:443  data-testid={`${testId}-search-clear`}
```

Erano **dormienti per ogni consumatore di `AssetSelect`**, perché la baseline non inoltrava
nulla. La mia riga li ha accesi tutti e cinque insieme: **quattro erano lo scopo di F30**,
**uno collideva col wrapper**. Quindi la correzione non è stata «spostare un id», è stata
**tenere i quattro che erano il punto e lasciar cadere quello che duplicava**.

> **Corollario per E e per F**: dopo la correzione ogni consumatore di `AssetSelect` guadagna
> `-trigger`, `-search` e `-search-clear` **gratis**. Lo helper `.locator('[role="combobox"]')`
> è quindi **superfluo**: `getByTestId('<id>-trigger')` è la forma diretta, ed è già quella che
> `risk-analysis.spec.ts:652` usa **nella baseline**.

### Il tabellone dei punti di chiamata, corretto

| # | punto di chiamata | testid |
|---|---|---|
| 1 | `ImportWizardModal:4324` | *nessuno* → default `asset-select` |
| 2 | `TransactionFormModal:1513` | `tx-form-asset` |
| 3 | `TransactionFormModal:1886` | `tx-form-asset` |
| 4 | `AssetMergeModal:259` | `asset-merge-target-select` |
| 5 | **`SignalAssetParamControl:35`** | **`testid={testId}` — una prop, nessun valore fisso** |

`AssetSetRiskPanel` **non è nell'elenco**. Il quinto punto **è mio** (29+/40−): è un
consumatore di **K3**, con `sections=[{key:'benchmark'}]`, e il suo id è coperto da
`asset-detail` (25 ✅) e `risk` (6 ✅), entrambi già verdi.

---

## Passo 21 — conferma esterna di F40/F41, e la forma esatta del debito

✅ chiuso · misura eseguita dal coordinatore su `e-alfy-ideal-eureka`, HEAD `cc33120eb`,
`git status --short frontend/ backend/ scripts/` **vuoto**, corsia 6250, DB ripopolato

Restava una cosa che **non potevo misurare io**: il comportamento dei due rossi sulla
baseline pura, perché non posso leggere un altro checkout e non avevo un «prima» per
`front-transaction`.

| spec | corse | esito |
|---|---|---|
| `tx-ca-contract` | 3 | **2 failed / 10**, sempre — **CAC-011, CAC-012** identici |
| `tx-import-asset-inspector` | 3 | **✘ / ✓ / ✘** — E2-001 cade **2 volte su 3** |

**Entrambi preesistenti. Nessuno dei due è mio.**

### 🔑 La ritrattazione F41 confermata dall'esterno, non solo accettata

Il verde di baseline che avevo osservato **una volta**, e da cui avevo concluso «provato mio»,
**è la corsa 2 di questo tabellone**. Esiste, capita **una volta su tre**, e non significa nulla.
La frase che avevo scritto ritrattando — *«un verde non è una misura: è una misura con N = 1»* —
non era una formula di contrizione: era **la descrizione anticipata di questa tabella**.

### 🔑 F40 confermata dai tempi, indipendentemente dal mio racconto

**12,9 s e 12,7 s contro 3,4 s.** Un'asserzione che sbaglia costa quanto una che indovina;
**un'attesa che scade costa nove secondi in più**. La firma è quella di un **timeout**, non di
un confronto fallito — cioè `optionsClosed()` (`probe.ts:46`) soddisfatto da una tendina
**aperta e vuota** (`SearchSelect:452` rende il listbox con `aria-busy` prima delle opzioni),
col `.click()` successivo che la **richiude**.

### ⚠️ Il debito mente in **due** direzioni, e non simmetricamente

Il coordinatore lo registra come *«una corsa su tre mente in una direzione o nell'altra»*.
Le due direzioni **non hanno lo stesso costo**:

| esito | cosa afferma di falso | costo |
|---|---|---|
| **verde** (⅓) | «la tua modifica è coperta» | non misuri, e non lo sai |
| **rosso** (⅔) | «la tua modifica ha rotto questo» | **falsa attribuzione** |

> Il rosso è il più caro, e ho la prova empirica perché **l'ho pagata io**: una bisezione in
> tre di `AssetModal.svelte` più cinque corse di controllo, tutte su un file innocente.
> Chi eredita il debito deve sapere che il guasto non è «uno spec ballerino»: è **uno spec che
> accusa il file che stai modificando**.

Indirizzi per il proprietario futuro: `frontend/e2e/fixtures/probe.ts:46`,
`frontend/src/lib/components/ui/select/SearchSelect.svelte:452`.
