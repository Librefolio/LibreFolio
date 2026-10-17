# Piano — fase 01, 03: plugin, asset e ricerca (X)

> **Via libera parziale al codice** — coordinatore 1.3, 14/10/2026 ~22:55, su delega esplicita del developer. Parole del
> developer, alla lettera, riportate dal coordinatore: «chat, sto leggendo
> LibreFolio_developer_journal/Release_2/Phase_1/decisioni-analisi-20261014.md — ho appena finito le prime 11 domande e
> sto iniziando piattaforma, ma ho già messo varie note dev, leggi intanto quelle, vedi se con quelle risposte devi
> aggiornare quello che viene dopo e poi vedi tu se aspettare che leggo tutto, o intanto grazie a queste riesci ad avviare
> qualche lavoro». Decisione del coordinatore: parte **solo X0 e CP1** (riordino puro); il resto aspetta il suo via, con
> le risposte del developer.
>
> - **Approvate** (coordinamento, 14/10): D-P1, D-X1, D-X3, D-X5, D-X6, D-X7, D-X8, D-X11, D-X12, D-X13, D-X14, D-X15.
>   D-X9 è **superata da C3** (schemi in pacchetti per dominio; gli eventi in `schemas/assets/events.py` o dove li colloca X
>   nel pacchetto). D-X10: oltre al confronto di `openapi.json`, la verifica della corrispondenza dei percorsi (C2).
>   **Ancora al developer**: D-X2 (voce 18, assorbita dalla voce 39, non ancora decisa). **D-X4 decisa il 15/10** (voce 19): §4.3.
> - **Regole comuni**: piano generale, §6 (Git, «Forma comune del riordino» C1–C7, superfici condivise, regole di ogni lotto
>   di riordino, «Taglio dichiarato», nuove schermate) e §7 (programma colori, regola «chi parte prima»).
> - **Primo treno**: H CP1 → X CP1 → A A1; il CP1 di X entra dopo quello di H, con gli import riallineati all'aggiornamento
>   di base.
> - **Indicazioni per dopo** (coordinatore, 14/10): `market_calendar` e `web_link_finder` → `services/assets/` in CP2a;
>   eventi in moduli propri, consegnati a W dopo CP2b; `AssetModal` è fuori dai lotti dei colori e si può tagliare prima
>   del lotto A, con annuncio (§7 del piano generale), la pagina dell'asset dopo la riga di G; nel lotto F05, dal giro di
>   sicurezza di H, il `css_scraper` non deve raggiungere loopback, reti private, link-local e metadati del cloud, anche
>   dopo un redirect; le parti X6, X7, X8 e `fx.py:717` di U1 le scrive J nei file di X dopo PL4 (regola 10), con X
>   informato.
> - **Finestra della galleria**: 15/10 dalle 09:00, circa 2 ore: nessuna `all-backend` né build pesanti nella corsia.
>
> - Sessione: «X - Plugin asset e ricerca»; coordinatore «Release 1.3 planning» (`928ffa97-f0c3-4975-a442-3de0c2c20fc7`).
> - Worktree: `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-cuddly-engine`; ramo
>   `e-alfy-x-plugin-asset-e-ricerca`. Base del codice: `c9bb8f257643c0b770788033789425b41ba16715` (fast-forward del
>   coordinatore da `459131eb8`, solo journal, `scripts/visual_review/gallery_snapshot.sh` e `TODO_FUTURI.md`).
> - Corsia: porta **6183**, data-dir **`/tmp/librefolio-r13-x`**. Preambolo:
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6183 --data-dir /tmp/librefolio-r13-x <CAT> <AZIONE>`.
> - L'analisi (§1–§14) è quella consegnata al coordinatore il 14/10, con le correzioni della rilettura; l'avanzamento è
>   nel §15.

## 1. Fonti lette

`.github/copilot-instructions.md`; istruzioni `backend`, `backend-providers-{asset,fx,brim}`, `backend-{signals,risk,tools,schemas,db}`,
`frontend`, indici di `backend-testing`, `frontend-testing`, `mkdocs`; skill `asset-plugin`, `brim-plugin`, `tool-plugin`,
`devpy-i18n`, `wiki-search`. Piano 1.3 (§1–§12) e README di `Phase_1`; piano 43 §1, §4, §7.2–7.5, P2.0–P2.7; piano 45 §2–§9
(U-B1); `TODO_FUTURI.md` («🔌 Arricchimento…» r. 8, «⚙️ Impostazioni per plugin» r. 1924); feedback utente C (voci 3, 11, 15);
`BACKLOG_POST_1.2.md` (C-65, C-66, C-90, T-PL*, U-B*, sezione X); backlog 38 (K-16, K-19, K-20, O-8, O-9, O-20);
`TODO_ProssimeAttivita.md` voce 5; specifica cloud «Feature SaaS Readiness» (F03, F05, F06, F21; sola lettura). devWiki:
`domains/assets.md`, `domains/fx.md`, `decisions/provider-registry-decision.md`, `entities/asset-sources-package.md`,
`decisions/settings-write-path-contract.md`. **Grafo della devWiki non disponibile** nel worktree (atteso): pagine lette
direttamente.

## 2. Stato reale verificato (su `459131eb8`)

### 2.1 Registri e contratti delle famiglie

| Oggetto | Dove oggi | Note verificate |
|---|---|---|
| Basi e decoratori | `services/provider_registry.py` (617 righe) | `AbstractPluginRegistry` :115, `AbstractProviderRegistry` :314, `register_provider` :574, `register_plugin` :593; re-export pigri `SignalPlugin`/`RiskAnalytic` :20-38 (usati solo da `test_signal_registry.py:644-645`) |
| `FXProviderRegistry` | `provider_registry.py:373` | importato da 12 file app (6 plugin) e 8 test |
| `AssetProviderRegistry` | `:379` | 18 app (6 plugin), 15 test |
| `SignalPluginRegistry` | `:385` (validazione con import pigro di `signal_plugins.base`) | 32 app (23 plugin), 17 test |
| `RiskAnalyticRegistry` | `:428` (import pigro di `risk.base`) | 18 app (15 plugin), 5 test |
| `BRIMProviderRegistry` | `:471` (+ `auto_detect_plugin`, `get_compatible_plugins`, `list_plugin_info`) | 43 app, 15 test |
| `ToolPluginRegistry` | `tools/registry.py:175` | già «uno per famiglia» (sottoclasse di `AbstractPluginRegistry`) |
| Importatori di `provider_registry` | — | **107 file app, 45 test, 2 script** (il piano 43 diceva 104) |
| Contratto asset | `asset_sources/core.py:251-885` (`AssetSourceProvider`) | `params_schema` lista di dict (`core.py:701`); `get_plugin_instance` (`provider_registry.py:155-163`) crea un'istanza nuova a ogni chiamata e ricade in silenzio su `plugin_class()` se i kwargs danno `TypeError` |
| Contratto FX | `fx.py:52-337` | **si chiama `FXRateProvider`**, non `FXProvider` come scrive `backend-providers-fx.instructions.md` (deriva da correggere) |
| Contratto BRIM / segnali / rischio / tools | `brim_provider.py:118` (W) / `signal_plugins/base.py` (J) / `risk/base.py` (J) / `tools/base.py:95` | nessuna famiglia ha impostazioni; i tools girano in processi isolati senza principal né DB; il parse BRIM gira in un **process pool** (`brim_parse_pool.py`) |

### 2.2 Asset (servizi)

- Shim `services/asset_source.py` (21 righe): **13 importatori app** (i 6 plugin asset, `mockprov` compreso;
  `brim_provider.py:79`, `scheduler/jobs.py:15`, `risk/service.py:57`, `ai_export/components/{asset_resources,technical_shared}.py`,
  `api/v1/assets.py:69`, import pigro in `schemas/provider.py:204`), ~25 file di test e un diagnostico; il vecchio percorso
  compare anche in commenti e docstring (`utils/json_utils.py:10`, `schemas/common.py:369`, `db/models.py:123`,
  `signal_plugins/drawdown/plugin.py:119`) e nel runner (`_backend_services.py:184,195,515,617`, `_backend_utils.py:112`,
  `_server.py:221`, `scripts/coverage_analysis.py:55,178`). In più **`asset_sources/__init__.py` è un barile pigro**
  (`_EXPORTS`, `__getattr__`), un secondo shim non citato dal piano 43; nessuno lo usa per i nomi (solo import di
  sottomoduli), quindi si riduce a docstring senza danni.
- Pacchetto `asset_sources/` (5 609 righe): `core.py` 899, `crud.py` 871, `price_query.py` 939, `price_store.py` 1 020,
  `refresh.py` 688, `provider_management.py` 466, `search.py` 444, `metadata.py` 210, `manager.py` 22 (mixin).
- `price_store.py`: prezzi :55-472 (con `_upsert_asset_events` :277 usato da `refresh.py:556`), cambio di valuta :473-628,
  eventi :629-1020 (`bulk_upsert_events`, `query_events_bulk`, `get_events_by_ids`, `delete_events_bulk`).
- `web_link_finder.py` (273, legge 7 variabili d'ambiente fra cui `LIBREFOLIO_WEB_LINK_FINDER_API_KEY`: **H la tocca per F03**)
  e `market_calendar.py` (183; importato da `main.py`, `series_preparation.py`, `risk/{service,eligibility}.py`, `price_query.py`).

### 2.3 Cambi, router, schemi

- `fx.py` **1 673 righe** (piano: 1 679): base :52-337, normalizzazione :344, errori :380, sync `ensure_rates_multi_source` :401,
  catene :681, `sync_pairs_bulk` :780, `convert_bulk` :1238, `upsert_rates_bulk` :1435, `delete_rates_bulk` :1536.
  **17 importatori app fuori dai plugin, più i 6 plugin FX** (piano: 19): 7 di J (`financial_math/{average_cost,native_cash,
  yield_on_cost}.py`, `financial_math/lots/conversions.py`, `financial_math/portfolio/engine.py`, `portfolio_service.py`,
  `risk/eligibility.py`), 6 dell'AI Export, 3 miei (`api/v1/fx.py`, `price_query.py`, `price_store.py`), `scheduler/jobs.py`;
  11 test; patch dei test su `fx_service._fx_fetch_cache` e `fx_service.FXProviderRegistry` (`test_fx_sync_service.py:210-288`);
  le patch di `convert_bulk` sono sui moduli consumatori (non cambiano).
- `api/v1/assets.py` 1 229: quattro router (`asset`, `price`, `provider`, `event`) composti a :1227-1229; eventi :1027-1166;
  market data :1167-1226; catalogo segnali `GET /assets/prices/signals` :735. `api/v1/fx.py` 1 091: `providers`, `currencies`;
  catalogo segnali :516; `convert` con piano/esecuzione dei segnali intrecciati :524-722; rotte :729-1089. `api/v1/signals.py` 65.
- `operationId` = nome funzione + percorso + metodo (default FastAPI): spostare le funzioni non li cambia; **l'ordine dei
  percorsi** in `openapi.json` segue l'ordine di registrazione (in `assets.py` le rotte proprie dell'`asset_router`, in ordine
  di file, poi `prices`, `provider`, `events`; in `fx.py` `providers` poi `currencies`): riproducibile identico dopo la
  divisione. `openapi.json`/`generated.ts` sono ignorati da git; `dev.py api schema` (solo Python) basta a provare «nessuna
  differenza» sui lotti backend; `api sync` completo vuole `node_modules`.
- **Test che importano i moduli dei router**: `test_fx_api_unit.py` (patch su `fx_api.sync_pairs_bulk`,
  `fx_api.FXProviderRegistry` e altre globali), `test_fx_signals_api.py` (`fx_api.convert_bulk`), `test_fx_compress_errors.py`,
  `test_signal_catalogs.py`, `test_signal_request_validation_api.py` (funzioni di `api/v1/{assets,fx}`),
  `test_schemas/test_fx_route_schemas.py`. Dopo la divisione le patch puntano al sotto-modulo che usa il nome; un `setattr` su
  un nome sparito fallisce rumorosamente (nessuna patch muta), ma va riscritto.
- Schemi: `assets.py` 1 000, `prices.py` 551 (eventi :270-456), `provider.py` 438 (`FXProviderInfo` dentro), `refresh.py` 245
  (FA + FX insieme), `fx.py` 500; importatori: assets 15 app/26 test, prices 13/32, provider 11/16, refresh 5/12.

### 2.4 Frontend

- `lib/components/assets/` 55 file; `AssetModal.svelte` **2 510**; `routes/(app)/assets/[id]/+page.svelte` **3 597** (piano 3 578;
  polling a :1494 e :2000-2064, che Z cambia); `assets/+page.svelte` 1 864; `lib/components/fx/` 10 file;
  `fx/+page.svelte` 1 263, `fx/[pair]/+page.svelte` 1 652. Importatori di `$lib/components/{assets,fx}`: 19 file, fra cui
  `ImportWizardModal` e `TransactionFormModal` (W, FE8), dashboard, rischio, lotti, planner del PAC.
- Impostazioni: `routes/(app)/settings/+page.svelte` con 4 schede fisse (`TabId`); il registro delle schede è di A.
- Ricerca: `AssetSearchAutocomplete.svelte` legge l'SSE con `fetch` manuale (`/assets/provider/search/stream`); i risultati
  arrivano **in ordine di risposta**; la cache di ricerca è per `(provider, query)` (`search.py:237`, `:368`).
- `node_modules` assente (atteso): servirà `npm ci` (con il via del coordinatore) al primo lotto frontend.

### 2.5 Voci del dominio

| Voce | Stato verificato |
|---|---|
| K-16 | aperta: `borsa_italiana/plugin.py:82` `"etc/etn": AssetType.ETF` |
| K-19 | aperta: la lista asset non ha snapshot né filtri nell'URL |
| K-20 | aperta, riga spostata: `assets/[id]/+page.svelte:2689` usa `$page.url`; `lib/utils/url/dateRangeUrl.ts:13` scrive con `history.replaceState` |
| O-8 | aperta: `AssetDataEditorSection.svelte:444`, `:466`, `:467` |
| O-9 | aperta: `justetf/` e `css_scraper/` non hanno `i18n/`; il frontend legge già `assets.providerParams.${code}.${kind}.${key}` (nessuna modifica frontend) |
| O-20 | aperta: `AssetModal.svelte:1462` (sync post-creazione `start: 'resume'`) più `assets/+page.svelte:1834-1840` |
| C-66 | aperta: `ui/modals/SyncModalBase.svelte`, `PageSyncModal`, `AssetSyncModal`, `FxSyncModal` |
| C-90 | aperta: `ProviderAssignmentSection.svelte:372` (**file del lotto A dei colori**) |
| Voce 5 (link alle transazioni nella modale di cancellazione) | **già fatta** il 10/09 (`e50d66408`): conteggio e link sia nella cancellazione singola (`assets/+page.svelte:920-934`, `asset-delete-transactions-link`) sia nella multipla (`:985-994`); backend `FAAssetDeleteResult.transaction_count` (`schemas/assets.py:809`, `crud.py:376-385`); E2E in `e2e/assets/asset-list.spec.ts`. Da chiudere |

## 3. Già fatto, contraddetto, derive

- Voce 5: fatta (sopra). La pagina wiki F-095 la dà ancora «pianificata».
- Numeri del piano 43 superati: importatori di `provider_registry` 107/45/2; `fx.py` 1 673 righe e 17 importatori app.
- PL2 non può spostare `FXProviderRegistry` nel suo runtime senza PL4: un pacchetto `services/fx/` e il modulo `services/fx.py`
  non possono convivere (vince il pacchetto). Il registro FX si sposta con PL4.
- `asset_sources/__init__.py` è un barile pigro: PL6 (CP2a) lo riduce a docstring.
- `backend-providers-fx.instructions.md` («`FXProvider`») e la mappa di `backend.instructions.md` («`services/fx.py`
  (`convert_bulk`)») vanno corrette nel lotto che sposta il file.
- La voce 15 dell'utente C («nazione e valuta») si traduce così: **justETF → valuta preferita** (EUR/USD/CHF/GBP, o la valuta
  del fondo 👑); **Borsa Italiana → lingua preferita** (IT/EN, le due bandiere). Default «tutte» = comportamento di oggi.
- La specifica cloud F21 nomina un terzo livello `advanced`; il perimetro testuale del coordinatore ne ha due
  (premium/community): seguo il coordinatore.
- Consegna degli eventi: confermata dal piano generale sulla base nuova (`f27e83448`, «Fuori pista» delle sessioni avviate).
- Il gate `utils gate-plugin-layout` trova le famiglie leggendo i registri in tutto `backend/app`
  (`test_plugin_layout_gate.py:166`, `:439`) e il solo `PLUGIN_MODULE_NAME` in `provider_registry.py`: sopravvive a PL2 senza
  modifiche, purché `PLUGIN_MODULE_NAME` resti nelle basi.

## 4. Disegno per area

### 4.1 Riordino backend — forma d'arrivo

```text
services/
  provider_registry.py      basi + decoratori (D-P1), senza registri di famiglia né re-export pigri
  plugin_settings/          NUOVO: campi dichiarati, archivio cifrato, risoluzione, servizio
  assets/                   ← asset_sources/* + registry.py + base.py + web_link_finder.py + market_calendar.py
    registry.py base.py core.py crud.py manager.py metadata.py price_query.py provider_management.py
    refresh.py search.py price_store.py currency_change.py event_store.py(→W) web_link_finder.py market_calendar.py
  asset_source_providers/   invariato (D-P2)
  fx/                       ← fx.py, che in CP1 entra come fx/fx.py (C1) accanto a fx/registry.py; al PL4 il taglio per tema
                            (base.py, sync.py, conversion.py, storage.py)
  fx_providers/             invariato
  brim/registry.py          NUOVO in PL2; il pacchetto lo riempie W (PL5)
  signals/registry.py       NUOVO in PL2; il pacchetto lo riempie J (PL1)
  risk/registry.py          NUOVO in PL2 (pacchetto di J)
api/v1/
  assets/  __init__.py (composizione dei sotto-router, C2) crud.py providers.py prices.py events.py(→W) market_data.py
  fx/      __init__.py (composizione, C2) providers.py currencies.py
  plugin_settings.py        NUOVO
schemas/                    pacchetti per dominio (C3): schemas/assets/ con gli eventi in schemas/assets/events.py (→W),
                            __init__.py con la sola docstring; l'hub schemas/__init__.py resta
```

Regole (piano 43 P2.0): prima la rinomina (`git mv`, ≥ 95 % in `git diff -M`), poi il taglio; niente shim né barili;
`patch` dei test sui nuovi percorsi; grep dei vecchi percorsi a zero in `backend/`, `scripts/`, `.github/`,
`mkdocs_src/docs/developer/` (commenti e docstring compresi); `openapi.json` identico (hash di `dev.py api schema`
prima/dopo); `python -c "import backend.app.main"`.

Due moduli toccano H: `market_calendar.py` (importato da `main.py:44`, che H svuota estraendo l'avvio) e
`web_link_finder.py` (H ci aggiunge `_FILE` per la sua chiave, F03). Si spostano in `services/assets/` in CP2a (indicazione
del coordinatore, 14/10); git segue una rinomina anche se l'altro ramo modifica il file, e il solo conflitto possibile è la
riga d'import in `main.py` o nel suo successore, da riallineare all'aggiornamento di base.

### 4.2 Riordino frontend

- **FE4** `lib/features/fx/` ← `components/fx/*`, `stores/fxStoreRegistry.ts`, `stores/fx/*`, gli helper solo-FX
  (`utils/currency/fxConversionHelper.ts`, e `fxRoutesStore`/`currencyGraph*` solo se nessun altro dominio li usa: si decide
  dagli importatori). Solo rinomina + import. Dopo il lotto A dei colori.
- **FE5** `lib/features/assets/` ← `components/assets/*`, `utils/{assetPriceDerived,assetSimilarity,assetGrouping,assetIdentifiers}`:
  FE5a rinomina; FE5b taglio di `AssetModal` lungo le cuciture già marcate (identificativi, confronto metadati, salvataggio
  create/edit, applicazione del risultato di ricerca) in componenti e moduli `.ts`; FE5c taglio della pagina
  `assets/[id]` (caricamento dati, azioni, derivati, schede del template). `data-testid`, chiavi i18n, URL invariati;
  D-P4 (file pubblico per gli import fra feature, mai per i moduli presi da `vi.mock`). Dopo il lotto A e dopo M2 di Z.
  Indicazione del coordinatore (14/10): `AssetModal` è fuori dai lotti dei colori e si può tagliare anche prima del lotto
  A, con l'annuncio della regola «chi parte prima» (§7 del piano generale); la pagina dell'asset dopo la riga di G.

### 4.3 Elenchi dei fornitori permessi (F05, parte X)

**D-X4, decisa dal developer il 15/10** (voce 19), alla lettera: «si al togliere il search, ma almeno all'inizio lasciamo che
se un utente proprio vuole può setupparlo manualmente uno di questi provider, poi capiremo se legalmente è un azzardo o una
zona grigia, essendo in fondo la sua macchina e offrendo noi i premium, diciamo che servirebbe più da tappa buchi per quei
titoli di super nicchia». In chat, sulla proposta di un avviso del coordinatore: «19 ok come proponi». Per questo lotto, dal
coordinatore:
- senza un elenco del pannello, le fonti scraper (Yahoo, justETF, Borsa Italiana, lo scraper CSS) non compaiono nella ricerca;
- l'utente può comunque assegnarne una a mano a un singolo asset, dalla configurazione della fonte;
- lì compare una riga d'avviso, del tipo «fonte non ufficiale, a tuo rischio»;
- i cambi delle banche centrali restano tutti; nel self-hosted non cambia niente.

Prima della decisione il profilo gestito senza elenchi toglieva gli scraper del tutto; ora li toglie solo dalla ricerca. Il
permesso e la ricerca diventano quindi due livelli, con un punto unico ciascuno nel registro della famiglia.

- **Permesso**, `is_allowed(code)`: `LIBREFOLIO_ASSET_PROVIDERS_ALLOWED` e `LIBREFOLIO_FX_PROVIDERS_ALLOWED` (senza `_FILE`:
  non sono segreti), lette con un accessore in `backend/app/config/plugins.py` (regola di H, sotto §6) e scritte in
  `.env.example`. **Non impostate = tutti permessi, in tutti e due i profili**: il self-hosted non cambia, e nel profilo
  gestito gli scraper restano assegnabili a mano. Impostate = solo gli elencati. `MANUAL` sempre permesso; i fornitori di test
  esclusi. È la leva per «poi capiremo se legalmente è un azzardo»: se la risposta è no, l'operatore elenca solo le fonti
  ufficiali e l'uso a mano si chiude senza codice nuovo; gli asset già legati seguono D-X5 (sotto).
- **Ricerca**, `is_searchable(code)`, solo per gli asset: vi partecipa un fornitore permesso che dichiara la ricerca, tranne
  gli scraper nel profilo gestito. **Lettura mia, confermata dal coordinatore il 15/10**: nel profilo gestito gli scraper restano fuori
  dalla ricerca anche con un elenco del pannello, perché l'elenco decide il permesso e mai la ricerca. Un pannello che elenca
  le fonti incluse in un piano (un diritto, non una scelta legale) non deve rimettere in ricerca gli scraper come effetto
  collaterale; e così si può tenere uno scraper solo a mano e chiuderne un altro. L'altra lettura (un elenco del pannello vale
  anche per la ricerca) è una riga nel registro.

  | Profilo | `…_ALLOWED` | Permessi: a mano, probe, sync | In ricerca |
  |---|---|---|---|
  | self-hosted | non impostata | tutti | tutti quelli con la ricerca, come oggi |
  | self-hosted | impostata | gli elencati | gli elencati con la ricerca |
  | gestito | non impostata | tutti | i non scraper con la ricerca: oggi nessuno, fino a F06 |
  | gestito | impostata | gli elencati | gli elencati non scraper con la ricerca |

- Ogni fornitore dichiara `is_scraper` (asset: yfinance, justETF, Borsa Italiana, CSS scraper = sì; scheduled_investment = no;
  FX: banche centrali = no). Default **prudente**: un fornitore che non lo dichiara conta come scraper, così un plugin di terzi
  montato non entra da solo nella ricerca di un'istanza gestita, e porta l'avviso. È un attributo distinto dal `tier` di F21
  («community» non vuol dire scraper: una futura API ufficiale gratuita, come OpenFIGI, sarebbe community ma non scraper) e
  dal `kind` di oggi (`FAProviderKind.ONLINE_SCRAPER` vuol dire «dati presi da fuori», e varrebbe anche per un'API ufficiale).
  Facoltativo: un flag dichiarato «solo test» sostituisce i nomi scritti a mano (`api/v1/assets/providers.py:62`, `mockprov`;
  `api/v1/fx/providers.py:80`, `_HIDDEN_FX_PROVIDERS`).
- **La riga d'avviso**: `FAProviderInfo` (`schemas/provider.py`) espone `searchable` e `notice` (`"unofficial_source"` |
  `null`), calcolati nel backend: `notice` vale `"unofficial_source"` per uno scraper permesso ma fuori dalla ricerca, cioè
  offerto solo a mano. La configurazione della fonte (`ProviderAssignmentSection`, in `AssetModalProvider`, alla creazione e
  alla modifica) mostra la riga quando il fornitore scelto ha il `notice`: una chiave nuova nelle 4 lingue, ruoli `lf-*`, lo
  stesso componente d'avviso per asset di F21 (§4.6) con un messaggio suo; UI dopo il lotto A, come C-90. Nel self-hosted
  senza elenchi nessuno scraper è fuori dalla ricerca, quindi la riga non compare mai. FX: oggi nessuno scraper e nessuna
  ricerca, quindi nessun secondo livello.
- **Dove si controlla**. `is_searchable`: l'elenco dei fornitori di ricerca, `GET /api/v1/assets/provider/search` e
  `/search/stream`, compresa la risoluzione di un URL incollato, che è un ingresso della ricerca (`services/assets/search.py:104`,
  `resolve_url`). Il filtro sta nel backend: una richiesta che nomina uno scraper in `providers=` non lo interroga.
  `is_allowed`: l'elenco per la configurazione, `POST /api/v1/assets/provider/probe`, l'assegnazione, il sync, il prezzo
  corrente e i metadati. Una fonte solo a mano fa quindi tutto tranne comparire nella ricerca: probe, «Chiedi al fornitore»,
  sync dello scheduler.
- **Asset già legati a un fornitore non permesso** (D-X5): l'assegnazione resta nel DB; sync e prezzo corrente lo saltano con
  esito per voce `PROVIDER_NOT_ALLOWED` (niente 500, niente spam nello scheduler); le letture delle assegnazioni espongono
  `provider_allowed: false`; la UI mostra un avviso con «Cambia fonte» o prezzi manuali; mai cancellazioni né riassegnazioni
  automatiche. FX: il fornitore non permesso esce dalla catena di ripiego della coppia, l'esito della gamba lo dice; nessuna
  modifica alle rotte salvate (l'ambiente può tornare indietro). Una fonte soltanto fuori dalla ricerca non è «non
  permessa»: nessun esito e nessun avviso di D-X5.
- Nel profilo gestito senza elenchi la ricerca degli asset resta senza fornitori finché non arriva il fornitore a pagamento
  (F06), o finché l'operatore non permette una fonte non scraper: è la specifica («scraper disattivati di default»). L'utente
  crea l'asset a mano e, se vuole, gli configura una fonte scraper con l'avviso; la ricerca vuota lo dice e porta lì (con F21,
  «Non lo trovi?»).
- Facoltativo, se H offre l'area avvisi: «N asset usano fonti non permesse su questa istanza» per l'admin.
- Dal giro di sicurezza di H (coordinatore, 14/10), nello stesso lotto: il `css_scraper` segue i redirect su URL scelti
  dall'utente (`css_scraper/plugin.py:192`, `follow_redirects=True`); vanno bloccati loopback, reti private, link-local e
  metadati del cloud, anche dopo un redirect. **Con D-X4 è una precondizione**: nel profilo gestito ogni utente può configurare
  a mano lo scraper CSS con un URL suo, e la probe lo fa partire subito; il profilo gestito con le fonti a mano non esce senza
  questo blocco.

### 4.4 Impostazioni dei plugin

> **Aggiornato dal disegno approvato il 15/10 (sezione «CP10» in fondo).** Restano validi contratto, precedenza,
> cifratura e permessi; cambiano otto punti: due tabelle al posto di una con indici parziali; scrittura tutto o niente;
> percorsi `GET /api/v1/settings/plugins` e `PATCH /api/v1/settings/plugins/bulk`; l'ambiente blocca solo i campi di
> sistema; `test_only` al posto dei nomi di prova scritti a mano; il confine `call_provider` nasce nel CP10; il
> mascheramento nei log con un ContextVar; le funzioni del ripristino sulle sottochiavi.

**Contratto** (`plugin_settings/fields.py`, `contract.py`): ogni base di famiglia (asset, FX, BRIM dopo PL5, tools) eredita
un mixin con `settings_fields: ClassVar[tuple[PluginSettingField, ...]] = ()`. Un campo dichiara: `key`, `type`
(`string|number|integer|boolean|select`), `scope` (`user` = personale | `system` = solo admin), `secret` (solo `string`),
`required`, `default`, `options`, `label`/`description` in inglese (ripiego per i plugin montati senza traduzioni) e chiavi
i18n dichiarate nel campo (come `name_i18n_key` dei tools: la UI non costruisce chiavi), `env` facoltativo (alias esplicito).
La dichiarazione è statica, validata alla registrazione (chiavi uniche, tipi, default validi; per i tools un campo `secret` è
rifiutato: un Tool non chiama fonti esterne). Un campo personale serve alle preferenze di un utente; un campo di sistema
all'istanza (per esempio la chiave di un fornitore a pagamento, che nel self-hosted l'admin inserisce una volta per tutti).

**Valori e precedenza** (`resolver.py`): variabile d'ambiente (`NAME`, poi `NAME_FILE`, letta con `env_secret()` di H in un
accessore di `backend/app/config/`) → DB → default. Nome derivato
`LIBREFOLIO_PLUGIN_<FAMIGLIA>_<CODICE>_<CAMPO>` (maiuscolo, non alfanumerici → `_`), più l'alias dichiarato (es.
`LIBREFOLIO_TWELVEDATA_API_KEY`, D-X6). Una variabile impostata **vince e blocca** il campo. Profilo gestito: i campi bloccati
dall'ambiente **non compaiono** né nella UI né nelle API.

**Archivio** (`store.py`, migrazione **007**, `007_plugin_settings`; la 005 e la 006 sono di A, A4 i token e A5
`registration_mode`, regola C7 del piano generale `ed29f77c2`): tabella `plugin_settings` (`family`, `plugin_code`,
`field_key`, `scope`, `user_id` FK `users.id ON DELETE CASCADE`, `value_json` | `secret_ciphertext`, `key_id`, `updated_at`,
`updated_by_user_id`); CHECK su scope/utente e «esattamente uno fra valore e cifrato»; indici unici **parziali** (uno per
`system`, uno per `user`), perché in SQLite i NULL non collidono in un UNIQUE; gli indici parziali vanno dichiarati anche nel
modello (`sqlite_where`), altrimenti il confronto modello/DB di `db_schema_validate.py` li vede come differenza. Righe di campi
non più dichiarati: ignorate. Id della revisione `007_plugin_settings` (19 caratteri, sotto il limite di 32).

**Cifratura** (`crypto.py`, D-X1): `cryptography`, AES-256-GCM; sottochiave HKDF-SHA256 dalla chiave d'istanza di H con
`derive_key(purpose="plugins.settings.v1", length=32)` di H (`services/platform/instance_key.py`); **AAD = contesto** (`famiglia|plugin|campo|scope|user_id`), così un cifrato spostato su
un'altra riga non si decifra; `key_id` = impronta della sottochiave, per la rotazione; nonce casuale da 96 bit.

**API** (`api/v1/plugin_settings.py`, bulk come il resto del progetto): `GET /api/v1/plugins/settings` (catalogo dei plugin
con campi, stato per il chiamante: valore se non segreto, `is_set`, `source` env|db|default, `locked`, `editable`);
`PATCH /api/v1/plugins/settings` (lista di `{family, plugin_code, field_key, scope, value | clear}`; esito **per campo**, tutti
tentati, rifiuti con codice: `FORBIDDEN_SCOPE`, `LOCKED_BY_ENV`, `INVALID_VALUE`, `UNKNOWN_FIELD`; contratto di
`settings-write-path-contract`). **Un segreto non torna mai**: lo schema di risposta non ha il campo; scrittura sola; in
ingresso il valore segreto è un `SecretStr` senza vincoli di validazione nello schema (i controlli stanno nel servizio, con
messaggi che non lo ripetono), così nessun 422 lo rimanda indietro né finisce in un log.
Permessi: `system` lo scrive solo l'admin; `user` solo il proprietario; l'admin non vede le impostazioni personali di altri,
nemmeno se esistono. Un non-admin vede i campi di sistema in sola lettura: il valore se non è segreto, altrimenti solo
«configurato / da configurare» (D-X15).

**Consegna al runtime** (D-X13): il core risolve i valori **prima** di entrare nel thread del provider (nessun DB nei plugin) e
li lega all'istanza con `bind_settings(...)`, letti dal plugin come `self.settings` (vuoto di default, così i plugin di oggi e
quelli di terzi non cambiano); mai via costruttore, per il ripiego silenzioso di `get_plugin_instance`. L'istanza è nuova a
ogni chiamata, quindi i valori di un utente non restano a un altro.

| Famiglia | Percorso | Valori consegnati |
|---|---|---|
| Asset | ricerca, probe (con utente) | `system` + `user` del chiamante |
| Asset | prezzo corrente, storico, metadati, sync, scheduler | solo `system` (i prezzi sono condivisi fra gli utenti) |
| FX | sync (utente o scheduler) | solo `system` |
| BRIM (dopo PL5) | parse dell'utente che carica | `system` + `user`, passati come argomento picklable al process pool |
| Tools | compute del richiedente | solo non segreti, `system` + `user`, nel contesto d'esecuzione |

Valore obbligatorio mancante → esito strutturato `NOT_CONFIGURED` (asset: `AssetSourceError`; FX: errore della gamba), mai 500;
nel pannello del fornitore e nella ricerca il fornitore compare «da configurare», con il pulsante Configura.
Le cache del core che dipendono dalle impostazioni (ricerca: oggi `(provider, query)`) aggiungono alla chiave **un'impronta
HMAC** (sottochiave d'istanza) di tutti i valori consegnati, segreti compresi: mai il valore, e nessuna condivisione dei
risultati fra preferenze o chiavi diverse.

**UI**: scheda «Plugin» nel registro di A (una riga) costruita dal catalogo, raggruppata per famiglia (Prezzi, Cambi, Import
broker, Strumenti); modulo generato per tipo; segreto = campo a sola scrittura con «impostato il …», «Sostituisci», «Cancella»;
campo bloccato con la nota «impostato dal server»; nel pannello del fornitore di «Aggiungi asset» il pulsante **Configura**
apre lo stesso modulo filtrato sul plugin. Sottosistema i18n nuovo `pluginSettings` (non tocco `settings` di A); le etichette
dei campi stanno nei frammenti dei plugin sotto `pluginSettings.<famiglia>.<codice>.*` (il gate di proprietà si estende di
un'area per plugin). Primo uso (D-X14): `justetf.preferred_currency`, `borsa_italiana.preferred_language` (personali, default
«tutte»; filtrano i risultati e, se il filtro svuota la lista, mostrano tutto; legenda della 👑).

**U-B1** (traduzioni dei plugin montati a runtime): con il testo inglese di ripiego nelle dichiarazioni non serve alle
impostazioni. Il merge a runtime (`GET` dei frammenti + `addMessages`) resta facoltativo (D-X11).

### 4.5 Analisi dei rischi delle chiavi (prima del codice)

**Cosa protegge la cifratura e cosa no**

| Scenario | Protetto? | Perché |
|---|---|---|
| Copia del solo DB (file condiviso per supporto, dump, replica Litestream su S3, backup del solo DB) | **Sì** | la chiave non è nel DB |
| Lettura via SQL o export di tabelle | **Sì** | si vede solo il cifrato |
| Volume dati intero, o zip di backup F01 con `secrets/` + DB | **No** | chiave e cifrato viaggiano insieme |
| Admin dell'app che scarica il backup completo (F01) e decifra offline | **No** | vedi D-X2: è il buco vero rispetto a «l'admin non legge i segreti personali» |
| Processo compromesso (RCE), dump di memoria, plugin malevolo montato | **No** | il valore in chiaro esiste in memoria durante la chiamata; un plugin gira nel processo e può leggere DB e chiave |
| Operatore con shell sul container o sul volume | **No** | confine di fiducia dichiarato: chi gestisce l'istanza può leggere tutto |
| Cifrato spostato su un'altra riga o un altro utente | **Sì** | AAD con il contesto: la decifratura fallisce |

**Minacce e misure**

1. Fughe applicative (API, UI, log, messaggi d'errore, AI Export, chiavi delle cache, `/settings/cache/status`):
   scrittura sola; nessuno schema di risposta porta il valore; **redazione per valore** dei segreti risolti in ogni
   `AssetSourceError`/errore FX/BRIM e nei log prima che escano (un provider che mette la chiave nell'URL produce eccezioni
   con l'URL); chiavi di cache con impronte, mai il valore; l'AI Export non legge la tabella (test con un segreto marcatore).
2. Admin e segreti personali: nessun endpoint li espone ad altri; il backup resta il canale aperto (D-X2).
3. Chiave sullo stesso volume: H la crea in `<DATA_DIR>/secrets/` (600, atomica); la doc consiglia
   `LIBREFOLIO_INSTANCE_KEY_FILE` su un mount separato (Docker secret); nel cloud la inietta il pannello.
4. Rotazione: righe con `key_id`; la decifratura prova le chiavi note, la cifratura usa la corrente; comando di ricifratura
   (`dev.py`, file condiviso: una voce) quando H definisce la rotazione della chiave d'istanza. Chiave persa o cambiata: il
   campo risulta «impostato ma illeggibile, reinseriscilo» (mai un crash, mai un valore sbagliato); avviso all'admin.
5. Memoria dei worker: risoluzione a ogni chiamata, nessuna cache del chiaro; i tools non ricevono segreti; il process pool
   BRIM li riceve solo se il plugin li dichiara.
6. Plugin di terzi montati: sono codice fidato (documentato); ognuno riceve solo le proprie impostazioni.
7. Profilo gestito: campi bloccati dall'ambiente invisibili; nessuna scrittura nel DB per quelli.
8. Test e fixture: mai chiavi vere; chiave d'istanza generata per corsia.
9. `provider_params` resta per i parametri d'identità dell'asset, condivisi fra gli utenti, in chiaro, esportati e visibili a
   chi vede l'asset: **mai un segreto lì** (regola scritta nella guida dei plugin, controllata in revisione).
10. Corpo delle richieste: nessun middleware registra il corpo di `PATCH /plugins/settings` (da verificare con H, che possiede
    i middleware); `SecretStr` in ingresso (§4.4).

**Proposta per §10 n. 5**: segreti personali ammessi, scrittura sola dal proprietario, l'admin non li legge mai **dall'app**;
in più (D-X2) gli zip di backup scaricabili dalla UI contengono la chiave d'istanza solo se protetti da password (decisione
6), altrimenti la escludono e i segreti si reinseriscono dopo il ripristino. Revisione `security-review` a fine lavoro.

**Note dalla revisione di sicurezza del CP3 di H** (riportate dal coordinatore il 15/10, ~03:00), da applicare nel CP10:
- **HKDF non ha un fattore di lavoro**: la chiave d'istanza dev'essere casuale, mai una passphrase (la doc di H lo dice già).
  La sottochiave delle impostazioni si deriva dalla chiave d'istanza, non da un segreto scelto da una persona.
- **`derive_key(purpose, n)`**: la lunghezza ora entra in `info`, quindi chiavi di lunghezze diverse non sono più una il
  prefisso dell'altra. Da parte mia: un solo `purpose` fisso e distinto per le impostazioni dei plugin,
  `plugins.settings.v1` (indicazione del coordinatore, 15/10), sempre lo stesso.
- **Valore di controllo della chiave (H-3)**: se `instance.key` si perde dopo il primo uso, oggi l'istanza ne genera una
  nuova senza avvisare, e i segreti cifrati diventano illeggibili. La cura è un valore di controllo salvato nel DB, da
  **progettare con H al mio primo uso di `derive_key`, nel CP10**: è il caso «chiave persa o cambiata» della misura 4,
  che così diventa rilevabile all'avvio invece che alla prima decifratura fallita.
- Una chiave uguale su più istanze dà le stesse chiavi derivate: è un requisito del pannello del cloud, e lo porta il
  coordinatore al developer. Effetto per me: nessuna isolazione crittografica fra istanze che condividono la chiave; l'AAD
  con il contesto della riga resta l'unica separazione.

#### Ripristino di un backup: il contratto con B (aggiunta del 15/10, solo disegno)

Richiesta dell'analisi di B, girata dal coordinatore il 15/10. Contesto: la decisione 39, che assorbe la 18, ancora al developer. La chiave
d'istanza entra in un backup solo con password e solo se generata; al ripristino l'istanza tiene la sua chiave e i segreti si
ricifrano, altrimenti restano «impostati ma illeggibili, reinseriscili» (misura 4). Il disegno regge entrambi gli esiti. Il
CP10 resta fermo fino alla decisione 39 (la 19 è decisa il 15/10, §4.3) e alla finestra di `cryptography`.

**Due funzioni sincrone** in `plugin_settings/crypto.py`, su una `sqlite3.Connection` della copia. Non usano il motore
dell'app e non leggono la configurazione: ricevono le sottochiavi.

- `rekey_plugin_secrets(conn, old_subkey, new_subkey) -> RekeyReport`. Per ogni riga con `secret_ciphertext`:
  - con il `key_id` della nuova sottochiave è già corrente e non si tocca. Due giri danno lo stesso stato, e con la stessa
    chiave sulle due istanze non c'è nessuna scrittura;
  - con il `key_id` della vecchia, se la decifratura riesce (AES-GCM, AAD = `famiglia|plugin|campo|scope|user_id` della
    riga), si ricifra con la nuova: nonce nuovo da 96 bit, `key_id` nuovo;
  - altrimenti (un altro `key_id`, un tag non valido, un contesto cambiato) resta com'è e si conta illeggibile: mai
    cancellata, mai un valore sbagliato.

  `RekeyReport(rekeyed, already_current, unreadable_system, unreadable_user)`: solo conteggi, mai nomi né valori.
- `count_unreadable_secrets(conn, subkey) -> UnreadableSecrets(system, user)`, con `total`. Sola lettura. È illeggibile una
  riga con un `key_id` diverso, o quella con il `key_id` giusto che non si decifra (copia corrotta).

Regole comuni:
- **Transazione**: tutto dentro un `SAVEPOINT`. Da sola è atomica; se B ha una transazione aperta, ne diventa parte. Non fa
  mai il `COMMIT` del lavoro di B. Un errore strutturale annulla il savepoint e risale; una riga illeggibile non è un errore.
- **Ordine**: si chiamano dopo l'aggiornamento della copia alla revisione di testa. Su una copia senza `plugin_settings`
  (un backup di prima della 007) rendono zeri.
- **Sincrone**: dall'app si chiamano in `asyncio.to_thread` (regola dell'I/O asincrono). Il chiaro vive solo in memoria
  durante la chiamata, mai nei log né nei rapporti.
- **Sottochiavi**: B non conosce il `purpose`. `settings_subkey(instance_key: str | None = None)` rende la sottochiave
  corrente, oppure quella di una chiave data (la chiave dello zip). Da H serve un solo pezzo: `derive_key_from(instance_key,
  purpose, length=32)`, la stessa derivazione di `derive_key` da una chiave esplicita, con lo stesso controllo di lunghezza;
  `derive_key` la userebbe con la chiave corrente.
- **Privacy**: il conteggio è diviso per scope, perché l'admin non deve sapere nemmeno se esistono impostazioni personali
  (§4.4). Il rapporto di ripristino mostra all'admin il numero dei segreti di sistema, e per quelli personali una frase
  generica; ogni utente vede i propri «illeggibili, reinseriscili» nella sua scheda.
- **Utenti**: l'AAD lega il cifrato al `user_id`. Un ripristino completo conserva gli id; uno che rinumerasse gli utenti
  renderebbe illeggibili i segreti personali, per costruzione.

**Il flusso di B**:
1. Con la chiave nello zip: `rekey_plugin_secrets(copia, settings_subkey(chiave_dello_zip), settings_subkey())`. Se la
   chiave dello zip non è quella che ha cifrato il DB, lo dice il rapporto (0 ricifrati, N illeggibili).
2. Senza la chiave: `count_unreadable_secrets(copia, settings_subkey())`, per il rapporto. Le righe restano; chi le
   reinserisce le sovrascrive con la chiave corrente.
3. In entrambi i casi B non scrive altro per le impostazioni dei plugin: lo stato sta tutto nei `key_id` delle righe.

**Il valore di controllo H-3**: d'accordo con B sul posto, «con i cifrati, nella 007», nella forma più semplice. È il
`key_id` di ogni riga: un'impronta con chiave della sottochiave, `HMAC-SHA256(sottochiave, "LibreFolio plugin settings key
id v1")` troncato a 16 byte, in esadecimale. Non rivela né la sottochiave né la chiave d'istanza. Nessuna tabella e nessuna
riga a parte, perché:
- i `key_id` dicono riga per riga quale chiave serve, e il rilevamento all'avvio è un conteggio delle righe con un `key_id`
  diverso da quello corrente, senza decifrare;
- senza segreti non c'è niente da perdere, e niente da segnalare;
- al ripristino B non deve aggiornare nessun valore.

Il controllo all'avvio è di H: un controllo con il DB, nel log e nella scheda Sicurezza come i `ConfigCheck` di
`config_audit.py`, che oggi leggono solo la configurazione. Chiama `plugin_secrets_key_status(session) -> UnreadableSecrets`
(la stessa regola, con un adattatore asincrono) e mostra all'admin solo il conteggio di sistema. Rischio residuo, dichiarato:
con un `key_id` chi ha il DB può provare una chiave candidata, come può già con il tag di ogni cifrato. Con una chiave casuale
da 256 bit non conta, ed è il motivo della regola «mai una passphrase» (nota di H).
Un valore di controllo dell'istanza (una tabella di una riga, in una migrazione di H) servirà se un secondo uso della chiave
d'istanza salverà dati nel DB. Nella 1.3 i segreti dei plugin sono l'unico dato cifrato con quella chiave.

**Prove (nel CP10)**: sottochiavi fisse dei test, mai chiavi vere (misura 8); `sqlite3` in memoria con lo schema della 007;
ricifratura, idempotenza, `key_id` misti, tag alterato, riga spostata (AAD), tabella assente, savepoint dentro una
transazione di B che poi annulla.

### 4.6 Ordine dei fornitori nella ricerca (F21) e C-90

- Ogni fornitore asset dichiara `tier` (`premium` | `community`, default `community`) e `search_priority` (intero, più basso =
  prima). Sovrascrittura (D-X8): `LIBREFOLIO_ASSET_PROVIDERS_PREMIUM` e `LIBREFOLIO_ASSET_PROVIDERS_ORDER`, non impostate =
  dichiarato. `FAProviderInfo` espone `tier` e `priority`; la ricerca non in streaming ordina per gruppo e priorità; lo
  streaming resta per arrivo e il frontend raggruppa.
- UI (dopo FE5 e il lotto A): sezione Premium in testa con badge (funzioni condivise dei colori); poi «Non lo trovi?
  Segnalacelo» (URL di supporto se configurato, altrimenti le issue GitHub) e «Prezzo manuale / import»; in fondo la sezione
  chiusa «Fonti non premium»; scegliendo un risultato di quella sezione, avviso «fonte di terzi, nessuna garanzia» che vale solo
  per quell'asset (niente memoria globale). **Se nessun fornitore premium è attivo, la lista resta come oggi** (D-X3).
- C-90: accanto al risultato di «Testa configurazione», la nota «prova sugli ultimi giorni: alla creazione LibreFolio scarica
  tutto lo storico» (in `ProviderAssignmentSection`, dopo il lotto A).

### 4.7 Voci del dominio

K-16 (`etc/etn` → `ETF_COMMODITY`, D-X7, test in `borsa-italiana-search`); O-9 (frammenti `i18n/` per justETF e CSS scraper,
4 lingue); O-8 (le tre stringhe con chiavi esistenti o nuove in `assets`); K-20 (URL della scheda da `window.location`, come
`AssetBrowseNav.svelte:91`); O-20 (un solo sync alla creazione, con un test rosso che conta le chiamate); K-19 (`snapshot` di
SvelteKit sulla pagina lista per i filtri); C-66 (avviso nel dialogo di sync quando l'intervallo copre dati già presenti;
`SyncModalBase` va verificato con le liste dei lotti colori); C-90 (sopra); voce 5 chiusa.

## 5. Superfici esatte

| Lotto | Sorgenti | Test | Doc e `.github` |
|---|---|---|---|
| PL2 | `provider_registry.py`; nuovi `assets/registry.py`, `brim/{__init__,registry}.py`, `signals/{__init__,registry}.py`, `risk/registry.py`; righe d'import in ~95 file app (plugin, servizi, `main.py`, `api/v1/{system,assets,fx,brokers}.py`, AI Export) | ~50 file (registri, gate `plugin-i18n-ownership`, `test_signal_registry.py:36,644`) | `patterns/registry_pattern.md`, guide dei plugin (asset, fx, brim, signal, tool), `backend/{assets,brim,risk}/architecture.md`; istruzioni `backend-providers-*`, `backend-{signals,risk,tools}`; skill asset/brim/signal/risk/tool |
| CP2a/CP2b — asset backend ed eventi | `asset_sources/*` → `assets/`, shim e barile via, `core.py` → `base.py` + `core.py`, `price_store.py` → `price_store`/`currency_change`/`event_store`; `api/v1/assets.py` → `api/v1/assets/{router,crud,providers,prices,events,market_data}.py`; schemi degli eventi in `schemas/assets/events.py` (C3); `api/v1/router.py` intatto (C2); `market_calendar.py`/`web_link_finder.py` in `services/assets/` (CP2a); ~30 importatori app | ~32 test di servizio e API; `test_signal_catalogs.py`, `test_signal_request_validation_api.py` (import dei router) | `backend/assets/architecture.md`, `backend/assets/events.md`, `search_link_finder.md`, `architecture/settings_cache.md`, `asset_plugin_guide.md`; `backend-providers-asset` (`applyTo`); runner (stringhe dei percorsi), `scripts/coverage_analysis.py` |
| CP3 — PL4 cambi | `fx.py` → `fx/{registry,base,sync,conversion,storage}.py`; `api/v1/fx.py` → `api/v1/fx/{router,providers,currencies}.py`; 6 plugin FX; 17 importatori app | 11 test di servizio, patch di `test_fx_sync_service.py`; `test_fx_api_unit.py`, `test_fx_signals_api.py`, `test_fx_compress_errors.py`, `test_fx_route_schemas.py` (patch sui nuovi sotto-moduli) | `fx_plugin_guide.md`, `backend/fx/{architecture,configuration}.md`, `financial_math.md`; `backend-providers-fx` (`applyTo`, nome della base), mappa di `backend.instructions.md` |
| PL7 | `api/v1/signals.py` + estrazione dei pezzi segnali da `prices/query` e `currencies/convert` | `api signal-*` | `backend-signals` (sezione API) |
| Schemi | `schemas/{assets,prices,provider,refresh,fx}.py` (D-X9) | importatori | `backend-schemas.instructions.md` |
| F05 | `assets/registry.py` (`is_allowed`, `is_searchable`), `fx/registry.py`, choke point nei servizi e nella ricerca, `config/plugins.py`, schemi `provider_allowed`, `searchable`, `notice` (`schemas/provider.py`); `ProviderAssignmentSection` (la riga d'avviso, dopo il lotto A); `css_scraper` (blocco SSRF) | nuovi pytest, Vitest della riga | sezione X di `.env.example`; testo per `admin/configuration` (H); la riga d'avviso nelle 4 lingue |
| Impostazioni | `plugin_settings/*`, `db/models.py` (un modello), `alembic/versions/007_plugin_settings.py`, `api/v1/plugin_settings.py`, `schemas/plugin_settings.py`, basi di famiglia, justETF/Borsa; frontend `lib/features/plugin-settings/*`, una riga nel registro schede di A, «Configura» | pytest servizi/API/migrazione/sicurezza; Vitest; E2E; galleria | pagina dev `patterns/plugin_settings.md`; admin (sicurezza e variabili); utente `user/settings/plugins.md`, pagine dei fornitori |
| F21 + C-90 | `assets/registry.py`, `assets/search.py`, `FAProviderInfo`; `features/assets/` ricerca e pannello | pytest, Vitest, E2E | `search_link_finder.md`, `user/assets/create-edit.en.md` |

Runner (condiviso, solo le mie voci): `services plugin-settings`, `api plugin-settings`, `services provider-policy`, guardie dei
vecchi percorsi; stringhe di percorso in `_backend_services.py`/`_backend_utils.py`.

## 6. Dipendenze, contratti e decisioni

**Contratti che chiedo**

| Da | Cosa | Serve a |
|---|---|---|
| H | ✅ consegnato con il CP3 di H: `env_secret()` (`NAME`, poi `NAME_FILE`), accessori per sezione in `backend/app/config/<sezione>.py`, guardie `config-package` e `config-env-example`; resta l'accessore del profilo gestito (CP6 di H) | F05, impostazioni |
| H | API della chiave d'istanza (`bytes` + id), comportamento se manca o cambia, piano di rotazione | impostazioni |
| H | area avvisi d'istanza (facoltativa) | F05, chiavi illeggibili |
| A | registro delle schede; id delle revisioni 005 e 006; cancellazione account (verifico la cascata) | impostazioni, 007 |
| W | PL5 dopo PL2; presa in carico, appena integrato CP2b, di `api/v1/assets/events.py`, `services/assets/event_store.py`, `schemas/assets/events.py` (e dei loro test; consegnati a W dopo l'ingresso del CP2b, `05c21b2b6`); ordine di V-22 e C-65 rispetto a FE5 | eventi, BRIM |
| J | PL1 dopo PL2; finestra per PL4 rispetto alle sue modifiche nei consumatori di `convert_bulk` | PL2, PL4, PL7 |
| Z | M2 sulle pagine asset prima di FE5; `scheduler/jobs.py` (riga d'import dello shim) | FE5, CP2a |
| Colori | liste dei lotti B/C/D sui miei file (`ui/modals/{SyncModalBase,PageSyncModal}`, `AssetSyncModal`, `FxSyncModal`, `utils/sync/syncHelpers.ts`, `Asset/FxDataEditorSection`, `AssetModal`, `AssetSearchAutocomplete`, pagine asset e cambi) | FE4, FE5, C-66, O-8 |
| Developer | `cryptography` nella finestra delle dipendenze | impostazioni |

**Regole di H per le variabili d'ambiente** (dal CP3 di H, riportate dal coordinatore il 15/10; guardie `services
config-package` e `services config-env-example`), valide per ogni mia variabile nuova (F05, impostazioni dei plugin, F21):
- si leggono solo in `backend/app/config/<sezione>.py`, con un accessore; il resto del codice chiama l'accessore;
- un segreto si chiama `LIBREFOLIO_*` e si legge con `env_secret()`, così vale anche la variante `_FILE` (Docker secrets);
- ogni variabile va in `.env.example`, nella sua sezione, come riga commentata con il default.

**Decisioni (con la mia raccomandazione)**

| # | Domanda | Raccomandazione |
|---|---|---|
| D-X1 | Cifratura | AES-256-GCM con AAD di contesto e sottochiave HKDF (`cryptography`); Fernet come alternativa più semplice ma senza AAD |
| D-X2 | Segreti personali e backup (§10 n. 5) | ammessi, scrittura sola dal proprietario; zip della UI con la chiave d'istanza solo se protetto da password, altrimenti senza chiave e segreti da reinserire (con B); voce 18, assorbita dalla 39, ancora al developer (15/10) |
| D-X3 | F21 senza fornitori premium attivi | lista come oggi: gruppi e avviso solo se almeno un premium è permesso |
| D-X4 | Default degli elenchi nel profilo gestito | **decisa dal developer il 15/10** (voce 19): gli scraper fuori dalla ricerca, assegnabili a mano con la riga «fonte non ufficiale»; permesso e ricerca su due livelli; cambi delle banche centrali tutti; self-hosted invariato (§4.3). Proposta di prima: solo fornitori non scraper |
| D-X5 | Asset legati a un fornitore non più permesso | assegnazione intatta, sync saltato con esito chiaro, avviso e «Cambia fonte» |
| D-X6 | Nome delle variabili per campo | `LIBREFOLIO_PLUGIN_<FAMIGLIA>_<CODICE>_<CAMPO>` (+ `_FILE`) più alias dichiarato; letti solo in `backend/app/config/` con `env_secret()`, ogni variabile in `.env.example` (regola di H, sotto) |
| D-X7 | K-16 | `etc/etn` → `ETF_COMMODITY` |
| D-X8 | Sovrascrittura di tier e priorità | due variabili (`…_PREMIUM`, `…_ORDER`); nessuna UI admin nella 1.3 |
| D-X9 | Forma degli schemi degli asset | **superata da C3** (coordinatore, 14/10): pacchetto `schemas/assets/` con moduli per tema, eventi in `schemas/assets/events.py`, `__init__.py` con la sola docstring, hub invariato |
| D-X10 | PL7 e ordine dei percorsi in `openapi.json` | accettare un riordino verificato (stessi URL e `operationId`, confronto canonico) se tenere l'ordine richiede artifici |
| D-X11 | U-B1 | testo inglese di ripiego ora; merge a runtime facoltativo, non bloccante |
| D-X12 | Tools e segreti | vietati alla dichiarazione |
| D-X13 | Consegna dei valori personali | solo nei percorsi interattivi non di prezzo (tabella §4.4) |
| D-X14 | Voce 15 dell'utente C («nazione e valuta preferite») | justETF → **valuta** preferita fra le 4 varianti (le bandiere sono di valuta); Borsa Italiana → **lingua** preferita fra le 2 varianti; default «tutte»; se il filtro svuota la lista, tutto |
| D-X15 | Campi di sistema visti da un non-admin | in sola lettura: valore se non segreto, altrimenti solo «configurato / da configurare» |

## 7. Previsione dei conflitti

| Con | Dove | Gestione |
|---|---|---|
| H | `main.py:44-49,318-320,348-350`, `api/v1/system.py:26` (import dei registri), `api/v1/router.py`, `market_calendar.py` (import in `main.py:44`), `web_link_finder.py` (F03), middleware (corpo delle richieste) | PL2 entra prima dell'estrazione dell'avvio da `main.py`, altrimenti le righe d'import si sistemano all'aggiornamento di base; `market_calendar`/`web_link_finder` nel commit a parte (§4.1); `router.py`: righe concordate |
| A | registro schede, catena 005→006 (A) → 007 (X), `db/models.py` (un modello in coda) | 007 con `down_revision` rimesso all'aggiornamento di base; nessun file di A toccato oltre la riga |
| W | import in 31 plugin BRIM, `brim_provider.py`, `brim_*`, `api/v1/brokers.py`; eventi; FE5 tocca gli import di `ImportWizardModal`/`TransactionFormModal`; V-22 e C-65 su componenti asset | PL2 integrato prima di PL5; il taglio degli eventi (CP2b) prima che W scriva codice sugli eventi, poi la consegna; FE5a (solo import) prima del taglio FE8; V-22 prima o dopo FE5, deciso col coordinatore |
| J | import in 23 plugin segnali, 15 rischio, `signal_service`, `risk/service`, AI Export, `financial_math/*` (FX), `series_preparation`/`risk` (`market_calendar`) | PL2 e PL4 presto, prima che J tocchi quegli import; PL7 dopo PL1; `signals/` e `risk/registry.py` sono file nuovi: J parte dalla base con PL2 dentro |
| Z | pagine asset (polling), `scheduler/jobs.py` | FE5 dopo M2; la riga d'import dello shim cambia in CP2a |
| Colori | 7 file del lotto A; possibili file dei lotti B/C/D (sopra); `app.css` | FE4/FE5, C-90, «Configura», badge F21 dopo il lotto A; C-66/O-8 dopo il lotto che li elenca |
| Y | `utils`/`stores` generici (FE9–FE10) | FE4/FE5 spostano solo moduli di dominio |
| Hotfix 1.2.x | eventuali correzioni ai plugin | i file dei plugin non si spostano; cambiano solo righe d'import |

## 8. Complessità e rischi

| Lotto | Peso | Rischio principale | Contromisura |
|---|---|---|---|
| PL2 | medio (largo, meccanico) | conflitti con W/J; cicli d'import nei registri dei segnali | integrazione immediata; import pigro mantenuto finché J non sposta la base; import di `main` e test di scoperta |
| CP2a/CP2b asset ed eventi | medio | import pigri dimenticati; barile rimosso; ordine dei percorsi e `operationId` del router diviso | grep a zero, guardia «vecchie case», suite asset, hash di `openapi.json` identico |
| PL4 (+ router dei cambi) | medio | patch mute; lavoro di J sui consumatori | niente shim, patch riscritte, finestra concordata, hash di `openapi.json` |
| PL7 | medio-basso | intreccio segnali/conversione in `convert` | dopo PL1; confronto canonico |
| Schemi | medio (molti import) | churn | D-X9 |
| FE4 / FE5a | basso / medio | `vi.mock` sui vecchi percorsi | nessun barile per i moduli mockati; Vitest + `svelte-check` + build + E2E |
| FE5b/c | alto | regressioni di comportamento in due file enormi | commit piccoli, test esistenti come oracolo, `data-testid` invariati |
| F05 | medio | scheduler rumoroso, UX degli asset orfani; con D-X4, lo scraper CSS configurato a mano da ogni utente del profilo gestito (SSRF) | esiti per voce, test dello scheduler, avviso; blocco degli indirizzi interni anche dopo i redirect, precondizione del profilo gestito |
| Impostazioni | alto | fughe di segreti, migrazione, permessi | analisi §4.5, test di sicurezza, `security-review` |
| F21 | medio | regressione UX self-hosted | D-X3, Vitest dei gruppi, E2E |

## 9. Lotti e checkpoint (ordine proposto)

Ordine rivisto alla rilettura: il lotto degli asset e degli eventi viene **prima** dei cambi, perché W aspetta il modulo degli
eventi e il taglio deve entrare prima che W scriva codice su quei file; le modifiche di PL4 ai file di J sono righe d'import.

```mermaid
graph TD
  X0[X0 base e misure] --> CP1[CP1 PL2 registri]
  CP1 --> CP2a[CP2a asset_sources → assets, via shim e barile]
  CP2a --> CP2b[CP2b tagli: base, price_store, router per risorsa, schemi eventi]
  CP2b --> HW[consegna eventi a W]
  CP2b --> CP3[CP3 PL4 cambi + router dei cambi]
  CP3 --> CP4[CP4 schemi asset e cambi]
  J1[J: PL1 integrato] --> CP5[CP5 PL7 router segnali]
  CP3 --> CP5
  H1[H: config + profilo] --> CP6[CP6 F05 elenchi permessi]
  CP3 --> CP6
  LA[Colori: lotto A] --> CP7[CP7 FE4 cambi]
  LA --> CP8[CP8 FE5a + voci asset]
  Z2[Z: M2] --> CP8
  CP8 --> CP9[CP9 FE5b/c tagli]
  H2[H: chiave d'istanza] --> CP10[CP10 impostazioni backend + 007]
  DEP[cryptography] --> CP10
  CP6 --> CP10
  CP10 --> CP11[CP11 impostazioni UI + Configura + justETF/Borsa]
  CP8 --> CP11
  W5[W: PL5] --> CP12[CP12 BRIM e tools]
  CP10 --> CP12
  CP11 --> CP13[CP13 F21 + C-90 + C-66]
  CP9 --> CP13
  CP13 --> FIN[Revisione sicurezza, doc, handoff finale]
  CP12 --> FIN
```

1. **X0** — piano nel journal; misure di base sulla corsia: `all-backend` con i conteggi, `ruff`/`black`, `lint --dead-code`,
   hash di `dev.py api schema`, `mkdocs build` stretto, conteggio di `check-links`, `check_source_paths.py`, `i18n check`.
2. **CP1 — PL2** (subito, da integrare subito): registri di asset, cambi, BRIM, segnali e rischio nei pacchetti di famiglia
   (§4.1); `provider_registry.py` con sole basi e decoratori; via i re-export pigri; import, test, gate, doc, istruzioni,
   skill. Il registro dei cambi chiede il pacchetto `services/fx/`, che non convive con `services/fx.py`: il file entra come
   `services/fx/fx.py` (C1, spostamento puro; il suo taglio resta al PL4). **Un solo commit** (opzione 1, approvata dal
   coordinatore il 14/10, condizioni nel §6 del piano generale): nessun file insieme rinominato e tagliato, ogni rinomina
   ≥ 95 % in `git diff --cached -M`, due elenchi nell'handoff (rinomine pure, tagli) e un messaggio con le due parti nel
   corpo.
3. **CP2a — rinomina degli asset**: `git mv asset_sources/ assets/` (il registro di CP1 è già lì), via lo shim
   `asset_source.py` e il barile di `asset_sources/__init__.py`; import, commenti, runner, doc; `market_calendar.py` e
   `web_link_finder.py` in `services/assets/` (indicazione del coordinatore).
4. **CP2b — tagli degli asset ed eventi**: `core.py` → `base.py` + `core.py`; `price_store.py` → `price_store` /
   `currency_change` / `event_store`; `api/v1/assets.py` → `api/v1/assets/` per risorsa con `events.py`, ordine dei percorsi
   identico (C2); schemi degli eventi in `schemas/assets/events.py` (C3). Integrato presto; **subito dopo, consegna degli
   eventi a W** (`api/v1/assets/events.py`, `services/assets/event_store.py`, `schemas/assets/events.py` e i loro test): da lì
   non tocco la logica degli eventi.
5. **CP3 — PL4**: il taglio di `services/fx/fx.py` per tema (`base`, `sync`, `conversion`, `storage`), poi
   `api/v1/fx.py` → `api/v1/fx/` per risorsa (C2). CP2b e CP3 possono viaggiare nello stesso treno. Dopo il PL4, J scrive
   nei miei file le parti X6, X7, X8 e `fx.py:717` di U1 (regola 10), con me informato.
   Poi **CP3b — test senza rete e residui di testo** (approvato dal coordinatore il 15/10, dopo l'ingresso del CP3 e prima
   del CP4): W-B9, W-B13, X-R5 (tranne `AssetModal` e le fixture della galleria) e X-R7, con test-author e docs-writer.
   Poi, in un mio lotto, **X-R8** (la cache dell'elenco delle valute dei fornitori, proposta del coordinatore).
6. **CP4 — schemi** (C3: pacchetti per dominio, al posto di D-X9), quando W e J sono fermi su quei file.
7. **CP5 — PL7**, dopo PL1 di J.
8. **CP6 — F05**: elenchi, `is_scraper`, i due livelli di D-X4 (permesso e ricerca, un punto unico ciascuno), esiti
   `PROVIDER_NOT_ALLOWED`, `provider_allowed`, `searchable` e `notice`, sezione `.env.example`; il blocco SSRF dello scraper
   CSS (precondizione); avviso minimo nella UI (asset e cambi) e la riga «fonte non ufficiale» nella configurazione della
   fonte (dopo il lotto A). K-16 e O-9 (backend, piccoli) viaggiano qui o in un treno qualunque.
9. **CP7 — FE4**; **CP8 — FE5a** con O-8, O-20, K-20, K-19; **CP9 — FE5b/c**.
10. **CP10 — impostazioni backend**: contratto e validazione, modello e migrazione 007 (upgrade/downgrade su un DB 1.2 popolato),
    cifratura, archivio, risoluzione, redazione, API, consegna asset/FX, test di sicurezza.
11. **CP11 — impostazioni UI**: scheda, modulo, «Configura», i18n, galleria; primo uso justETF/Borsa Italiana.
12. **CP12 — BRIM e tools**: mixin nelle due basi e consegna (BRIM con W, dopo PL5).
13. **CP13 — F21 + C-90 (+ C-66)**; facoltativo U-B1.
14. **Finale**: `security-review` sulle impostazioni e sugli elenchi; doc (`docs-writer`); handoff finale.

## 10. Definizione di fatto

- Riordino: vecchi percorsi a zero (`services.asset_source` puntato, `services.asset_sources`, `services/fx.py`,
  registri in `provider_registry`, `api/v1/{assets,fx}.py` monolitici); guardia «vecchie case» verde; `all-backend` con gli
  stessi conteggi della base (+ test nuovi); `ruff`/`black` puliti; `--dead-code` senza reperti nuovi; `openapi.json`
  identico (o D-X10 per PL7); `mkdocs build` e `check-links` verdi; `check_source_paths.py` non peggiora; rinomine ≥ 95 %.
- Frontend: `svelte-check`, Vitest, `front build`, E2E di asset e cambi verdi; `data-testid` e chiavi invariati.
- F05: default invariato nel self-hosted provato da test (nessuna fonte fuori dalla ricerca, nessuna riga d'avviso);
  profilo gestito provato con D-X4: scraper fuori dalla ricerca (anche nominati in `providers=` o con un URL incollato),
  assegnabili a mano con il `notice`, probe e sync che funzionano, cambi delle banche centrali tutti; asset orfani gestiti;
  SSRF dello scraper CSS bloccato, anche dopo i redirect.
- Impostazioni: §4.5 nel piano prima del codice; contratto in 4 famiglie; 007 testata su un DB 1.2; nessun segreto in risposte,
  log, errori, AI Export (test); permessi provati (utente/utente, admin/personale, non-admin/sistema); env vince e blocca;
  invisibilità nel profilo gestito; chiave persa o cambiata gestita; 4 lingue; doc; `security-review` senza HIGH/CRITICAL aperti.
- F21: ordine, gruppi, badge, azioni, sezione chiusa, avviso per asset; D-X3 provato.
- Voci K-16, K-19, K-20, O-8, O-9, O-20, C-66, C-90 chiuse con test; voce 5 chiusa come già fatta.
- Ogni schermata nuova (scheda dei plugin, «Configura», gruppi della ricerca, avviso delle fonti non permesse) nella galleria,
  con lo scatto assestato di G quando è integrato.
- Sezione X di `BACKLOG_POST_1.2.md` aggiornata a ogni checkpoint; porta 6183 libera (`lsof`) a ogni handoff.

## 11. Test e selettori (corsia 6183)

**Vincolo**: il server di test della corsia è unico e il suo ambiente non cambia durante una run. Tutto ciò che dipende da
variabili d'ambiente (profilo gestito, elenchi permessi, blocco di un campo da `NAME`/`NAME_FILE`) si prova **in processo**:
servizi e handler chiamati direttamente con `monkeypatch` dell'ambiente, come fanno già `api fx-unit` e `api signal-catalogs`;
mai riavviando il server della corsia. Il risolutore legge l'ambiente a ogni chiamata, non all'import.

- **CP1 (PL2)**: `services provider-registry`, `provider-registry-misc`, `signal-registry`, `signal-plugin-matrix`, `risk-all`,
  `tools-registry`, `brim-provider-base`, `provider-contracts`, `asset-source`; `api signal-catalogs`, `assets-provider`, `fx`;
  `utils gate-plugin-layout`, `gate-plugin-i18n-ownership`, `gate-i18n-catalog`; `external brim-providers` (file d'esempio,
  offline); poi `all-backend`.
- **CP2a/CP2b (asset ed eventi)**: `services asset-source`, `asset-source-refresh`, `asset-source-guards`, `asset-signals`,
  `current-price-bootstrap`, `scheduled-investment-param-change`, `asset-sync-counts`, `borsa-italiana-search`,
  `borsa-italiana-funds`, `web-link-finder`, `provider-errors`, `series-preparation`, `risk-all`, `scheduler-jobs`; `utils
  provider-core-cache`; `api assets-crud`, `assets-price`, `assets-events`, `events-target-currency`, `events-suggest`,
  `assets-metadata`, `asset-merge`, `market-data-wipe`, `asset-currency-change`, `ohlc-sentinel`, `current-price-persistence`,
  `prices-currency-coherence`, `prices-sync-delta`, `asset-signals`, `signal-catalogs`, `signal-request-validation`;
  `db asset-merge`; `all-backend`; hash di `api schema`.
- **CP3 (PL4 + router dei cambi)**: `services fx-conversion`, `fx-core`, `fx-sync-service`, `financial-math`, `roi-fifo-utils`,
  `portfolio-engine`, `lots-analysis-pure`, `ai-export-pure`; `api fx`, `fx-unit`, `fx-sync`, `fx-signals`,
  `fx-compress-errors`, `signal-catalogs`, `signal-request-validation`; `schemas fx-routes`; `all-backend`; hash di `api schema`.
- **F05**: `services provider-policy` (nuovo, in processo: la tabella di §4.3, profilo × elenco × `is_scraper` → permesso,
  ricerca, `notice`, compreso il fornitore senza dichiarazione), `scheduler-jobs`, `asset-source-refresh`, `fx-sync-service`;
  `api assets-provider` (default invariato; profilo gestito in processo: la ricerca, anche in streaming, con `providers=` e
  con un URL, non interroga gli scraper, la probe e l'assegnazione sì), `fx-sync` (comportamento di default, invariato); il
  blocco SSRF senza rete (risolutore finto, redirect verso un indirizzo interno); Vitest della riga d'avviso in
  `ProviderAssignmentSection.test.ts`.
- **Impostazioni**: `services plugin-settings` (nuovo: dichiarazioni, cifratura, AAD, risoluzione, redazione, blocco da ambiente
  in processo), `api plugin-settings` (nuovo: permessi, scrittura sola, esiti per campo; profilo gestito in processo),
  `db post-migration` + test della 007 (upgrade/downgrade su un DB 1.2 popolato, `db validate`), `api account-deletion`,
  `services ai-export` (marcatore), `utils gate-plugin-i18n-ownership`; Vitest del modulo; E2E delle impostazioni.
- **Frontend**: `front-asset asset-unit|asset-list|asset-detail|asset-modal|asset-data-editor|asset-classification|asset-event-delete|asset-merge`,
  `front-fx fx-unit|fx-list|fx-detail|fx-add-pair|fx-editor|fx-csv-import|fx-sync|fx-sync-mock|fx-bulk|fx-destructive`,
  `front-utility core-unit|component-unit`; `front check`, `front build` (senza porta).
- Senza porta: `pipenv run python dev.py lint`, `lint --dead-code`, `api schema`, `mkdocs build`, `mkdocs check-links`, `i18n check`.

## 12. Specialisti

- `test-author`: guardie dei vecchi percorsi, aggiornamenti dei test dei registri, tutta la suite delle impostazioni (inclusa
  la sicurezza e la migrazione), F05, F21, i rossi delle voci del dominio, Vitest/E2E dei lotti frontend.
- `docs-writer` (solo EN): pagine dev dei pattern e delle famiglie, pagina nuova `patterns/plugin_settings.md`, testo admin
  (variabili e note di sicurezza, da consegnare a H per `admin/configuration`), pagina utente delle impostazioni dei plugin,
  ricerca e preferenze dei fornitori; `translate-stamp` solo per ritocchi puntuali.
- `security-review`: a fine CP10–CP11 e prima dell'handoff finale.
- `project-historian`: tabelle «Source files» e una pagina di decisione sulle impostazioni dei plugin, su richiesta del coordinatore.
- Skill: `asset-plugin`, `brim-plugin`, `tool-plugin`, `devpy-i18n`, `testing-backend`, `testing-frontend`, `lint-format`,
  `lint-format-frontend`, `test-triage` quando serve.

## 13. Dipendenze nuove

- Python: **`cryptography`** (solo questa; serve a CP10). Nessuna per i test.
- npm: nessuna. `npm ci` (lock esistente) al primo lotto frontend, dopo un errore confermato e col via del coordinatore.

## 14. Proposte per CHANGELOG e navigazione (le scrive il coordinatore)

- `[Unreleased]`: «✨ Impostazioni dei plugin», «✨ Fonti premium in testa alla ricerca», «🔄 Elenchi dei fornitori permessi»,
  «🐛» per K-16, K-20, O-8, O-20, O-9; nessuna voce per il riordino.
- Nav MkDocs: `developer/architecture/patterns/plugin_settings.md`; `user/settings/plugins.md`.

## 15. Avanzamento

### Via libera parziale ✅ (2026-10-14, ~22:55)

> **Note implementazione**: approvazione del coordinatore 1.3, su delega del developer (testo nell'intestazione).
> Perimetro: X0 e CP1. Il 14/10 il coordinatore ha anche approvato l'opzione (1) per il CP1: un solo commit (§9, passo 2).
>
> **Fuori pista**: alla prima approvazione nella sessione ho scritto al coordinatore che il piano l'aveva approvato
> direttamente il developer «alle 19:30». Non era così: l'ha approvato il coordinatore alle 22:55, su delega del developer,
> e il coordinatore l'ha corretto nel suo messaggio successivo.

### X0 — base e misure ✅ (2026-10-14)

- ✅ Piano nel journal (questo file), dalla mia analisi del 14/10, aggiornato con le decisioni del coordinatore (C1–C3,
  opzione 1, indicazioni per dopo).
- ✅ Misure rapide sulla base `c9bb8f257` (14/10, ~23:00), log in `/tmp/libreFolio_x_base/`:
  - `pipenv run python dev.py lint` (ruff): «All checks passed!»;
  - `pipenv run python -m black --check backend/`: **4 file da riformattare, preesistenti** (728 invariati):
    `alembic/versions/004_release_1_2_0_schema.py`, `test_api/test_portfolio_wac.py`, `test_api/test_portfolio_api.py`,
    `test_utilities/test_i18n_usage_gate.py`. Nessuno è mio: il CP1 non deve aggiungerne altri;
  - `pipenv run python dev.py lint --dead-code --scope backend`: 10 reperti non referenziati, 26 referenziati solo dai test
    (581 a basso segnale nascosti);
  - `pipenv run python dev.py api schema`: sha256 `openapi.json` `1302530690b505a767f1b0fc855edac193ab3e530f052ba70588dfbf8e213c2b`,
    `tool-contracts.openapi.json` `202402e592a48f3085ffbb6fda0f8b5d422f29c5fac794c318b5ace7f46dcc1d` (copia in
    `/tmp/libreFolio_x_base/openapi.base.json`);
  - `pipenv run python dev.py i18n check`: 4 361 chiavi, sorgenti base 1, plugin 71, sottosistemi 17, severo, verde;
  - `python3 LibreFolio_devWiki/check_source_paths.py`: 8 percorsi inesistenti (13 occorrenze) su 3 844 citati, in 9
    pagine (preesistenti, fra cui gli output della coverage ignorati da git: C-92 del backlog);
  - `pipenv run python dev.py mkdocs build` (stretto): verde, 3 012 URL relativi risolti;
  - `pipenv run python dev.py mkdocs check-links`: 95 link validi, verde.
- ✅ `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6183 --data-dir /tmp/librefolio-r13-x --fresh-run all-backend`
  (14/10, 23:06–23:46, 39 min 17 s) sulla base `c9bb8f257`: **7/7 categorie verdi**; nei 23 riepiloghi di pytest
  **12 965 passati, 28 saltati, 0 falliti** (righe in `/tmp/libreFolio_x_base/allbackend_counts.txt`, log completo in
  `/tmp/libreFolio_x_base_allbackend.log`). Porta 6183 libera alla fine.

> **Note implementazione**: la seconda trappola segnalata dal coordinatore (il server condiviso costruisce frontend e
> mkdocs dentro un limite di 300 s) qui non è scattata: la build di debug è entrata nel limite e il sito mkdocs c'era già
> dalle misure rapide («Shared backend ready on port 6183», riga 27 del log).

> **Fuori pista**:
> - HEAD si è spostato da `459131eb8` a `c9bb8f257` (fast-forward del coordinatore, solo journal, uno script della galleria e
>   `TODO_FUTURI.md`) prima delle misure: le misure sono tutte su `c9bb8f257`.
> - La prima `all-backend` (14/10 23:04) si è fermata prima di qualunque test: il backend condiviso è uscito all'avvio
>   (codice 1). `dev.py server --test` costruisce il frontend se manca, e il worktree nuovo non aveva `node_modules`. In
>   quel passaggio la build ha lanciato `npm run generate-api`, che chiama `npx openapi-zod-client`, eseguito dalla cache
>   utente (`~/.npm/_npx/347e8615a33b6e89`, toccata alle 23:04:49; versione 1.18.3, la stessa del lock): è il `npx`
>   vietato, come per H, partito dal runner e non da un mio comando. Toccati: il DB di test in `/tmp/librefolio-r13-x`
>   (creato dal runner) e il file ignorato `frontend/src/lib/api/generated.ts`, che ogni build rigenera. Nessun server
>   rimasto acceso. Cura: `npm ci` dal lock in `frontend/` (regola C5), 23:05, uscita 0, nessun file tracciato cambiato;
>   poi la run ripartita con `--fresh-run`.

### CP1 — un registro per famiglia (PL2) ✅ (2026-10-15)

- ✅ **Registri nei pacchetti di famiglia**: `services/assets/registry.py` (`AssetProviderRegistry`),
  `services/fx/registry.py` (`FXProviderRegistry`), `services/brim/registry.py` (`BRIMProviderRegistry`),
  `services/signals/registry.py` (`SignalPluginRegistry`), `services/risk/registry.py` (`RiskAnalyticRegistry`); classi
  spostate tali e quali. I pacchetti `assets/`, `fx/`, `brim/`, `signals/` nascono con `__init__.py` di sola docstring.
- ✅ **`provider_registry.py`** tiene basi, errori, scoperta e decoratori (617 → 400 righe), con una docstring di modulo che
  dice dove stanno i registri; via `_LAZY_PLUGIN_BASES`, `__getattr__`, `__dir__` e l'`import importlib` rimasto senza uso.
- ✅ **Spostamento puro** `services/fx.py` → `services/fx/fx.py` (C1), con `mv` e non `git mv` (lo staging è del
  coordinatore): cambia una riga su 1 673, l'import del registro.
- ✅ **Import**: 168 istruzioni in 156 file riscritte con uno script AST usa e getta (`/tmp/libreFolio_x_cp1_rewrite.py`:
  nomi spostati da `provider_registry` al modulo nuovo, `services.fx` → `services.fx.fx`), poi `ruff --select I001 --fix` e
  `black` sui file toccati. A mano: `test_signal_registry.py` (le basi lette dall'alias del modulo), il codice in stringa di
  `test_provider_core_cache.py:179` (eseguito in un sottoprocesso, invisibile all'AST), le forme sintetiche della guardia
  `test_layer_boundaries.py`, docstring e commenti con il vecchio percorso (6 moduli dell'AI Export, i plugin asset), le
  stringhe del runner e di `scripts/coverage_analysis.py`, 8 righe in `.github` (istruzioni di FX, asset, BRIM, segnali,
  rischio, tools, `backend.instructions.md`, l'agente historian), 32 tabelle «Source files» della devWiki (C6).
- ✅ **Verifiche statiche**: `dev.py lint` pulito; `black --check backend/` con gli stessi 4 file preesistenti della base;
  `import backend.app.main`; scoperta dei registri identica alla base (stessi codici nello stesso ordine: asset 6, cambi 7,
  BRIM 33, segnali 23, rischio 15; confronto con una copia di HEAD estratta con `git archive`); `pytest --collect-only` su
  tutto `backend/test_scripts`: 12 976 test raccolti, nessun errore; `dev.py api schema`: `openapi.json` identico alla base
  tranne `info.version` (`-dirty`, escluso da C2), stessi 113 percorsi nello stesso ordine e stessi 133 `operationId`,
  `tool-contracts.openapi.json` identico byte per byte; `check_source_paths.py`: nessun percorso mancante nuovo.
- ✅ **Suite del dominio** sulla corsia 6183, una invocazione alla volta (14/10 23:53 – 15/10 00:03, script
  `/tmp/libreFolio_x_cp1_targeted.sh`), tutte verdi: `services` provider-registry 7, provider-registry-misc 23,
  signal-registry 65, signal-plugin-matrix 92, risk-all 896, tools-registry 109, brim-provider-base 34, provider-contracts
  435 (+1 saltato), asset-source 61, fx-conversion 18, fx-core 23, fx-sync-service 5, financial-math 212; `utils`
  gate-plugin-layout 33, gate-plugin-i18n-ownership 45, gate-i18n-catalog 176, provider-core-cache 33; `api`
  signal-catalogs 4, signal-request-validation 2, assets-provider 24, fx 21, fx-unit 29, fx-signals 8, fx-compress-errors
  6, fx-sync 10; `external` brim-providers 706 (+1 saltato).
- ✅ **Doc per sviluppatori** (`docs-writer`, solo EN): 10 pagine di `mkdocs_src/docs/developer/` (pattern dei registri,
  guide dei plugin asset, FX, BRIM, segnali e tools, architettura di FX, rischio e matematica finanziaria); nessuna
  traduzione toccata, nessun `translate-stamp` necessario. `dev.py mkdocs build` stretto e `mkdocs check-links` verdi
  (95 link validi).
- ✅ **Codice morto** (`lint --dead-code --scope backend`): nessun reperto nuovo; due in meno (`__getattr__` e `__dir__` di
  `provider_registry.py`, tolti), uno con il percorso nuovo (`fx/fx.py`).
- ✅ **Grep dei vecchi percorsi** in `backend/`, `scripts/`, `dev.py`, `.github/`, `mkdocs_src/docs/developer/`,
  `pyproject.toml`: zero, tranne l'eccezione di `api/v1/fx.py:767` (sopra).

> **Fuori pista**:
> - `black` su `scripts/coverage_analysis.py` (mai formattato: `dev.py format` copre solo `backend/`) aveva riformattato
>   216 righe non mie. Rifatto da `git show HEAD:…` con le sole due righe del percorso.
> - Unica eccezione al grep dei vecchi percorsi: la docstring di `api/v1/fx.py:767` («in ``services/fx.py``») finisce
>   nella descrizione di un endpoint in `openapi.json`, e cambiarla romperebbe C2. Resta com'è e si corregge al PL4, quando
>   `normalize_rate_for_storage` avrà la sua casa definitiva (voce nel backlog X).
> - Nell'analisi avevo scritto che la pagina F-095 la dava «pianificata»: era `documented`; la elencava come futura solo
>   `domains/assets.md`, corretta in X0.
- ✅ **Backend intera** sull'albero del CP1: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
  --test-port 6183 --data-dir /tmp/librefolio-r13-x --fresh-run all-backend` (15/10 00:04–00:26, 21 min 34 s): **7/7
  categorie verdi**, 23 riepiloghi di pytest **identici alla base uno per uno**: 12 965 passati, 28 saltati, 0 falliti
  (log in `/tmp/libreFolio_x_cp1_allbackend.log`). Porta 6183 libera; `git diff --check` pulito.

### Checkpoint CP1 ✅ (2026-10-15) — committato dal coordinatore: `9426c1bae` (codice) e `9d895a9c4` (journal)

- Base `c9bb8f257`; un solo commit (opzione 1): 1 rinomina pura (`services/fx.py` → `services/fx/fx.py`), 10 file nuovi
  (9 di codice più questo piano), 218 modificati; elenco esplicito in `/tmp/libreFolio_x_cp1_paths.txt`.
- Esclusi, ignorati da git: `frontend/node_modules/` (`npm ci`), `frontend/build/`, `frontend/.svelte-kit/`, i file
  generati di `frontend/src/lib/api/` e `frontend/src/lib/i18n/`, `.testLog/`, `.pytest_cache/`, `.ruff_cache/`, i
  `__pycache__`, il sito mkdocs, `backend/data/prod/logs/librefolio.log` (vuoto, scritto da `dev.py api schema`).
- Messaggio proposto: `refactor(plugins): one registry per plugin family`, con le due parti (rinomine pure, tagli) nel
  corpo.

### CP2a — gli asset in `services/assets/`, via lo shim e il barile (PL6) ✅ (2026-10-15)

Via del coordinatore il 15/10 (~00:28), sul mio ramo a `9d895a9c4`. All'handoff il coordinatore porta nel ramo
`dev_release2` (A1 e H CP1); i conflitti d'import li risolvo io, poi entrano CP1 e CP2a insieme.

- ✅ **Spostamento puro (C1)**, con `mv` (lo staging è del coordinatore):
  `services/asset_sources/{core,crud,manager,metadata,price_query,price_store,provider_management,refresh,search}.py` →
  `services/assets/`; `services/market_calendar.py` e `services/web_link_finder.py` → `services/assets/` (indicazione del
  coordinatore). Tolti lo shim `services/asset_source.py` e il barile pigro `services/asset_sources/__init__.py`.
  `services/assets/__init__.py` resta di sola docstring, ora con la mappa dei moduli, e non riesporta nulla.
- ✅ **Import**: 93 istruzioni in 48 file, con lo script AST `/tmp/libreFolio_x_cp2a_rewrite.py`. Lo script porta i nomi dello
  shim e del barile al modulo che li definisce, `asset_sources.<m>` → `assets.<m>`, e `services import
  web_link_finder|market_calendar` e `import …market_calendar as …` nel pacchetto nuovo. Poi `ruff --select I001 --fix` su
  16 file: `assets` ordina dopo `asset_source_providers`. Lo script aveva raccolto su una riga sola 6 istruzioni su più
  righe dei moduli spostati (`manager`, `metadata`, `price_query`, `price_store`, `provider_management`, `refresh`): hanno
  ripreso la forma di HEAD, e cambia solo il percorso.
- ✅ **A mano**:
  - le stringhe che l'AST non vede: `MODULE` e la sonda in sottoprocesso di `test_market_calendar.py`, il percorso in
    `test_data_quality_thresholds.py`;
  - docstring e commenti con il vecchio percorso:
    - 3 in `assets/core.py`, `utils/json_utils.py`, il commento del drawdown in `signal_plugins/`;
    - 9 docstring di test che citavano le righe del vecchio monolite: tolte le righe, citato il modulo giusto;
    - i commenti di `test_signal_registry.py` e `test_risk_signal_plugins.py`;
  - le stampe del runner (`_backend_services.py` ×5, `_backend_utils.py`) e il commento di `_server.py`;
  - `scripts/coverage_analysis.py`: la voce HIGH dello shim, che non copriva più i servizi veri, diventa il pacchetto
    `backend/app/services/assets/`; lo stesso per la categoria CORE_SVC;
  - `.github`: `applyTo` e 3 righe delle istruzioni degli asset, la skill `asset-plugin`, la skill `testing-backend`.
- ✅ **Test** (`test-author`): `test_provider_core_cache.py` perde il contratto della facciata, che non esiste più. Via
  `test_legacy_and_canonical_public_symbols_share_identity` (5 casi), gli alias `Canonical*` e i due import rotti; la sonda a
  freddo verifica la sola base `AssetSourceProvider` di `assets/core.py`. Il file passa da 33 a 28 test.
- ✅ **Doc per sviluppatori** (`docs-writer`, solo EN, nessuna traduzione): 13 pagine, 40 sostituzioni su 42. Le 2 rimaste
  sono corrette: un nome di file in un diagramma e un file di test. In `backend/assets/architecture.md` la sezione «Canonical
  Package and Compatibility» diventa «Package Layout and Imports» (nessun link all'ancora vecchia), e la tabella dei moduli
  guadagna `registry.py`, `web_link_finder.py` e `market_calendar.py`.
- ✅ **devWiki (C6)**: 80 sostituzioni in 59 pagine, con lo script `/tmp/libreFolio_x_cp2a_wiki.py`, che lega ogni modifica a
  pagina e riga.
  - Le tabelle «Source files» che citavano lo shim puntano ora al modulo che fa la cosa descritta: base, thread e cache →
    `core.py`; sincronizzazione → `refresh.py`; metadati → `metadata.py`; assegnazione → `provider_management.py`; scritture,
    eventi e azzeramento → `price_store.py`; letture → `price_query.py`; registro → `registry.py`; la «facciata» del
    pianificatore → `manager.py`. Le altre tabelle seguono lo spostamento.
  - Aggiornata la prosa al presente di feature, concetti e problemi; quella storica no.
  - L'entità `asset-sources-package.md` è riscritta per lo stato nuovo (il nome del file non cambia, per i link).
  - `check_source_paths.py`: 5 percorsi mancanti, tutti preesistenti e ignorati da git (15 a metà lavoro).
- ✅ **Verifiche statiche**:
  - ruff su `backend/` pulito; `black --check backend/` con gli stessi 4 file preesistenti;
  - sui 4 file di `scripts/` toccati, nessun reperto ruff; `_server.py` e `coverage_analysis.py` erano già fuori da black a
    HEAD (non riformattati);
  - `import backend.app.main`; scoperta: asset 6, cambi 7, BRIM 33; i 12 moduli di `services/assets/` si importano, i 4
    vecchi no;
  - `pytest --collect-only`: 12 971 test (CP1: 12 976, meno i 5 casi tolti), nessun errore;
  - `dev.py api schema`: `openapi.json` identico alla base tranne `info.version`; `tool-contracts.openapi.json` identico;
  - `lint --dead-code`: nessun reperto nuovo (via `__getattr__`/`__dir__` del barile, due reperti con il percorso nuovo);
  - `mkdocs build` stretto verde; `check-links` 95 validi; `git diff --check` pulito.
- ✅ **Similarità**, misurata con git in un repo usa e getta (`/tmp/libreFolio_x_cp2a_sim`), senza toccare l'indice del
  worktree:
  - 100 %: `market_calendar.py`, `web_link_finder.py`;
  - 99 %: `core`, `crud`, `price_query`, `price_store`, `provider_management`, `refresh`, `search`; 98 %: `metadata`;
  - **50 %: `manager.py`**. Il file ha 22 righe, e 8 sono le 6 istruzioni d'import che devono portare il percorso nuovo; il
    corpo della classe non cambia.
- ✅ **Grep dei vecchi percorsi** in `backend/`, `scripts/`, `dev.py`, `.github/`, `mkdocs_src/docs/developer/`: zero, tranne
  le due docstring che finiscono in `openapi.json` (sotto, voce X-R2 del backlog).
- ✅ **Suite del dominio** sulla corsia 6183, una alla volta (`/tmp/libreFolio_x_cp2a_targeted.sh`, 15/10 00:48–00:51), tutte
  verdi:
  - `services`: asset-source 61, asset-source-refresh 12, asset-signals 30, current-price-bootstrap 8,
    scheduled-investment-param-change 3, asset-sync-counts 1, web-link-finder 24, provider-errors 134, signal-registry 65,
    risk-all 896;
  - `utils` provider-core-cache 28; `db` asset-merge 12.
- ✅ **Backend intera** sull'albero del CP2a: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
  --test-port 6183 --data-dir /tmp/librefolio-r13-x all-backend` (15/10 00:52–01:14, 22 min 38 s): **7/7 categorie
  verdi**. 22 riepiloghi di pytest su 23 sono identici al CP1; il ventitreesimo, l'unità consolidata di `utils`, passa da 2 191
  a 2 186: sono i 5 casi del test della facciata, tolto. Totale **12 960 passati, 28 saltati, 0 falliti** (CP1: 12 965 e
  28). Log in `/tmp/libreFolio_x_cp2a_allbackend.log`, righe in `/tmp/libreFolio_x_cp2a_allbackend_counts.txt`. Porta 6183
  libera alla fine; `git diff --check` pulito.
- ✅ **Backlog** (la mia sezione di `Phase_0/BACKLOG_POST_1.2.md`): aggiunte X-R2 (le due docstring sotto) e W-B9 (il test dei
  cambi che chiama dal vivo la BCE, passato a X dal coordinatore il 15/10).

> **Fuori pista**:
> - Nella prima stesura avevo corretto due docstring che `openapi.json` riporta come descrizioni di schemi: `BackwardFillInfo`,
>   da `schemas/common.py:369`, e `IdentifierType`, da `db/models.py:123`. Il confronto con la base le ha mostrate come
>   uniche differenze. Le ho rimesse com'erano, come per X-R1: si correggono in un lotto che cambia comunque l'API (voce
>   X-R2). Effetto utile: `db/models.py` e `schemas/common.py`, file condivisi, restano intatti.
> - Lo script degli import raccoglieva su una riga sola le istruzioni su più righe: un cambio di forma, non di percorso, che
>   abbassava la similarità (`manager.py` al 46 %, sotto la soglia di rinomina di git). Rimesse 6 istruzioni nella forma di
>   HEAD.
> - `docs-writer` segnala la docstring di `assets/manager.py` («Compatibility manager…»), che non torna più ora che la
>   facciata non c'è. Cambiarla adesso porterebbe il file sotto il 50 %: si aggiorna nel CP2b, che è un lotto di tagli.

### Checkpoint CP2a ✅ (2026-10-15) — committato dal coordinatore: `4284c50f3` (codice) e `e8f0b293c` (journal)

- Base `9d895a9c4`. 11 rinomine pure, 2 file tolti, 134 modificati (compresi questo piano e il backlog), nessun file nuovo
  oltre alle rinomine; elenco esplicito in `/tmp/libreFolio_x_cp2a_paths.txt`. Nessun file tagliato: un solo elenco.
- Esclusi, ignorati da git: `frontend/src/lib/api/openapi.json` e `tool-contracts.openapi.json` (rigenerati da
  `dev.py api schema`), il sito mkdocs, `.testLog/` (con `00_archive/test-db_20261015_011424.tar.xz`), `.pytest_cache/`,
  `.ruff_cache/`, i `__pycache__`, `backend/data/prod/logs/librefolio.log`.
- Messaggi proposti: `refactor(assets): move asset services, drop shim` per il codice, `docs(journal): X CP2a log, backlog
  X-R2 and W-B9` per il journal.

### Aggiornamento di base: `dev_release2` (A1, A2, H CP1, W1, W2) nel ramo X ✅ (2026-10-15) — merge `d036d4896`, nota `5052c808f`

Il coordinatore ha aperto il merge (`git merge --no-ff --no-commit e0816ec9c` sul mio `e8f0b293c`; base comune
`c9bb8f257`), fermo su 35 conflitti, tutti di percorso: i miei (`assets/`, registri per famiglia, `fx/fx.py`) contro quelli
di A (`accounts/`), H (`platform/`, `platform/scheduler/`, `files/`) e W (`transactions/`, `brokers/`). Il merge commit lo fa
lui; io risolvo, metto in stage i soli file risolti o corretti, e valido.

- ✅ **Risoluzione dei 35 conflitti**:
  - 25 file Python con conflitti di soli import (22 in `backend/app`, 3 test): preso il lato in arrivo di ogni blocco (script
    `/tmp/libreFolio_x_merge_take_theirs.py`, che si ferma se un blocco contiene altro che import), poi rimesse le mie rinomine
    con i due riscrittori AST del CP1 e del CP2a (28 istruzioni), poi `ruff --select I --fix`. Il confronto con i due genitori
    lo prova: rispetto al lato in arrivo cambiano solo le mie rinomine, rispetto al mio solo le loro;
  - riga per riga, tenendo per ogni voce la casa più nuova (script `/tmp/libreFolio_x_merge_manual.py`): le forme sintetiche
    di `test_layer_boundaries.py` (`brokers.broker_service`; `fx.fx` con `transactions.transaction_service`), 7 pagine della
    devWiki, i due blocchi di `mkdocs_src/docs/developer/backend/risk/architecture.md` (tabella ed esempio di codice) e i due
    di `scripts/coverage_analysis.py` (le chiavi di tutti, senza riformattare).
- ✅ **Rischio semantico** (import verso vecchie case fuori dai conflitti): nessuno nei moduli nuovi di W, H e A. L'unico
  riferimento fuori dai conflitti era un commento di `scripts/visual_review/live_price_check.py` (nuovo, della galleria G):
  `asset_sources/price_query.py` → `assets/price_query.py`. I riscrittori, a secco, ora non trovano più nulla.
- ✅ **Grep dei vecchi percorsi** di X, A, H e W in `backend/`, `scripts/`, `dev.py`, `.github/`,
  `mkdocs_src/docs/developer/`: zero, tranne le eccezioni note X-R1 (`api/v1/fx.py:767`) e X-R2 (`db/models.py:123`,
  `schemas/common.py:369`).
- ✅ **Verifiche sulla revisione combinata** (confronti con `e0816ec9c` estratto con `git archive` in
  `/tmp/libreFolio_x_theirs_tree`):
  - `dev.py api schema`: `openapi.json` identico a quello di `e0816ec9c` tranne `info.version`; 113 percorsi e 133
    `operationId` nello stesso ordine; `tool-contracts.openapi.json` identico;
  - scoperta dei registri identica (stessi codici, stesso ordine): asset 6, cambi 7, BRIM 33, segnali 23, rischio 15;
  - `pytest --collect-only`: 12 971 (`e0816ec9c`: 12 976; differenza = i 5 casi della facciata tolti nel CP2a, più l'id
    rinominato del test delle soglie su `assets/crud.py`);
  - ruff su `backend/` pulito; `black --check backend/` con i soliti 4 file preesistenti; `lint --dead-code --scope
    backend`: rispetto a `e0816ec9c` cambiano solo i reperti già spiegati nel CP1 e nel CP2a;
  - `check_source_paths.py`: i 5 artefatti ignorati preesistenti; `mkdocs build` stretto verde; `check-links` 95 validi;
  - `dev.py front build --debug` (01:26–01:28): svelte-check 0 errori e 0 avvisi, build vite verde;
  - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6183 --data-dir
    /tmp/librefolio-r13-x --fresh-run all-backend` (01:28–01:48, 19 min 36 s): **7/7 categorie verdi**, 23 riepiloghi
    identici a quelli del CP2a, **12 960 passati, 28 saltati, 0 falliti**. Porta 6183 libera alla fine.
- ✅ **Stage**: i 35 file risolti più `live_price_check.py`, nient'altro; `git diff --cached --check` pulito. Il merge
  messo in stage, rispetto al mio `e8f0b293c`, ha esattamente le modifiche di `e0816ec9c` sulla base (364 file, +13 799
  −4 787); rispetto a `e0816ec9c`, esattamente le mie (323 file, +1 739 −981) più la riga del commento.
- Questo piano resta fuori dallo stage: è journal, da committare dopo il merge.

> **Fuori pista**: nessuno. Segnalato al coordinatore, fuori dal mio perimetro: `scripts/coverage_analysis.py` cita
> `backend/app/uploads.py`, che non esiste (preesistente, già alla base `c9bb8f257`).

### Secondo aggiornamento di base: H CP2a (pacchetto `config/`) nel ramo X ✅ (2026-10-15) — merge `bff1bd97b`, nota `64a5a3fe7`; CP1 e CP2a in `dev_release2`

Mentre risolvevo il primo merge è entrato in `dev_release2` H CP2a (`60f8a35ce`): `config.py` → `config/__init__.py` (stesso
percorso d'import), letture d'ambiente in `config/platform.py` e `config/accounts.py`, guardia nuova `services
config-package` (nessuna lettura di `os.environ` fuori da `config/`; `web_link_finder.py` esentato per nome di file). Il
coordinatore ha aperto `git merge --no-ff --no-commit 0ac49739d` sul mio `5052c808f` (base comune `e0816ec9c`).

- ✅ **Un conflitto**, `LibreFolio_devWiki/wiki/decisions/utils-leaf-functions-only.md`, tabella «Source files»: tenute le
  due righe col percorso più nuovo di ciascuna, `services/fx/fx.py` (mia) e `config/__init__.py` (di H). Verificate sul
  codice: `clear_cache` è importato in testa a `fx/fx.py:29`, `get_git_version` in testa a `config/__init__.py:40`.
- ✅ **Rischio semantico**: fra le righe aggiunte dal lotto di H, una sola citava un mio vecchio percorso:
  `mkdocs_src/docs/developer/architecture/settings.md:39` («still read by `services/web_link_finder.py`») →
  `services/assets/web_link_finder.py`. Le letture d'ambiente di `web_link_finder.py` restano dove sono: le sposta H nel
  suo CP3. I due riscrittori AST, a secco, non trovano nulla; nei file fusi senza conflitto (`main.py`, `api/v1/system.py`,
  `_backend_services.py`, la pagina del rischio, `backend.instructions.md`, F-052, il backlog) le parti di H non toccano
  righe mie, e le intestazioni di `main.py` e `system.py` tengono sia i registri per famiglia sia `is_test_mode` e
  `owning_test_lane_id`.
- ✅ **Verifiche sulla revisione combinata** (confronti con `0ac49739d` estratto in `/tmp/libreFolio_x_theirs2_tree`):
  - `services config-package` sulla 6183: 472 passati; la scansione raggiunge i miei moduli nuovi (`services/assets/`,
    `fx/`, `brim/`, `signals/`, `risk/registry.py`) e `web_link_finder.py` passa come eccezione dichiarata;
  - grep dei vecchi percorsi di X, A, H (compreso `app/config.py`) e W: zero, tranne X-R1 e X-R2;
  - `pytest --collect-only`: 13 443 (`0ac49739d`: 13 441). Differenza spiegata sui node id: la guardia di H, parametrizzata
    per file, ha 21 casi sui miei pacchetti nuovi invece dei 14 sui vecchi percorsi (+7); i 5 casi della facciata tolti nel
    CP2a; un id rinominato (`assets/crud.py`);
  - `api schema`: identico a `0ac49739d` tranne `info.version`; `tool-contracts` identico; scoperta dei registri identica
    (asset 6, cambi 7, BRIM 33, segnali 23, rischio 15);
  - ruff pulito; `black --check backend/` con i soliti 4 file; `mkdocs build` stretto verde, `check-links` 95 validi;
    `check_source_paths.py` con i 5 artefatti ignorati;
  - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6183 --data-dir
    /tmp/librefolio-r13-x --fresh-run all-backend` (01:54–02:16, 21 min 40 s): **7/7 verdi**, **13 432 passati, 28
    saltati, 0 falliti**. Rispetto al primo merge +472, esattamente la guardia nuova (nell'unità consolidata dei
    `services`, 6 436 → 6 908); gli altri 22 riepiloghi identici. Porta 6183 libera.
- ✅ **Stage**: il file del conflitto e `settings.md`, nient'altro; `git diff --cached --check` pulito. Rispetto al mio
  `5052c808f` il merge porta esattamente le modifiche di H (35 file, +611 −52); rispetto a `0ac49739d` esattamente le mie
  più la riga di `settings.md`.

> **Fuori pista**: lo stage di `settings.md` va oltre la lettera «stage solo di quel file»: la riga è il solo riferimento al
> mio vecchio percorso entrato con H, e il grep a zero lo chiedeva. Dichiarato al coordinatore, che può toglierlo dallo stage.

### CP2b — tagli degli asset, router per risorsa, eventi in moduli propri ✅ (2026-10-15)

Via del coordinatore il 15/10 (~02:17), sul mio ramo a `64a5a3fe7` (uguale a `dev_release2`: CP1 e CP2a integrati). Sua
decisione (A) del 15/10 (~02:35): `schemas/assets.py` → `schemas/assets/assets.py` come rinomina pura, nello stesso commit dei
tagli (opzione 1: rinomine e tagli in due elenchi, nessun file insieme rinominato e tagliato, rinomine ≥ 95 %).

- ✅ **Rinomina pura (C1)**: `schemas/assets.py` → `schemas/assets/assets.py` (99 %: cambia solo la riga che importa
  `FAAssetEventPoint`), con `schemas/assets/__init__.py` di sola docstring. Serve a far esistere `schemas/assets/events.py`. La
  via di H per `config` (il contenuto nell'`__init__.py`) qui chiudeva un ciclo d'import: `prices` → `assets.events` →
  `assets/__init__` → `prices`.
- ✅ **Taglio di `services/assets/core.py`** (899 → 156 righe) → `base.py` (759): il contratto dei plugin
  (`AssetSourceProvider` con la guardia OHLC, `AssetSourceError`, `AssetHistoryStartDate`, `ASSET_HISTORY_MIN_FALLBACK`).
  In `core.py` restano cache, `_run_provider_in_thread`, parametri e `_json_safe_details`. Le 17 definizioni sono identiche a
  HEAD; la parte che resta non usa nessuno dei nomi spostati, e nessun modulo li leggeva come attributo di `core`.
- ✅ **Taglio di `services/assets/price_store.py`** (1 020) per tema, mixin composti in `AssetSourceManager` (C4):
  `price_store.py` (338: upsert e delete dei prezzi), `currency_change.py` (183: wipe al cambio di valuta), `event_store.py`
  (539: eventi; importa `PRICE_UPSERT_CHUNK_SIZE` dai prezzi). I 12 metodi sono identici, salvo le 6 chiamate qualificate
  `PriceStoreOperations.` → `EventStoreOperations.` dentro gli eventi; nessuna collisione di nomi fra i mixin, e ogni
  metodo pubblico del manager risolve come prima. `refresh.py` chiama `EventStoreOperations._upsert_asset_events`. La
  docstring di `manager.py` non dice più «Compatibility» (segnalata da docs-writer nel CP2a).
- ✅ **Router per risorsa (C2)**: `api/v1/assets.py` (1 225) → pacchetto `api/v1/assets/` con `crud.py` (7 rotte),
  `market_data.py` (2), `prices.py` (6), `providers.py` (8) ed `events.py` (4). `__init__.py` compone `asset_router`
  includendo ogni sotto-router con prefisso `/assets` e tag `FA (Financial Assets)`, nell'ordine di registrazione di prima;
  `router.py` è intatto. Le 27 funzioni sono identiche (cambia il nome del router in 9 decoratori). FastAPI rifiuta un
  `include_router` senza prefisso con rotte dal percorso vuoto, da qui il prefisso messo all'inclusione.
- ✅ **Schemi degli eventi (C3)**: le 11 classi da `schemas/prices.py` (551 → 369) a `schemas/assets/events.py`, identiche;
  `prices.py` importa il punto evento per `FAHistoricalData` e `FAPriceQueryResult`.
- ✅ **Import**: 90 istruzioni in 60 file (`/tmp/libreFolio_x_cp2b_rewrite.py`), ogni nome al modulo che lo definisce,
  compresi quelli che `schemas/assets.py` ri-esportava (`FACurrentValue`, `FAHistoricalData`, `FAPricePoint` → `prices`;
  `AssetType`, `IdentifierType` → `db.models`). Uno a mano (`db_schema_validate.py`, `# noqa` sulla prima riga). Hub
  `schemas/__init__.py`: gruppi `assets.assets` e `assets.events`, e i nomi ri-esportati puntano al modulo che li definisce
  (191 nomi di `__all__` risolti). Poi `ruff --select I --fix` su 18 file.
- ✅ **Test** (adattamenti meccanici, nessuna asserzione cambiata): `test_asset_source_upsert_guards.py` chiama i metodi degli
  eventi da `EventStoreOperations`; in `test_provider_core_cache.py` il caso «price-store» della sonda diventa
  «currency-change» (l'unico dei tre moduli che usa le cache di `core`) e la sonda a freddo importa `AssetSourceProvider` da
  `base`.
- ✅ **Doc e wiki**: docs-writer, 7 pagine e 20 sostituzioni (più un esempio di codice che col pacchetto di sola docstring
  sarebbe stato rotto); `.github`, 4 righe in 3 file (istruzioni di asset e segnali, skill `asset-plugin`); 6 commenti nel
  codice, nei test e nel runner; devWiki (C6), 40 pagine: 61 sostituzioni nelle tabelle «Source files» e nella prosa al
  presente, più l'entità `asset-sources-package` riscritta per lo stato nuovo.
- ✅ **Prova C2** (`/tmp/libreFolio_x_cp2b_routes_probe.py`, prima e dopo): la tabella delle 139 rotte effettive dell'app è
  identica nell'ordine e in percorso, metodi, nome, endpoint, tag, `unique_id`, `operation_id`, stato, modello di risposta e
  dipendenze; 46 richieste d'esempio arrivano allo stesso endpoint, compresi i casi ambigui
  (`/assets/prices/market-data/summary` → `market_data_summary`), i 405 e il catch-all del frontend.
- ✅ **Verifiche statiche** (confronti con HEAD estratto da `git archive` in `/tmp/libreFolio_x_cp2b_base_tree`):
  - `dev.py api schema`: `openapi.json` identico tranne `info.version`; `tool-contracts.openapi.json` identico;
  - `pytest --collect-only`: 13 453 (HEAD 13 443). I +10 sono la guardia `config-package` di H, parametrizzata per file, che
    perde i 2 file spariti e conta i 12 nuovi; il caso della sonda cambia solo nome;
  - ruff pulito; `black --check backend/` con i soliti 4 file; codice morto identico; `mkdocs build` stretto verde,
    `check-links` 95 validi; `check_source_paths.py` con i 5 artefatti ignorati; `git diff --check` pulito;
  - grep dei vecchi percorsi di CP1, CP2a e CP2b: zero, tranne X-R1 e X-R2 (ora anche `db/models.py:117`, che resta per
    indicazione del coordinatore); i riscrittori dei tre lotti e la scansione delle stringhe, a secco: zero.
- ✅ **Suite del dominio** sulla corsia 6183, una alla volta (`/tmp/libreFolio_x_cp2b_targeted.sh`), tutte verdi:
  `services` asset-source 61, asset-source-refresh 12, asset-source-guards 29, asset-signals 30, current-price-bootstrap 8,
  scheduled-investment-param-change 3, asset-sync-counts 1, provider-errors 134, config-package 482, provider-registry 7,
  signal-registry 65; `utils` provider-core-cache 28; `db` asset-merge 12; `schemas` all 1 705.
- ✅ **Backend intera**: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6183
  --data-dir /tmp/librefolio-r13-x --fresh-run all-backend` (15/10 02:48–03:11, 22 min 17 s): **7/7 categorie verdi**,
  **13 442 passati, 28 saltati, 0 falliti**. Rispetto alla base (il secondo aggiornamento, 13 432) i +10 sono la guardia
  `config-package` sui file nuovi, nell'unità consolidata dei `services` (6 908 → 6 918); gli altri 22 riepiloghi sono
  identici. Log in `/tmp/libreFolio_x_cp2b_allbackend.log`. Porta 6183 libera.
- ✅ **Similarità**, misurata con git in un repo usa e getta (`/tmp/libreFolio_x_cp2b_sim`): una sola rinomina,
  `schemas/{ => assets}/assets.py` (99 %); `api/v1/assets.py` risulta cancellato, accanto a sei moduli nuovi, senza
  appaiamento.

> **Fuori pista**:
> - La prima `utils provider-core-cache` è caduta su un test: la sonda a freddo, codice dentro una stringa eseguito in un
>   sottoprocesso, importava ancora `AssetSourceProvider` da `core`, e l'AST non la vede (come nel CP1). Corretta; poi una
>   scansione delle costanti stringa di `backend/` e `scripts/` non ha trovato altro. Rilancio: 28 verdi.
> - FastAPI 0.141 non appiattisce più i router inclusi (`_IncludedRouter`): la sonda delle rotte segue le rotte effettive e
>   scende con `_IncludedRouter._match` come fa il router. La prova di corrispondenza C2 resta valida, ed è più stretta di
>   un confronto per percorso.
> - Il riscrittore ha trovato nomi che `schemas/assets.py` ri-esportava senza definirli (11 importatori fra plugin e test):
>   ognuno ora punta al modulo che lo definisce. Il grep iniziale non li vedeva.

### Checkpoint CP2b ✅ (2026-10-15) — committato dal coordinatore: `870c9956f` (codice) e `84a72c0b2` (journal)

- Base `64a5a3fe7`. Un commit con due elenchi (opzione 1): 1 rinomina pura (`schemas/assets.py` → `schemas/assets/assets.py`,
  99 %) e i tagli (`core`, `price_store`, `api/v1/assets.py`, `schemas/prices.py`); 12 file nuovi, 2 tolti, 113 modificati
  (compresi questo piano e il backlog); elenco esplicito in `/tmp/libreFolio_x_cp2b_paths.txt`.
- File di altre sessioni, una riga d'import ciascuno: `brim_provider.py` (W); `risk/service.py`,
  `ai_export/components/asset_resources.py` e il suo test (J); `db/models.py:700` (condiviso). L'hub `schemas/__init__.py`:
  9 righe (gruppi e import di tipo).
- Consegna degli eventi a W dopo l'ingresso: `api/v1/assets/events.py`, `services/assets/event_store.py`,
  `schemas/assets/events.py` e i loro test; le righe che toccano gli eventi nei miei file restano mie (elenco nell'handoff).
- Messaggi proposti: `refactor(assets): cut asset services, router and event schemas` (due parti nel corpo) e
  `docs(journal): X CP2b log, CP10 key notes, backlog X-R2 and X-R3`.

### Terzo aggiornamento di base: W I1 e A3, validazione della revisione combinata ✅ (2026-10-15)

Il coordinatore ha portato nel mio ramo `dev_release2` a `0ddd296a0` (W I1 `dc7e4e48e`, A3 `90491071d`): merge `eb245b624`,
senza conflitti (unione automatica su `brim_provider.py` e sul backlog), worktree pulito. Ordine d'ingresso: X prima di J.
Validazione sulla corsia 6183, confronti con `0ddd296a0` estratto da `git archive` in `/tmp/libreFolio_x_base3_tree`:

- ✅ Riscrittori di CP1, CP2a e CP2b a secco: 0; scansione delle stringhe (bersagli di `patch`, codice in sottoprocesso): 0;
  grep dei vecchi percorsi nel perimetro della regola: solo X-R1 e X-R2. Nel frontend, fuori perimetro, `asset_source.py`
  compare in tre commenti (X-R3, ora allargata) e nel `generated.ts` ignorato, che riprende la docstring di X-R2.
- ✅ `pytest --collect-only`: 13 487 contro 13 477. Le differenze sono le stesse del CP2b: la guardia `config-package` perde 2
  file e ne conta 12 nuovi, il caso della sonda cambia nome. I test nuovi di W I1 e A3 ci sono da tutte e due le parti.
- ✅ `api schema`: identico a `0ddd296a0` tranne `info.version`; 113 percorsi e 133 `operationId` nello stesso ordine;
  `tool-contracts` identico.
- ✅ Sonda delle rotte: tabella identica (139 rotte effettive) e 46 risoluzioni identiche. La prima volta l'albero estratto
  aveva 138 rotte: senza la build del frontend `main.py` non monta `/_app` (`frontend_available()`, righe 467-477). Con un
  `index.html` e una cartella `_app` vuoti nell'albero estratto le tabelle coincidono. È una differenza d'ambiente, non di
  codice.
- ✅ `dev.py front build --debug` (svelte-check 0 errori e 0 avvisi) e `dev.py mkdocs build` prima della run, perché A3 ha
  toccato il frontend; nessun manifesto di dipendenze cambiato.
- ✅ `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6183 --data-dir
  /tmp/librefolio-r13-x --fresh-run all-backend` (15/10 03:23–03:44, 20 min 59 s): **7/7 verdi**, **13 476 passati, 28
  saltati, 0 falliti**. I +34 rispetto al CP2b sono i 34 test nuovi di W I1 e A3, gli stessi della raccolta (unità
  consolidate: `services` +3, `utils` +22, `api` +9); gli altri 20 riepiloghi sono identici. Porta 6183 libera.

> **Fuori pista**: nessuno.

### Quarto aggiornamento di base: H CP3, controllo leggero ✅ (2026-10-15) — CP2b in `dev_release2` (`05c21b2b6`)

Merge `92b42d796` del coordinatore (H CP3 `940297265`: `env_secret()`, chiave d'istanza e `derive_key`, controlli all'avvio,
`.env.example`, guardie `config-package` estesa e `config-env-example`). Controllo leggero, senza `all-backend` (la run completa
su X CP2b + H CP3 la fa J): `services config-package` 485 (475 su `940297265`, +10 = la guardia per file: −2 file spariti, +12
moduli nuovi del CP2b), `services config-env-example` 36, raccolta 13 760 contro 13 750 (le stesse differenze del CP2b),
`api schema` identico salvo `info.version`, sonda delle rotte identica (139 rotte, 46 richieste). Ingresso: avanzamento veloce
di `dev_release2` a `92b42d796`, record `05c21b2b6`; eventi passati a W con i miei elenchi.

### CP3 — PL4: il servizio e il router dei cambi tagliati per tema ✅ (2026-10-15)

Via del coordinatore il 15/10 (~03:51), sul mio ramo a `05c21b2b6`. Lotto di soli tagli: nessuna rinomina (con
`git diff -M95%` nessuna coppia; alla soglia di default git appaia due file tagliati al loro pezzo più grande, sotto).

- ✅ **Taglio di `services/fx/fx.py`** (1 673 righe, il file sparisce) per tema; le 17 definizioni sono identiche a HEAD, ognuna
  con il commento che la precede; ogni modulo ha i suoi import e, dove serve, il suo logger:
  - `base.py` (323): `FXRateProvider`, `FXProviderStartDate`, `FX_HISTORY_MIN_FALLBACK`, `FXServiceError`, `RateNotFoundError`;
  - `sync.py` (834): `sync_pairs_bulk`, `_count_actual_changes`, `_is_date_within_sync_range`, la cache `_fx_fetch_cache` e
    l'orchestratore non collegato `ensure_rates_multi_source`;
  - `conversion.py` (269): `compute_chain_rate`, `_RateRow`, `convert_bulk`;
  - `storage.py` (298): `normalize_rate_for_storage`, `upsert_rates_bulk`, `delete_rates_bulk`.
  Dipendenze a senso unico: `sync` → `conversion`, `storage`, `base`; `conversion` → `base`. `__init__.py` con la sola
  docstring (la mappa dei moduli).
- ✅ **Router (C2)**: `api/v1/fx.py` (1 083) → pacchetto `api/v1/fx/`: `providers.py` (`router_providers`, 4 rotte: catalogo e
  rotte di conversione) e `currencies.py` (`router_currencies`, 5 rotte: sync, tassi manuali, catalogo dei segnali,
  conversione); `__init__.py` ricompone `fx_router` (prefisso `/fx`, tag `FX (Forex)`) nell'ordine di prima; `router.py`
  intatto. Le 18 definizioni sono identiche.
- ✅ **Import**: 31 istruzioni in 31 file (`/tmp/libreFolio_x_cp3_rewrite.py`, ogni nome al modulo che lo definisce). Alias di
  modulo nei test, a mano: `test_fx_sync_service.py` (`fx as fx_service` → `sync as fx_service`), `test_fx_signals_api.py`
  (→ `currencies`), `test_fx_route_schemas.py` (→ `providers`), `test_fx_api_unit.py` (alias diviso in
  `fx_providers_api`/`fx_currencies_api`: 13 usi su `providers`, 5 su `currencies`, le 3 `monkeypatch.setattr` su
  `currencies`, dove gli endpoint leggono `sync_pairs_bulk`, `upsert_rates_bulk` e `delete_rates_bulk`).
- ✅ **Guardia contro le patch mute (C4)** (`/tmp/libreFolio_x_cp3_mute_patch_guard.py`): per ogni
  `monkeypatch.setattr(<alias di modulo>, "<nome>")` dei test sui pacchetti asset e cambi, il modulo bersaglio deve legare il
  nome a livello di modulo e leggerlo (nel suo codice o come `modulo.nome` da un altro modulo dell'app): 39 patch, nessuna
  muta.
- ✅ **Riferimenti**: docstring e commenti dei componenti dell'AI Export (`fx.fx.convert_bulk` → `fx.conversion.convert_bulk`,
  9 righe in 6 file di J), 5 docstring di test, le forme sintetiche di `test_layer_boundaries.py`, 5 righe del runner,
  `coverage_analysis.py` (pacchetto `services/fx/`), `.github` 9 righe (istruzioni FX, mappa del backend, segnali, esempi
  dell'agente historian); docs-writer 11 sostituzioni in 6 pagine; devWiki (C6) 57 sostituzioni in 37 pagine, compresi
  alcuni `services/fx.py` di prima del CP1 rimasti nella prosa al presente. Una riga della wiki puntava già male (il
  «serializer» dei tassi del backup): ora punta a `api/v1/backup.py`.
- ✅ **Prova C2** (`/tmp/libreFolio_x_cp3_routes_probe.py`, con 17 richieste in più sui cambi): tabella delle 139 rotte identica
  e 63 risoluzioni identiche, compresi i 405 e il catch-all.
- ✅ **Verifiche statiche** (HEAD estratto in `/tmp/libreFolio_x_cp3_base_tree`): `openapi.json` identico tranne
  `info.version`, `tool-contracts` identico; raccolta 13 765 contro 13 760 (+5: la guardia `config-package` per file, −2 file
  spariti e +7 moduli nuovi); scoperta dei registri invariata; ruff pulito; `black --check backend/` con i soliti 4; codice
  morto identico (`ensure_rates_multi_source` con il percorso nuovo); `mkdocs build` stretto verde; `check-links` 95;
  `check_source_paths.py` con i 5 artefatti ignorati; `git diff --check` pulito; grep dei vecchi percorsi di CP1-CP3: solo X-R1
  (ora `api/v1/fx/providers.py:183`) e X-R2; riscrittori dei quattro lotti e scansione delle stringhe: zero.
- ✅ **Suite del dominio** sulla 6183 (`/tmp/libreFolio_x_cp3_targeted.sh`, 04:04–04:13), tutte verdi: `services`
  fx-conversion 18, fx-core 23, fx-sync-service 5, financial-math 212, config-package 490, provider-registry 7,
  signal-registry 65, ai-export 1 021, risk-all 896; `db` fx-rates 6; `schemas` all 1 705; `api` fx 21, fx-unit 29, fx-signals 8,
  fx-compress-errors 6, fx-sync 10, signal-catalogs 4, signal-request-validation 2.
- ✅ **Note del coordinatore nel piano** (richieste al checkpoint): migrazione delle impostazioni **007** (§4.4, §5, §6, §7, §9,
  §10, §11); `derive_key(purpose="plugins.settings.v1")` (§4.4, §4.5); regole di H per le variabili d'ambiente (§6, §4.3,
  D-X6); la nota H-3 resta in §4.5.
- ✅ **Backlog**: X-R1 riformulata (il PL4 non la chiude: il testo è in `openapi.json`, segue X-R2); W-B9 con il percorso nuovo
  (`api/v1/fx/providers.py`, `list_providers`) e non chiusa qui: il CP3 è un riordino puro, con test e `openapi.json`
  invariati, quindi propongo al coordinatore un lotto di solo test dopo l'ingresso; X-R4 nuova (il diagramma della guida
  dei plugin FX, segnalata da docs-writer). Nel §6 corretto un percorso degli eventi rimasto dall'analisi
  (`schemas/asset_events.py` → `schemas/assets/events.py`).
- ✅ **`all-backend`** sulla 6183 (04:15:11–04:36:04, 20 min 53 s): 7/7 verdi, **13 754 passati, 28 saltati**, 0 falliti, 0 errori;
  i 23 blocchi sono identici a quelli di `eb245b624` (13 476 / 28) tranne due: `services` 6 921 → 7 186 (+265) e `utils`
  2 208 → 2 221 (+13). La somma, +278, è +273 di H CP3 (la differenza di raccolta già misurata nel controllo leggero, 13 487 →
  13 760) e +5 del CP3 (la guardia `config-package` per file, nel blocco `services`). Porta 6183 libera alla fine
  (`lsof -nP -iTCP:6183 -sTCP:LISTEN` vuoto). Log in `/tmp/libreFolio_x_cp3_allbackend.log`, righe in
  `/tmp/libreFolio_x_cp3_allbackend_counts.txt`.

### Checkpoint CP3 ✅ (2026-10-15) — committato dal coordinatore: `b991d5e26` (codice) e `7639d71d9` (journal)

- **Base**: HEAD `05c21b2b6` (record dell'ingresso del CP2b); `dev_release2` è nel frattempo a `d9b853395` (W K1, lotto
  `web_link_finder` di H).
- **Elenchi**: rinomine pure, nessuna. Tagli: `services/fx/fx.py` → `services/fx/{base,storage,conversion,sync}.py` e
  `api/v1/fx.py` → `api/v1/fx/{__init__,providers,currencies}.py` (2 file tolti, 7 nuovi). Con la soglia di default git
  appaia `fx.py` → `sync.py` (53 %) e `api/v1/fx.py` → `fx/providers.py` (50 %); con `-M95%` nessuna coppia. Nessun file è
  insieme rinominato e tagliato. Modificati 93: 23 nel backend, 18 test, 3 script, 4 in `.github`, 6 pagine MkDocs, 37
  pagine della devWiki, 2 del journal. Totale 102 percorsi (`/tmp/libreFolio_x_cp3_paths.txt`).
- **Conflitti previsti** (simulati con `git merge-file`, a vuoto): con `dev_release2` solo il backlog, che si fonde da solo;
  con J (`b8d604086`) cinque file in comune, tutti fusi da soli: `test_layer_boundaries.py` (J sposta
  `portfolio_allocation_source`, io `fx.fx` → `fx.conversion`, righe diverse della stessa tupla),
  `_backend_services.py`, `financial_math.md`, `financial-math-single-average-cost.md` e il backlog. Nessun riferimento
  nuovo ai vecchi percorsi dei cambi in `dev_release2` né in J (confronto per file e testo con la base). Con A, T, G, R e il
  laboratorio di design solo il backlog. Rischio semantico: codice scritto altrove dopo questa base che importi
  `services.fx.fx` o `api.v1.fx` come modulo cade all'import; i nomi stanno ora nel modulo che li definisce.
- **Mappa per J** (U1, regola 10): `fx.py:717` di U1 è l'inversione in `compute_chain_rate`, ora
  `services/fx/conversion.py:62`; X7 è `services/fx/storage.py:99` (`upsert_rates_bulk`) e `api/v1/fx/currencies.py:129`
  (`upsert_rates_endpoint`); X8 è `api/v1/fx/currencies.py:532` (`convert_currency_bulk`); X6 è
  `services/assets/price_query.py:474-489` dal CP2a.
- **Messaggi di commit proposti**: `refactor(fx): cut FX service and router by theme` (100 percorsi, tutto tranne il journal)
  e `docs(journal): X CP3 log, plan 007 and env rules, backlog X-R1, X-R4, W-B9` (piano e backlog).

> **Fuori pista**:
> - Il riscrittore del CP1, rilanciato a secco, segnalava `from backend.app.services.fx import sync as fx_service`: conosceva
>   come sottomoduli del pacchetto solo `fx` e `registry`. Falso positivo; aggiornata la sua lista (`/tmp`, fuori dal repo).
> - La prima versione della guardia delle patch mute dava 13 falsi positivi sugli asset (letture `core.X` da altri moduli,
>   `DDGS` legato in un `try` di modulo): corretta prima di usarla come prova.

### Quinto aggiornamento di base: W K1, H `web_link_finder`, J CP-1, W4 CP6 — validazione di `d1ef3ddeb` ✅ (2026-10-15) — journal `3f6a2f47e`

Il coordinatore ha committato il CP3 (`b991d5e26`, 100 file, con il suo controllo sull'AST: 32/32 definizioni dei servizi e
20/20 del router identiche) e il journal (`7639d71d9`), poi ha fuso `dev_release2` a `0902524e5` nel mio ramo: HEAD
`d1ef3ddeb` (genitori `7639d71d9` e `0902524e5`). Il merge porta W K1, il lotto `web_link_finder` di H (`config/plugins.py`),
J CP-1 (il PAC per tema, che usa le funzioni dei cambi) e W4 CP6 (il BRIM in `services/brim/`). Unione automatica di 7 file
in comune; worktree pulito. Richiesta: validazione completa sulla 6183, handoff entro le 08:45.

- ✅ **Riscrittori e percorsi vecchi** (`/tmp/libreFolio_x_base5_static.sh`, log `/tmp/libreFolio_x_base5_static.log`):
  riscrittori di CP1, CP2a, CP2b e CP3 a secco a zero (resta il solito `router.py:8`, che usa `fx_router` del pacchetto);
  risoluzione statica degli import su `backend/` e `scripts/` 0 irrisolti su 9 557 nomi (9 541 su `0902524e5`); guardia
  contro le patch mute (C4) 42 patch, nessuna muta (+3 dai test arrivati col merge); nessuna coppia (file, testo) nuova con
  un vecchio percorso di X rispetto a `7639d71d9`.
- ✅ **Stringhe** (nuovo `/tmp/libreFolio_x_base5_strings.py`): ogni `from backend.app… import …` scritto in una stringa,
  ogni `backend.app.x.y` puntato e ogni percorso `.py` del backend citato in una stringa deve risolversi sull'albero. 50
  righe su tutti e due gli alberi, identiche tranne X-R1, che ha cambiato file: sono le forme sintetiche delle guardie
  (`gate_probe_plugins`, i confini dei livelli, il PAC di J), X-R2 e due righe da correggere (sotto, X-R5 e X-R2).
- ✅ **Raccolta** contro `0902524e5` estratto: 13 886 contro 13 881. Le sole differenze sono i 2 → 7 casi della guardia
  `config-package` per file del CP3.
- ✅ **`api schema`** identico a quello di `0902524e5` salvo `info.version` (113 percorsi); `tool-contracts` identico.
  **Sonda delle rotte**: 139 rotte e 63 risoluzioni d'esempio identiche. **Scoperta dei registri** identica: 6 asset, 7 cambi,
  33 BRIM, 23 segnali, 15 rischio, ciascuno dal suo `registry.py`.
- ✅ **Build e `all-backend`** (`/tmp/libreFolio_x_base5_heavy.sh`): `front build --debug` verde (158 s), `mkdocs build` verde
  (45 s, 3 012 URL risolti); `all-backend` sulla 6183 (04:54:41–05:17:16, 22 min 35 s): 7/7 verdi, **13 875 passati, 28 saltati**,
  0 falliti, 0 errori. Dei 23 blocchi cambia solo `services`: 7 186 → 7 307 (+121, e un'unità in più, 122 → 123), pari alla
  differenza di raccolta (13 765 del CP3 → 13 886): 34 da `test_pac_planner_engine_boundaries.py` (nuovo, J CP-1), 82 dalla
  guardia `config-package` per file (572 contro 490 al CP3: i moduli nuovi di J e W4), 5 da altri test modificati dal merge.
  Porta 6183 libera alla fine. Log in `/tmp/libreFolio_x_base5_allbackend.log`, righe in
  `/tmp/libreFolio_x_base5_allbackend_counts.txt`.

> **Fuori pista**:
> - **Residui di testo dei miei lotti (X-R5).** Il grep di questa validazione, più largo di quelli dei lotti (nomi di file
>   nudi come «fx.py», nomi puntati nelle docstring, il frontend, `TODO_FUTURI.md`), trova 16 righe che citano un percorso
>   tolto da CP2a, CP2b o CP3: 5 nel backend (docstring), 9 nel frontend (commenti), 2 in `TODO_FUTURI.md`. Tutte erano già
>   nel mio ramo prima del merge; nessuna è in `openapi.json` né cambia comportamento. I miei grep cercavano le forme
>   d'import e i percorsi completi in `backend/`, `scripts/`, doc, `.github` e devWiki. Elenco e proposta in X-R5:
>   correzione nel CP3b, tranne i due commenti di `AssetModal` (X-R3, FE5).
> - **Una riga di W nella docstring di X-R2.** `db/models.py:127` cita `services/brim_provider.py`, spostato da W nel W4
>   CP6. È nella stessa docstring di X-R2, che finisce in `openapi.json`: l'ho aggiunta a X-R2.

Note del coordinatore per i prossimi lotti, registrate:
- **W-B9** approvata come lotto di soli test (CP3b), dopo l'ingresso del CP3 e prima del CP4; **W-B13** (la ✕ di
  `fx-csv-import.spec.ts:247` e `:276`, col `data-testid` `data-import-modal-close`) passata nella mia sezione, nello stesso
  lotto.
- Da H, sul `web_link_finder`: valori di `_TIMEOUT` e `_MAX` non validati (X-R6, con il CP6 o il CP10, d'accordo con H).
- Doc: `provider_borsa_italiana.md:123` senza `_FILE` (X-R7, nel CP3b). Le mie variabili d'ambiente nuove vanno in
  `config/plugins.py`.
- Preparando il CP3b: `GET /fx/providers` va alla BCE a ogni richiesta, senza cache (X-R8, prodotto). Il W-B9 è più largo
  del solo test 1: anche `test_get_providers` (`test_fx_api.py:175`) vuole valute per ogni fornitore, e i suoi controlli del
  filtro usano la BCE (`:186`, `:199`); la verifica dal vivo della BCE c'è già in
  `test_external/test_fx_providers.py::test_supported_currencies`.

### Sesto aggiornamento di base: A4 — controllo leggero di `9a3ba752a` ✅ (2026-10-15)

Il coordinatore ha committato il journal della validazione precedente (`3f6a2f47e`) e fuso `dev_release2` a `be2ad6573`
(A4: migrazione 005, `account_tokens`, `services/accounts/token_service.py`): HEAD `9a3ba752a` (genitori `3f6a2f47e` e
`be2ad6573`), unione automatica (backlog e `_backend_services.py`), worktree pulito. Richiesta: controllo leggero, senza
`all-backend`, poi l'ingresso del CP3. Script `/tmp/libreFolio_x_base6_static.sh` (quello del quinto aggiornamento, con i
nuovi riferimenti), log `/tmp/libreFolio_x_base6_static.log`.

- ✅ `services config-package` sulla 6183: **573 passati** = 572 su `d1ef3ddeb` + 1, il caso di
  `services/accounts/token_service.py` (A4). Contro `be2ad6573` estratto (568 casi raccolti) il +5 è il CP3 (−2 file tolti,
  +7 moduli nuovi).
- ✅ Raccolta: 13 976 contro 13 971 di `be2ad6573`; la differenza è la stessa, i casi 2 → 7 della guardia.
- ✅ `api schema` identico a quello di `be2ad6573` salvo `info.version` (113 percorsi); `tool-contracts` identico.
- ✅ Oltre la richiesta, perché costano poco: riscrittori a secco a zero (resta `router.py:8`); 0 import irrisolti su 9 585
  nomi; 42 patch, nessuna muta; scanner delle stringhe uguale sui due alberi salvo X-R1; nessun riferimento nuovo ai vecchi
  percorsi rispetto a `3f6a2f47e`; sonda delle rotte identica (139 rotte, 63 richieste); scoperta dei registri identica.
- Porta 6183 libera prima e dopo.

Decisioni del coordinatore sul CP3b (15/10, ~05:20):
- **W-B9**: sì, come proposto. Contratto e filtri su FED, BOE e SNB; le chiamate senza filtro controllano solo i codici; la
  BCE dal vivo solo in `test_external`. **W-B13**: sì.
- **X-R5**: sì per le docstring del backend, i commenti del frontend fuori da `AssetModal`, il commento di
  `auth.test.ts:574` (lo dice il coordinatore ad A) e le 2 righe di `TODO_FUTURI.md`. **No** per le 3 fixture della galleria
  (di G, nella finestra): le gira il coordinatore al coordinatore colori — `frontend/e2e/fixtures/galleryOfflineData.ts:62`
  (`api/v1/fx.py` → `api/v1/fx/providers.py`), `galleryProviderCompare.ts:40` e `galleryReportSets.ts:398`
  (`asset_sources/search.py` → `services/assets/search.py`).
- **X-R7**: sì.
- **X-R8, proposta del coordinatore** (il developer può cambiarla): una cache dell'elenco delle valute dei fornitori,
  valida 24 ore; se la BCE non risponde si usa l'ultimo elenco noto, con un timeout breve. In un mio lotto dopo il CP3b.

### CP3 in `dev_release2` ✅ (2026-10-15)

Avanzamento veloce di `dev_release2` a `8000aba5a` (il journal del sesto aggiornamento sopra `9a3ba752a`), record del
coordinatore `5d21f2d85`; il mio ramo è avanzato lì, worktree pulito. Le 3 fixture della galleria le ha girate il
coordinatore al coordinatore colori.

### CP3b — test dei cambi senza rete e residui di testo ✅ (2026-10-15)

Via del coordinatore alle ~05:25, nel perimetro deciso: W-B9, W-B13, X-R5 (tranne `AssetModal` e le fixture di G), X-R7.
Base: HEAD `5d21f2d85`. Nessun file del backend dell'app cambia comportamento; `openapi.json` deve restare identico.

Passi:
1. ✅ Prova a vuoto della rete: `api fx` con `HTTP(S)_PROXY` su una porta chiusa (localhost escluso), prima delle modifiche,
   per vedere quali test dipendono dalla rete.
   > **Note implementazione**: `env HTTP_PROXY=… HTTPS_PROXY=… ALL_PROXY=…` (anche in minuscolo) `=http://127.0.0.1:9`,
   > `NO_PROXY=localhost,127.0.0.1,::1`, poi `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
   > --test-port 6183 --data-dir /tmp/librefolio-r13-x api fx` (05:27–05:28): **2 falliti, 19 passati**. Rossi
   > `test_providers_include_target_currencies` («Provider ECB should have at least one target currency», `:126`) e
   > `test_get_providers` («Provider should have target_currencies», `:175`); gli altri 19 non dipendono dalla rete (la
   > creazione delle rotte con ECB non chiama il fornitore, e i sync usano MOCKFX). httpx sul server rispetta le variabili del
   > proxy: è la prova che il server è rimasto senza rete. Log `/tmp/libreFolio_x_cp3b_offline_before.log`.
2. ✅ X-R5: i commenti e le docstring nel perimetro deciso (io).
   > **Note implementazione**: 13 righe in 9 file, sostituzioni sul posto (Prettier ha `printWidth` 300, nessun ritorno a
   > capo): docstring di `scheduled_investment/plugin.py:33-34` (→ `schemas.assets.assets`), `services/assets/core.py:15`
   > (→ `services/fx/`), `test_fx_compress_errors.py:1` (→ `api/v1/fx/currencies.py`), `test_fx_core.py:5` (→
   > `services/fx/` `storage.py`, `sync.py`); commenti di `e2e/assets/asset-modal.spec.ts:526` (→
   > `services/assets/provider_management.py`, dove c'è «provider changed», `:134`), `ScheduledInvestmentEditor.svelte:75`,
   > `:81`, `:89` (→ `schemas/assets/assets.py`), `auth.test.ts:574` di A (→ `api/v1/assets/crud.py`, il 409 con `error_code`
   > in `detail`, `:139-146`), `fxRoutesStore.test.ts:8` (→ `services/fx/sync.py`, che salva il tasso composto su
   > `route.base/route.quote`, `:728`); `TODO_FUTURI.md:1121` e `:2067`. Restano, come deciso: X-R1, X-R2, `AssetModal`
   > (X-R3) e le 3 fixture di G; `schemas/fx.py` esiste ancora, e `TODO_Completati.md:202` è storia.
3. ✅ X-R7: la riga di `provider_borsa_italiana.md` (docs-writer).
   > **Note implementazione**: `provider_borsa_italiana.md:123` non ripete più le variabili: rimanda a
   > [Asset Search & Link-Finder](search_link_finder.md#configuration-env-vars-all-optional), che le elenca tutte, compresa
   > `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE`, e dice che si leggono in `backend/app/config/plugins.py`. docs-writer ha
   > controllato l'ancora nell'HTML costruito (en, it, fr, es): MkDocs segnala le ancore sbagliate solo come INFO.
   > `mkdocs build` stretto verde (3 012 URL), `check-links` 95 validi, 0 rotti. Pagina senza traduzioni: nessun timbro.
4. ✅ Una sola build del frontend (le modifiche in `frontend/src` la rendono vecchia) e di MkDocs, prima dei test.
   > **Note implementazione**: `dev.py front build --debug` 05:30:55–05:32:27, rc 0, dopo le modifiche di X-R5 in
   > `frontend/src` (`scripts/cli_base.py`, `check_frontend_needs_build`: conta ogni file di `frontend/src` più nuovo della
   > build; `frontend/e2e` no, quindi W-B13 non la invecchia). MkDocs ricostruito da docs-writer dopo X-R7 (il sito va in
   > `mkdocs_src/site`, separato da `frontend/build`: le due build potevano sovrapporsi).
5. ✅ W-B9 e W-B13 (test-author).
   > **Note implementazione**: `test_fx_api.py`: due costanti (`_STATIC_FX_PROVIDERS = ("FED", "BOE")`,
   > `_PUBLIC_FX_PROVIDERS`) con il perché in commento; `test_providers_include_target_currencies` chiede l'elenco filtrato
   > sui fornitori statici, vuole esattamente quei codici e tiene i controlli per fornitore di prima; `test_get_providers`
   > sposta il contratto completo su una chiamata filtrata (2a), prova i filtri con FED e con FED + BOE (2b, 2c), e le chiamate
   > senza filtro (la prima e 2d) controllano solo che ci siano i codici pubblici ECB, FED, BOE, SNB (sottoinsieme, mai un
   > conteggio). `test_manual_provider_hidden_from_list` è rimasto com'era; `TIMEOUT` invariato. `fx-csv-import.spec.ts:247` e
   > `:276`: `modal.getByTestId('data-import-modal-close')`. Prove di test-author: `api fx` senza rete 21/21, `api fx` normale
   > 21/21, `front-fx fx-csv-import` 21/21 (log `/tmp/libreFolio_x_cp3b_ta_*.log`).

> **Fuori pista**:
> - **La SNB non ha un elenco statico: l'errore era mio.** Nell'handoff della validazione di `d1ef3ddeb` ho scritto che FED,
>   BOE e SNB hanno elenchi statici, e il coordinatore ha deciso su quella base. Il mio controllo guardava solo il corpo di
>   `get_supported_currencies` (nessuna chiamata HTTP); la SNB però passa da `_ensure_currency_map()`
>   (`fx_providers/snb/plugin.py:139-149`), che scarica la mappa delle valute da data.snb.ch con 15 s di timeout e la tiene
>   in memoria solo se riesce. test-author l'ha trovato: con FED, BOE e SNB come deciso, `api fx` senza rete dà ancora 2
>   rossi, tutti e due sulla SNB (`/tmp/libreFolio_x_cp3b_ta_offline_literal_snb.log`; nel log del server, `Failed to fetch
>   target currencies for SNB … All connection attempts failed`, già presente nella mia prova a vuoto, dove però l'ECB
>   veniva prima in ordine alfabetico). Ha tenuto il principio della decisione (solo fornitori statici, nessuna rete) e
>   ristretto a FED e BOE; la SNB dal vivo è già in `test_external/test_fx_providers.py::test_supported_currencies`.
>   **Scostamento dalla decisione: confermato dal coordinatore il 15/10** («la regola era nessuna rete nei test, e la SNB
>   dal vivo resta coperta in `test_external`»).
> - La SNB cade anche nel residuo X-R8: senza filtro il server la interroga finché non riesce una volta nel processo.
> - Nella stessa spec restano quattro selettori in inglese (`:233`, `:234`, `:250`, `:261`), fuori dal perimetro di W-B13:
>   registrati come X-R9.
6. ✅ Verifica: `api fx` di nuovo senza rete, `api schema` identico, lint, test mirati, journal e handoff.
   > **Note implementazione** (`/tmp/libreFolio_x_cp3b_verify.sh`, 05:44–05:45, log `/tmp/libreFolio_x_cp3b_verify.log`):
   > `api schema` identico a quello di `be2ad6573` salvo `info.version` (113 percorsi), `tool-contracts` identico; scoperta
   > dei registri identica (6 / 7 / 33 / 23 / 15); **`api fx` senza rete 21/21** (prima delle modifiche 19/21); `api
   > fx-compress-errors` 6; `services fx-core` 23; vitest `front-user user-unit` 78 (con `auth.test.ts`) e `front-utility
   > core-unit` 4 266 (con `fxRoutesStore.test.ts`); `ruff` e `black --check` puliti sui 5 file Python; Prettier pulito sui 5
   > file del frontend; `git diff --check` pulito; porta 6183 libera.

### Checkpoint CP3b ✅ (2026-10-15) — committato dal coordinatore: `cea5ce859` (codice, 12 file) e `cc242dee8` (journal)

- **Base**: HEAD `5d21f2d85`.
- **Elenchi**: nessuna rinomina, nessun taglio. 14 file modificati, nessuno nuovo:
  - test: `backend/test_scripts/test_api/test_fx_api.py` (W-B9), `frontend/e2e/fx/fx-csv-import.spec.ts` (W-B13);
  - commenti e docstring (X-R5): `backend/app/services/asset_source_providers/scheduled_investment/plugin.py`,
    `backend/app/services/assets/core.py`, `backend/test_scripts/test_api/test_fx_compress_errors.py`,
    `backend/test_scripts/test_services/test_fx_core.py`, `frontend/e2e/assets/asset-modal.spec.ts`,
    `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte`, `frontend/src/lib/stores/app/auth.test.ts` (di A),
    `frontend/src/lib/stores/reference/fxRoutesStore.test.ts`, `TODO_FUTURI.md` (del developer, 2 righe);
  - doc (X-R7): `mkdocs_src/docs/developer/backend/assets/provider_borsa_italiana.md`;
  - journal: il piano e il backlog.
- **Commit proposti**: `test(fx): keep FX provider tests offline, fix stale module paths` (12 file: tutto tranne il journal)
  e `docs(journal): X CP3b log, backlog W-B9, W-B13, X-R5, X-R7 closed, X-R9` (piano e backlog).

### Settimo aggiornamento di base: W7 — controllo minimo di `7d6710fd0` ✅ (2026-10-15)

Il coordinatore ha fuso `dev_release2` a `58be885a9` (W7: `schemas/transactions/` per tema) nel mio ramo: HEAD `7d6710fd0`
(genitori `cc242dee8` e `58be885a9`), merge pulito, nessun file in comune. Controllo minimo sulla 6183
(`/tmp/libreFolio_x_base7.sh`, 05:49–05:53, log `/tmp/libreFolio_x_base7.log`):
- ✅ Raccolta contro `58be885a9` estratto: 13 981 contro 13 981, nessuna differenza (il CP3 è già in `dev_release2`, e il CP3b
  cambia i corpi dei test, non i loro nomi).
- ✅ `front build --debug` (89 s) e `mkdocs build` (36 s, 3 012 URL) prima dei test: W7 tocca un file di `frontend/src` e uno
  di `mkdocs_src`, e il server li avrebbe ricostruiti dentro il suo limite d'avvio.
- ✅ `api fx` 21/21; `api fx` senza rete (proxy su `127.0.0.1:9`) 21/21.
- Worktree pulito dopo le build; porta 6183 libera.

Decisioni del coordinatore (15/10, ~05:49):
- W-B9 con FED e BOE: confermato.
- **CP4 (schemi) prima di X-R8**: il riordino viene prima. Durante la finestra della galleria si scrive il codice;
  `all-backend` dopo l'avviso di fine. W7 ha già messo `schemas/transactions/` per tema: è la forma da seguire.
- **X-R9 con il FE4**; i test-id in `DataImportModal.svelte` il coordinatore li chiede a W, che ne è il proprietario.
- La nota su `tx-bulk-operations.spec.ts:428` la scrive il coordinatore nella sezione di W, come W-B15.

### CP3b in `dev_release2` ✅ (2026-10-15)

Avanzamento veloce di `dev_release2` a `63a1f675c` (il journal del settimo aggiornamento), record del coordinatore
`c81670354` (con W-B15 nella sezione di W); il mio ramo è avanzato lì, worktree pulito.

### CP4 — gli schemi degli asset per tema (C3) ✅ (2026-10-15)

Via del coordinatore alle ~05:55 («gli schemi di asset e cambi, nella forma C3 di W7»). Durante la finestra della galleria
solo codice; `all-backend` prima delle 08:45 o dopo l'avviso di fine. Base: HEAD `c81670354`.

**Perimetro.** C3 e il piano 43 (P2.2, riga dei moduli di schemi «da 2 522 a 1 000») dividono i moduli di schemi da ~1 000
righe in su: fra i miei c'è solo `schemas/assets/assets.py` (1 001 righe, 28 nomi). Il resto è sotto soglia e resta dov'è:
`schemas/fx.py` (500), `provider.py` (438, con `FXProviderInfo`), `prices.py` (370), `refresh.py` (245, FA e FX). La rinomina
in pacchetto l'ha già fatta il CP2b (`schemas/assets.py` → `schemas/assets/assets.py`); qui solo tagli, come il secondo
commit di W7 (`e28aad42f`). Nessuna dipendenza circolare fra i temi (analisi `/tmp/libreFolio_x_cp4_deps.py`).

**Forma d'arrivo** (`schemas/assets/`, `__init__.py` con la sola docstring, mappa dei moduli):
- `assets.py` (C1, resta): `FAAssetProviderAssignment`, creazione, lettura (`FAAinfoFiltersRequest`, `FAinfoResponse`),
  cancellazione, `PATCH`, unione; importa `FAClassificationParams` da `metadata.py`.
- `metadata.py` (nuovo): `BaseDistribution`, `FAGeographicArea`, `FASectorArea`, `FAClassificationParams`,
  `FAAssetMetadataResponse`, `FAMetadataRefreshResult`, `FABulkMetadataRefreshResponse` (il nome segue
  `services/assets/metadata.py`).
- `scheduled_investment.py` (nuovo): `MaturationFrequency`, `DayCountConvention`, `InterestType`, `FAInterestRatePeriod`,
  `FALateInterestConfig`, `FAScheduledInvestmentSchedule` (il nome segue il fornitore `scheduled_investment`).
- `events.py`: di W, intatto.
- Via l'`__all__` di `assets.py`: ripeteva anche 5 nomi di altri moduli (`BackwardFillInfo`, `FACurrentValue`, `FAPricePoint`,
  `FAHistoricalData`, `FAAssetEventPoint`), cioè faceva da barile (C3: niente barili). Nessun `import *`, e i moduli di
  W7 non hanno `__all__`.
- Hub `schemas/__init__.py`: blocco `TYPE_CHECKING`, `_EXPORT_GROUPS` (`assets.assets` si divide in `assets.assets` e
  `assets.metadata`) e docstring; `__all__` per nome, invariato. I nomi del calendario non sono esportati dall'hub.

Passi:
1. ✅ Basi a HEAD: `openapi.json`, `tool-contracts`, raccolta, impronta AST delle 27 definizioni.
   > **Note implementazione**: `/tmp/libreFolio_x_cp4_baseline.sh` (05:59), in `/tmp/libreFolio_x_cp4_base/`: raccolta 13 981,
   > 27 classi impresse con `ast.dump`, `openapi.json` e `tool-contracts` copiati.
2. ✅ Taglio (`/tmp/libreFolio_x_cp4_split.py`): ogni definizione si sposta intatta col commento che la precede; ogni modulo
   con i suoi import (poi `ruff --select F401,I --fix`).
   > **Note implementazione**: lo script verifica da sé che le 27 classi escano identiche all'impronta (stesso `ast.dump`) e
   > che ogni nome finisca in un solo modulo. Dopo ruff (47 import tolti o riordinati) e black (nessun cambio):
   > `scheduled_investment.py` 279 righe (6 definizioni), `metadata.py` 309 (7), `assets.py` 397 (14, da 1 001). Ogni modulo
   > ha una docstring nuova con la sua mappa; `assets.py` tiene le note di nomi e di disegno ancora vere e perde quelle
   > dei temi andati via. Prova di fumo: i 24 modelli Pydantic dei tre moduli producono il loro JSON Schema (riferimenti in
   > avanti risolti con `from __future__ import annotations`). Dipendenze fra temi: `assets` → `metadata`
   > (`FAClassificationParams`); `scheduled_investment` → `events` (`FAAssetEventPoint`, di W, solo import).
3. ✅ Hub e docstring del pacchetto.
   > **Note implementazione**: `schemas/__init__.py`: blocco `TYPE_CHECKING` diviso (`assets.assets` 11 nomi, nuovo
   > `assets.metadata` 7), `_EXPORT_GROUPS` uguale, docstring dell'elenco dei moduli; `__all__` invariato. Controllo:
   > coppie (modulo, nome) del `TYPE_CHECKING` = quelle di `_EXPORT_GROUPS`; 190/190 nomi esportati risolvibili;
   > `__all__` contenuto negli export. `schemas/assets/__init__.py`: mappa dei quattro moduli.
4. ✅ Import dei 40 file (`/tmp/libreFolio_x_cp4_rewrite.py`, ogni nome al modulo che lo definisce) e casi a mano.
   > **Note implementazione**: 20 istruzioni in 20 file (gli altri 20 importatori usano solo nomi rimasti in `assets.py`),
   > nessun caso a mano; `ruff --select I --fix` ne ha riordinati 6. File di altri, una riga ciascuno: `db/models.py`
   > (import locale di `FAClassificationParams`), `ai_export/components/asset_resources.py` e `risk/service.py` di J. Il
   > riscrittore rilanciato a secco dà 0; risoluzione statica 0 irrisolti su 9 600 nomi. `api schema`: `openapi.json`
   > identico (113 percorsi, 586 schemi), `tool-contracts` identico (160 schemi).
5. ✅ Riferimenti: docstring e commenti nel codice, `.github`, MkDocs, devWiki (C6), `TODO_FUTURI.md:1121`.
   > **Note implementazione**: 21 righe citavano il vecchio modulo; corrette quelle sui nomi spostati, lasciate quelle sui
   > nomi rimasti (F-095 e F-114 della devWiki, le due pagine dei problemi: cancellazione, filtro, `PATCH`,
   > `FAinfoResponse`). Codice: docstring di `scheduled_investment/plugin.py:33-34` (`schemas.assets.scheduled_investment`) e
   > di `utils/asset/geo.py:5` (`metadata.py`); commenti di `populate_mock_data.py:1043`,
   > `ScheduledInvestmentEditor.svelte:75`, `:81`, `:89`; docstring di `test_asset_schemas.py:9` e la stampa del runner
   > `_backend_schemas.py:39` (le tre fonti). devWiki (C6): F-029 (`FAAssetMetadataResponse` → `metadata.py`) e F-096, riga
   > della tabella e prosa (`FAInterestRatePeriod` → `scheduled_investment.py`); `check_source_paths` ai soliti 5 artefatti.
   > `.github/instructions/backend-schemas.instructions.md`: l'albero mostra il pacchetto `assets/` coi suoi quattro moduli.
   > `TODO_FUTURI.md:1121` di nuovo (la riga di X-R5 ora punta a `scheduled_investment.py`). MkDocs (docs-writer):
   > `assets_pricing.md:66-67` (righe in `metadata.py`) e `lint_gates.md`, dove le eccezioni RUF022 scendono da 4 a 3 perché
   > `assets.py` non ha più `__all__`.
   > Controlli: raccolta 13 983 contro 13 981 (+2: i casi della guardia `config-package` per i due moduli nuovi); scanner
   > delle stringhe senza righe nuove (spariscono le 2 vecchie della docstring del fornitore; l'unica in più,
   > `test_brim_report_sets.py:3134`, è un `git show v1.1.0:…`, storico e giusto); guardia delle patch mute 42, nessuna
   > muta; `schemas all` 1 705.
6. ✅ Verifiche: identità AST, ruff e black, `api schema` e `tool-contracts` identici, raccolta, import, stringhe, patch mute,
   suite mirate, `all-backend`; journal e handoff.
   > **Note implementazione**: identità AST sui file finali (dopo ruff e black) 27/27 classi (14 `assets`, 7 `metadata`,
   > 6 `scheduled_investment`); `ruff check` e `black --check` puliti sui 28 file Python toccati, Prettier sullo `.svelte`;
   > `openapi.json` (586 schemi) e `tool-contracts` (160) identici a HEAD salvo la versione; raccolta 13 983 (+2, la guardia
   > `config-package`); 0 import irrisolti su 9 600; nessuna patch muta; `schemas all` 1 705. Build e run completa
   > (`/tmp/libreFolio_x_cp4_heavy.sh`): `front build --debug` 85 s, `mkdocs build` 34 s, **`all-backend` sulla 6183
   > 06:10:32–06:31:13, 7/7, 13 972 passati, 28 saltati**, 0 falliti. Il +97 sui 13 875 della mia ultima run completa (su
   > `d1ef3ddeb`) è la differenza di raccolta (13 886 → 13 983: A4 +90, W7 +5, CP4 +2): +72 nel blocco `services` e un
   > blocco nuovo di 25 arrivato con gli aggiornamenti di base. Porta 6183 libera; `git diff --check` pulito. Log
   > `/tmp/libreFolio_x_cp4_allbackend.log`, righe `/tmp/libreFolio_x_cp4_allbackend_counts.txt`.

> **Fuori pista**:
> - **Un commento di `pyproject.toml`** (file condiviso) contava ancora 4 barili RUF022 con `schemas/assets`: corretto a 3,
>   come `lint_gates.md` (segnalato da docs-writer). Nessun effetto sulla configurazione.
> - docs-writer ha corretto anche la riga 27 di `lint_gates.md` («with 4 deliberate exceptions»), fuori dalla sezione
>   indicata: tenuta, perché la pagina altrimenti diceva 4 in cima e ne elencava 3.
> - Nell'albero di `.github/instructions/backend-schemas.instructions.md` la riga `transactions.py` non esiste più dopo W7
>   (`schemas/transactions/`): è di W, non toccata; segnalata al coordinatore.
> - Un file `frontend/src/lib/api/.tools-codegen.lock` compare durante la build del frontend e sparisce alla fine
>   (`frontend/scripts/tools-generation-io.mjs:94`): non è un artefatto da escludere.

### Checkpoint CP4 ✅ (2026-10-15) — in `dev_release2` come `7f4618494` (merge del mio `805f2f112`), record `786f3e216`

- **Base**: HEAD `c81670354`; `dev_release2` nel frattempo a `6d67fdaac` (J C-93, H CP4): nessun file in comune, nessun import
  nuovo dei nomi spostati (55 coppie su tutti e due gli alberi).
- **Elenchi**: rinomine pure, nessuna. Tagli: `schemas/assets/assets.py` → `assets.py` + `metadata.py` + `scheduled_investment.py`
  (2 file nuovi; `assets.py` resta, da 1 001 a 397 righe). Modificati 35, compreso il piano: 20 file con le sole righe
  d'import (3 di altri: `db/models.py`, `ai_export/components/asset_resources.py` e `risk/service.py` di J), l'hub e
  `schemas/assets/__init__.py`, 6 di commenti e docstring (`scheduled_investment/plugin.py`, `utils/asset/geo.py`,
  `populate_mock_data.py`, `test_asset_schemas.py`, `_backend_schemas.py`, `ScheduledInvestmentEditor.svelte`),
  `TODO_FUTURI.md` (1 riga), `pyproject.toml` (commento), `.github` 1, MkDocs 2, devWiki 2.
- **Messaggi di commit proposti**: `refactor(schemas): split asset schemas by theme` (36 percorsi: tutto tranne il piano) e
  `docs(journal): X CP4 log` (il piano).

Il coordinatore ha integrato il CP4 con un merge (`7f4618494`): nel frattempo erano entrati J C-93, H CP4 e J G-8, senza
file in comune; il suo controllo sull'AST: 49/49 nomi identici, tolto solo `__all__`. `schemas/fx.py` resta intero (sotto
soglia): niente lotto di simmetria. La riga `transactions.py` dell'albero delle istruzioni la gira lui a W. Il mio ramo è
avanzato a `786f3e216`, che porta J-5 nella mia sezione del backlog.

### J-5 — `_run_provider_in_thread` non lascia un loop chiuso come corrente ✅ (2026-10-15)

Via del coordinatore alle ~06:34 («una riga più il test di test-author; poi X-R8»). Base: HEAD `786f3e216`.

**Il difetto** (triage di J, piano 05 §10 «C-93»): `services/assets/core.py:114-119`, `_sync_runner` (dentro
`asyncio.to_thread`), crea un loop, lo imposta come corrente, lo chiude e non lo toglie. Nel thread dell'executor resta
così un loop chiuso come corrente: una connessione aiosqlite raccolta dal GC in quel thread crea il suo future con
`asyncio.get_event_loop()`, lo lega al loop chiuso e muore con «Event loop is closed» (`PytestUnhandledThreadExceptionWarning`
attribuito a un test estraneo). Nel backend è l'unico punto che lo fa.

**La cura**: `asyncio.set_event_loop(None)` nel `finally`, prima di `loop.close()`, come fa `asyncio.Runner.close()`.

Passi:
1. ✅ Test (test-author) in `test_utilities/test_provider_core_cache.py`, classe `TestRunProviderInThread`: dopo una
   chiamata, il thread che l'ha eseguita non ha un loop chiuso come corrente. Rosso sul codice di oggi.
   > **Note implementazione**: `test_worker_thread_does_not_keep_closed_event_loop` (righe 267–315). Il thread si fissa con
   > un `ThreadPoolExecutor(max_workers=1)` privato: `asyncio.to_thread` è sostituito, solo per quella chiamata
   > (`monkeypatch.context()`), con il suo stesso corpo su quell'executor; una sonda prima e una dopo nello stesso thread
   > (verificato, non supposto: il fornitore e le due sonde registrano il thread). L'executor di default del loop del test
   > non c'entra. Asserzione stretta: nessun loop corrente, come il thread era stato trovato. **Rosso sul codice di oggi**:
   > 1 fallito, 28 passati, «pinned-provider_0 still has <_UnixSelectorEventLoop running=False closed=True …> as its current
   > loop» (`/tmp/libreFolio_x_j5_ta_red_current.log`).
2. ✅ La riga in `core.py`; il test diventa verde.
   > **Note implementazione**: `asyncio.set_event_loop(None)` nel `finally` di `_sync_runner`, prima di `loop.close()`
   > (`core.py:120`). `utils provider-core-cache` 29/29 (`/tmp/libreFolio_x_j5_green.log`); ruff e black puliti.
3. ✅ Verifiche: `utils provider-core-cache`, ruff e black, i test dei chiamanti; journal e handoff.
   > **Note implementazione**: la riga sta nel percorso di ogni chiamata ai fornitori (prezzi, storico, metadati, ricerca),
   > quindi la run completa: `front build --debug` (97 s) e `mkdocs build` (47 s), resi vecchi dall'integrazione del CP4 (14
   > file di `frontend/src`, 8 di MkDocs, il CHANGELOG), poi **`all-backend` sulla 6183, 06:46–07:08, 7/7, 14 003 passati,
   > 29 saltati**, 0 falliti (`/tmp/libreFolio_x_j5_heavy.sh`, log `/tmp/libreFolio_x_j5_allbackend.log`). Rispetto al CP4
   > (13 972 / 28) il +32 è la differenza di raccolta (13 983 → 14 015, +33 −1): il mio test più 32 arrivati con
   > l'aggiornamento di base (H CP4: `test_system_api` 8, `test_config_misc` 8, 7 casi della guardia `config-package`,
   > uno tolto, `api/v1/system.py`; `test_tools_api` 5; J: 4 in `test_ai_export_components_portfolio_broker_integration`).
   > Il saltato in più è `test_external/test_asset_providers.py::test_current_value[css_scraper]`: la pagina di Borsa
   > Italiana senza prezzo («market closed or in Call status», 07:00), dipende dall'ora, non dalla riga. Porta 6183 libera.

### Checkpoint J-5 ✅ (2026-10-15) — `7794e2fb0` (codice) e `cb0bac88d` (journal), in `dev_release2` col merge `743fca514`, record `4fdc0d9c5`

- **Base**: HEAD `786f3e216`.
- **Elenchi**: nessuna rinomina, nessun taglio, nessun file nuovo. Modificati 4: `backend/app/services/assets/core.py` (1 riga),
  `backend/test_scripts/test_utilities/test_provider_core_cache.py` (il test e 4 import), il piano e il backlog (J-5 chiusa).
- **Messaggi di commit proposti**: `fix(assets): unset the provider thread's closed event loop` (i 2 file di codice) e
  `docs(journal): X J-5 log, W agreements` (piano e backlog).

> **Accordi con W, comunicati dal coordinatore il 15/10 (~07:00), da rispettare nel FE5:**
> - Lotto E1b degli eventi (dopo le decisioni 20–23 del developer): W modifica in
>   `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` il salvataggio degli eventi (righe 349–438: prima le
>   cancellazioni, poi gli upsert; `asset_id` nella cancellazione; la valuta della riga quando c'è; la conferma per gli
>   eventi collegati) e il toast d'errore con il `detail` (461–466). Finché il lotto non entra, quelle righe non le tocco.
> - Lotto E0 (dopo la finestra della galleria): W scrive in `frontend/src/lib/components/assets/EventDataImportModal.svelte:38`
>   `matchKey: true` sulla colonna `type`, così che i doppioni del CSV degli eventi siano solo le righe con stessa data e
>   stesso tipo (I-11a). Prezzi, cambi e distribuzioni non cambiano.
> Nessuna obiezione da parte mia: non ho modifiche previste su quelle righe.

### X-R8 — l'elenco delle valute dei fornitori dei cambi in cache ✅ (2026-10-15)

Via del coordinatore alle ~07:13: disegno approvato così com'è («nessun cambio all'API; la cache con nome si vede nel
pannello delle cache»). Finestra della galleria dalle 09:00 (~2 ore): lì solo codice, la run completa prima delle 08:45 o
dopo l'avviso di fine. Base: HEAD `4fdc0d9c5`.

**Il problema** (X-R8): `list_providers` (`GET /fx/providers`, `api/v1/fx/providers.py:96-101`) chiama
`get_supported_currencies` di ogni fornitore pubblico a ogni richiesta. La BCE fa una richiesta HTTP senza cache (30 s di
timeout), la SNB finché non riesce una volta nel processo (15 s): ogni apertura dell'elenco li aspetta, e senza rete
compaiono con zero valute. È l'unico chiamante dell'app.

**Disegno** (nuovo modulo `services/fx/catalog.py`, una funzione che `list_providers` usa al posto della chiamata diretta):
- cache con nome `fx_provider_currencies` (`get_ttl_cache`, chiave il codice del fornitore): un elenco riuscito vale 24 ore;
- se il fornitore fallisce o va oltre il timeout breve (5 s, `asyncio.wait_for`), si risponde con l'ultimo elenco noto
  nel processo (vuoto prima del primo successo) e lo si mette in cache per 5 minuti, così che senza rete l'elenco non
  aspetti a ogni richiesta; poi si riprova. `NamedCache.set` accetta un TTL per voce: una sola cache;
- l'ultimo elenco noto resta anche dopo uno svuotamento dal pannello delle cache;
- un lock per fornitore contro le richieste simultanee a cache vuota, tenuto per loop (`WeakKeyDictionary`), perché un
  `asyncio.Lock` conteso resta legato al suo loop;
- nessun cambio all'API: stessa risposta, stesso `openapi.json`.

Passi:
1. ✅ `services/fx/catalog.py` e il collegamento in `list_providers`.
   > **Note implementazione**: `get_supported_currencies_cached(code, provider, *, timeout=5.0)`, ~60 righe; la chiave è il
   > codice del registro, che `list_providers` ha già (un fornitore finto di `test_fx_api_unit.py` non ha `code`, ed è il
   > registro a dare l'identità). In `list_providers` la chiamata diretta e il suo `try/except` lasciano il posto a una riga;
   > `services/fx/__init__.py` elenca `catalog.py`. Prova di fumo fuori dal repository (`/tmp/libreFolio_x_r8_smoke.py`):
   > due richieste, una chiamata; fallimento senza storia `[]` e nessun nuovo tentativo per 5 minuti; fallimento dopo un
   > successo, l'ultimo elenco; timeout 0,2 s rispettato; 10 chiamate simultanee, una sola al fornitore, anche in un secondo
   > loop; cache registrata. `api schema` identico a HEAD (`openapi.json` 114 percorsi, `tool-contracts`); ruff e black
   > puliti.
2. ✅ Test senza rete (test-author).
   > **Note implementazione**: `test_services/test_fx_catalog.py`, 8 test con fornitori finti e una fixture autouse che
   > svuota cache e ultimi elenchi prima e dopo: copie, fallimento senza storia e attesa di 5 minuti, ultimo elenco anche
   > dopo uno svuotamento, timeout, una sola chiamata con 8 chiamanti simultanei (con un cancello che si apre quando tutti
   > hanno trovato la cache vuota) anche in un secondo loop, cache nel pannello, TTL chiesto per un elenco (24 h) e per un
   > ripiego (5 min) letto da un involucro della cache vera. test-author ha provato che i test del lock possono cadere
   > (senza lock: «8 fetches for 8 concurrent callers»; un lock unico fra due loop: «bound to a different event loop»),
   > poi ha tolto le due mutazioni. Azione nuova `services fx-catalog` in `_backend_services.py` (pura). In
   > `test_fx_api_unit.py` la fixture `fed_currencies_not_cached` toglie la voce `FED` prima e dopo
   > `test_list_providers_filters_hidden_and_sorts_targets`, che ora passa dalla cache del processo. `services fx-catalog`
   > 8/8, `api fx-unit` 29/29.
3. ✅ Doc (docs-writer): la tabella delle cache in `settings_cache.md`, le pagine dei cambi.
   > **Note implementazione**: cinque pagine per sviluppatori, nessuna con traduzioni. `settings_cache.md`: riga
   > `fx_provider_currencies` (32, 24 h, `fx/catalog.py`, il ripiego 5 min) e data del registro (le altre 17 righe
   > ricontrollate); una frase sugli ultimi elenchi, che nessuno svuotamento toglie. `fx_plugin_guide.md`: contratto di
   > `get_supported_currencies()` (Mermaid, paragrafo della fase 1, tabella, esempio): passa da `catalog.py`, quindi un
   > fornitore può scaricare l'elenco ma non contare di essere chiamato a ogni richiesta (X-R4 non toccata). `ecb.md` e
   > `snb.md`: l'elenco resta in cache 24 h. `developer/frontend/fx-chain-algorithm.md:295`: diceva che `GET /fx/providers`
   > non cambia fino al riavvio del server; ora dice la cache di 24 h e che `currencyGraphStore.ts` tiene il grafo fino al
   > ricaricamento della pagina (verificato nel codice). `mkdocs build` stretto verde, `check-links` 95 validi, 0 rotti.

> **Fuori pista**:
> - Quattro imprecisioni preesistenti viste da docs-writer, lasciate e registrate come X-R10 (per il FE4).
4. ✅ Verifiche: `api schema` identico, ruff e black, test mirati, `api fx` anche senza rete, `all-backend`; journal e handoff.
   > **Note implementazione** (`/tmp/libreFolio_x_r8_verify.sh`, log `/tmp/libreFolio_x_r8_verify.log`): ruff e black puliti
   > sui 6 file Python; `openapi.json` (114 percorsi) e `tool-contracts` identici a HEAD; raccolta 14 131 contro 14 122 (+9:
   > gli 8 test nuovi e il caso `config-package` di `catalog.py`); 0 import irrisolti su 9 658; nessuna patch muta;
   > `services fx-catalog` 8, `api fx-unit` 29, `api fx` 21 e, senza rete, 21. **`all-backend` sulla 6183, 07:42–08:06, 7/7,
   > 14 119 passati, 29 saltati**, 0 falliti (`/tmp/libreFolio_x_r8_allbackend.log`). Il +116 sui 14 003 di J-5 è la
   > differenza di raccolta (+117 −1): i miei 9 e 107 arrivati con l'aggiornamento di base (A4b: `test_session_version` 47,
   > `test_session_revocation_api` 3; K2a: test BRIM 28 + 27 + 2 + 1). Porta 6183 libera.

### Checkpoint X-R8 ✅ (2026-10-15) — committato dal coordinatore: `1dfd4e657` (codice, 11 file) e `edbb067b5` (journal)

- **Base**: HEAD `4fdc0d9c5`.
- **Elenchi**: nessuna rinomina, nessun taglio. Nuovi 2: `backend/app/services/fx/catalog.py`,
  `backend/test_scripts/test_services/test_fx_catalog.py`. Modificati 11: `backend/app/api/v1/fx/providers.py`,
  `backend/app/services/fx/__init__.py`, `backend/test_scripts/test_api/test_fx_api_unit.py`,
  `scripts/test_runner/_backend_services.py` (superficie condivisa: un'azione in più, `fx-catalog`), 5 pagine MkDocs
  (`settings_cache.md`, `fx_plugin_guide.md`, `fx/providers/ecb.md`, `fx/providers/snb.md`,
  `frontend/fx-chain-algorithm.md`), il piano e il backlog (X-R8 chiusa, X-R10 nuova).
- **Messaggi di commit proposti**: `feat(fx): cache the providers' supported currencies for a day` (11 percorsi: tutto
  tranne il journal) e `docs(journal): X X-R8 log, backlog X-R8 closed, X-R10` (piano e backlog).

### Ottavo aggiornamento di base: H CP5a, J-6, W E0 — controllo leggero di `38b913df3` ✅ (2026-10-15)

Il coordinatore ha fuso `dev_release2` a `979d9ac2e` (H CP5a, la guardia di J-6, W E0, i record) nel mio ramo: merge
`38b913df3`, pulito (`_backend_services.py` mette `fx-catalog` accanto a `platform-readiness` di H). La guardia di J-6 manda
in ERROR, al suo teardown, ogni test che lascia aperta una connessione aiosqlite creata da lui: la run completa di X-R8 non
l'aveva. Controllo leggero sulla 6183 (`/tmp/libreFolio_x_base8.sh`, 08:13–08:17, log `/tmp/libreFolio_x_base8.log`):
- ✅ `front build --debug` (86 s): E0 ha cambiato il frontend e CP5a l'API.
- ✅ Con la guardia: `services fx-catalog` 8, `api fx-unit` 29, `api fx` 21; nessun ERROR al teardown.
- ✅ `services config-package` 593; `check-orphans`: nessun file orfano, ogni test registrato raggiungibile da un `all`.
- ✅ `api schema` contro `979d9ac2e` estratto: `openapi.json` identico (115 percorsi), `tool-contracts` identico.
- ✅ `mkdocs build` stretto (41 s, 3 012 URL), `check-links` 95 validi.
- Worktree pulito dopo, porta 6183 libera.

Note del coordinatore: X-R10 riceve una quinta voce (la docstring di `create_routes_bulk`), che è X-R1: registrata come
rimando. Il CHANGELOG di X-R8 lo scrive lui all'ingresso. Prossimo: il disegno di FE5b (taglio di `AssetModal.svelte`) in
sola lettura, mentre chiede il via al coordinatore colori; non FE5a (dopo il lotto A) né FE5c (dopo il lotto di Z sul
polling); taglio dichiarato con `theme-roles.mjs --split` nello stesso commit, poi `--check`; prove dopo la finestra.

### X-R8 in `dev_release2` ✅ (2026-10-15)

Journal `849c98dda`; merge `173ba19e2` alle 08:18, record `380a3e768` (la riga nel CHANGELOG, «🔄 Changed», e lo SHA
accanto a X-R8 nel backlog). Il mio ramo è avanzato a `380a3e768`. La docstring di X-R1 si corregge col CP6, insieme a
X-R2, dichiarando il cambio delle descrizioni in `openapi.json`.

### FE5b — il taglio di `AssetModal.svelte` ⏳ (2026-10-15)

Via del coordinatore e del coordinatore colori alle ~08:30. Record da ripartire con `--split`: `AssetModal` m1 **214**, m2
vuoto; i pezzi non portano letterali e le classi nuove vanno sui ruoli `lf-*` (T converte i pezzi nella sua ondata W4: chi
parte prima sono io). Durante la finestra della galleria (fino alle ~12:30) solo codice; le prove dopo l'avviso di fine.
Non FE5a (lo spostamento in `lib/features/assets/`, dopo il lotto A) né FE5c (la pagina dell'asset, dopo il lotto di Z).
Base: HEAD `380a3e768`. Inventario delle dipendenze (agente explore, sola lettura): `files/fe5b-inventory.md` della
cartella di sessione.

**Il punto critico.** Le quattro cuciture della logica (identificativi, confronto dei metadati, salvataggio,
applicazione del risultato di ricerca) condividono stato mutabile: `identifierRows`, `manualFieldRevisions`, il confronto
trattenuto (`heldComparison`, `selectionQuestions`, variabili non reattive), `providerProbe`; e lanciano compiti
asincroni in un ordine preciso (sonda, confronto, riuso). Il markup invece si divide con pochi props. Le prove arrivano
solo dopo la finestra: conviene tagliare prima ciò che è quasi solo markup.

**Due passi** (due checkpoint):
- **FE5b-1, ora: i pezzi del markup e la cucitura degli identificativi** (taglio dichiarato con `--split`):
  - `AssetModalImportNotices.svelte` (avvisi d'importazione, 1707–1726): `groups`;
  - `AssetModalDetails.svelte` (icona, nome, tipo, quantità di base, valuta, URL, descrizione, 1760–1954): bindable
    `displayName`, `assetType`, `quoteBaseQuantity`, `providerUserUrl`, `shortDescription`; in sola lettura `currency`,
    `iconUrl`, `hasProvider`, `askingProvider`, `duplicateAssetName`, gli errori della quantità di base; callback per la
    valuta scelta, il campo toccato a mano, «Chiedi al fornitore», l'icona, la descrizione;
  - `AssetModalIdentifiers.svelte` (tabella degli identificativi, etichette «altri», cancellazione multipla con la sua
    conferma, 1988–2066 e 2487–2499, con colonne, azioni e operazioni sulle righe, 533–596): bindable `rows`; in sola
    lettura `hasProvider`, `askingProvider`, `zIndex`; callback `onmanualedit`, `onaskprovider`. `storageKey` invariato;
  - `AssetModalProvider.svelte` (intestazione richiudibile, stato, «nessun fornitore», `ProviderAssignmentSection`,
    2085–2157): bindable `expanded`, `noProvider` e i quattro campi del fornitore; in sola lettura `providerUrl`,
    `probeState`, `testStatus`, `saving`; callback `onreconcile`;
  - `AssetModalFooter.svelte` (interruttori attivo/benchmark, Annulla, Salva, 2177–2254): bindable `active`,
    `isBenchmark`; callback `oncancel`, `onsave`;
  - `AssetModalSelectionPrompts.svelte` (scelta dell'identificativo primario, la sua conferma d'abbandono, riuso
    dell'asset esistente, 2277–2372): i flag restano nel padre (il `$derived` `selectionPromptOpen` e l'effetto che
    rilascia il confronto trattenuto devono vederli), il figlio riceve stato e callback;
  - resta nel padre: stato, derivati, effetti, popolamento, nome doppio, ricerca, confronto, salvataggio, chiusura; la
    cornice, l'intestazione, la ricerca online (col suo `{#key}`), il contenitore «Altre informazioni» con le due
    distribuzioni, i due avvisi, le conferme rimaste (salvataggio senza prova, cambio d'identificativo, abbandono,
    rigenerazione, cambio di fornitore parametrico, confronto, valuta, icona).
  `data-testid`, chiavi i18n, ancore della guida e attributi `data-*` (`data-busy`, `data-snapshot-ready`, `data-dirty`,
  `data-expanded`) invariati; markup spostato tale e quale (nessuna classe nuova, quindi nessun ruolo da scegliere).
  X-R3 (i due commenti di `AssetModal` su `asset_source.py`) si corregge qui.
- **FE5b-2, dopo: le cuciture della logica in moduli `.ts` puri**, con i loro test (test-author): il nucleo del confronto
  dei metadati (`compareMetadata`, conservando l'ordine degli auto-riempimenti), i payload di creazione e di modifica, la
  patch dal risultato di ricerca; l'orchestrazione (rete, biglietti della sonda, modali di conferma) resta nel padre. Nessun
  `--split` (nessuna classe si sposta).

Passi di FE5b-1:
1. ✅ I sei pezzi, uno alla volta, leggendo ogni sezione; X-R3.
   > **Note implementazione**: `/tmp/libreFolio_x_fe5b_cut.py` sposta un blocco di markup tale e quale (trovato per
   > contenuto, non per numero di riga), toglie il rientro e mette l'uso del pezzo al suo posto; poi le sole rinomine dei
   > nomi del padre nel pezzo, con un controllo che non ne resti nessuno. `AssetModal.svelte` da 2 510 a **1 932** righe;
   > i pezzi: `AssetModalDetails` 257, `AssetModalIdentifiers` 197, `AssetModalSelectionPrompts` 156,
   > `AssetModalFooter` 101, `AssetModalProvider` 96, `AssetModalImportNotices` 35. Scelte:
   > - **La conferma della cancellazione multipla resta nel padre.** `ModalBase` si monta sul posto (nessun portale: lo
   >   sfondo è `position: fixed` dentro chi lo monta), e dentro il pezzo finirebbe nel fieldset e nella scatola che
   >   scorre. Quindi la selezione è `bind:selectedIds` e il pezzo chiede la cancellazione con `onbulkdelete`.
   > - **I flag delle domande dopo la scelta di un risultato restano nel padre**, perché il derivato
   >   `selectionPromptOpen` e l'effetto che rilascia il confronto trattenuto devono vederli; nel pezzo vanno insieme le
   >   quattro modali contigue (scelta del primario, la sua conferma d'abbandono, cambio d'identificativo, riuso), così
   >   l'ordine nel DOM non cambia.
   > - Nel pezzo dei dettagli va `truncateQuoteBaseQuantity` (usata solo lì); le operazioni sulle righe degli
   >   identificativi, le colonne e le azioni vanno in `AssetModalIdentifiers`; `getIdentifierByType` e la cancellazione
   >   confermata restano nel padre (le usano il confronto e la modale). I campi toccati a mano arrivano al padre con il
   >   loro nome (`identifier_<tipo>`, `display_name`, …), come prima.
   > - Le scritture su un `$bindable` arrivano al padre in modo sincrono: quando il pezzo del fornitore chiama
   >   `onreconcile()` dopo aver cambiato «nessun fornitore», il padre vede già il valore nuovo, come prima.
   > - 19 import tolti dal padre (icone e componenti passati ai pezzi), controllati uno a uno.
   > X-R3: i due commenti di `AssetModal` puntano a `services/assets/provider_management.py`, quello di
   > `assetPayload.test.ts:58` a `services/assets/crud.py`. `.github/agents/test-author.agent.md:289` citava
   > `AssetModal.svelte:595` (già sbagliata a HEAD: la riga era la 667): ora cita la funzione, `populateFromEditData`.
2. ✅ `theme-roles.mjs --split` e `--check`; Prettier sui file toccati.
   > **Note implementazione**: Prettier ha solo raccolto su una riga l'uso di `AssetModalIdentifiers` (il padre era pulito a
   > HEAD). `node frontend/scripts/theme/theme-roles.mjs --split lib/components/assets/AssetModal.svelte:<le sette parti>`:
   > 26 + 79 + 29 + 12 + 10 + 20 + 38 = **214**, come il record, m2 vuoto, più la riga `~split`; `--check`: «Colour gates:
   > clean».
3. ⏳ Dopo la finestra: `front build --debug` (svelte-check), vitest di `AssetModal` (`AssetModal.test.ts`,
   `AssetModal.providerLifecycle.test.ts`), E2E degli asset e dei flussi che aprono la modale; journal e handoff.
   > **Note implementazione** (prima della finestra, 08:33–08:35): `npm run check` (svelte-check) **0 errori, 0 avvisi**;
   > vitest `AssetModal.test.ts`, `AssetModal.providerLifecycle.test.ts`, `assetPayload.test.ts`,
   > `assetIdentifiers.test.ts`: 4 file, **116/116**. Restano gli E2E dopo la finestra: `front-asset` (asset-modal,
   > asset-classification, asset-mobile-layout, asset-detail), i flussi d'importazione che aprono la modale
   > (tx-import-resolution, tx-import-asset-inspector, tx-import-ca-contract), `utilities`, `onboarding-guides`.

**FE5b-1 committato sul mio ramo, non integrato** (15/10, 08:38): `37532d558` (codice, 10 file; il coordinatore ha rifatto
`--check`) e `448d8dd33` (journal). Gli E2E dopo la finestra, poi l'ingresso con l'avviso (prima R, poi L).

### FE5b-2 — le cuciture della logica di `AssetModal` in moduli `.ts` puri ✅ (2026-10-15; E2E dopo la finestra)

Sopra `448d8dd33`, durante la finestra della galleria: codice, e solo prove leggere (svelte-check, singoli file vitest).

**La condizione che rende sicuro estrarre il confronto dei metadati** (verificata leggendo il codice): ogni confronto legge
solo il proprio campo, e lo scrive solo il proprio passo (`setFieldValue` scrive il campo, più `quoteBaseQuantity` per il tipo
e `descriptionFromPrefill` per la descrizione, che non sono confrontati); le righe OTHER le legge solo il loro passo.
Quindi una funzione pura su una fotografia presa prima del confronto decide esattamente le stesse cose, e il padre applica
le azioni nell'ordine. `autoFilledFields` è solo scritto, mai letto (12 assegnazioni, 0 letture): resta com'è, per non
cambiare nulla. La nota «COVERAGE NOTE» sopra il confronto, che sconsigliava l'estrazione perché avrebbe lasciato nel
componente il ramo di rete, decade: la rete resta nel padre e la decisione diventa provabile senza rete.

Passi:
1. ✅ (2026-10-15) `assetIdentifiers.ts`: `identifierValue`, `withIdentifier`, `mergeOtherIdentifierValues`, `withElectedPrimary`
   (le operazioni sulle righe di `getIdentifierByType`, `setIdentifierByType`, `mergeOtherIdentifiers`,
   `confirmIdentifierPrimary`).
   > **Note implementazione**: le quattro funzioni sono pure e rendono righe nuove; il padre delega e assegna
   > (`mergeOtherIdentifiers` assegna solo se `added > 0`, come prima).
2. ✅ (2026-10-15) `assetSearchSelection.ts` (nuovo): il tipo, la decisione sull'identificativo (conflitto → scelta, aggiorna,
   aggiungi) e i parametri del fornitore di un risultato di ricerca; `applySearchResult` tiene gli effetti.
   > **Note implementazione**: `searchResultAssetType`, `searchResultIdentifier` (esito `none | conflict | rows`),
   > `searchResultProviderParams`. Gli effetti di `applySearchResult` restano nello stesso ordine (scelta del primario e
   > domanda, campi del fornitore, azzeramenti, compiti asincroni). `generateUUID` e `ASSET_TYPES` escono dal padre.
3. ✅ (2026-10-15) `assetMetadataComparison.ts` (nuovo): `compareMetadata(patchData, fotografia, scope, manuallyChanged, etichette)`
   → azioni ordinate, differenze, campi mancanti; `fetchAndCompareMetadata` tiene rete, biglietti, avvisi, apertura.
   > **Note implementazione**: confrontato riga per riga con l'originale (`git show HEAD:…`, righe 953–1077). Il padre
   > costruisce la fotografia (`comparisonSnapshot()`) e applica le azioni (`applyComparisonAction()`); ogni azione
   > porta il suo `field`, che finisce in `autoFilledFields` come prima (`mergeOther` solo se aggiunge righe). La
   > «COVERAGE NOTE» è tolta. Tolti anche un commento orfano precedente a FE5b («Helper: field name like
   > 'identifier_ticker'…», sopra `setIdentifierByType`), e la JSDoc di `setFieldValue` è tornata sopra la sua funzione.
   > **⚠️ Fuori pista**: nella prima stesura l'azione `mergeDescription` non portava `field`, e `autoFilledFields` avrebbe
   > ricevuto `undefined` al posto di `short_description`. Visto rileggendo, prima di ogni prova: ora ogni azione ha il
   > suo `field`.
4. ✅ (2026-10-15) `assetPayload.ts`: gli elementi di creazione, di modifica e di assegnazione del fornitore; `saveCreate` e `saveEdit`
   tengono conferme, 409, cache, sync.
   > **Note implementazione**: `AssetFormFields`, `buildCreateItem`, `buildPatchItem`, `ProviderAssignment`,
   > `buildProviderAssignItem`; nel padre `formFields()` e `providerAssignment()`. Il `naLog` della creazione legge
   > `createItem.quote_base_quantity`. Unico spostamento di tempo: in `saveEdit` la base di quotazione si normalizza dopo
   > `await ensureAssetProvidersCached()` invece che prima. È equivalente: `handleSave` esce se `!isValid`, che vuole un
   > intero finito ≥ 1, quindi l'unico scrittore raggiungibile (`truncateQuoteBaseQuantity`, sul blur) non scrive; e
   > `doSave` mette `saving = true` prima di `saveEdit`, che disabilita il fieldset. Dal padre escono 8 import
   > (`ASSET_TYPES`, `isFamilyOnlyProposal`, `generateUUID`, `identifierRowsToColumns`, `normalizeQuoteBaseQuantity`,
   > `normalizeDistribution`, `sameDistribution`, `buildClassificationPatch`). `AssetModal.svelte`: 1 932 → 1 779 righe.
   > Prove leggere: `npm run check` 0 errori / 0 avvisi; vitest su `AssetModal`, `AssetModal.providerLifecycle`,
   > `assetPayload`, `assetIdentifiers`: 116/116, come prima (i due file del componente percorrono confronto, ricerca e
   > salvataggi). Prettier: nessun cambio.
5. ✅ (2026-10-15) Prove leggere (svelte-check, vitest dei moduli e di `AssetModal`); test nuovi (test-author); journal e handoff.
   > **Note implementazione**: test-author ha scritto 130 test unitari: `assetIdentifiers.test.ts` +24 (45),
   > `assetPayload.test.ts` +17 (39), `assetSearchSelection.test.ts` nuovo (28), `assetMetadataComparison.test.ts` nuovo
   > (61, ogni ramo: ambito, tre esiti per campo, famiglia del tipo, maiuscole, valuta non scelta, OTHER, descrizione da
   > prefill, distribuzioni nelle due forme, ordine delle azioni e delle righe, ingressi congelati). I due file nuovi
   > sono registrati in `scripts/test_runner/_frontend_utility.py` (`front_utility_unit`, cioè `front-utility core-unit`),
   > due righe aggiunte accanto ad `assetPayload.test.ts`. Prove finali: `npm run check` 0/0; vitest sui sei file degli
   > asset 246/246 (116 + 130); `theme-roles.mjs --check` pulito (nessuna classe spostata, niente `--split`);
   > `dev.py test --test-port 6183 --data-dir /tmp/librefolio-r13-x check-orphans`: 372 file unitari, tutti raggiungibili;
   > ruff e black puliti su `_frontend_utility.py`; Prettier pulito. Porta 6183 libera.
   > **⚠️ Fuori pista**: (a) svelte-check ha trovato 7 errori di tipo in `assetPayload.test.ts:238`: il tipo dedotto di
   > `buildCreateItem` perde la firma d'indice delle colonne degli identificativi (come il letterale di prima). Corretto
   > dal secondo test-author solo nel test, con una vista `Record<string, unknown>`; sorgente invariata. (b) Una
   > differenza vera, vista da test-author: con una risposta malformata (un peso di distribuzione non numerico)
   > l'originale aveva già scritto i campi confrontati prima del settore e poi mostrava l'errore; ora `compareMetadata`
   > lancia prima di ogni scrittura, quindi il modulo resta intatto e l'avviso d'errore è lo stesso. Tenuta (un errore
   > atomico invece che a metà), dichiarata nella JSDoc del modulo e nell'handoff. Il backend valida i pesi, quindi
   > serve una risposta malformata. (c) Stranezze preesistenti copiate fedelmente: nuova voce **X-R11** del backlog (la
   > più visibile: l'etichetta `'Description'` del dialogo di confronto non è tradotta).
   > E2E di FE5b (1 e 2 insieme) dopo l'avviso di fine finestra: `front build --debug`, poi `front-asset` (asset-modal,
   > asset-classification, asset-mobile-layout, asset-detail), i flussi d'importazione che aprono la modale
   > (tx-import-resolution, tx-import-asset-inspector, tx-import-ca-contract), `utilities`, `onboarding-guides`.

FE5b-2 committato sul mio ramo, non integrato: `fc6220d28` (refactor, 10 file, con le due differenze dichiarate nel corpo)
e `a50ec87d6` (journal). Il coordinatore: X-R11 nella sua prima voce, in un commit a parte sopra FE5b-2, che entra con
FE5b; la riga 🐛 del CHANGELOG la scrive lui. Gli E2E dopo la finestra valgono per FE5b-1, FE5b-2 e X-R11a insieme.

### X-R11a — la riga della descrizione nel dialogo di confronto, tradotta ✅ (2026-10-15; E2E dopo la finestra)

Sopra `a50ec87d6`. Ogni riga del dialogo di confronto prende l'etichetta da `ComparisonLabels`, tradotta dal padre, salvo
quella della descrizione, che usava il letterale `'Description'`: in italiano e in spagnolo restava in inglese
(`ProviderComparisonModal` mostra `item.label` com'è). Preesistente, copiata fedelmente nel FE5b-2.

1. ✅ (2026-10-15) Test prima, rosso. test-author: in `assetMetadataComparison.test.ts` l'etichetta `description: 'Desc'`
   nelle `LABELS` dei test (diversa da `'Description'` di proposito: in inglese `common.description` e il letterale
   coincidono, e solo un valore diverso li distingue); le tre attese che fissavano il letterale ora leggono
   `LABELS.description`, e il titolo del test che diceva «under the literal label» porta `(X-R11)`.
   Contro il sorgente non corretto: 3 rossi su 61, esattamente i tre test che leggono l'etichetta della descrizione,
   ognuno solo su `"Desc"` contro `"Description"`.
   > **Note implementazione**: niente test di componente: i test di `AssetModal` girano col catalogo inglese, dove le due
   > etichette coincidono. Il padre non può dimenticare l'etichetta: il campo è obbligatorio nel tipo, e svelte-check lo
   > controlla.
2. ✅ (2026-10-15) La cura, tre righe: `ComparisonLabels` riceve `description: string` (obbligatorio);
   `compareMetadata` usa `labels.description`; `AssetModal.svelte` passa `$t('common.description')`, chiave che c'è già
   nei quattro cataloghi (Description, Descrizione, Description, Descripción) e che la sezione dei dettagli usa già.
   Nessun catalogo toccato.
   > **Note implementazione**: prove leggere: vitest sui sei file degli asset 246/246 (i 3 rossi ora verdi);
   > `npm run check` 0/0; Prettier pulito. Nessuna classe toccata. Osservazione di test-author, fuori dalla voce: anche
   > `name`, `type`, `currency` e `sector` nelle `LABELS` dei test coincidono con le parole inglesi, quindi un letterale
   > futuro su quelle righe non si vedrebbe; oggi il sorgente passa `labels.*` per tutte.

X-R11a committato sul mio ramo, non integrato: `ac89cea72` (fix) e `4b3455a9b` (journal). La riga 🐛 del CHANGELOG la scrive
il coordinatore all'ingresso.

### X-R1 + X-R2 — i vecchi percorsi nelle descrizioni di `openapi.json` ✅ (2026-10-15)

Sopra `4b3455a9b`, chiesto dal coordinatore durante la finestra della galleria (lavoro leggero); entra con FE5b.

1. ✅ (2026-10-15) Le docstring:
   - `create_routes_bulk` (`api/v1/fx/providers.py`): `normalize_rate_for_storage` sta in `services/fx/storage.py`, non in
     `services/fx.py` (X-R1, e la quinta voce di X-R10, che è la stessa riga);
   - `BackwardFillInfo` (`schemas/common.py`): «FX (fx.py)» e «Asset pricing (asset_source.py)» diventano
     `services/fx/conversion.py` (dove si calcola il riempimento all'indietro dei cambi) e `services/assets/price_query.py`
     (dove lo calcolano i prezzi, con `AssetBackwardFillInfo`);
   - `IdentifierType` (`db/models.py`): `schemas/assets/assets.py`, `services/assets/crud.py`, `services/brim/brim_provider.py`.
     Verificato che le classi e le funzioni nominate esistono ancora lì (`FAAssetCreateItem`, `FAAssetPatchItem`,
     `FAinfoResponse`, `FAAinfoFiltersRequest`; `list_assets`, `create_assets_bulk`; `search_asset_candidates`; il test
     `test_identifier_columns_match_enum`).
   > **⚠️ Fuori pista**: nella stessa docstring di `IdentifierType` il passo 1 diceva di aggiungere la colonna in
   > `001_initial.py`. Contraddice la regola delle migrazioni incrementali (la tabella `assets` è già rilasciata: una colonna
   > nuova vuole una migrazione nuova, come fu `002_identifier_other_json_list.py`), e un agente che seguisse la docstring
   > romperebbe i DB installati. Corretta nello stesso commit, una riga: «a new incremental Alembic migration (./dev.py db
   > migrate "..."), never 001_initial.py: the assets table has already shipped». Dichiarata nell'handoff.
2. ✅ (2026-10-15) Prova: `dev.py api schema` prima della modifica (HEAD pulito) e dopo, con un confronto strutturato dei due
   `openapi.json` (`/tmp/libreFolio_x_xr1_schema_diff.py`): **4 percorsi diversi, nessuno fuori dalle descrizioni**:
   `components/schemas/BackwardFillInfo/description`, `components/schemas/IdentifierType/description`,
   `paths//api/v1/fx/providers/routes/post/description` e `info/version` (il suffisso `-dirty`). `tool-contracts.openapi.json`
   identico (`202402e5…`, lo stesso hash dal CP1). ruff e black puliti sui 3 file; nessun test cita quei testi; il grep dei
   vecchi percorsi in `backend/app` trova solo `brim_providers/__init__.py:10`, che nomina il file `brim_provider.py` senza
   percorso (il file esiste ancora, in `services/brim/`) e non finisce in `openapi.json`: lasciato.

### CP10 — aggiunta al disegno per il ripristino dei backup (B) ✅ (2026-10-15, solo disegno)

Chiesta dal coordinatore il 15/10 per l'analisi di B. Scritta in §4.5, «Ripristino di un backup: il contratto con B»:
`rekey_plugin_secrets` e `count_unreadable_secrets` su una `sqlite3.Connection` della copia, e il valore di controllo H-3 = il
`key_id` di ogni riga nella 007, senza tabelle a parte. Da H servono `derive_key_from(instance_key, purpose, length)` e il
controllo all'avvio con il DB. Corrette anche due righe rimaste a `006_plugin_settings` (§4.4 e §5): la migrazione è la 007.

### D-X4 decisa dal developer: il piano del profilo gestito ✅ (2026-10-15)

Girata dal coordinatore alle 12:44, senza richiesta di risposta. Scritta in §4.3, con le conseguenze in §5, §6 (D-X4; e D-X2,
voce 18, assorbita dalla 39 e ancora al developer), §8, §9 (CP6), §10, §11 e nella nota del CP10, fermo fino alla 39.
Il disegno: permesso e ricerca su due livelli. Nel profilo gestito gli scraper escono solo dalla ricerca e restano assegnabili
a mano, con un `notice` calcolato nel backend e la riga d'avviso nella configurazione della fonte. L'elenco del pannello
decide il permesso: è la leva per chiudere l'uso a mano senza codice, se il dubbio legale lo chiede. Il blocco SSRF dello
scraper CSS diventa una precondizione del profilo gestito. Corretti anche due riferimenti di §4.3 rimasti alle righe dei
router di prima del CP2b e del CP3.
> **⚠️ Fuori pista**: la frase del coordinatore «senza un elenco del pannello, le fonti scraper non compaiono nella ricerca» si
> può leggere come «un elenco del pannello le rimette in ricerca». Ho scritto l'altra lettura (l'elenco vale per il permesso,
> mai per la ricerca): è più vicina alle parole del developer («si al togliere il search») e regge un elenco di diritti per
> piano. Segnalata al coordinatore, che può chiedere l'altra (una riga nel registro). **Confermata** dal coordinatore alle
> 12:53, con le altre tre scelte (permesso di default in tutti e due i profili, `notice` dal backend, URL incollato come
> ricerca, SSRF come precondizione); ad H non era stato girato niente, quindi niente da riallineare. Piano committato in
> `d9b79bb8c`. «Il via te lo do con l'avviso di fine finestra» (coordinatore); il CP6 dipende ancora dal profilo gestito di
> H (§9).

### Nono aggiornamento di base: R, L, G, la 1.2.1 — merge di `13705dd05` in `d9b79bb8c` ✅ (2026-10-15) — merge `2fb577588`

Finestra della galleria chiusa alle 13:01; da ora al massimo 2 suite pesanti sulla macchina, assegnate dal coordinatore (a
me il secondo slot), il resto con `nice -n 10`. Merge aperto dal coordinatore nel mio worktree: `MERGE_HEAD` `13705dd05`,
base comune `380a3e768`, un solo conflitto, `frontend/src/themeRoles.baseline.tsv`. La mia modifica non committata del
piano 03 resta fuori dallo stage (la committa lui a parte).

1. ✅ Il baseline, prima di scrivere: prova a secco di `--resolve` (`resolveConflict()` e `compareWithBaseline(scanTree(),
   …)`, come consiglia la pagina della devWiki `problems/colour-ratchet-resolve-drops-an-accept.md` che il merge porta).
   Previsione: una violazione, `R2 m2 lib/stores/app/themeStore.ts: colour literals beyond its record: #166534`. Le tre
   versioni della riga: base e mio lato `0 #156534 #1a4031` (il mio ramo non ha mai toccato il file), `dev_release2`
   `0 #166534 #1a4031` (l'`~accept` D3 di R del 14/10, decisione del developer). `mergeBaselines` tiene solo i valori comuni
   ai due lati e non guarda la base: è R-8. Le 81 «drops» sono solo margine da stringere (`--update`, di T); le 22 «moves»
   (`lib/components/{auth,settings,support}` → `lib/features/…`) il cancello le riconosce da solo.
2. ✅ `--resolve` scritto (identico alla prova a secco, nessun marcatore); `--check` rosso come previsto; **non in stage**.
   Prova a secco della cura della pagina, cioè ripetere l'`--accept` di R con la stessa ragione: la riga torna
   `0 #166534 #1a4031`, identica a `dev_release2` e a quello che misura l'albero; un solo `~accept`; 0 violazioni. Il baseline
   finale differirebbe da `dev_release2` solo per il mio split di FE5b-1 (8 righe) e dal mio lato solo per la riga accettata
   di R e la sua dichiarazione: è il risultato di un vero merge a tre vie. `--accept` allarga un record, quindi vuole l'OK
   del coordinatore colori: chiesto al coordinatore alle 13:07; il baseline non si tocca fino alla risposta.
3. ✅ Gli altri file cambiati dai due lati: `scripts/test_runner/_frontend_utility.py` (i 6 test di R e i miei 2, il file si
   analizza) e il backlog (nessun doppione nuovo: G-8, J-5, T-B4, W-B13, W-B9 compaiono due volte già nella base e nei due
   lati).
4. ✅ Prove leggere sull'albero fuso, prima della pausa delle dipendenze (13:10, `cryptography` nell'ambiente condiviso:
   niente Python fino all'avviso): `dev.py api sync` verde (solo file ignorati; hash dei tool-contracts `202402e5…`
   invariato); `npm run check` 0/0. Durante la pausa, solo Node: vitest dei sei file degli asset 246/246; vitest delle unità
   del Designer Lab (i 15 file di `front-designer-lab unit`) 394/394.
5. ✅ OK del coordinatore colori alle 13:12 («è la stessa D3 già autorizzata dal developer, con la stessa ragione»); la
   correzione di `--resolve` è passata nel backlog di T come TC-7. `--accept lib/stores/app/themeStore.ts` con la ragione D3:
   file identico alla prova a secco, un solo `~accept`; `--check` pulito (81 «drops», margine per l'`--update` di T); `git
   add` del solo baseline; nessuna voce in conflitto rimasta. Il baseline in stage: contro `dev_release2` +8 −1 (il mio split
   di FE5b-1), contro il mio HEAD +2 −1 (la riga di R e il suo `~accept`). «staged» al coordinatore, che fa il commit del
   merge.
   Commit del merge del coordinatore: `2fb577588` (genitori `d9b79bb8c` e `13705dd05`), verificato: il baseline committato è
   byte per byte quello controllato, nessun merge aperto, il piano 03 fuori.
6. ✅ Sulla revisione combinata `2fb577588`, dopo la fine della pausa (13:36: `cryptography 50.0.2` nell'ambiente condiviso,
   `dc9a5d232` su `dev_release2`; regole sul carico più strette: per H, X, A ed E le prove leggere e medie sono libere, una alla
   volta per corsia con `nice -n 10`; a me lo slot pesante 2, per `front-asset`). Medie, tutte verdi:
   - `dev.py front build --debug` (13:37–13:41);
   - `dev.py mkdocs build`, stretto, 94 s;
   - `front-utility core-unit`: 142 file, 4 510 test (comprese le guardie dei colori sul baseline fuso);
   - `check-orphans`: 121 spec E2E, 393 file unitari, 281 file del backend, tutti raggiungibili da un `all`.
   Poi la prova pesante e le spec singole, tutte con `--workers 2` e `nice -n 10`, una alla volta:
   - `front-asset all` (13:45–14:00): 21 file unitari (1 001 test) e 144 E2E verdi, comprese tutte le spec del lotto
     (asset-modal, asset-classification, asset-mobile-layout, asset-detail, asset-data-editor); **2 rossi in
     `asset-browse`**: AB-001 (`locator.fill` sulla ricerca della lista, 60 s scaduti) e AB-002 (dopo la ricerca la griglia
     tiene 22 schede invece delle 3 del test);
   - triage con la skill `test-triage`, verdetto **ambiente**: alle 13:54 il carico della macchina era 110–139 su 10 core
     (coordinatore). Nella run pesante i test verdi di `asset-browse` duravano 34–46 s e i due rossi 78–97 s; in AB-002
     Playwright ha interrogato il conteggio solo 4 volte in 15 s (runner affamato, non solo la pagina). Escluse le altre
     ipotesi: prodotto (`searchText` lo scrivono solo l'input con 300 ms di debounce e «pulisci filtri», nessun ripristino
     asincrono), test (attende presenza, valore e conteggio delle sue schede, con un token unico), stato condiviso (token
     diversi, contesti separati). Conferma: la spec da sola, alle 14:02 con carico 39–49, **8/8 in 33,5 s** (6–9 s per test);
   - `front-transaction` `tx-import-resolution` 15/15, `tx-import-asset-inspector` 5/5, `tx-ca-contract` 12/12;
   - `front-utility` `utilities` 16/16, `onboarding-guides` 24/24;
   - `front-designer-lab` `live` 7/7, `picker` 3/3, `neutral` 1/1.
   Porta 6183 libera alle 14:15. `all-backend` non eseguita (non richiesta; dal mio lato, dopo l'ultima, solo le docstring
   di X-R1/R2).
   > **⚠️ Fuori pista**: un rosso da carico. Proposta al coordinatore, fuori dal mio perimetro: il runner potrebbe stampare
   > il carico a inizio e fine run, così una run satura si vede nel log e non solo dai tempi.

FE5b-1, FE5b-2, X-R11a e X-R1/R2 integrati in `dev_release2` il 15/10 (pomeriggio); journal `e78eb7b6f`.

## CP10 — impostazioni dei plugin, backend ✅ (15/10, 16:36–20:40; FROZEN, in attesa del checkpoint)

### Analisi su `14d58cc61` e via (15/10)

Il coordinatore ha chiesto alle 16:20 l'ordine dei lotti e l'analisi del CP10 sulla base nuova; analisi mandata alle
16:33; **via alle 16:36**, con tutte le scelte approvate. Worktree portato a `dae4de4fa` (= `dev_release2`) con un
avanzamento veloce del coordinatore.

**Ordine dei lotti** (confermato): CP10 → X1–X8 (dopo Z7a) → CP11 (UI delle impostazioni; la riga della scheda in
`settingsTabs.ts`, file di A, va dichiarata nel checkpoint, aggiunta pura) → CP6 (profilo gestito; nota da Z6b: la doc
del profilo gestito dice `kill_signal = "SIGTERM"` e `kill_timeout = 10` per Fly) → CP13 (F21 + C-90 + C-66) → FE4,
FE5a, FE5c col via dei colori → CP12, CP5.

**Stato reale** (letto dagli oggetti di git su `14d58cc61`):
- `cryptography 50.0.2` nel lock (`cffi 2.1.1`, `pycparser 3.11`); testa delle migrazioni `006_registration_mode`, la 007
  è mia (C7); `instance_key.py` ha solo `derive_key(purpose, length)`; `LIBREFOLIO_PROFILE` (`selfhosted|managed`) in
  `Settings`; `.env.example` ha la sezione «Plugins», vuota; `config/plugins.py` c'è (web_link_finder).
- `get_plugin_instance` crea un'istanza nuova a ogni chiamata (`provider_registry.py:143`); 13 siti di creazione per gli
  asset e 9 chiamate in thread; 5 siti per i cambi, chiamate sul loop principale.
- La ricerca ha due cache (query 15 min, elementi 24 h) che vogliono l'impronta delle impostazioni.
- `config-env-example` vede solo i nomi letterali; `db_schema_validate` controlla gli indici solo per numero.
- `delete_user` cancella la riga; il DB fa la cascata. Nessun middleware legge i corpi; `httpx` è a WARNING.
- `/backup/export` e `/backup/restore` sono segnaposti (501): `derive_key_from` (H) serve solo al ripristino.

**Scelte approvate dal coordinatore (16:36)**:
1. Due tabelle, `plugin_system_settings` e `plugin_user_settings` (`user_id` NOT NULL, `ON DELETE CASCADE`), vincoli unici
   normali; AAD e `key_id` invariati.
2. Scrittura tutto o niente: si valida tutto, ogni rifiuto ha il suo codice, 422 e niente scritto; altrimenti una sola
   transazione (il contratto di `/settings/global/bulk`).
3. `GET /api/v1/settings/plugins` e `PATCH /api/v1/settings/plugins/bulk`, modulo `api/v1/plugin_settings.py`, una riga in
   `router.py` (la scrivo io, dichiarata nel checkpoint).
4. L'ambiente blocca solo i campi di sistema.
5. `test_only` sulla classe del plugin: toglie i fornitori di prova da catalogo ed elenchi, al posto di
   `api/v1/assets/providers.py:62` e `api/v1/fx/providers.py:80`; `mockprov` e `mockfx` dichiarano campi per i test.
6. Il confine `call_provider` nasce nel CP10, con il punto d'aggancio di X1–X7 (`check`/`refused`/`succeeded` del registro
   di Z7a, che non tocco). Disegno di Z7: commit `4992b864b`, piano 06, «Z7 — disegno».
7. Mascheramento nei log: un processore di structlog in `logging_config.py` (lo scrivo io, dichiarato), per valore, dai
   segreti della chiamata in corso, in un ContextVar.
8. `rekey_plugin_secrets` e `count_unreadable_secrets` sulle sottochiavi, `plugin_secrets_key_status(session)`; la
   variante con la chiave dello zip dopo `derive_key_from` di H; il controllo all'avvio è di H.
9. X-R6 (TIMEOUT e MAX di `web_link_finder`) entra nel CP10, se resta piccolo.
Rischio alto: la `security-review` va fatta **prima** del checkpoint. Slot pesanti (anche `all-backend`) chiesti al
coordinatore; prove singole e medie una alla volta, con `nice -n 10`.

**Il confine, deciso nel mio perimetro.** Z7 si aspetta `call_provider(provider_code, fn, *, timeout, scope=None)`. Il
primo argomento diventa **l'istanza configurata**: ne ricava il codice (`provider.provider_code`), le impostazioni
consegnate (per `NOT_CONFIGURED` e per i segreti da mascherare) e, in X1–X7, `cooldown_scope`. Con il solo codice il
confine non saprebbe quali segreti mascherare; un argomento facoltativo si potrebbe dimenticare. Lo dico al coordinatore
per Z, che non chiama il confine. Per i cambi il confine è `_fetch_provider` di `fx/sync.py`.

### Passi

1. ✅ (2026-10-15) Contratto: `services/plugin_settings/fields.py` (campo dichiarato) e `contract.py` (mixin `settings_fields`,
   `settings`, `bind_settings`), validazione alla registrazione in `provider_registry.py`; mixin su `AssetSourceProvider`
   e `FXRateProvider`; `test_only` al posto dei nomi scritti a mano; campi di prova in `mockprov` e `mockfx`.
   > **Note implementazione**: `fields.py` (foglia, solo stdlib): `PluginSettingField` (chiave, tipo, scope, etichetta e
   > descrizione inglesi con le chiavi i18n, `secret`, `required`, `default`, opzioni, lunghezze, limiti, alias `env`),
   > `validate_declaration` per famiglia (`FAMILY_RULES`: gli asset ammettono campi personali e segreti; i cambi solo campi
   > di sistema, perché un sync serve tutti), `validate_value` e `parse_env_value`, i cui messaggi non contengono mai il
   > valore; un segreto è testo, senza default, di almeno 8 caratteri salvo dichiarazione (mai sotto 4: il mascheramento
   > per valore toccherebbe parole comuni); `env_name` dà `LIBREFOLIO_PLUGIN_<FAMIGLIA>_<CODICE>_<CAMPO>`. `contract.py`:
   > `BoundSettings` (`get` per i valori normali, `secret` per i segreti, `missing`, `secret_values`; il `repr` nomina i
   > segreti e non li mostra) e `PluginSettingsMixin` (`settings_fields`, `test_only`, `settings`, `bind_settings`).
   > `provider_registry.py`: `settings_family()` (asset, fx) e il controllo della dichiarazione in `register`: un plugin
   > con una dichiarazione sbagliata non si registra, come uno che non si importa. `mockprov` dichiara un campo di ogni
   > tipo (sistema e personale, normale e segreto, con un alias `env`) e, cercando `lf-settings-echo`, descrive le
   > impostazioni ricevute (i segreti solo come «set» o «unset»); `mockfx` un segreto e un intero di sistema. `test_only`
   > sostituisce `code == "mockprov"` e `MOCKFX`/`MOCKFX_FAIL` nei due elenchi; `MANUAL` resta nascosto per nome (è la
   > sentinella dei tassi inseriti a mano, non un fornitore di prova). Prova: scoperta senza errori (6 asset, 7 cambi),
   > `test_only` su `mockprov`, `MOCKFX`, `MOCKFX_FAIL`; ruff e black puliti.
   > **⚠️ Fuori pista**: il frontend filtra ancora `mockprov` per nome (`AssetSearchAutocomplete.svelte:132`,
   > `ProviderAssignmentSection.svelte:185`): ridondante, il backend non lo elenca già. Lasciato: il CP10 è solo backend;
   > da togliere nel FE5a.
2. ✅ (2026-10-15) Modelli e migrazione `007_plugin_settings` (due tabelle), upgrade e downgrade su un DB 1.2 popolato.
   > **Note implementazione**: `PluginSystemSetting` (`plugin_system_settings`: famiglia, codice, campo, `value_json` |
   > `secret_ciphertext` + `key_id`, `updated_at`, `updated_by_user_id` `SET NULL`) e `PluginUserSetting`
   > (`plugin_user_settings`: le stesse più `user_id` NOT NULL, `CASCADE`), dopo `GlobalSetting` in `db/models.py`
   > (`LargeBinary` aggiunto agli import); vincoli unici per campo e due CHECK per tabella: esattamente uno fra valore e
   > cifrato, `key_id` se e solo se c'è un cifrato. `db/base.py` e `db/__init__.py` non cambiano: le tabelle entrano nei
   > metadati con il modulo. Migrazione idempotente nei due sensi, come la 005; il downgrade perde valori e segreti, e lo
   > dice. Prova a mano su un file temporaneo (`/tmp/libreFolio_x_cp10_mig_smoke.py`): upgrade da zero alla testa,
   > `compare_metadata` senza differenze sulle due tabelle, i quattro casi dei CHECK e il doppione rifiutati, cascata
   > all'eliminazione dell'utente, downgrade a 006 senza le tabelle, secondo downgrade senza effetti, upgrade di nuovo
   > alla 007. La prova su un DB 1.2 popolato la scrive test-author (passo 7).
3. ✅ (2026-10-15) Cifratura (`crypto.py`): AES-256-GCM, AAD di contesto, `key_id`, sottochiave `plugins.settings.v1`; ripristino.
   > **Note implementazione**: blob = byte di formato `1` + nonce casuale da 96 bit + cifrato con tag; AAD = JSON di
   > `["lf-plugin-setting/v1", famiglia, plugin, campo, scope, user_id]`; `key_id` = 16 byte di
   > `HMAC-SHA256(sottochiave, etichetta)` in esadecimale; sottochiavi `plugins.settings.v1` (cifratura) e
   > `plugins.settings.fingerprint.v1` (impronta delle cache). `plugin_secrets_key_status(session)` conta per `key_id`
   > senza decifrare, e senza segreti salvati non legge nessuna chiave (un controllo all'avvio non crea il file della
   > chiave). `rekey_plugin_secrets` e `count_unreadable_secrets` su una `sqlite3.Connection`, dentro un `SAVEPOINT`.
   > Prova a mano (`/tmp/libreFolio_x_cp10_crypto_smoke.py`): una riga copiata su un altro utente risulta illeggibile;
   > dentro una transazione del chiamante il lavoro sparisce con il suo rollback; da sola fa il commit; il secondo giro
   > non scrive niente; la decifratura con il contesto di un'altra riga fallisce.
4. ✅ (2026-10-15) Archivio e risoluzione: ambiente (accessore in `config/plugins.py`), DB, default; blocco; profilo gestito;
   «illeggibile»; impronta per le cache.
   > **Note implementazione**: `config/plugins.py`: `plugin_setting_env(name)` = `env_secret(name)`, quindi ogni campo
   > accetta anche `_FILE`. `resolver.py`: `resolve_plugin_fields` (sincrona, in un thread: legge l'ambiente, i file e la
   > chiave d'istanza) dà per campo `FieldState` (fonte `env|db|default|none`, `locked`, la variabile che blocca, il
   > problema `unreadable|invalid_env|invalid_stored`); una variabile impostata vince e blocca anche con un valore non
   > valido (problema, mai un ripiego muto); il catalogo giudica un segreto dal `key_id`, senza decifrare. Un segreto
   > illeggibile si scrive nel log una volta per processo (campo e plugin, mai il valore). `build_bound_settings` dà i
   > valori di una chiamata con l'impronta: SHA-256 dei soli valori normali, HMAC con la sottochiave quando ci sono
   > segreti. `runtime.py`: `configure_instance` legge le righe in una sessione propria e corta (mai quella del chiamante:
   > la ricerca chiama i fornitori in parallelo), salta il DB per un plugin senza campi o, senza utente, senza campi di
   > sistema; un errore del DB lascia ambiente e default e scrive un avviso. Il profilo gestito tocca solo il catalogo
   > (passo 6). Lo «store.py» del disegno non serve: lettura in `runtime.py`, scritture nel servizio dell'API.
5. ✅ (2026-10-15) Il confine: `call_provider` per gli asset, `_fetch_provider` per i cambi; consegna; `NOT_CONFIGURED`; mascheramento
   (eccezioni e log); impronta nelle cache della ricerca.
   > **Note implementazione**: `utils/runtime/secret_masking.py` (foglia della stdlib): `secrets_in_flight` (ContextVar,
   > copiato da `to_thread` nel thread del fornitore), `mask_text` (il valore e le sue forme URL-encoded), `mask_exception`
   > (sul posto: argomenti, `message`, `details`, catena `__cause__`/`__context__`, gruppi; tipo e traceback restano, quindi
   > gli `except` dei chiamanti non cambiano), il processore `mask_event_dict` dopo `format_exc_info` e prima del JSON, e
   > `SecretMaskingFilter` sui due handler (console e file) per i logger delle librerie. `assets/core.py`:
   > `configured_provider(code, *, user_id=None)`, `call_provider(provider, fn, *, timeout, scope=None)` (`NOT_CONFIGURED`
   > prima di ogni I/O, poi segreti in volo; il punto d'aggancio di X1–X7 è scritto lì), `settings_cache_part`,
   > `settings_cache_part_for`. `fx/runtime.py` (nuovo): `configured_fx_provider`, `call_fx_provider`,
   > `FXNotConfiguredError` in `fx/base.py`; tutte le chiamate ai fornitori FX passano di lì (`ensure_rates_multi_source`,
   > `_fetch_provider`, il catalogo). Siti cambiati: ricerca (anche in streaming e `resolve_url`, con `user_id` dagli
   > endpoint), prova della configurazione (con `user_id`), metadati, prezzo dal vivo, refresh; ogni cache dei risultati di
   > un fornitore ha l'impronta nella chiave (query di ricerca, metadati, storico e corrente, scaricamento FX, valute FX:
   > per un fornitore senza campi la chiave del catalogo FX resta il codice, come prima). Restano istanze semplici dove non
   > c'è una chiamata: elenco dei fornitori, `get_asset_url`, il controllo del tipo parametrico, il validatore dei parametri,
   > il preriscaldamento, la capacità di volume. Un oggetto che non è un plugin (un doppio di test) passa dal confine senza
   > controlli. Prova a mano (`/tmp/libreFolio_x_cp10_mask_smoke.py`, logging vero dell'app): un plugin che solleva e
   > scrive nel log il proprio segreto dal thread (structlog e `logging`), poi un `logger.exception` dopo il confine: il
   > messaggio, i `details` e la causa sono mascherati, nel log né il segreto né la sua forma codificata, 7 `***`; un campo
   > obbligatorio senza valore dà `NOT_CONFIGURED` con `details.missing`.
   > **⚠️ Fuori pista**: l'impronta nelle chiavi dello storico e del corrente avrebbe spento in silenzio due invalidazioni
   > che ricostruiscono la chiave a mano (`currency_change.py`, `provider_management.py`): allineate con
   > `settings_cache_part_for`. Un'entrata salvata con altre impostazioni ha un'altra chiave: nessuna lettura la raggiunge
   > e scade con il suo TTL. Trovata anche, preesistente e non toccata, la chiave della cache dei metadati senza
   > `provider_params`.
   > **Nota per Z** (da girare): il primo argomento di `call_provider` è l'istanza configurata, non il codice; per i cambi
   > il confine unico è `call_fx_provider` (`fx/runtime.py`), usato anche da `_fetch_provider`.
6. ✅ (2026-10-15) API e schemi: catalogo, scrittura tutto o niente, permessi, segreti in sola scrittura.
   > **Note implementazione**: `schemas/plugin_settings.py` (letture: nessun campo per il valore di un segreto, solo
   > `is_set`, `source`, `locked`, `problem`; scrittura: `value` | `secret_value: SecretStr` | `clear`, da 1 a 100 voci) e
   > `api/v1/plugin_settings.py`: `GET /api/v1/settings/plugins` (filtri `family`, `plugin_code`; un plugin `test_only`
   > solo se nominato) e `PATCH /api/v1/settings/plugins/bulk` (422 con `detail.results` di ogni voce, 409, 503).
   > Regole in `services/plugin_settings/service.py`: campi di sistema scritti solo da un amministratore, letti da tutti
   > (un segreto solo come impostato o no); campi personali solo del loro utente, mai mostrati ad altri, amministratore
   > compreso; un campo bloccato dall'ambiente dà `LOCKED_BY_ENV` e, nel profilo gestito, non compare e dà `UNKNOWN_FIELD`;
   > ogni voce controllata prima di scrivere, poi una transazione; il log dice chi ha scritto quali campi, mai i valori.
   > Riga in `api/v1/router.py` dopo `settings.router` (file condiviso, da dichiarare). Prova dal vivo sulla corsia (server
   > `--test --port 6183 --no-scheduler --no-reload`, DB popolato passato da 005 a 007 all'avvio):
   > `/tmp/libreFolio_x_cp10_api_smoke.py`, 38/38 — catalogo e filtri, i rifiuti tutto o niente (ogni voce col suo
   > esito, niente scritto), i valori fuori limite, il doppione, il segreto nel campo sbagliato, scope sbagliato, scritture
   > di admin e utente, isolamento fra i due, consegna al plugin con la ricerca `lf-settings-echo` (l'utente riceve i suoi
   > campi, l'admin i default), cancellazione, nel DB nessun marcatore in chiaro (`iterdump`), pulizia a zero righe; in 22
   > risposte, nel log del server e in `librefolio.log` della corsia nessuna traccia dei marcatori. I cambi: `MOCKFX` col
   > suo segreto e il suo intero, in sola lettura per l'utente (`FORBIDDEN_SCOPE`); l'elenco dei fornitori FX resta
   > `BOE, ECB, FED, SNB`. `api schema` contro la base (`git archive dae4de4fa` in `/tmp`, `app.openapi()` dei due alberi):
   > solo aggiunte, 2 percorsi e 14 schemi `PluginSetting*`, nessuna operazione o schema esistente cambiato; `api sync`
   > senza file tracciati cambiati (il client generato è ignorato).
   > **⚠️ Fuori pista**: la prova ha trovato una fuga. Il 422 di validazione di FastAPI rimanda l'`input`, e con un campo
   > mancante, con 101 voci o con un segreto non testuale il segreto tornava in chiaro (solo a chi l'aveva mandato, ma un
   > toast o un proxy lo mostrano). Corretto con una `route_class` del solo router (`_NoInputEchoRoute`, come `ToolRoute`
   > in `tools.py`): stesso 422, senza `input`, rilanciato fuori dall'`except` perché non tenga l'errore originale. Riprova
   > dei cinque casi (`/tmp/libreFolio_x_cp10_leak_probe.py`): nessun eco, `loc`/`msg`/`type`/`ctx` intatti. Da coprire
   > nelle prove del passo 7.
7. ✅ (2026-10-15) Prove (test-author): unità, API, migrazione, sicurezza (segreto marcatore in risposte, log, errori, AI Export;
   permessi; chiave cambiata; cascata); voci del runner.
   > **Note implementazione**: 8 file nuovi, 8 unità nuove, tutte verdi. Services, `pure` (DB privati sotto
   > `tmp_path`, motore privato al posto di `runtime.get_async_engine`, chiave di prova con monkeypatch, nessun file di
   > chiave nella corsia):
   >
   > | unità | test |
   > |---|---|
   > | `plugin-settings-contract` | 190 |
   > | `plugin-settings-crypto` | 30 |
   > | `plugin-settings-runtime` | 79 |
   > | `plugin-settings-service` | 54 |
   > | `secret-masking` | 48 |
   > | `plugin-settings-guards` | 25 |
   >
   > Le altre due:
   > - db `migration-007` (29, `pure`);
   > - api `plugin-settings` (11, 24 s, verde due volte), **esclusiva**. Ragione scritta: scrive e cancella i campi di
   >   sistema di `mockprov`, la cui impronta sta nelle chiavi di cache di ogni chiamata a `mockprov`, quindi un'unità
   >   concorrente perderebbe le sue voci a metà prova.
   >
   > Dati: i campi personali solo su utenti che la prova crea e cancella; la metà SET NULL con un admin usa e getta;
   > `MOCKFX` solo letto via HTTP. Il guard: le variabili dei campi di sistema dei plugin veri in `.env.example`
   > (barriera sintetica, nessun plugin vero ne dichiara), nomi derivati unici, nessun alias letto dall'app stessa
   > (barriera: `LIBREFOLIO_INSTANCE_KEY`), `services/ai_export/` non importa le impostazioni.
   >
   > X-R6 in `test_config_package.py` (di H, dichiarato): sei casi e i nomi dei due test aggiornati alla regola nuova.
   > Voci in `_backend_services.py`, `_backend_api.py`, `_backend_db.py` (`migration-007` anche in `db_order`).
   > Orfani: puliti (305 file). Unità esistenti verdi (services `config-package` 656, `config-env-example` 36,
   > `config-audit` 90, `provider-registry` 7, `provider-registry-misc` 23, `provider-contracts` 435, `web-link-finder`
   > 29, `fx-catalog` 8, `settings` 23; api `fx` 21, `assets-provider` 24, `account-deletion` 6; db `validate` 17,
   > `migration-006` 37, `post-migration` 41; schemas `assets` 70, `fx-routes` 34).
   > **⚠️ Fuori pista**: le prove hanno trovato due difetti del CP10.
   > (1) `configure_instance` cadeva su un oggetto senza `settings_fields` (i doppi dei test): 500 in `fx-unit`, rossi in
   > `asset-source` e `provider-core-cache`. Corretto con `getattr(..., "settings_fields", ())`, come i confini.
   > (2) `refresh.py` non esponeva più `AssetProviderRegistry`, che due test degli asset prendevano da lì: riparati da
   > test-author importando la classe dal suo modulo (`assets/registry.py`).
   > Prima dell'irrobustimento le prove avevano visto anche due fughe del mascheramento (il messaggio di un gruppo di
   > eccezioni, valori non testuali nei log): chiuse dall'irrobustimento del passo 9 e coperte.
8. ✅ (2026-10-15) X-R6, documentazione (docs-writer), `.env.example`.
   > **Note implementazione**: X-R6 nel codice dal passo 5 (`config/plugins.py`, `web_link_finder.py`), chiusa nel
   > backlog. docs-writer, solo inglese:
   > - nuova `developer/architecture/patterns/plugin_settings.md`;
   > - una sezione «Settings» in `asset_plugin_guide.md` e `fx_plugin_guide.md`;
   > - la frase sulla registrazione in `registry_pattern.md`;
   > - `## 🧩 Plugin Settings` in `admin/configuration.en.md`;
   > - le due tabelle in `database/users_access.md` e la 007 in `database/index.md`;
   > - la riga di `core.py` e le chiavi di cache in `backend/assets/architecture.md`;
   > - TIMEOUT e MAX in `search_link_finder.md`;
   > - una riga in `admin/hosting_providers.en.md`, `architecture/settings.md` e `api/index.md`.
   >
   > Una riga nella nav di `mkdocs.yml`. Nessun timbro di traduzione: il debito è reale e tocca solo
   > `admin/configuration.{it,fr,es}.md`.
   > `.env.example`: la sezione «Plugins» (lo schema dei nomi, alias solo per un segreto, una variabile non valida ferma
   > il plugin) e «at least 1» per TIMEOUT e MAX.
   > **⚠️ Fuori pista**: la rilettura del codice di docs-writer ha portato alle due correzioni di prodotto del passo 9
   > (variabile non valida; chiave inutilizzabile). Restano per H due note su `architecture/security.md`, che è sua e
   > non ho toccato: l'elenco dei segreti di `env_secret()` non nomina le variabili dei plugin, e il «known limitation»
   > dice «planned» per un controllo della chiave che il CP10 rende possibile (`key_id` per riga,
   > `plugin_secrets_key_status`).
9. ✅ (2026-10-15) `security-review`, poi `all-backend` (slot del coordinatore), poi il checkpoint.
   > **Note implementazione (security-review, 15/10)**: fatta prima del checkpoint, come chiesto, su tutto il diff del
   > CP10 (test e documentazione esclusi, in scrittura). Esito: **nessuna vulnerabilità sfruttabile**. Verificati: nonce,
   > completezza dell'AAD, `key_id` e impronta come oracolo, IDOR su `user_id`, profilo gestito, plugin `test_only`
   > raggiungibili per nome, corpi dei 422/409/503, flusso SSE, ordine dei processori del log, percorso `_FILE`,
   > downgrade. Tre lacune latenti (nessun plugin vero dichiara oggi un segreto), chiuse subito perché nel codice del CP10:
   >
   > | # | Gravità | File | Lacuna | Cura |
   > |---|---|---|---|---|
   > | 1 | ⚪ LOW (latente) | `utils/runtime/secret_masking.py` | un valore non testuale (un URL `httpx`, byte, un'eccezione nei `details`) non veniva mascherato, e `_json_safe_details` lo trasformava in testo per la prova: un segreto di sistema poteva arrivare a un utente qualsiasi | ogni valore giudicato dal testo che mostra (`str`/`repr`); chiavi dei dict, attributi e note delle eccezioni, nomi di file di `OSError`; un errore che mostra ancora un segreto (`__str__` su stato irraggiungibile) è sostituito al confine da `PROVIDER_ERROR` / `FXServiceError` senza legami con l'originale |
   > | 2 | ⚪ LOW (latente) | `plugin_settings/fields.py` | due plugin potevano leggere la stessa variabile (`foo_bar`+`baz` e `foo`+`bar_baz`, o un alias): il segreto di uno poteva comparire come valore normale dell'altro, che il catalogo mostra a tutti | una variabile appartiene a un solo campo di un solo plugin (`claim_env_variables`, alla registrazione, dopo i controlli dei codici doppi); alias solo su un campo segreto di sistema e fuori da `LIBREFOLIO_PLUGIN_`; nessuna chiave che finisca in `_file` |
   > | 3 | ⚪ LOW (latente) | `plugin_settings/fields.py` | il mascheramento come oracolo: la prova rimanda l'identificativo e maschera il segreto, quindi con 4 caratteri un utente poteva provare a indovinarlo | `SECRET_MIN_LENGTH_FLOOR` da 4 a 8 (= il default) |
   >
   > Prova a mano (`/tmp/libreFolio_x_cp10_hardening_smoke.py`, 29/29): dichiarazioni, collisioni rifiutate anche dal
   > registro vero (il plugin non viene salvato), rilascio dei claim, mascheramento di URL, byte, chiavi, `OSError`,
   > note; ai due confini l'errore mascherabile tiene il tipo, quello opaco è sostituito senza `__cause__` né
   > `__context__`, `CancelledError` mai. Riprova del vecchio smoke del mascheramento col logging vero: invariato (7 `***`,
   > nessun segreto nel log). Scoperta: 6 asset e 7 cambi senza errori; ruff e black puliti. test-author e docs-writer
   > avvisati dei cambi mentre scrivevano.
   > **⚠️ Fuori pista**: `NOT_CONFIGURED` e `PROVIDER_ERROR` non hanno una chiave `providerErrors.*`: la prova mostra il
   > messaggio inglese (il ripiego di `resolveProviderError.ts`). Le chiavi nelle 4 lingue vanno nel CP11, con la UI.
   > **⚠️ Fuori pista (dalla rilettura di docs-writer, 15/10)**: due lacune di prodotto, corrette.
   > (1) Una variabile impostata ma non valida (valore o `_FILE` illeggibile) non lasciava traccia nel log, e un campo
   > facoltativo col default arrivava al plugin come `None`, rompendo il contratto «un campo col default ha sempre un
   > valore». Ora il campo conta in `missing` anche se facoltativo: il plugin non è configurato e il confine rifiuta con
   > `NOT_CONFIGURED`; un avviso per processo e per variabile, col motivo e mai il valore. Mai il default: è il «mai un
   > ripiego muto» del disegno approvato. Così è vera anche la frase della sezione «Secrets» di `.env.example`.
   > (2) Con la chiave d'istanza inutilizzabile (un file generato guasto: H fa partire il server lo stesso, con un errore
   > nel log) `GET /settings/plugins` dava 500 appena c'era un segreto salvato, e un segreto dall'ambiente faceva fallire
   > le chiamate (l'HMAC dell'impronta). Ora i segreti salvati risultano `unreadable` (catalogo e chiamate), un errore
   > nel log per processo, quelli dall'ambiente arrivano ancora, e l'impronta senza chiave usa i soli nomi dei segreti
   > (con la chiave guasta solo l'ambiente fornisce segreti, fissi per il processo). `plugin_secrets_key_status` dà i
   > totali come illeggibili invece di sollevare, e deriva la chiave in `asyncio.to_thread`: prima la leggeva dentro un
   > `async def`, contro la regola dell'I/O. Prova: `/tmp/libreFolio_x_cp10_env_key_smoke.py`, 11/11.
   > Restano, accettati e scritti nella guida: la lista delle valute di riserva di un fornitore FX (5 minuti dopo un
   > errore) è per codice, non per impostazioni; una ricerca senza `providers` interroga anche i plugin `test_only`
   > (`search.py:204` e `:348`, preesistente): da escludere nel FE5a, quando il frontend smette di filtrare `mockprov` per
   > nome.
   > **`all-backend --workers 2`** (slot pesante 2 del coordinatore, 19:37–20:21, corsia 6183,
   > `--log-dir /tmp/libreFolio_x_cp10_allbackend`): 5 categorie su 7 verdi (External, DB 18/18, Utils, Schemas, E2E).
   > Le fasi parallele: 3364, 5268 (1 saltato), 1308, 1230, 705, 1000 test. Due rossi, uno per categoria:
   > - services `fx-sync-service`, **del CP10**: `test_sync_pairs_bulk_repeated_provider_cache_hit_preserves_source_and_steps`
   >   fissa la chiave della cache di `_fetch_provider` a tre elementi, e dal CP10 c'è l'impronta come quarto. test-author
   >   l'ha riparato tenendo l'intento (la chiave intera con `settings_cache_part`) e ha cercato altre chiavi scritte a mano.
   >   Ne ha trovata un'altra, verde ma svuotata dal CP10:
   >   `test_provider_core_cache.py::TestProbeBypassesCache::test_probe_bypasses_all_core_caches_and_executes_each_operation_through_thread_boundary`.
   >   La prova pianta sentinelle sotto le chiavi che i percorsi con cache calcolerebbero, per mostrare che la prova di
   >   configurazione non le legge. Senza la parte delle impostazioni, una prova che usasse la cache le avrebbe mancate
   >   passando lo stesso. Ora ogni chiave chiude con `settings_cache_part`.
   >   Riprove da sole, come chiesto dal coordinatore (ruff e black puliti sui due file): services `fx-sync-service` 5,
   >   utils `provider-core-cache` 29, services `fx-catalog` 8, api `fx` 21, tutte verdi; i due test riparati risultano
   >   PASSED nei log.
   > - api `pac-planner-tool`, **non del CP10**: vedi il «Fuori pista» sotto.
   > Slot liberato alle 20:21 e detto al coordinatore (niente secondo `all-backend`, d'accordo col coordinatore).
   > **⚠️ Fuori pista (ambiente)**: `test_pac_planner_tool_api.py::test_pac_compute_plans_the_compact_twin_like_the_explicit_request`
   > dà `(1, 1)` invece di `(2, 0)`. Da sola passa 12/12 in 18 s, con la macchina a 80. Verdetto (`test-triage`):
   > **environment**. Girava nel passo consolidato delle API con la macchina a 75–121 su 10 core, e il CP10 non tocca il
   > percorso dei Tools. La causa esatta non si recupera: i Tools non scrivono un elemento fallito nel log, e la prova
   > controlla i conteggi prima di stampare i risultati. Il suggerimento (`results` nel messaggio dell'asserzione) lo
   > gira il coordinatore a J.

### Note arrivate durante il CP10 (15/10, sera)

- **X-R12, da W (E1b), girata dal coordinatore e valutata**: il refresh chiede la storia fino a ieri
  (`refresh.py:227`), e un evento del fornitore datato oggi (un dividendo, uno split) arriva il giorno dopo.
  - Il taglio è voluto per i prezzi: la chiusura di oggi non c'è ancora, e il valore di oggi viene da
    `get_current_value`.
  - Per gli eventi no: viaggiano solo nella stessa chiamata.
  - Nessun errore di valore: uno split sposta le posizioni con la transazione ADJUSTMENT legata all'evento
    (`portfolio/engine.py:213-223`). Solo un giorno di ritardo per l'evento, per il suo collegamento e per AI Export.
  - Cura proposta: storia fino a oggi, poi via il prezzo di oggi prima della cache e della scrittura, tenendo gli
    eventi. Due cose da verificare: la copertura `dates` della cache, e `end_date` inclusivo in ogni plugin (e
    `scheduled_investment`).
  - Un lotto piccolo dopo X1–X8, fuori dal CP10. Voce nel backlog, sezione X.
- **Z7a è in `dev_release2`** (`2ab8a3a43`): `services/platform/provider_cooldown.py` e `utils/runtime/cooldown.py`.
  X1–X8 può chiamarlo da `call_provider` / `call_fx_provider`, dove il punto d'aggancio è scritto. La previsione dei
  conflitti contro `10d5ccd2d` non tocca i miei confini: Z7a non ha cambiato `assets/core.py` né `fx/`.
- **`backend/app/main.py` congelato** fino al CP2b di H, che lo divide in `services/platform/lifecycle.py`,
  `middleware.py`, `static_site.py` e `database_bootstrap.py`. Un passo d'avvio o di spegnimento, o un middleware, di un
  mio lotto aspetta il CP2b, e poi è una riga nel modulo giusto. Il CP10 non tocca `main.py`.
- **X-R13, per il FE5c** (dal programma colori, DV-3): con DV `AllocationEntry` perde `emoji`, ma il `map` dei settori
  in `routes/(app)/assets/[id]/+page.svelte:3496` (su `dev_release2`) lo calcola ancora: da togliere col taglio della
  pagina. Voce nel backlog, sezione X.

### Checkpoint CP10 ✅ (2026-10-15) — committato dal coordinatore: `efa135c75` (codice) e `6f8b81e32` (journal)

### Decimo aggiornamento di base: `dev_release2` (`6102d5097`) nel ramo X ✅ (2026-10-15) — merge `f2a766f45`

Dentro: CP2b di H (`main.py` diviso in `services/platform/`), E2 (`router.py` email), B e B8 (backup), W, J CP-4, Z6b
parte 1, Y2. Merge aperto dal coordinatore e committato da lui (`f2a766f45`, genitori `6f8b81e32` e `6102d5097`).

- **Conflitto**: uno solo, quello previsto, in `developer/architecture/settings.md`. Risolto tenendo la lista del target
  (`LF_APP_VERSION`, `LIBREFOLIO_BLOCKED`, `LIBREFOLIO_DELETION_DATE`) e aggiungendo le variabili delle impostazioni
  dei plugin (`LIBREFOLIO_PLUGIN_*` e gli alias dei segreti, anche come `_FILE`). Le altre due aggiunte del CP10 nel
  file sono passate da sole. `git add` del solo file.
- **Controlli di significato**:
  - `router.py`: le due include, `plugin_settings` dopo `settings` ed `email`;
  - `logging_config.py`: intatto, con il filtro sui due handler e il processore dopo `format_exc_info`; il CP2b non lo
    tocca, e `main.py` chiama ancora `configure_logging`;
  - Alembic: una sola 007 sopra la 006;
  - B8 legge `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`, anche come `_FILE`. Né `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` né le
    variabili nuove di Z (`LIBREFOLIO_PROVIDER_COOLDOWN_*`, `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`) stanno nello spazio
    `LIBREFOLIO_PLUGIN_`, e nessuna è un alias: i claim non c'entrano. Lo conferma la guardia.
- **Prove sulla revisione combinata**, una alla volta con `nice -n 10`, tutte verdi:
  - db `migration-007` 29, `post-migration` 41;
  - services: contract 190, crypto 30, runtime 80, service 54, guards 25, `secret-masking` 48, `config-package` 679,
    `config-env-example` 36.
  Poi la pausa delle prove chiesta dal coordinatore (galleria di DV, macchina a 89): fermata la sequenza dopo l'unità in
  corso, senza toccarla (`kill` del solo script).
  **⚠️ Fuori pista (ambiente, ordine delle mie prove)**: api `plugin-settings` è uscita 11 rossi su 11 in 11 s. Ogni
  `services <unità>` lanciata da sola esegue prima `_services_setup()`, che ricrea vuoto il DB della corsia (il file
  è nato alle 20:39:56, durante `config-env-example`). Il setup delle API (`_api_setup` → `db populate`) gira solo
  con `api all`. La prova ha trovato 0 utenti, e la sua precondizione lo ha detto: «the api setup (db populate) did
  not run on this lane». Non c'entrano né il merge, né `main.py`, né `router.py`: le rotte rispondono.
  Rimedio, dopo la pausa: `test db populate --force` sulla corsia (il setup stesso delle API), poi api
  `plugin-settings`, `fx`, `assets-provider`, `check-orphans`, `api sync`. La nota per T (una `api <unità>` dopo una
  `services <unità>` trova il DB vuoto) è passata al coordinatore.
- **Dopo la ripresa** (20:54), con il via del coordinatore, una alla volta con `nice -n 10`, aspettando un carico ≤ 70:
  - `test db --force populate` sulla corsia: il setup stesso delle API, PASSED;
  - api `plugin-settings` 11 su 11 (stesse 11 prove, ora verdi), `fx` 21, `assets-provider` 24;
  - `check-orphans`: ogni prova registrata raggiungibile da `all` (backend 323, frontend e2e 127, Vitest 421);
  - `api sync`: nessun file tracciato cambiato.
  Porta 6183 libera; i tre processi Python rimasti sono di altre corsie (6182 A, 6184 W, 6186 Z).
  **⚠️ Fuori pista**: l'avviso della seconda pausa (dalle 21:00) mi è arrivato dopo. `api assets-provider` era già in
  corso e ha finito alle 21:01:11. Dopo, lo script ha lanciato da solo due passi leggeri, `check-orphans` (7 s, una
  scansione dei file) e `api sync` (24 s), finiti alle 21:01:42. Da allora niente in esecuzione.

## X-RL (X1–X8) — il contratto dei limiti dei fornitori, sopra Z7a ✅ (15/10, 21:03–23:16; FROZEN, in attesa del checkpoint)

> **Via del coordinatore** (15/10, 21:03): «Via a X1–X8, il contratto dei limiti dei fornitori sopra Z7a, che è già
> dentro.» Base: `86da642c3` (= `dev_release2`, avanzamento veloce del coordinatore). Disegno: piano 06 di Z, sezione
> «Z7 — disegno», contratto X1–X8; decisioni D-Z7-1…4 del coordinatore (attuazione della decisione 34 del developer).

### Analisi sul codice (15/10)

- **Z7a** (`utils/runtime/cooldown.py`, `services/platform/provider_cooldown.py`):
  - `RateLimitedError(retry_after, scope)`, `retry_after_seconds()`;
  - `wait_before_call(domain, provider, scope)` (0 o i secondi che mancano; alla scadenza un solo tentativo);
  - `record_refusal(…, retry_after) -> attesa`, `record_success`, `record_no_verdict` (altro errore, timeout,
    cancellazione: libera il tentativo).
  Sincroni, in memoria, impostazioni lette a ogni chiamata (0 spegne).
- **I segnali dei fornitori**:
  - yahoo: `yfinance` 1.7.0 ha `YFRateLimitError`; `_yf_with_retry` riprova anche i 429 con `sleep` 1,5–3–6 s;
  - css_scraper: `httpx.HTTPStatusError` (oggi `HTTP_ERROR`), l'URL è l'identificativo, quindi lo scope è il suo host;
  - justETF: `justetf_scraping` non ha eccezioni sue: `RuntimeError("…status 429…")` (`helpers.py:64`,
    `etf_profile.py:232`), riconoscibile solo dal testo;
  - Borsa Italiana: `borsa_italiana_scraping` 0.3.2 ha `RateLimitRaggiunto`, per un 429 dopo i suoi ritentativi con
    `sleep` 2–4 s, e per un 403 del WAF;
  - FX ECB, FED, BOE, SNB: `httpx` con `raise_for_status()`, poi `FXServiceError`.
- **I confini** sono già unici dal CP10: `call_provider(provider, fn, *, timeout, scope=None)` per gli asset (ogni
  chiamata: dal vivo, refresh, metadati, ricerca anche in streaming, `resolve_url`, prova) e `call_fx_provider` per i
  cambi (sync, `ensure_rates_multi_source`, catalogo delle valute). Le cache stanno già prima del confine.
- **Gli schemi**: `FACurrentPriceItem` (`prices.py:352`), `FARefreshResult` (`refresh.py:111`), `FXSyncPairResult`
  (`refresh.py:206`) e `BaseProbeOperationResult` (`provider.py:346`, ha già `error_code` ed `error_details`). La
  ricerca: `providers_with_errors` è una lista di codici; l'evento SSE `provider_error` è un JSON libero.

### Scelte

1. Ai consumatori arriva come `retry_after` **l'attesa decisa dal confine** (`record_refusal`, ≥ il `Retry-After` del
   fornitore), non il solo `Retry-After`: è il tempo dopo cui una chiamata passa davvero.
2. Lo scope lo dà il plugin con l'hook `cooldown_scope(identifier, identifier_type, provider_params)` (default `None`;
   css_scraper: l'host). Lo calcolano i chiamanti, che hanno l'identificativo, con `core.cooldown_scope_for(...)`, e lo
   passano a `call_provider`; la ricerca non ha identificativo, quindi scope `None`.
3. I doppi dei test che non sono plugin restano fuori dalle pause, come restano fuori dalle impostazioni.
4. yahoo: un rifiuto per troppe richieste non si riprova più nel thread (via i `sleep` sul 429); gli altri errori
   transitori sì. justETF dal testo `status 429`; Borsa Italiana da `RateLimitRaggiunto`. I `sleep` interni della
   libreria di Borsa restano: è un pacchetto a parte; lacuna scritta nella guida.
5. Ricerca: `providers_with_errors` resta com'è; l'evento `provider_error` aggiunge `error_code` e `retry_after`.
6. Prova (X8): `retry_after` in `BaseProbeOperationResult` e in `error_details`; la UI mostra «in pausa fino alle
   HH:MM» con l'ora locale, chiave nuova `providerErrors.RATE_LIMITED` nelle 4 lingue; un'operazione in pausa è
   un avviso, non un fallimento.
7. Modalità «troppe richieste» dei doppi:
   - `mockprov`: il parametro `mock_rate_limited` (secondi, o `true`) e la ricerca `lf-rate-limited`;
   - `mockfx`: due attributi di classe per le prove in processo.
   Mai una pausa vera sul backend condiviso.

### Passi

1. ✅ (2026-10-15) X1/X2: `AssetRateLimitedError`, `FXRateLimitedError`, gli aiuti per riconoscere un 429, l'hook `cooldown_scope`.
   > **Note implementazione**: `assets/base.py`:
   > - `AssetRateLimitedError(AssetSourceError, RateLimitedError)`: codice `RATE_LIMITED`, `retry_after`, `scope`;
   > - gli aiuti `rate_limited_from_response` (un 429 di `httpx` o `requests` col suo `Retry-After`),
   >   `rate_limited_from_exception` (anche dal testo «status 429» / «HTTP 429») e `raise_if_rate_limited`;
   > - l'hook `cooldown_scope(identifier, identifier_type, provider_params)` del plugin, default `None`.
   >
   > `fx/base.py`: `FXRateLimitedError(FXServiceError, RateLimitedError)`, `fx_rate_limited_from_response`,
   > `raise_if_fx_rate_limited`, `longest_refusal` e `raise_longest_refusal`.
2. ✅ (2026-10-15) X4: le pause nei due confini; lo scope dai chiamanti.
   > **Note implementazione**: `core.call_provider` e `fx/runtime.call_fx_provider` chiamano Z7a:
   > - prima `wait_before_call`: in pausa → `AssetRateLimitedError` / `FXRateLimitedError` subito, senza thread né I/O;
   > - dopo, un `RateLimitedError` → `record_refusal`, e l'errore riparte con `retry_after` = la pausa decisa;
   > - una risposta → `record_success`; ogni altra fine, cancellazione compresa → `record_no_verdict`.
   >
   > Un `RateLimitedError` che non è dell'errore del dominio, o che mostra ancora un segreto, è sostituito da un
   > `AssetRateLimitedError` / `FXRateLimitedError` senza legami. `core.cooldown_scope_for` chiama l'hook in modo sicuro
   > (un hook che fallisce → `None`, nel log). Lo scope arriva da:
   > - il dal vivo di `price_query`;
   > - le due chiamate di `refresh`;
   > - `metadata`;
   > - le tre operazioni della prova.
   >
   > La ricerca e `resolve_url` restano senza scope.
3. ✅ (2026-10-15) X3: i fornitori (yahoo, css_scraper, justETF, Borsa Italiana, 4 FX) e le modalità dei doppi.
   > **Note implementazione**:
   > - **yahoo**: `_is_rate_limited` (`YFRateLimitError`, o `429` come parola intera, «too many requests», «rate
   >   limit») → `AssetRateLimitedError` in `_yf_with_retry`, senza ritentativi; tolti dalle parole transitorie. Ricerca
   >   e metadati ora lo lasciano passare: prima ogni errore diventava `[]` o `None`.
   > - **css_scraper**: un 429 → `AssetRateLimitedError` con `Retry-After` e scope = host; l'hook `cooldown_scope` dà
   >   l'host dell'URL (identificativo). `_url_host` regge un URL malformato.
   > - **justETF**: il testo «status 429» nei quattro gestori.
   > - **Borsa Italiana**: `RateLimitRaggiunto` (429 dopo i ritentativi della libreria, 403 del WAF) nei cinque gestori.
   > - **I 4 FX**: un 429 nei gestori `httpx`. Una valuta rifiutata rifiuta tutta la chiamata: BOE e FED dopo il
   >   `gather`, ECB si ferma nel suo ciclo seriale.
   > - **Doppi**: `mockprov` col parametro `mock_rate_limited` (secondi, o `true`) in corrente, storico e metadati, e
   >   la ricerca `lf-rate-limited` (`Retry-After` 30 s); `MockFXProvider.rate_limited` /
   >   `.rate_limited_retry_after`, che valgono per il catalogo e le quotazioni.
   >
   > Prova: l'app si importa; scoperta: 6 asset e 7 cambi senza errori; ruff e black puliti.
   > **⚠️ Fuori pista**:
   > - Al primo giro i rami aggiunti portavano 5 funzioni sopra il limite di complessità (C901). Invece di `noqa`, aiuti
   >   che sollevano da sé: una riga per gestore, nessun ramo.
   > - Una sostituzione automatica degli import, troppo larga, aveva fuso le righe di import seguenti in 6 file.
   >   Riparata ricostruendo il blocco dalla versione di HEAD; controllo con `ast` e diff di sole righe d'import volute.
4. ✅ (2026-10-15) X5: gli schemi e i servizi che li riempiono (dal vivo, refresh, sync FX, prova, evento della ricerca); `api sync`.
   > **Note implementazione**: `error_code` e `retry_after` (secondi, `ge=0`) in `FACurrentPriceItem`,
   > `FARefreshResult` e `FXSyncPairResult`; `retry_after` in `BaseProbeOperationResult`. Chi li riempie:
   > - **dal vivo** (`price_query`): una pausa ripiega sull'ultimo prezzo come prima (`db:last_known`, HTTP 200), con
   >   codice e attesa; anche senza prezzo salvato;
   > - **refresh**: `_fetch_refresh_item` restituisce anche il rifiuto incontrato, storico o corrente (vince l'attesa più
   >   lunga); `_persist_refresh_items` lo aggiunge al risultato finito con `model_copy`, che sia fallito o parziale, e
   >   `_persist_refresh_item` resta com'è;
   > - **sync FX**: i fornitori in pausa registrati da `_fetch_provider` (INFO, non più un'eccezione nel log); dopo il
   >   `gather`, una coppia FAILED o PARTIAL con uno di loro nelle sue rotte prende `RATE_LIMITED` e l'attesa più
   >   breve; una coppia servita per intero da un'altra rotta resta com'è;
   > - **prova**: `_probe_failure_fields` mette `retry_after` sul risultato e in `error_details`;
   > - **ricerca**: un fornitore in pausa scrive un INFO al posto di un traceback, e l'evento SSE `provider_error` porta
   >   `error_code` e `retry_after`; la risposta non in streaming non cambia.
   >
   > `api sync` fatto; il client generato è ignorato.
5. ✅ (2026-10-15) X8: la UI della prova e la chiave i18n.
   > **Note implementazione**: `resolveProviderError.ts`: `RATE_LIMITED` → `providerErrors.RATE_LIMITED`, «…fino
   > alle {time}». L'attesa viene da `retry_after` o da `error_details.retry_after`, e `formatResumeTime` arrotonda per
   > eccesso al minuto in `uiLocale()`: solo l'ora oggi, data e ora un altro giorno. Senza attesa,
   > `providerErrors.RATE_LIMITED_NO_TIME`. `providerProbe.ts`: `RATE_LIMITED` in `SOFT_FAIL_CODES`, un avviso: la
   > configurazione può essere giusta, e il messaggio dice fino a quando. `ProviderAssignmentSection.svelte` non
   > cambia: passava già `error_details`. Le due chiavi nelle 4 lingue con `dev.py i18n add` (sorgente
   > `i18n/assets/`). Prove: Vitest `resolveProviderError` + `providerProbe` 36/36; Prettier invariato;
   > `front check` 0 errori e 0 avvisi.
   > Il primo smoke dei confini (`/tmp/libreFolio_x_rl_smoke.py`) dà 17/17:
   > - il rifiuto mette in pausa per max(base, `Retry-After`);
   > - durante la pausa nessuna chiamata;
   > - dopo la scadenza passa un tentativo solo, e il successo toglie la pausa;
   > - lo scope per host, i riconoscitori e il confine FX;
   > - a pause spente ogni chiamata arriva al fornitore, con il suo `Retry-After`.
   > **⚠️ Fuori pista (dalla rilettura di docs-writer, 15/10)**: cinque correzioni.
   > - **Il riassunto della prova** (`summarizeProbeError`) taglia a 60 caratteri, e in spagnolo l'ora andava persa.
   >   Testi accorciati, sotto i 60 nelle 4 lingue anche con la data (misurati). Una chiave in più,
   >   `providerErrors.RATE_LIMITED_DAY`, perché in italiano «fino alle» non regge una data, e in FR/ES nemmeno; il
   >   nuovo `resumesToday` sceglie la chiave.
   > - **SNB**: anche la richiesta della mappa delle valute riconosce un 429 (`_ensure_currency_map`).
   > - **Borsa Italiana `resolve_url`**: i due gestori best-effort non ingoiano più un rifiuto: il fornitore va in
   >   pausa, e la ricerca salta comunque quell'URL. Resta best-effort solo la scheda del fondo dentro la ricerca.
   > - **Le docstring**: la libreria di Borsa dorme 2, 4 e 8 s, non 2 e 4; `_yf_with_retry` fa al massimo tre
   >   tentativi, con attese di 1,5 e 3 s.
   > - **Il commento di `refresh.py`** prometteva il comportamento di Z7b, che non c'è ancora.
   >
   > Vitest 36/36, Prettier e ruff puliti.
6. ✅ (2026-10-15) X6: prove (test-author), alla ripresa.
   > **Note implementazione** (test-author). Quattro unità nuove, tutte `pure`:
   >
   > | unità | test |
   > |---|---|
   > | services `rate-limit-errors` | 43 |
   > | services `rate-limit-boundaries` | 33 |
   > | services `rate-limit-http-providers` | 18 (`httpx.MockTransport`) |
   > | services `rate-limit-results` | 22 (DB privato sotto `tmp_path`) |
   >
   > Estesi `provider-errors` (Yahoo, justETF, Borsa Italiana: 177) e i due Vitest (`resolveProviderError` 35,
   > `providerProbe` 30). Ogni prova installa il suo `Cooldowns` (orologio finto, jitter 0) con monkeypatch: nessuna
   > pausa tocca il backend condiviso. Regressioni verdi:
   > - services: asset-source 61, asset-source-refresh 12, asset-source-guards 29, provider-contracts 435,
   >   provider-registry 7, web-link-finder 29, borsa-italiana-search 5 e -funds 17, fx-sync-service 5, fx-catalog 8,
   >   provider-cooldown 66, plugin-settings-runtime 80;
   > - utils: cooldown 112, provider-core-cache 29;
   > - schemas: assets 70, fx-routes 34;
   > - api (dopo `db --force populate`): fx-unit 29, fx 21, assets-provider 24;
   > - `check-orphans` pulito; `providerProbeState` 237 e `svelte-check` 0/0.
   >
   > **Tre osservazioni**:
   > 1. Una coppia FX PARTIAL con una rotta di riserva in pausa prende `RATE_LIMITED`: tenuta, perché finita la pausa
   >    quella rotta può riempire le date che mancano.
   > 2. Il riconoscitore di testo era stretto: allargato a «HTTP Error 429» (urllib), «status code 429» e «Too Many
   >    Requests», con i casi aggiunti alle prove.
   > 3. Un refresh può essere OK con `RATE_LIMITED`: Z7b deve rimandare in base a `error_code`, non allo stato
   >    (nota per Z).
7. ✅ (2026-10-15) X7: guide dei plugin e architettura (docs-writer).
   > **Note implementazione** (docs-writer, solo inglese, tre giri):
   > - **Guide dei plugin**: in `asset_plugin_guide.md` e `fx_plugin_guide.md` una sezione «Too many requests» con le
   >   regole, gli aiuti, l'hook (asset), la regola della chiamata intera (FX), un esempio e le modalità dei doppi.
   > - **Architettura e cambi**: `backend/assets/architecture.md` («Provider Pauses»: il confine, le pause, la tabella
   >   dei chiamanti, i testi della prova); `backend/fx/configuration.md` («Paused Providers»).
   > - **Pagine dei fornitori**: Yahoo, CSS, justETF, Borsa Italiana (le lacune volute) e i quattro FX. Sistemati anche
   >   FED e BOE, che dicevano «sequenziale» per un codice parallelo.
   > - **Altre pagine**: `plugin_settings.md`, `search_link_finder.md`, `api/overview.md` e
   >   `test-walkthrough/external.md`, che dava ancora il 429 di yfinance fra gli errori riprovati.
   > - **Utente**: `create-edit.en.md` (il messaggio della prova), `yahoo-finance.en.md`, `css-scraper.en.md`.
   >
   > Nessuna pagina nuova, nessuna riga in nav. Debito di traduzione: i tre `.it/.fr/.es` delle pagine utente. Le sue
   > riletture hanno portato le correzioni del «Fuori pista» qui sopra, più due in Borsa Italiana: `_fund_metadata`
   > rilancia un rifiuto prima di `except AssetSourceError`, e la scheda di `resolve_url` lo rilancia. Restano
   > best-effort, scritti, solo la valuta (`_price_api_currency`) e la scheda del fondo dentro la ricerca.
   > Le pagine di Z (scheduler, live ticker, variabili `LIBREFOLIO_PROVIDER_COOLDOWN_*`) non sono toccate: i link
   > puntano a `.env.example` finché Z non le scrive (Z-9).
8. ✅ (2026-10-15) Revisione, prove della corsia, checkpoint.
   > **Note implementazione**:
   > - `all-backend --workers 2` sullo slot pesante 1 (22:43–23:16, corsia 6183,
   >   `--log-dir /tmp/libreFolio_x_rl_allbackend`): **7 categorie su 7 verdi**. Le fasi parallele 4796, 4819, 2750, 1119,
   >   586 e 75 test. Le 6 righe ❌ della suite esterna FX sono stampe dentro prove che passano (28 passate, 21 saltate),
   >   identiche nel giro del CP10.
   > - `mkdocs build` (strict, 52 s) e `check-links` (96 link) verdi sulla documentazione finale.
   > - `front check` 0/0; ruff pulito su 31 file. Black segnala solo `_backend_services.py`, che fallisce già a HEAD
   >   per una riga di un altro lotto (l'anteprima della cancellazione dell'account): non toccata.
   > - OpenAPI contro `86da642c3`: solo campi facoltativi aggiunti (`error_code`/`retry_after` in `FACurrentPriceItem`,
   >   `FARefreshResult` e `FXSyncPairResult`; `retry_after` nei tre risultati della prova), nessun `required` cambiato,
   >   nessun percorso.
   > - Previsione dei conflitti contro `45499dec4`: due file in comune (`api/overview.md`, `_backend_services.py`),
   >   entrambi puliti.

### Checkpoint X-RL ✅ (2026-10-15) — committato dal coordinatore: `693b9ac3c` (codice, 58 percorsi) e `65b3fc0c4` (journal)

### Undicesimo aggiornamento di base: `dev_release2` (`84a18fb4c`) nel ramo X ✅ (2026-10-15) — merge `276982a65`, pulito

Dentro anche T+DV (la palette nuova, cambia `SectorListResponse`) e H CP-U1. `api/overview.md` e `_backend_services.py`
si sono fusi da soli, come previsto. Le prove d'ingresso sulla revisione combinata, una alla volta con `nice -n 10` e
un carico ≤ 70 (`/tmp/libreFolio_x_rl_entry_checks.sh`, log in `/tmp/libreFolio_x_rl_entry/`), tutte verdi:
- `api sync`, senza file tracciati cambiati; `front check` 0/0; `front-utility core-unit` 5491, la regola per chi
  tocca i cataloghi i18n;
- services `rate-limit-errors` 55, `-boundaries` 33, `-http-providers` 18, `-results` 22, `provider-errors` 177;
- Vitest `resolveProviderError` e `providerProbe` 65;
- `mkdocs build` (strict) e `check-links` (96), perché `overview.md` si è fuso da solo; `check-orphans` pulito.

Niente secondo `all-backend`, d'accordo col coordinatore: vale quello delle 23:16. Porta 6183 libera.

### X-RL in `dev_release2` ✅ (2026-10-15) — treno 67, merge `da21c48c4`, registri `4ef2fc199`

### CP11 — impostazioni dei plugin nell'interfaccia: analisi ⏳ (2026-10-15, 23:35)

Base: HEAD `276982a65`; worktree pulito salvo questo piano. Disegno di riferimento: §4.4, D-X13, D-X14, D-X15.

**Stato reale verificato**
- Il backend del CP10 è completo.
  - `GET /api/v1/settings/plugins`: filtri `family` e `plugin_code`; un plugin `test_only` compare solo se nominato.
  - `PATCH …/bulk`: tutto o niente; un 422 porta `detail.results`.
  - Ogni campo ha `label_key`, `description_key`, `options[].label_key`, `is_set`, `source`, `locked`, `env_variable`
    (solo per l'admin), `editable`, `problem` e `updated_at`.
  - Client generato: `get_plugin_settings_api_v1_settings_plugins_get`,
    `update_plugin_settings_api_v1_settings_plugins_bulk_patch`.
- Solo i doppi di prova dichiarano campi, ed entrambi sono `test_only`: `mockprov` ne ha 7, di ogni tipo, di sistema e
  personali, con due segreti; `mockfx` ne ha 2. Oggi quindi la scheda, in produzione, sarebbe vuota; con D-X14
  compaiono justETF e Borsa Italiana.
- Il catalogo **non dice se un plugin è configurato**: il calcolo di `missing` vive solo nel resolver
  (`resolver.py:254`).
- La ricerca non dice perché un fornitore non ha risposto.
  - Ricerca semplice: `NOT_CONFIGURED` finisce in `providers_with_errors`, che ha solo i codici.
  - Stream: `provider_error` senza `error_code` (lo porta solo `RATE_LIMITED`).
  - `AssetSearchAutocomplete` ignora ogni `provider_error`.
- Le chiavi `providerErrors.NOT_CONFIGURED` e `providerErrors.PROVIDER_ERROR` mancano (sottosistema `assets`): la sonda
  mostra il messaggio grezzo.
- Gate di proprietà (`test_plugin_i18n_ownership_gate.py`):
  - un plugin asset ha lo spazio `assets.providerParams.<codice>`, senza chiavi dichiarate raccolte;
  - un plugin FX non ha spazio;
  - le chiavi dei campi delle impostazioni non le legge nessuno.
- justETF dà sempre 4 righe per fondo (EUR/USD/CHF/GBP), con 👑 sulla valuta del fondo, e non ha frammento i18n.
- Borsa Italiana dà 2 righe per strumento (IT/EN), in tre punti (`_fund_search_items_all_langs`,
  `_scheda_search_items_all_langs`, `search`), nell'ordine fisso `("it", "en")`. Il suo frammento ha
  `assets.providerParams.borsa_italiana.*`.
- UI riusabile senza colori legacy: `ModalBase` (m1 = 0) e `PasswordInput` (pulito).
- Debito del programma colori: `SimpleSelect` (40), `Setting*.svelte` (palette), `ProviderAssignmentSection` (95) e
  `AssetSearchAutocomplete` (57). Li riuso o li tocco solo con ruoli, senza classi legacy nuove.
- Modello di scheda recente, `features/email/`:
  - la scheda, `emailApi.ts` sottile, `emailText.ts` puro, i Vitest accanto;
  - la galleria con la risposta servita da una fixture prima della navigazione (`galleryEmail.ts`);
  - il `?tab=` onorato dalla pagina.

**Disegno (dentro §4.4 approvato)**
- Backend:
  1. `PluginSettingsPluginRead.configured: bool`: la verità del resolver, campi nascosti compresi, con un solo helper
     per `missing`, condiviso fra resolver e catalogo.
  2. Ricerca:
     - nello stream `NOT_CONFIGURED` porta `error_code`, come `RATE_LIMITED`;
     - nella ricerca semplice, `providers_not_configured: list[str]` (additivo).
  3. D-X14:
     - justETF `preferred_currency`: select personale, con `all` e le 4 valute con la bandiera, default `all`;
     - Borsa `preferred_language`: `all`/`it`/`en`, default `all`;
     - il filtro agisce dopo ogni cache interna del plugin, con ricaduta per strumento;
     - chiavi i18n nei frammenti `pluginSettings.asset.<codice>.label.<campo>`, `.description.<campo>`,
       `.option.<campo>.<valore>`, come `providerParams`;
     - frammento nuovo per justETF.
  4. Gate esteso:
     - ogni plugin asset e FX ha l'area `pluginSettings.<famiglia>.<codice>`;
     - chiavi dichiarate: i `label_key` e `description_key` dei campi e delle opzioni;
     - FX entra fra le famiglie con spazio.
- Frontend, in `lib/features/plugin-settings/`:
  - `pluginSettingsApi.ts`, sottile.
  - `pluginSettingsForm.ts`, puro: gruppi per famiglia, testo con ripiego inglese, bozza → voci di scrittura, errori
    per campo dal 422, stato del segreto.
  - `PluginSettingsForm.svelte`, per tipo di campo:
    - segreto a sola scrittura, con «impostato il …», «Sostituisci» e «Cancella»;
    - campo bloccato con «impostato dal server», più la variabile per l'admin;
    - campo di sistema in sola lettura per chi non è admin (D-X15);
    - salva e annulla per plugin; ripristino del default = `clear`.
  - `PluginSettingsTab.svelte`: gruppi Prezzi e Cambi, stato vuoto.
  - `PluginSettingsModal.svelte`, su `ModalBase`, filtrata su un plugin.
  - Una riga in `settingsTabs.ts`: `plugins`, icona `Puzzle`, ordine 25, visibile a tutti.
  - «Configura» nella riga 1 di `ProviderAssignmentSection`, accanto alla guida, quando il plugin ha campi; badge «da
    configurare» quando `configured` è falso.
  - `AssetSearchAutocomplete`:
    - una riga «<fornitore> da configurare · Configura» per ogni `provider_error` con `NOT_CONFIGURED`;
    - la legenda della 👑 quando un risultato la mostra.
  - i18n: il sottosistema nuovo `pluginSettings` (`prefixes.txt`: `pluginSettings`), più `providerErrors.NOT_CONFIGURED`
    e `PROVIDER_ERROR` in `assets`.
  - Nel codice nuovo solo ruoli colore.

**Decisioni notturne, da rivedere**
- **N1.** La scheda è visibile a tutti, con ordine 25 (dopo Preferenze, nel gruppo di sinistra): ha campi personali, e
  per chi non è admin quelli di sistema sono in sola lettura (D-X15).
- **N2.** `configured: bool` al posto delle chiavi mancanti: non rivela campi che il profilo gestito nasconde.
- **N3.** Il filtro D-X14 ricade per strumento: uno strumento senza la variante preferita le mostra tutte. È un
  superinsieme di «se svuota la lista, tutto».
- **N4.** Le chiavi i18n delle impostazioni seguono il modello di `providerParams` (`label.<campo>`).
- **N5.** Nel gate, lo spazio `pluginSettings.<famiglia>.<codice>` vale anche per gli FX.

**Lotti**, ognuno con handoff FROZEN:
- **CP11a**, backend e contratto i18n: i punti 1–4, le chiavi `providerErrors`, le unità, `api sync`.
- **CP11b**, frontend: scheda, modulo, modale, Configura, ricerca; Vitest.
- **CP11c**:
  - E2E, fuori dalla finestra 00:00–01:15;
  - galleria, su uno slot pesante;
  - documentazione (docs-writer): pagina utente nuova, `admin/configuration`, `patterns/plugin_settings`, ricerca;
  - revisione di sicurezza CP10–CP11.

**Superfici condivise da dichiarare**
- `settingsTabs.ts` (A): una riga e un import.
- `_backend_services.py`, `_backend_utils.py` (la descrizione del gate) e la registrazione dei Vitest e degli E2E.
- i18n `assets/`: due chiavi.
- `openapi.json`.
- `mkdocs.yml`: la navigazione della pagina utente nuova; la propongo, la scrive il coordinatore.
- CHANGELOG: testi proposti.

**Conflitti previsti**
- `ProviderAssignmentSection.svelte` e `AssetSearchAutocomplete.svelte`, con il programma colori (se un suo lotto li
  migra) e con il mio FE5a.
- `settingsTabs.ts`, con chi aggiunge schede: la riga è additiva.

**Rischi**
- Un segreto nel browser: mai precompilato, `autocomplete="new-password"`, svuotato dopo il salvataggio. Da verificare
  che nessun intercettore registri i corpi delle richieste.
- Le preferenze personali nel DB condiviso degli E2E: scritture solo con un utente proprio o con ripristino garantito.
- La cache della ricerca: l'impronta c'è già; il filtro va dopo le cache interne del plugin.

**Prove (corsia 6183)**
- CP11a:
  - services `plugin-settings-*` e le unità nuove di justETF e Borsa (pure);
  - utils `gate-plugin-i18n-ownership` e `gate-i18n-catalog`;
  - api `plugin-settings` e `assets-provider`;
  - `front-utility core-unit`.
- CP11b: i Vitest dei file nuovi e toccati, `front check`.
- CP11c: E2E `settings/plugin-settings`, galleria, `mkdocs build` e `check-links`.

### CP11a — backend e contratto i18n ⏳ (via del coordinatore 2026-10-15, 23:35)

N1–N5 restano «da rivedere»: il coordinatore le mette nella lista di domattina. Le due chiavi in `assets/` vogliono
`front-utility core-unit` prima dell'handoff. La riga di `mkdocs.yml` la scrivo io con CP11c, dichiarata.

1. ✅ (2026-10-15) `configured` nel catalogo.
   > **Note implementazione**:
   > - `missing_field_keys(states)` in `resolver.py` è la regola unica: un campo obbligatorio senza un valore usabile,
   >   o con `invalid_env`.
   > - Un segreto risolto senza decifrarlo (il catalogo) è usabile se impostato e leggibile.
   > - La usano `build_bound_settings` (il `NOT_CONFIGURED` di una chiamata) e `read_catalogue`, dove si calcola su
   >   tutti i campi, anche quelli che il profilo gestito nasconde (N2).
   > - Schema: `PluginSettingsPluginRead.configured: bool`, obbligatorio.
2. ✅ (2026-10-15) La ricerca dice chi è da configurare.
   > **Note implementazione**:
   > - Ricerca semplice: `FAProviderSearchResponse.providers_not_configured` (facoltativo, lista vuota per default),
   >   un sottoinsieme di `providers_with_errors`. Ogni fornitore passa nel compito anche il codice d'errore.
   > - Stream: `provider_error` porta `error_code` per ogni `AssetSourceError`, compreso `NOT_CONFIGURED`, che va nel
   >   log come info e non come warning. La docstring ora elenca l'evento.
3. ✅ (2026-10-15) D-X14.
   > **Note implementazione**:
   > - justETF `preferred_currency`: select personale, `all` più le 4 valute con la bandiera (opzioni costruite dalle
   >   costanti del modulo), default `all`.
   > - Borsa Italiana `preferred_language`: `all`/`it`/`en`, default `all`. `_languages_in_order` e
   >   `_emitted_languages` sostituiscono i tre calcoli copiati di `emit_language_order`; la lingua del fetch resta la
   >   prima di sempre (`it`).
   > - Frammenti, con `dev.py i18n add --into`: il nuovo `justetf/i18n/` (3 chiavi) e `borsa_italiana/i18n/` (5 chiavi
   >   nuove), sotto `pluginSettings.asset.<codice>.{label,description,option}`. `i18n check` severo verde (4645 chiavi).
   > - Prova in processo (`/tmp/libreFolio_cp11a_smoke.py`, rete simulata): justETF dà 1 riga per fondo con la valuta
   >   preferita, e la 👑 resta sulla valuta del fondo; Borsa dà solo la lingua preferita e fa il fetch sempre in `it`.
4. ✅ (2026-10-15) `providerErrors.NOT_CONFIGURED` e `providerErrors.PROVIDER_ERROR` nel sottosistema `assets`.
   > **Note implementazione**: il testo di `NOT_CONFIGURED` sta nei 60 caratteri del riassunto della sonda.
   > `PROVIDER_ERROR` porta `{detail}` (N6).
5. ✅ (2026-10-15) `api sync`: nessun file tracciato cambiato; `configured` e `providers_not_configured` sono nel client
   generato. ruff e black puliti sugli 8 file Python.

**Decisioni notturne, da rivedere** (seguono N1–N5)
- **N6.** `PROVIDER_ERROR` porta la descrizione mascherata in `details["detail"]`, e il testo tradotto la mostra
  («Il provider ha restituito un errore: {detail}»). La sonda mostra il testo tradotto al posto dell'errore grezzo:
  con un testo fisso, la causa (per esempio un 401 su una chiave sbagliata) sparirebbe. La descrizione è già
  mascherata dal confine del CP10.
- **N7.** Nello stream, `error_code` per ogni `AssetSourceError` e non solo per `NOT_CONFIGURED`: un campo in più, che il
  frontend ignora quando non lo conosce.
- **N8.** Il filtro D-X14 restringe le varianti emesse invece di filtrarle dopo. Ogni strumento ha sempre ogni variante
  (justETF 4 valute, Borsa 2 lingue), quindi è già per strumento e non svuota mai la lista. Per Borsa la lingua del
  fetch non cambia.

**Documentazione lasciata indietro dal CP11a**, per docs-writer nel CP11c (nessun controllo automatico la confronta col
runner, verificato):
- `developer/test-walkthrough/utils.md:25`: la riga del gate, con i nuovi spazi;
- `patterns/asset_plugin_guide.md` (~392, «Translations») e `patterns/fx_plugin_guide.md`:
  `pluginSettings.<famiglia>.<codice>`;
- `developer/frontend/i18n.md`: che cosa tengono i frammenti dei plugin;
- `patterns/plugin_settings.md`: `configured`, `missing_field_keys`, `PROVIDER_ERROR` con `detail`;
- la ricerca: `providers_not_configured` e l'`error_code` dello stream;
- lo skill `devpy-i18n` («Sources»).

`front check` 0/0 dopo il CP11a. Audit i18n: le 10 chiavi nuove risultano usate; i 2 «likely unused»
(`events.deleteBlocked`, `events.deleteNotFound`) c'erano già a HEAD (`f2a394a0f`), e non sono miei.
6. ✅ (2026-10-16) Test (test-author), in 7 file esistenti, nessun file nuovo, quindi nessuna registrazione.
   > **Note implementazione**:
   > - **Gate di proprietà** (64 passati, prima delle modifiche 1 rosso atteso: R1 sulle 8 chiavi nuove):
   >   - lo spazio di un plugin asset è `assets.providerParams.<codice>` più `pluginSettings.asset.<codice>`;
   >   - quello di un FX è `pluginSettings.fx.<codice>`, col codice com'è nel registro (N5); FX è fra le famiglie con
   >     spazio;
   >   - le chiavi dichiarate dalle impostazioni si leggono col walker esistente, sulla dichiarazione ridotta a dati
   >     semplici; `default` è un valore, mai una chiave;
   >   - la sentinella copre anche gli attributi di `PluginSettingField` e `SettingOption`, prima che un plugin li usi;
   >   - la descrizione `desc=` è aggiornata in `_backend_utils.py`.
   > - `plugin-settings-service` 61:
   >   - `configured` vero e falso: niente di obbligatorio, obbligatorio fino al salvataggio, segreto illeggibile con
   >     la chiave B, variabile non valida su un campo facoltativo;
   >   - profilo gestito: il campo nascosto non compare in nessuna parte della voce.
   > - `plugin-settings-runtime` 96:
   >   - `PROVIDER_ERROR` porta `details["detail"]`, mascherato;
   >   - una matrice di 12 casi su `missing_field_keys`, uguale fra la chiamata e il catalogo;
   >   - la ricerca: `providers_not_configured`, e l'evento SSE con esattamente 4 chiavi, loggato come info.
   > - `rate-limit-results` 23: XRL-R21, `SEARCH_ERROR` porta il suo codice e nessun `retry_after`; la voce 5 della
   >   docstring è riscritta.
   > - `provider-errors` 182: le dichiarazioni e il filtro di justETF, su 3 fondi.
   > - `borsa-italiana-search` 18: le preferenze su un fondo e un'azione; ricerca e scheda sempre in `it`, una volta.
   > - `gate-i18n-catalog` 176 e `gate-i18n-usage` 195: le chiavi nuove risultano usate.
   > - `api plugin-settings` 13, dopo `test db --force populate`: justETF e Borsa nel catalogo completo, e un giro
   >   di salvataggio e cancellazione che non lascia righe.
   > - **Limite noto, fissato da un test.** Un blob cifrato con l'impronta della chiave giusta ma non decifrabile:
   >   il catalogo lo vede configurato, perché non decifra mai per scelta, mentre una chiamata risponde
   >   `NOT_CONFIGURED`. L'API non può produrre una riga così.
   >
   > **⚠️ Fuori pista**:
   > - test-author ha lanciato `plugin-settings-service` con un carico a 5 minuti di 70,73, appena sopra 70: aveva
   >   letto il carico e lanciato nello stesso comando. Da lì in poi ha sempre letto il carico in un passo separato.
   > - Su sua segnalazione: nella ricerca semplice il controllo testuale «not supported» veniva prima di
   >   `NOT_CONFIGURED`. Un nome dichiarato da un plugin che contenesse quel testo avrebbe saltato il fornitore senza
   >   segnalarlo nella lista nuova. Ora i due rifiuti tipizzati (`NOT_CONFIGURED`, `RATE_LIMITED`) vengono prima.
7. ✅ (2026-10-16) Prove di chiusura, una alla volta con `nice` e il carico ≤ 70 (`/tmp/libreFolio_cp11a_checks.sh`,
   log in `/tmp/libreFolio_cp11a_checks/`), dopo il riordino:
   > - services `plugin-settings-runtime` 96 e `rate-limit-results` 23;
   > - `front-utility core-unit` 5491, la regola per chi tocca le chiavi in `assets/`;
   > - Vitest `resolveProviderError` e `providerProbe` 65; `check-orphans` pulito; porta 6183 libera.
   > - `front check` 0/0; `i18n check` severo; ruff pulito sui 16 file Python cambiati; `git diff --check` pulito.
   > - black segnala solo una riga che a HEAD era già fuori formato, in `_backend_utils.py` (il `print_info` del Designer Lab), e
   >   che non tocco.
   > - Previsione dei conflitti contro `dev_release2` (`59ce8ba20`): nessun percorso in comune.

### Checkpoint CP11a — pronto, FROZEN (2026-10-16, 00:45)

Committato dal coordinatore: `f7508ff84` (codice, 28 file) e `d592b5ef3` (journal).

### Dodicesimo aggiornamento di base: `dev_release2` (`59ce8ba20`) nel ramo X ✅ (2026-10-16) — merge `91928edc5`, pulito

Nessun file fuso da solo. Le prove d'ingresso del CP11a da solo, sulla revisione combinata, una alla volta con
`nice -n 10` e il carico ≤ 70 (`/tmp/libreFolio_cp11a_entry_checks.sh`, log in `/tmp/libreFolio_cp11a_entry/`), tutte
verdi:
- `api sync`, senza file tracciati cambiati; `front check` 0/0;
- `front-utility core-unit` 5661, cresciuto con la base;
- `gate-i18n-catalog` 176, `gate-i18n-usage` 195, `gate-plugin-i18n-ownership` 64;
- `test db --force populate`, poi `api plugin-settings` 13.

Porta 6183 libera.

### CP11b — frontend: scheda, modulo, «Configura», ricerca ⏳ (via del coordinatore 2026-10-16, 00:42, dopo le prove del CP11a)

Colori: passo prima io. `ProviderAssignmentSection` e `AssetSearchAutocomplete` sono nell'ondata W4 dei colori, che
stanotte non arriva; `settingsTabs.ts` non è in nessun lotto dei colori. Nel markup nuovo, solo ruoli (skill
`theme-roles`). Il CHANGELOG si scrive con il CP11b, che rende visibile la funzione.

**⏸️ Pausa delle prove 00:55–01:40** (coordinatore: la galleria dei colori ha avuto 6 rossi per il carico, e la mia
`vite build` delle 00:52, dentro `api plugin-settings`, era fra le cause). Nessun processo mio era in esecuzione; nella
pausa scrivo solo il codice e non lancio niente, nemmeno `dev.py i18n add`.

1. ✅ (2026-10-16) Il codice, scritto senza lanciare niente.
   > **Note implementazione** (nuova cartella `frontend/src/lib/features/plugin-settings/`):
   > - `pluginSettingsApi.ts`:
   >   - tipi ristretti dalle risposte generate (`fieldOf`, `entryOf`);
   >   - `fetchPluginSettings`, `fetchPluginEntry`;
   >   - `savePluginSettings`, che non lancia mai e dà `saved` / `refused` (422 con `detail.results`) /
   >     `conflict` (409) / `keyUnavailable` (503) / `failed`.
   > - `pluginSettingsForm.ts`, puro:
   >   - lo stato del modulo: testi digitati, scelte, valori da cancellare; da lì `draftOf` deriva le modifiche,
   >     così un campo riportato al valore in vigore non ha modifica e un campo mostra sempre ciò che si è digitato;
   >   - i controlli prima del server: lunghezze in code point, come `len()`; numeri, interi, limiti, opzioni;
   >   - `writeItems`; i rifiuti per campo;
   >   - i testi con ripiego inglese (`translateOr`);
   >   - le classi, letterali interi e solo ruoli.
   > - `PluginSettingsForm.svelte`, un plugin:
   >   - un controllo per tipo;
   >   - il segreto a sola scrittura («impostato il …», «Sostituisci», «Cancella», il testo dimenticato dopo il
   >     salvataggio, `autocomplete="new-password"`);
   >   - in sola lettura, con il motivo: bloccato dal server (la variabile solo per l'admin) o riservato all'admin
   >     (D-X15);
   >   - «Usa il predefinito» per un valore salvato;
   >   - errori locali e rifiuti del server per campo;
   >   - salvataggio tutto o niente, poi rilettura del plugin; `data-busy` e `aria-busy`.
   > - `PluginSettingsTab.svelte`: la scheda (gruppi Prezzi e Cambi, stato vuoto, errore di caricamento).
   > - `PluginSettingsModal.svelte`: «Configura», su `ModalBase`, filtrato sul plugin.
   > - Altrove:
   >   - `settingsTabs.ts`: una riga e un import (`plugins`, `Puzzle`, ordine 25);
   >   - `ProviderAssignmentSection.svelte`: badge «Da configurare» e pulsante «Configura» nella riga 1, più la modale;
   >   - `AssetSearchAutocomplete.svelte`: la riga «<fornitore> va configurato» con «Configura», dallo stream
   >     (`error_code`) e dal ripiego REST (`providers_not_configured`); la legenda della 👑; una ricerca nuova
   >     dopo un salvataggio.
   > - i18n:
   >   - il sottosistema nuovo `frontend/src/lib/i18n/pluginSettings/` (`prefixes.txt`);
   >   - 47 chiavi `pluginSettings.*` e 2 `assets.search.*`, pronte in `/tmp/libreFolio_cp11b_i18n_add.py` (`set_key`
   >     come `i18n add`, in un processo solo), da lanciare alla ripresa.
   > - Nel markup nuovo e aggiunto, solo ruoli: nessuna classe di palette e nessun `dark:`.

**Decisioni notturne, da rivedere** (seguono N1–N8)
- **N9.** Nel pannello del fornitore in sola lettura, «Configura» non compare; il badge «Da configurare» sì.
- **N10.** `NOT_CONFIGURED` resta un fallimento vero della sonda (rosso), non un avviso: la configurazione è davvero
  incompleta, e «Configura» è lì accanto.
- **N11.** La modale «Configura» sta al livello 80, sopra la modale dell'asset (50) e le sue richieste (70): il pannello
  non conosce il livello del genitore.
- **N12.** Niente cache a livello di modulo dello stato dei plugin: una GET a ogni scelta di fornitore. Una cache
  sopravvivrebbe al logout e mostrerebbe a un altro utente le preferenze personali di chi c'era prima.
- **N13.** Un salvataggio riuscito non dà toast, solo l'evento `pluginSettings.saved`: l'esito si vede nel campo. Rifiuti
  ed errori danno sempre il toast.
- **N14.** La scheda non ha ancora il link alla documentazione: arriva con la pagina utente, nel CP11c, per non lasciare
  un link senza pagina.

**Alla ripresa, in ordine**:
- le chiavi i18n, poi `i18n check`;
- `front check`;
- i Vitest con test-author: il modulo puro, l'API, i tre componenti, `settingsTabs.test.ts` (la riga di oggi),
  autocomplete e pannello;
- `front-utility core-unit`, con i gate dei colori.
2. ✅ (2026-10-16, dopo la ripresa delle 01:33) Le chiavi, i controlli statici e i Vitest scritti da test-author.
   > **Note implementazione**:
   > - `/tmp/libreFolio_cp11b_i18n_add.py`: 49 chiavi in un processo solo (47 nel sottosistema `pluginSettings`, 2 in
   >   `assets`). `i18n check` severo verde: 4714 chiavi, 22 sottosistemi.
   > - `front check` 0/0.
   > - Prettier sui file toccati: `ProviderAssignmentSection` a HEAD era pulito, e `--write` ha cambiato solo il mio
   >   blocco aggiunto.
   > - Gate dei colori standalone (`theme-roles.mjs --check`): pulito.
   > - test-author ha scritto, senza lanciare niente fino al via:
   >   - 5 file nuovi: `pluginSettingsForm.test.ts`, `pluginSettingsApi.test.ts`,
   >     `PluginSettingsForm.component.test.ts` (su macOS un nome che differisce solo per le maiuscole è lo stesso
   >     file), `PluginSettingsTab.test.ts`, `PluginSettingsModal.test.ts`;
   >   - 4 file aggiornati: `ProviderAssignmentSection.test.ts`, `AssetSearchAutocomplete.test.ts`,
   >     `settingsTabs.test.ts` (la riga di oggi), `page.tabs.test.ts` (il mock della scheda, senza il quale
   >     l'import falliva);
   >   - le registrazioni in `_frontend_utility.py` (2 in `core-unit`, 3 in `component-unit`).
   >
   > **⚠️ Fuori pista**: tre difetti trovati da test-author, corretti nel prodotto:
   > - `fieldOf` accettava come `problem` un array di un elemento: ora vuole una stringa;
   > - dopo un salvataggio in «Configura» dal pannello, la modale si ricaricava, perché leggeva `pluginCode`
   >   attraverso l'oggetto sostituito: ora le passo due stringhe `$derived`;
   > - una chiave di campo `constructor`, valida per il backend, trovava `Object.prototype` con `in` e `[]`: ora ogni
   >   ricerca per chiave passa da `own()` (`Object.hasOwn`), nel modulo puro e nel componente.
3. ✅ (2026-10-16) Prove.
   > **Note implementazione**:
   > - I Vitest di test-author, quattro lanci separati con il carico fra 40 e 57: 235, 48, 43 e 113, cioè 439 prove
   >   verdi al primo colpo e senza traffico non previsto. Coprono:
   >   - il modulo puro e l'API;
   >   - modulo, scheda e modale;
   >   - `settingsTabs` e `page.tabs`;
   >   - pannello, ricerca e il ciclo di vita della sonda di `AssetModal`, il cui finto client ora risponde «nessuna
   >     impostazione» alla lettura nuova invece di non averla.
   > - Le prove di chiusura, una alla volta con `nice` e il carico ≤ 70 (`/tmp/libreFolio_cp11b_checks.sh`, log in
   >   `/tmp/libreFolio_cp11b_checks/`): `front check` 0/0; `front-utility core-unit` 5898 (170 file, con i gate dei
   >   colori); `front-utility component-unit` 3828 (145 file); `check-orphans` pulito; porta 6183 libera;
   >   `git diff --check` pulito.
   > - Previsione dei conflitti contro `dev_release2` (`db384eaf5`), due superfici in comune:
   >   - `assets/*.json`: il bersaglio toglie le due chiavi morte `events.delete*` intorno alla riga 379, le mie stanno
   >     alla 327;
   >   - `_frontend_utility.py`: righe aggiunte in punti diversi, separate da righe invariate.
   >
   >   Fusione pulita probabile. Le registrazioni vanno tenute tutte: sono solo aggiunte.
   > - Non lanciati: E2E, galleria, mkdocs (CP11c); `vite build` e `front build`, vietati stanotte dal coordinatore.

### Checkpoint CP11b — pronto, FROZEN (2026-10-16, 02:30)

Committato dal coordinatore: `649783e3f` (codice, 28 file) e `9bc442ca9` (journal).

### Tredicesimo aggiornamento di base: `dev_release2` (`db384eaf5`) nel ramo X ✅ (2026-10-16) — merge `7b903ccef`

- **Fusioni automatiche**, verificate sulla revisione combinata:
  - `assets/*.json`: le mie 2 chiavi presenti e le 2 di W tolte;
  - `_frontend_utility.py`: le 5 registrazioni mie e le 7 del bersaglio, tutte presenti.
- **Prove leggere d'ingresso**, una alla volta con `nice` e il carico ≤ 70 (`/tmp/libreFolio_cp11b_entry_checks.sh`), tutte
  verdi: `api sync` senza file tracciati cambiati; `i18n check` severo (4748 chiavi); `front check` 0/0;
  `core-unit` 6144; `component-unit` 3900.
- **E2E prima dell'ingresso**, su richiesta del coordinatore (cambia la barra delle schede di ogni pagina delle
  Impostazioni, e i pannelli degli asset). Slot pesante 1, una spec alla volta (`/tmp/libreFolio_cp11b_e2e.sh`, log in
  `/tmp/libreFolio_cp11b_e2e/`).
  - `front-asset asset-modal` 17 verdi, ricostruzione del frontend compresa (la prima corsa la fa quando le
    sorgenti cambiano).
  - `front-utility settings` 50, `admin-users` 10, `scheduler` 17, `email-tab` 5, `backup` 5: tutti verdi, nessuna
    prova instabile. In tutto 104, dalle 02:39 alle 03:00. Porta 6183 libera.
  - Le altre spec che passano dalle Impostazioni non dipendono dall'elenco delle schede: nessun ciclo sulle schede, e
    i filtri di testo di `select-components.spec.ts` non prendono «Plugins».
- `providerProbe.ts` (riga 111, Q10 dei colori): il CP11b non lo tocca, verificato.

### CP11b in `dev_release2` ✅ (2026-10-16) — treno 84, merge `0241a87e8`, con le due righe ✨ nel CHANGELOG

### CP11c — E2E, documentazione, sicurezza, galleria ⏳ (via del coordinatore 2026-10-16, 03:01)

Ordine dato dal coordinatore:
1. E2E nuovi, documentazione, la riga di nav in `mkdocs.yml` (dichiarata) e il link nella scheda;
2. revisione di sicurezza CP10–CP11;
3. galleria. `gallery.spec.ts` è sorvegliato dai colori: l'elenco degli scatti va prima al coordinatore, che lo
   concorda con G; la run filtrata si fa in uno slot suo, prima delle 05:15 (dalle 05:30 alle 06:45 la macchina è
   ferma).

La base si aggiorna al checkpoint. Da non toccare: `e2e/fx/fx-list.spec.ts` ed `e2e/assets/asset-data-editor.spec.ts`
(W1-c dei colori) e `components/assets/providerProbe.ts` (Q10 dei colori).

1. ⏳ Avvio, alle 03:05.
   > - Galleria: proposto al coordinatore uno scatto solo, `settings/plugins` (e2e_test_user, tutte le lingue e i
   >   temi, desktop e mobile, regola C4 sul desktop). Facoltativo, se G lo vuole: la modale «Configura» sopra
   >   la modale dell'asset.
   > - In parallelo, su file diversi:
   >   - test-author: la spec nuova `e2e/settings/plugin-settings.spec.ts` con l'azione `front-utility plugin-settings`;
   >   - docs-writer: la pagina utente nuova, più le pagine per admin e per sviluppatori lasciate indietro dal CP11a;
   >   - security-review, in sola lettura.
   > - Mio: la riga di nav `- Plugin Settings: user/settings/plugins.md` in `mkdocs.yml`, e il `DocsLink` della
   >   scheda verso `user/settings/plugins/` (N14 chiusa).
2. ⏳ (2026-10-16, 03:20–03:35) La revisione di sicurezza CP10–CP11 (security-review, in sola lettura).
   > **Esito**: nessuna vulnerabilità sfruttabile su questo ramo, perché nessun plugin di produzione dichiara un
   > segreto. Verificati e sani: crittografia e AAD, schemi di lettura, 422 e log, autorizzazioni (gestito
   > compreso), percorsi dei valori personali, cache della ricerca, componenti nuovi (nessun `{@html}`, segreti mai
   > nei `notify`, nella console o negli URL), stato fra utenti, CSRF, SQL, alias delle variabili, cancellazione utente.
   > Rilievi:
   > - **MEDIUM, latente (9/10)**: il mascheramento sostituiva una forma alla volta, prima la più lunga. Un utente che
   >   sceglie un segreto personale lungo, parzialmente sovrapposto a un segreto di sistema che l'errore del fornitore
   >   mostra (contesto noto + un carattere), lasciava in chiaro il resto del segreto di sistema.
   >   - La correzione proposta, unire gli intervalli, da sola **non basta**: verificato in processo, la forma del
   >     testo mascherato (`'***'` contro `…apikey=***`) dice ancora se l'ipotesi è giusta. Un carattere alla volta
   >     resta un oracolo.
   >   - **Correzione fatta** (N15):
   >     - `mask_text` trova tutte le occorrenze nel testo originale e unisce quelle sovrapposte o contigue;
   >     - modalità `whole`: quando la chiamata porta un segreto personale (`BoundSettings.carries_user_secrets`), il
   >       confine degli asset nasconde intero ogni testo che mostra un segreto, e tiene tipo e `error_code`;
   >     - i log restano mascherati con precisione; le chiamate con soli segreti di sistema restano come prima.
   >   - Prova in processo: due ipotesi danno uscite identiche (`***`, `FETCH_ERROR`).
   > - **LOW (9/10), percorso già esistente**: `buildProbeTooltipHtml` (`providerProbe.ts:109,138`) restituisce il
   >   testo dell'errore senza escaparlo, reso con `{@html}`; DOMPurify ferma gli script ma non immagini, form e stili.
   >   La correzione, `escapeHtml(result.detail)` nei due rami più la prova, tocca un file di Q10 dei colori.
   >   **APERTO**: per decisione del coordinatore (04:25) si fa dopo l'aggiornamento della base al checkpoint del CP11c,
   >   che porta Q10 (entrato in `dev_release2` come `503dce683`). Prima non si può aggiornare: i miei file aperti
   >   (`configuration.en.md`, `hosting_providers.en.md`, `_frontend_utility.py`) toccano gli stessi file.
   > - **LOW, latente**:
   >   - la sonda calcola `provider_url` fuori dal confine; ora `core.public_asset_url` lo trattiene (None, e un
   >     avviso nel log) se mostra un segreto;
   >   - per gli autori di plugin, la regola nelle guide (affidata a docs-writer): mai un segreto in `get_asset_url`,
   >     in `cooldown_scope`, o in una richiesta con l'host preso da identificatore o parametri.
   > - **Informativo, profilo gestito**: `NOT_CONFIGURED` nomina il campo nascosto quando la variabile dell'hoster non è
   >   valida. È un identificatore pubblico, nessun valore. Accettato, nessuna modifica.
   > - **Non di sicurezza**: l'input del segreto leggeva `form.texts[...]` senza `own()`. Corretto.
   > - Le prove di regressione le scrive un test-author a parte, e partono dopo l'E2E in corso: ogni unità `services`
   >   ricrea il DB della corsia.

**Decisione notturna, da rivedere**
- **N15.** Una chiamata asset che porta un segreto personale nasconde intero ogni testo d'errore che mostra un segreto,
  invece di mascherarlo in loco: meno dettaglio per chi ha scelto il segreto, nessun oracolo sul segreto di sistema.
  I log restano mascherati con precisione per l'admin.
3. ⏳ (2026-10-16, 03:26–03:50) La spec E2E nuova (test-author).
   > **Note implementazione**:
   > - `frontend/e2e/settings/plugin-settings.spec.ts`, 5 prove, registrata come `front-utility plugin-settings`:
   >   - la scheda, in sola lettura, per un membro e per un admin;
   >   - «Configura» su mockprov per un membro (numero e segreto personale) e per un admin (segreto dell'istanza);
   >   - la ricerca con la riga «da configurare» e la legenda della 👑, con lo stream SSE simulato.
   > - mockprov non si sceglie nella modale dell'asset (il pannello lo filtra di proposito): le prove 2 e 3 creano un
   >   asset loro via API, con mockprov e un identificativo che il mock rifiuta, ne aprono la modifica e cliccano
   >   `provider-configure`.
   > - La pulizia, sempre, via API: dopo la prima corsa, nel DB della corsia zero righe di mockprov e zero asset
   >   rimasti.
   >
   > **⚠️ Fuori pista**:
   > - **Difetto del prodotto, corretto**: la modale «Configura» non aveva un'area che scorresse. Con i 7 campi di
   >   mockprov, a 1280×720 «Salva» e «Chiudi» finivano sotto il bordo: `allowOverflow` toglieva il limite di 90vh, e la
   >   pagina è bloccata. Prima corsa: 3 prove verdi e 2 rosse per timeout.
   >   - Ora titolo e «Chiudi» restano fermi e il corpo scorre in mezzo (`min-h-0 flex-1 overflow-y-auto`), dentro la
   >     colonna di `ModalBase`.
   >   - Le select aprono l'elenco con `position:fixed`, quindi il corpo che scorre non le taglia.
   >   - Con i plugin di produzione (un campo ciascuno) non si vedeva.
   > - **Seconda corsa, ambiente**: il backend di prova non ha risposto in 300 s. `server --test` ricostruisce il sito
   >   della documentazione se una pagina è più nuova, e docs-writer stava salvando pagine. Le E2E e la galleria vanno
   >   lanciate dopo `mkdocs build`, a documentazione ferma.
4. ✅ (2026-10-16, 03:05–04:00) La documentazione (docs-writer), più le mie righe.
   > **Note implementazione**:
   > - Pagina nuova `user/settings/plugins.en.md`, con l'immagine `settings/plugins` (lo scatto arriva con la
   >   galleria).
   > - 21 pagine aggiornate:
   >   - utente: indice delle impostazioni, justETF e Borsa Italiana con la preferenza;
   >   - admin: `configuration` e `hosting_providers`;
   >   - galleria desktop e mobile;
   >   - sviluppatori: `plugin_settings`, guide asset e FX, `registry_pattern`, `frontend/i18n`, `test-walkthrough`
   >     utils e front-utility, `assets/architecture`, `search_link_finder`, `api/overview`, componenti e toolbar delle
   >     impostazioni.
   > - Le due regole della revisione di sicurezza sono nelle guide. Nessuna pagina timbrata: ogni modifica aggiunge
   >   contenuto, quindi resta debito di traduzione.
   > - Mie:
   >   - la nav, rinominata `- Plugins: user/settings/plugins.md`, con `nav_translations` IT/FR/ES. «Plugin Settings»
   >     era anche il titolo della pagina per sviluppatori, e una traduzione le avrebbe rinominate tutte e due;
   >   - il passo 8 di `.github/instructions/backend-providers-asset.instructions.md`: le impostazioni e le regole per
   >     gli autori.
   > - `mkdocs build` severo verde (94 s), `check-links` 97 link (il `DocsLink` nuovo compreso).
   >
   > **⚠️ Fuori pista**:
   > - Il primo `mkdocs build` severo è fallito con 5 avvisi: la pagina nuova, senza traduzioni, si costruisce anche in
   >   IT/FR/ES, e i suoi link puntavano ad ancore che esistono solo in inglese (`admin/configuration#plugin-*`,
   >   `#startup-checks`, `justetf#search-currency`). Ora i link vanno alle pagine, senza ancora.
   > - docs-writer ha trovato:
   >   - Nessuna colonna salva l'URL dell'asset: ho corretto le docstring, l'URL è solo «mostrato».
   >   - Un campo personale obbligatorio lascerebbe per sempre `NOT_CONFIGURED` le chiamate fatte per nessuno
   >     (prezzi, job), mentre la scheda direbbe «configurato». Ora la dichiarazione lo rifiuta: N16.
   >   - Il `CHANGELOG.md` riga 40, la voce del CP10, dice ancora «la schermata arriva dopo». Lo segnalo al
   >     coordinatore.

**Decisione notturna, da rivedere**
- **N16.** Un campo personale non può essere `required` (`validate_declaration`): le chiamate fatte per nessuno non lo
  ricevono mai. Nessun plugin lo dichiarava.
5. ✅ (2026-10-16, 04:00–04:05) Le prove di regressione della sicurezza (un test-author a parte), in 4 file esistenti,
   senza file nuovi. Lanciate dopo la documentazione e prima dell'E2E, una alla volta con il carico fra 38 e 39:
   > - `services secret-masking` 68: 20 nuove (l'attacco della sovrapposizione chiuso; con `whole` le due ipotesi
   >   danno la stessa uscita; intervalli sovrapposti o contigui; `mask_exception` e `masked_description` con `whole`).
   > - `services plugin-settings-runtime` 120: 24 nuove:
   >   - `carries_user_secrets`;
   >   - `call_provider` con mockprov e un segreto personale: stesso errore, stesso codice, testi `***` per le due
   >     ipotesi; senza segreto personale il mascheramento resta preciso;
   >   - `public_asset_url`, e la sonda che trattiene un URL con un segreto (di sistema o personale).
   > - `services plugin-settings-contract` 194: 4 nuove (un campo personale obbligatorio rifiutato, anche alla
   >   registrazione).
   > - Vitest `PluginSettingsForm.component.test.ts` 34: PSF-25, un segreto con chiave `constructor`.
   > - Lint e formato puliti; nessun difetto del prodotto; porta 6183 libera.
6. ✅ (2026-10-16, 04:05–04:22) E2E nuove dopo la correzione della modale, e controlli leggeri.
   > - `front-utility plugin-settings`: due corse 5/5 (04:05, con la ricostruzione del frontend, e 04:10), più una con
   >   `--workers 4`, 5/5 in 21,6 s (04:22).
   > - Le due prove di «Configura» passano da 60 s di timeout a 4–5,5 s. I controlli della correzione: il modulo di
   >   mockprov supera il corpo della modale, «Chiudi» resta tutto nella finestra, e «Salva» si raggiunge scorrendo il
   >   corpo a ognuno dei 4 salvataggi.
   > - Dopo ogni corsa, nel DB della corsia: zero righe di mockprov, zero impostazioni personali, zero asset di prova.
   > - Controlli leggeri (`/tmp/libreFolio_cp11c_checks.sh`): `front check` 0/0, `core-unit` 6144, `component-unit` 3901,
   >   `check-orphans` pulito, `i18n check` severo. Porta 6183 libera.
   > - tsc sulla configurazione e2e: 2 errori che c'erano già (`onboarding-tour.spec.ts:863` e il percorso
   >   `$lib/api/generated` in `src/lib/types/files.ts`), non miei. Le mie due spec sono pulite.
7. ✅ (2026-10-16, 04:25–04:30) La galleria.
   > - G ha dato l'ok allo scatto `settings/plugins` (senza la modale), alle sue condizioni:
   >   - dopo `waitForSettled`, nessun `plugin-settings-load-error` né `plugin-settings-empty`, e almeno una
   >     `plugin-settings-family`;
   >   - nessun `plugin-setting-secret-state` con `data-state` `set` o `env`;
   >   - sul desktop la regola degli schermi alti, come `email`, e oltre ~2500 px la prima famiglia; sul mobile il
   >     primo schermo;
   >   - solo `data-testid`, niente attese a tempo né maschere.
   > - Il messaggio originale di G (arrivato dopo il riassunto del coordinatore, che accettava anche `TEST_ADMIN`)
   >   chiedeva la vista di un membro: uso `TEST_USER`, aggiunto all'import di `test-users` (unico tocco permesso oltre
   >   al test). È la vista che la pagina del manuale utente descrive. `data-busy` della scheda vale `true` dal primo
   >   render (`loading = $state(true)`), quindi `waitForSettled` aspetta davvero.
   > - Test scritto in `gallery.spec.ts`, dopo `email`: +36 righe e 1 riga d'import. Prettier pulito.
   > - Run filtrata nello slot del coordinatore, verso le 04:50, da finire entro le 05:15:
   >   `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r13-x … mkdocs gallery --test-port 6183 --filter "plugins - all
   >   languages and themes" --workers 2`. La ricarica del DB della galleria non riceve `--data-dir`, quindi passa per
   >   la variabile.
   > - `providerProbe.ts`: per decisione del coordinatore, le due righe di escape arrivano dopo l'aggiornamento della
   >   base al checkpoint del CP11c, che porta Q10.
   > - Slot pesante 2 dal coordinatore. Run filtrata, `--filter "plugins - all languages and themes"`: solo quel test,
   >   verificato con `--list`. 2 prove passate (desktop e mobile) in 1,4 minuti, dalle 04:27:40 alle 04:29:49.
   > - 16 immagini (4 lingue × 2 temi × 2 viewport), ignorate da git per regola (`.gitignore:79`).
   > - Desktop: 📐 blocco di 656 px, schermo 1280×745 in tutte le lingue, ben sotto i 2500.
   > - Guardato a occhio lo scatto desktop in inglese, tema scuro: ruoli corretti, la barra del membro, le due schede
   >   «Configurato».
   > - Slot liberato e porta 6183 libera alle 04:30.

### Checkpoint CP11c — pronto, FROZEN (2026-10-16, 04:35)

Previsione dei conflitti contro `dev_release2` (`3edfc4b9a`): sette file in comune, e un solo punto vicino.
- `admin/hosting_providers.en.md:44`:
  - io riscrivo la riga della tabella sui campi bloccati dall'ambiente;
  - il bersaglio aggiunge subito sotto la riga nuova del limite di caricamento del ripristino (B);
  - risoluzione: la mia riga 44, poi la loro riga nuova; il resto come nel bersaglio.
- Gli altri sei (`gallery.spec.ts`, `admin/configuration.en.md`, `api/overview.md`,
  `frontend/components/features/settings.md`, `frontend/i18n.md`, `_frontend_utility.py`) hanno pezzi a più di 3 righe
  di distanza.

Resta aperto, da fare subito dopo l'aggiornamento della base: l'escape in `providerProbe.ts` (righe 109 e 138), con la
sua prova.

Committato dal coordinatore: `c8d23c544` (fix, 39 file) e `3d122d28a` (journal).

### Quattordicesimo aggiornamento di base: `dev_release2` (`3edfc4b9a`, con Q10 dei colori) nel ramo X ✅ (2026-10-16) — merge `024a6a067`

- Un conflitto, previsto, in `admin/hosting_providers.en.md`. Risolto tenendo la mia riga dei campi bloccati
  dall'ambiente e subito sotto la riga nuova del limite di caricamento del ripristino; il «four things» del bersaglio
  torna. In stage solo quel file; il commit del merge l'ha fatto il coordinatore.
- Fusioni automatiche controllate: `gallery.spec.ts` (lo scatto e `TEST_USER`), `_frontend_utility.py`,
  `frontend/i18n.md`, `admin/configuration.en.md`, `api/overview.md`, `features/settings.md`.

### Sicurezza, il punto aperto: l'escape del tooltip della sonda ✅ (2026-10-16, 04:45) — commit a parte

- `providerProbe.ts::buildProbeTooltipHtml`: `escapeHtml(result.detail ?? 'Error')` per un fallimento, e
  `escapeHtml(result.detail ?? '—')` nel ramo di ripiego. Le tabelle non cambiano, e nemmeno la riga 111 di Q10 (il
  bordo). La prova (`providerProbe.test.ts`) la sistema test-author.
- La prova (test-author): `providerProbe.test.ts` 38/38. Il caso del fallimento ora vuole il testo escapato; 8 casi
  nuovi (markup ostile su fallimento e ripiego, testo semplice invariato, le tabelle intatte). Il revisore lo chiude:
  le celle delle tabelle non possono portare testo del fornitore.
- Prove d'ingresso su `024a6a067` più l'escape, una alla volta con `nice` e il carico ≤ 70
  (`/tmp/libreFolio_cp11c_entry_checks.sh`, log in `/tmp/libreFolio_cp11c_entry/`):
  - `front check` 0/0, dopo `api sync`;
  - `core-unit` 6154;
  - services `secret-masking` 68, `plugin-settings-runtime` 120, `plugin-settings-contract` 194;
  - `mkdocs build` severo (74 s), `check-links` 97, `i18n check` severo (4750 chiavi). Porta 6183 libera.
- Niente E2E: lo slot 2 era di A fino alle 05:25. Le E2E `plugin-settings` verdi erano sulla base precedente; si
  possono rifare dopo le 06:45.

> **⚠️ Fuori pista**: il primo `front check` dava 1 errore in `LoginCard.svelte:112`: `first_account_open`, il flag
> di A6d entrato con la base. Il client generato (ignorato da git) era ancora quello di prima dell'aggiornamento:
> `api sync`, nessun file tracciato cambiato, poi `front check` 0/0. Dopo ogni aggiornamento di base che cambia l'API,
> `api sync` va prima di `front check`.

### CP11c ed escape in `dev_release2` ✅ (2026-10-16) — treno 91

- Commit sul mio ramo: `17a8b396f` (fix) e `a10af747d` (journal).
- Merge in `dev_release2`: `2f1d77a23`. Il mio ramo è stato portato avanti alla punta, HEAD `6c03c38b8` (verificato).
- CHANGELOG: nessuna riga 🔒, perché la funzione non è ancora uscita. La riga «Settings › Plugins» ora dice che il
  segreto non si vede «nemmeno nel messaggio d'errore di una fonte né nell'indirizzo della pagina di un asset».

### X-R12 — gli eventi del fornitore datati oggi ✅ (via del coordinatore 2026-10-16, 04:50; pronto alle 05:10)

Ordine dato dal coordinatore: X-R12, poi FE5c più X-R13 (sblocca Z7c-1; da controllare con la regola dei colori
«niente elementi misti»), poi CP13. Un commit per lotto. Dalle 05:30 alle 06:45 la macchina è ferma: nessuna prova,
nemmeno leggera, solo scrittura.

1. ✅ (04:50–04:53) La correzione, in `services/assets/refresh.py::_fetch_refresh_item`.
   > **Note implementazione**:
   > - Quando l'intervallo arriva a oggi, la chiamata della storia finisce **oggi** (`call_end`), non più ieri. È così
   >   solo quando la storia è già chiesta (`start == "min" or start < today`): le stesse chiamate di prima, cambia solo
   >   la fine.
   > - I prezzi della storia dopo `history_end` (ieri) restano fuori dalla cache e da `prices_data`: il prezzo di oggi
   >   resta il valore corrente.
   > - Gli eventi fino a oggi restano.
   > - Con un buco nella cache e `end >= today`, la chiamata va fino a oggi; la copertura si conta ancora fino a ieri.
   > - Un intervallo passato non cambia, e `start == today` non chiama la storia.
   > - `end_date` è inclusivo in tutti i plugin che danno la storia: Yahoo aggiunge un giorno da sé; justETF, Borsa,
   >   scheduled_investment e mockprov filtrano con `<=`; css_scraper non ha storia.
   > - Prova in processo (`/tmp/libreFolio_xr12_smoke.py`), tutto come atteso:
   >   - la chiamata finisce oggi;
   >   - il prezzo di oggi è quello corrente (11), non quello della storia (10);
   >   - il dividendo di oggi resta;
   >   - la cache non ha oggi.
   > - Le suite esistenti del percorso sono verdi: `services asset-source-refresh` 12, `utils provider-core-cache` 29,
   >   `services rate-limit-results` 23, `services scheduler-jobs` 43.
   >
   > **⚠️ Fuori pista**: la prima delle quattro suite è partita con il carico a 74,4, sopra 70. Il ciclo stampava il
   > carico ma non aspettava. Le altre tre sono partite sotto 70. D'ora in poi il controllo del carico resta un passo
   > che blocca.
2. ✅ (05:08) I test di regressione: test-author, sei test `test_fetch_*` in
   `test_services/test_asset_source_refresh.py`.
   > **Note implementazione**:
   > - **Il fornitore finto** gira in processo, registra ogni chiamata e restituisce un evento solo se l'intervallo
   >   chiesto ne contiene la data, come uno vero.
   > - **La data** è fissata con la fixture `xr12_today` (non autouse), che sostituisce `refresh.date_type`, l'unico
   >   orologio di `_fetch_refresh_item`, e svuota le due cache del core prima e dopo ogni test.
   >   - Non è autouse perché `_prepare_refresh_items` usa `date_type` in un `isinstance`.
   > - **La chiave di cache** è ricostruita dalle stesse parti di `refresh.py`: se cambia, i test falliscono, non passano
   >   in silenzio.
   > - **I sei casi**:
   >   1. intervallo fino a oggi;
   >   2. cache fino a ieri, cioè colpo pieno senza chiamata;
   >   3. buco nella cache: chiamata dal giorno mancante fino a oggi;
   >   4. intervallo passato: la chiamata finisce a `end`, senza valore corrente;
   >   5. `start == today`: nessuna chiamata della storia;
   >   6. punti futuri del fornitore scartati.
   > - **Prove** (ognuna dopo il controllo del carico, con `nice`):
   >   - `services asset-source-refresh` → **18 passed**, i 12 di prima più i 6 nuovi (05:08, carico 54;
   >     `/tmp/libreFolio_xr12_test_1.log`);
   >   - **rosso sul codice vecchio**: con il `refresh.py` di HEAD rimesso per una sola run e poi ripristinato (`cmp`
   >     uguale), **3 failed, 15 passed**, esattamente 1, 3 e 6, i casi previsti. Cadono per la ragione giusta: la chiamata
   >     della storia finisce ieri (3/17) invece che oggi (3/18), e nel buco finisce al giorno mancante. 2, 4 e 5 tengono
   >     i casi invariati (`/tmp/libreFolio_x_fe5c/xr12_red_proof.log`);
   >   - `ruff check` e `black --check` sui due file: puliti.

**Decisione notturna, da rivedere**
- **N17.** La correzione è generica, nel refresh, senza toccare i plugin. Il costo noto è su justETF: con `end_date`
  uguale a oggi, la sua storia aggiunge la quotazione corrente (`add_current`, solo per l'EUR), cioè una richiesta in
  più per ETF per ora di cache del grafico, per un punto che il core poi scarta. Gli eventi di justETF vengono da righe
  passate del grafico, quindi non ci guadagna niente.
  - Alternativa, da decidere di giorno: la storia di justETF smette di aggiungere la quotazione corrente, perché il
    core non usa mai un prezzo di storia datato oggi.

### FE5c — il taglio della pagina dell'asset, più X-R13: analisi ⏳ (2026-10-16, 04:58)

Inventario in sola lettura (agente explore): `routes/(app)/assets/[id]/+page.svelte`, 3603 righe, lo script va dalla 1
alla 2698.
- **Lo stato**: ~80 `$state` in un unico centro (148–371), letti e scritti da quasi tutte le regioni.
- **Helper puri, spostabili così come sono**:
  - `isRecord`, `parseBackendSignalResults`, `priceConversionErrorFromItem`;
  - le tre funzioni del calendario (1191–1291), `comparisonAssetIds`, `mergeChartPointsIncremental` (2542),
    `emptyCalendarReturnView`.
  - Due chiedono attenzione: `calendarDataFingerprint` legge un `$derived`, `translateCalendarProblem` usa `$t`.
- **Il markup**:
  - poco costosi: intestazione (2707–2765), metadati e classificazione (3445–3560), scheda del rischio (3562–3583),
    modali (3585–3603);
  - intrecciati: la barra degli strumenti (2775–2888) e l'area del grafico (2943–3292), che ha i controlli del
    calendario duplicati a 2973 e 3211.
- **Colori**: zero classi `-lf-`, quindi zero elementi misti. Baseline 312 (`themeRoles.baseline.tsv:259`).
- **X-R13**:
  - alla riga 3496, `emoji: getSectorEmoji(name)` non lo legge nessuno: `AllocationEntry` ha solo
    `name`/`value`/`amount`, e il grafico ricava l'emoji da sé alla riga 210;
  - va tolto, con l'import della riga 33.
- **Prove**:
  - `comparisonSignalPages.test.ts:67` legge il sorgente della pagina come testo (`catalogueError(...)`, l'helper,
    nessuna chiave con `_i18n:`): `catalogueError` e le sue chiamate restano nella pagina;
  - una dozzina di spec E2E e la galleria selezionano i `data-testid` della pagina;
  - nessun `vi.mock` sui moduli della pagina (D-P4 libera);
  - l'àncora `guideAnchor('asset.detail.header')` resta.
- **Punti caldi per i conflitti**: il polling dal vivo di Z (`74d028ec6`, ≈1486–1606), la scheda e gli import del
  rischio di Y4b (`51aff4a12`), la barra degli strumenti dei colori.
- **Taglio proposto**, dai pezzi meno cari:
  1. X-R13;
  2. gli helper puri in `.ts`, con le loro unità;
  3. il pannello dei metadati;
  4. la scheda del rischio e le modali;
  5. l'intestazione;
  6. `requiredFxPairs` e `assetDetailIssues` come funzioni pure;
  7. i pannelli dei segnali e delle misure;
  8. i controlli del calendario in un componente solo;
  9. la barra degli strumenti, e il caricamento più il polling in uno stato `.svelte.ts`.
- **Regole del taglio**: le classi si spostano con i loro elementi interi; le classi nuove solo sui ruoli; il taglio va
  dichiarato con `theme-roles.mjs --split` nello stesso commit.
- **Chiesto al coordinatore** che cosa serve a Z7c-1, che decide se il pezzo 9 va anticipato. Nella pausa dalle 05:30
  alle 06:45 scrivo i pezzi 1–5; le prove partono dopo.

**Risposta del coordinatore (04:59)**:
- l'ordine resta 1→9, con il pezzo 9 per ultimo;
- Z7c-1 non chiede il taglio: chiede solo che `pollLivePriceOnce` restituisca l'esito `{ok, notBefore}`, poche righe che Z
  scrive nella pagina e che entrano **prima** del pezzo 9. Al pezzo 9 le sposto nello stato `.svelte.ts` così come
  sono;
- le righe ≈1486–1606 non si toccano fino al pezzo 9: allora il coordinatore aggiorna la base con le righe di Z;
- un commit per pezzo, e `--split` nel commit di ogni pezzo che sposta classi;
- J (CP-10a) aggiunge casi a `e2e/assets/asset-detail.spec.ts`, solo per `data-testid`: se un `data-testid` deve
  cambiare, va detto al coordinatore prima del commit.

#### FE5c-1 · X-R13 ✅ (2026-10-16, 05:06)

> **Note implementazione**: due righe tolte da `routes/(app)/assets/[id]/+page.svelte`:
> - `emoji: getSectorEmoji(name)` nel `map` dei settori passato ad `AllocationPieChart` (`AllocationEntry` ha solo
>   `name`/`value`/`amount`, e il grafico legge l'emoji dal negozio dei settori);
> - l'import ormai inutile (riga 33).
>
> Nessun'altra lettura di `getSectorEmoji` nella pagina (grep).
> - Prova: `dev.py front check` → `svelte-check found 0 errors and 0 warnings` (05:06, carico 62).
> - La pagina passa da 3603 a 3602 righe; da qui i numeri di riga dell'inventario scalano di 1 dopo la 33.

> **⚠️ Fuori pista**:
> - il primo `front check` (05:03) è uscito con 4 errori, tutti in `ui/input/PasswordStrength.svelte`
>   (`password_rules`, di A6c). La causa era il client generato vecchio (04:46, zero `password_rules`): il ramo è
>   avanzato fino a `6c03c38b8` e quindi `api sync` serviva ancora.
> - L'ho lanciato **senza attendere il carico**: alla partenza la media di 1 minuto era 81, sopra la soglia di 70.
>   Errore mio, senza danni (`api sync` è leggero ed è finito in pochi secondi).
> - Da qui ogni prova passa da `/tmp/libreFolio_x_fe5c_check.sh`, che aspetta il carico ≤ 70 prima di partire.

**Commit dei primi due lotti (~05:11)**:
- `1439491ca` X-R12, `9b58867eb` X-R13, `62726a83f` journal;
- HEAD `62726a83f`;
- ingresso in `dev_release2` dopo il blocco dei colori (~06:45).

**Come entrano i pezzi del FE5c**: tutti toccano `+page.svelte`, quindi un pezzo si consegna solo dopo il commit del
precedente. Nella pausa i pezzi 3–5 nascono come **file nuovi**; li innesto nella pagina uno alla volta dopo le
06:45, e ogni innesto ha la sua prova e il suo handoff.

#### FE5c-2 · gli helper puri in moduli `.ts` ✅ (2026-10-16, scritto 05:15–05:30, provato 06:46–06:48)

> **Note implementazione**:
> - `lib/charts/chartPageSignals.ts` (nuovo, **N18**): `parseBackendSignalResults`, `signalDataContextFingerprint` e
>   `comparisonAssetIds(configs, excludeAssetId?)`.
>   - La pagina dei cambi ne ha copie identiche (`fx/[pair]/+page.svelte:525,548,564`; il suo
>     `comparisonAssetIds` non esclude nessun asset). Le adotta col FE4, che resta mio.
>   - Casa neutra accanto a `loadComparisonData.ts`, che si dichiara già «condiviso dalle due pagine di dettaglio».
> - `lib/components/assets/detail/assetDetailPriceQuery.ts` (nuovo): quello che la pagina legge dalla query dei prezzi.
>   - `parseAssetPriceQueryWithSignalIsolation(data)`: è il corpo di `queryAssetPricesBulkWithSignalIsolation`; nella
>     pagina resta solo la chiamata axios, in tre righe;
>   - `priceConversionErrorFromItem`, `calendarComparisonProblemsFromResponse`,
>     `calendarComparisonFxFailuresFromResponse` e `preserveFactualCalendarPeersForCurrentUnavailable`.
> - `lib/components/assets/detail/assetDetailChartPoints.ts` (nuovo): `mergeChartPointsIncremental`.
>   - Le chiamate della pagina restano uguali, compresa quella del polling di Z (riga ~2072 di prima), che non tocco.
> - `lib/components/charts/priceChartHelpers.ts`: `emptyCalendarReturnView` era privato e diventa esportato, con lo
>   stato `idle` di default. La pagina ne aveva una copia identica, che sparisce.
> - **Corpi spostati alla lettera**, verificato con `diff`. Le uniche differenze:
>   - i commenti di documentazione;
>   - `export`;
>   - un `responseItemFor` privato al posto di due `find` uguali;
>   - `views` come `ReadonlyMap`;
>   - `allAssets` e `displayCurrency` della pagina, che diventano l'argomento `context` (`{assets, displayCurrency}`),
>     valutato nello stesso momento di prima: all'arrivo della risposta.
> - **Nella pagina**:
>   - `comparisonAssetIds(configs)` resta come involucro di una riga, legato a `data.assetId`, così le sue sei chiamate
>     non cambiano;
>   - dagli import escono `schemas`, `backendSignalSchemas` e `COMPARISON_ASSET_RUNTIME_PARAM_KEYS`.
> - La pagina passa da 3602 a **3407 righe**. Nessun blocco del diff cade nel polling di Z (righe 1486–1606 di prima).
> - Nessuna classe spostata, quindi niente `--split`.
> - **Test**: un test-author in background scrive i Vitest dei tre moduli e dell'export, e li registra in `core-unit`.
>   Non lancia niente fino al mio via, dopo le 06:45.
> - **Da provare dopo le 06:45**:
>   - `front check`;
>   - i Vitest nuovi;
>   - `comparisonSignalPages.test.ts`, che legge il sorgente della pagina;
>   - `core-unit` e `component-unit`.

> - **I test del pezzo 2** (test-author, 05:36, scritti e non lanciati), registrati in `core-unit`:
>   - 31 in `chartPageSignals.test.ts`;
>   - 76 in `assetDetailPriceQuery.test.ts`;
>   - 7 in `assetDetailChartPoints.test.ts`;
>   - +9 in `priceChartHelpers.test.ts`.
>   - Usano gli schemi veri, senza mock; i problemi sono asseriti per `code` e `status`.
> - **⚠️ Fuori pista**, dal suo rapporto: nessun test in node caricava i **valori** del barile `$lib/charts/signals`.
>   - I due moduli nuovi ora importano direttamente da `signals/backendTypes`, `/ChartSignal`, `/resultMapper` e
>     `/signalProblem`, come già fa `priceChartHelpers.ts`.
>   - `$lib/api` invece si carica già in node in vari test (`stressBuckets`, `eligibility`, …).
> - **Comportamenti fissati dai test, non cambiati**:
>   - `priceConversionErrorFromItem` legge solo il primo errore;
>   - l'avviso di valute miste conta come errore di conversione;
>   - un ramo morto: `Array.isArray(result.error)` dopo `safeParse`.
> - **Trovato fuori dal codice spostato**: la riga 1665 di `loadChartData`. Va nel backlog come **X-R16**; non lo
>   correggo nel taglio.
> - **Secondo giro di test-author** (05:45, solo scrittura):
>   - unità di `assetDetailFxPair.ts` e di `assetDetailFxRequirements.ts`, compreso il **contratto di pigrizia** dei
>     getter: quali chiavi si leggono in quali casi;
>   - test di componente piccoli per `AssetChartModeToggle`, `AssetCalendarWindowControls`, `AssetDetailSignalsPanel` e
>     `AssetDetailMeasuresSection`;
>   - niente test di componente per intestazione e metadati: grafici, mappe e navigazione li coprono le E2E.

> - **Prove** (06:46–06:48, ognuna dopo il controllo del carico, con `nice`; la macchina era libera, carico 8–21):
>   - Prettier sui file del pezzo: ha riformattato solo `assetDetailPriceQuery.ts`, la firma su più righe;
>   - `front check` → **0 errori, 0 avvisi**, compresi i moduli e i test dei pezzi 4 e 6, già nell'albero;
>   - Vitest dei 6 file puri (pezzi 2, 4 e 6) → **373/373**;
>   - `front-utility core-unit` → **177 file, 6343/6343**, compresi i cancelli dei colori e
>     `comparisonSignalPages.test.ts`;
>   - `git diff --check` pulito.
> - Niente `api sync`, niente `--split`, niente E2E (le E2E della pagina arrivano alla fine, nello slot pesante).
> - Testo aggiornato in `developer/frontend/components/charts.md`. Il `mkdocs build` gira prima dello slot E2E.
> - **⚠️ Fuori pista**: il primo Vitest è uscito con 127, perché il wrapper fa `cd` nella radice e il percorso di
>   `vitest` era relativo a `frontend/`. Rilanciato con `bash -c 'cd frontend && …'`. Nessun effetto.

**Decisione notturna, da rivedere**
- **N18.** Gli helper che la pagina dell'asset ha in comune con quella dei cambi vanno in un modulo neutro nuovo,
  `lib/charts/chartPageSignals.ts`, non sotto `components/assets/`, così il FE4 li adotta senza import fra feature.
  - Il resto va in `lib/components/assets/detail/`, una sottocartella che il rename del FE5a si porta dietro.
  - `isRecord` resta privato, come nei sei moduli che ne hanno già una copia: nessuna utilità condivisa nuova in
    questo lotto.

#### FE5c-3/4/5 · i pezzi nuovi, scritti nella pausa ⏳ (2026-10-16, 05:20–05:30; innesti dopo le 06:45)

I componenti sono generati da script (`/tmp/libreFolio_x_fe5c_piece3.py`, `…piece5.py`), copiando alla lettera il blocco
della pagina e togliendo solo l'indentazione. La pagina **non** è ancora toccata per questi pezzi: resta al pezzo 2.

- **FE5c-3** `lib/components/assets/detail/AssetDetailMetadataPanel.svelte`, dal blocco «Metadata & Classification»
  (righe 3253–3365 della pagina al pezzo 2).
  - Uniche differenze: `showMetadata` diventa `open` (`$bindable`), e l'azione di modifica diventa `onedit`.
  - Tolto `disabled={!assetInfo}`: dentro `{#if assetInfo}` valeva sempre falso, e senza l'attributo il DOM è uguale. Le
    classi `disabled:` restano com'erano.
  - **Innesto**:
    - al posto del blocco: `<AssetDetailMetadataPanel bind:open={showMetadata} {shortDescription} {providerExternalUrl}
      {classificationLoaded} {sectorDistribution} {geographicDistribution} {identifiersList} {providerAssignment}
      {providerIconUrl} {assignmentProviderName} onedit={() => { editDataForModal = buildEditData(); editModalOpen = true;
      }} />`;
    - `showMetadata` resta nella pagina, così sopravvive al cambio di scheda e di asset come oggi;
    - dalla pagina escono gli import che restano inutili: `GeographyMap`, `AllocationPieChart` e forse `Info`,
      `ChevronDown`, `currentLanguage`, `uiLocale` (da verificare uno per uno);
    - `--split` della pagina verso la pagina e il pannello.
- **FE5c-4** `lib/components/assets/detail/assetDetailFxPair.ts` (**N19**):
  - `fxPairCreateDefaults(slug, assetCurrency, displayCurrency)`: i tre `{@const}` della modale delle coppie;
  - `displayCurrencyAfterFxPairCreated(pair, assetCurrency)`: la scelta della valuta in `handleFxPairCreated`.
  - **Innesto**: un `{@const}` al posto di tre, e due righe in `handleFxPairCreated`. Il `readonlyBase={!fxPairCreateSlug}`
    resta nella pagina. Test con test-author.
- **FE5c-5** `lib/components/assets/detail/AssetDetailHeader.svelte`, dal blocco dell'intestazione (righe 2514–2569).
  - `use:guideAnchor={'asset.detail.header'}` resta sulla radice del componente.
  - Uniche differenze:
    - `transactionsHref` in ingresso al posto di `buildTransactionsFiltersUrl(...)`: è una funzione pura di una rotta, e
      un componente di `$lib` non importa dalle rotte;
    - `{assetId}` per `AssetBrowseNav`.
  - **Innesto**: `<AssetDetailHeader assetId={data.assetId} {assetInfo} {loading} {currencyFlag} {providerIconUrl}
    {assetProviderName} {userUrl} {providerExternalUrl} transactionsHref={assetInfo ?
    buildTransactionsFiltersUrl({asset_id: assetInfo.id}) : ''} {liveUpdatesState} />`; dalla pagina escono gli import
    rimasti inutili (`ArrowLeft`, `ExternalLink`, `AssetIcon`, `AssetBrowseNav`, `LiveUpdatesStatus`, …, da verificare);
    poi `--split`.
- **Colori**: le classi si spostano intere, senza cambiarle. Nessun `-lf-` in questi blocchi, quindi nessun elemento misto.
  Le stringhe inglesi già scritte a mano («Provider», «✏️ Manual») si spostano così come sono; restano da tradurre.

**Decisione notturna, da rivedere**
- **N19.** Il pezzo 4 era «scheda del rischio e modali».
  - La scheda del rischio resta nella pagina: è un solo `<AssetRiskScenariosView>` con 11 proprietà, e un componente
    che le inoltra soltanto non toglie logica.
  - Le modali restano nella pagina, ognuna in una riga. Esce invece la loro logica, in `assetDetailFxPair.ts`: i lati
    proposti dalla modale delle coppie e la valuta mostrata dopo la creazione, con le sue unità.
- **FE5c-6** `lib/components/assets/detail/assetDetailFxRequirements.ts`: `buildRequiredFxPairs(input)` e
  `buildAssetDetailIssues(input)`, dai due `$derived.by` della pagina (`requiredFxPairs`, 125 righe; `assetDetailIssues`,
  70). Il tipo `RequiredFxPairInfo` si sposta con loro.
  - **La trappola della reattività**: il `$derived` di oggi legge lo stato **in modo pigro**.
    - Per esempio, `chartData.length` solo quando la coppia principale non ha ancora una data convertita;
      `calendarSnapshotIsCurrent` solo nella vista del calendario; `$t(...)` del nome di ripiego solo per un pari che
      non si trova.
    - Un oggetto letterale leggerebbe tutto subito: più dipendenze, e la lista delle coppie, il banner compreso, si
      ricalcolerebbe a ogni punto del polling.
    - Per questo la pagina passerà un oggetto di **getter**, e il modulo lo legge nello stesso ordine e alle stesse
      condizioni del corpo di prima. Dipendenze identiche.
  - **Differenze dal corpo di prima**:
    - `assetInfo` è letto una volta in una variabile locale, nello stesso punto;
    - la variabile del ciclo degli eventi si chiama `peer`, per non coprire la nuova locale;
    - tolto `const parts = pair.slug.split('-')`, mai usato;
    - `any[]` diventa `readonly unknown[]`;
    - le due chiamate a `$t` passano per `eventsLabel` e `assetFallbackLabel(assetId)`, lette negli stessi punti.
  - **Innesto**:
    - `const fxRequirementsState: RequiredFxPairsInput = {get displayCurrency() {…}, get asset() {return assetInfo},
      get pageAssetId() {return data.assetId}, get configuredFxSlugs() {return allConfiguredFxSlugs}, …, get
      hasChartData() {return chartData.length > 0}, get eventsLabel() {return $t('events.fxBannerContext') ?? 'for
      dividend/cash events'}, assetFallbackLabel: (id) => $t('chartSettings.signals.assetFallback', {values: {id:
      String(id)}})}`;
    - poi `let requiredFxPairs = $derived(buildRequiredFxPairs(fxRequirementsState))`, e lo stesso per
      `assetDetailIssues`;
    - restano nella pagina `fxConversionMissing`, `fxPairSlug` e `mainFxPairUrl`.
  - **Da notare per il FE4**: `toSlug` è una copia di `createPairSlug` di `fxStoreRegistry.ts`, che però rende
    maiuscolo. Si sposta così com'è; l'unificazione si decide col FE4.
- **FE5c-8** (anticipato rispetto al 7, perché più semplice e senza `bind:this`). Il «doppione» dei controlli del
  calendario è il selettore prezzi/rendimento, disegnato in due rami: quello con i dati (o col calendario) e quello
  vuoto, che è sempre in modalità prezzi.
  - `AssetChartModeToggle.svelte` (generato da `/tmp/libreFolio_x_fe5c_piece8.py`, dal primo ramo):
    - una sola copia per i due rami;
    - il tipo `AssetChartPrimaryMode` esportato dallo `<script module>`, così la pagina lo importa e toglie l'alias
      locale.
    - Nel ramo vuoto il bottone del calendario guadagna `disabled:opacity-40 disabled:cursor-not-allowed`, inerti
      perché non è mai disabilitato. `aria-pressed` viene disegnato `"true"`/`"false"` come prima.
  - `AssetCalendarWindowControls.svelte`: i preset, la durata personalizzata e il link alla doc. Ha tre `$bindable`
    (`customAmount`, `customUnit`, `customEditing`), che restano stato della pagina perché `setPrimaryMode` e
    `setCalendarPreset` chiudono l'editor. Il `$derived` delle opzioni di durata ci entra, perché lo usa solo lui.
  - **Innesto**:
    - ramo 1: `<AssetChartModeToggle {primaryMode} onselect={setPrimaryMode} />`, e sotto `{#if primaryMode ===
      'calendar-return'}<AssetCalendarWindowControls selection={calendarWindowSelection}
      bind:customAmount={calendarCustomAmount} bind:customUnit={calendarCustomUnit}
      bind:customEditing={calendarCustomEditing} onpreset={setCalendarPreset} oncustom={setCalendarCustom} />{/if}`;
    - ramo 2: lo stesso toggle;
    - escono gli import inutili (`ChartLine` resta per le schede, `Percent`, `CompactDurationBadge`, `DocsLink`, e da
      `calendarReturnWindow` quello che non serve più);
    - poi `--split`.
- **FE5c-7** (**N20**): i due pannelli diventano **cornici con uno snippet `children`**, generate da
  `/tmp/libreFolio_x_fe5c_piece7.py`.
  - Il contenuto resta nella pagina: `ChartSignalsSection` con le sue 20 proprietà, e i due `MeasurePanel` con i loro
    `bind:this`, che la pagina usa per `addPoint`, `clearMeasures` e `stopMeasureMode`.
  - `AssetDetailSignalsPanel.svelte`: il riquadro, il toggle (`asset-detail-signals-toggle`, che
    `openSignalConfiguration` cerca per testid), l'intestazione e il chevron. `open` è `$bindable`, e lo stato
    `showSignals` resta nella pagina, che lo usa anche in `savedPanelStates` e in `openSignalConfiguration`.
    `{@render children()}` sta dentro `{#if open}`, quindi la sezione si monta e si smonta come prima.
  - `AssetDetailMeasuresSection.svelte`: il riquadro (`data-mode`) e l'intestazione, con il distintivo «attivo»,
    «Aggiungi misura» e il chevron.
    - Ingressi: `mode`, `open`, `measureModeActive`, `canAddMeasure`, `ontoggle`, `onaddmeasure`.
    - La pagina li calcola come prima: `activeMeasuresOpen()`, `activeMeasureMode()` e
      `activeChartData.filter((point) => !point.missing).length >= 2`, valutati nel suo template, quindi con le stesse
      dipendenze.
    - I due pannelli delle misure sono lo snippet.
  - **Innesto**:
    - `<AssetDetailSignalsPanel bind:open={showSignals}><ChartSignalsSection … /></AssetDetailSignalsPanel>`;
    - `<AssetDetailMeasuresSection mode={primaryMode} open={activeMeasuresOpen()} measureModeActive={activeMeasureMode()}
      canAddMeasure={…} ontoggle={() => setActiveMeasuresOpen(!activeMeasuresOpen())} onaddmeasure={() => {
      setActiveMeasuresOpen(true); activeMeasurePanel()?.addMeasureFromChartData(); }}>…i due pannelli…</AssetDetailMeasuresSection>`;
    - escono gli import inutili (`TrendingUp`, `Ruler`, …);
    - poi `--split`.

**Decisione notturna, da rivedere**
- **N20.** I pannelli dei segnali e delle misure diventano cornici con lo snippet, non componenti che inoltrano tutte
  le proprietà del contenuto.
  - L'inoltro avrebbe spostato una ventina di proprietà senza togliere logica.
  - Avrebbe portato il `bind:this` dei pannelli delle misure dentro un componente intermedio.
  - Con lo snippet il contenuto resta tipizzato dove vivono i suoi dati, e la cornice (le classi, il toggle e il
    chevron) esce dalla pagina.
- **Gli innesti, scritti in uno script** (`/tmp/libreFolio_x_fe5c_splice.py <pezzo> [--apply]`, uno per pezzo).
  - Sostituisce il blocco con la chiamata, aggiunge l'import, e toglie solo gli import che nessuna riga fuori dagli
    import usa più, compresi i nomi dentro gli import su più righe.
  - **Prova a secco** su una copia in `/tmp` (05:28): la catena 3→8 si applica tutta sulla pagina al pezzo 2, da
    3408 a **2996 righe**.
  - Gli import tolti sono solo quelli rimasti inutili. `Ruler`, `ChartLine` e `currentLanguage` restano, perché la
    pagina li usa ancora.
- **`--split` per pezzo**, dentro `frontend/src`. Serve solo ai pezzi che spostano classi: 3, 5, 7 e 8. I pezzi 2, 4 e 6
  sono TypeScript puro.
  - Pezzo 3: `node frontend/scripts/theme/theme-roles.mjs --split 'routes/(app)/assets/[id]/+page.svelte:routes/(app)/assets/[id]/+page.svelte,lib/components/assets/detail/AssetDetailMetadataPanel.svelte'`.
  - Gli altri allo stesso modo, con i loro file.

### K-16 e O-9 — un lotto piccolo, scritto nella pausa ✅ (2026-10-16, scritto 05:30–05:40, provato 06:49–06:53)

Sono le due voci backend del dominio che il piano mette «in un treno qualunque» (§9, punto 8). Nessun file in comune con
il FE5c, quindi un commit separato.

- **K-16** (D-X7): in `borsa_italiana/plugin.py`, `"etc/etn"` passa da `AssetType.ETF` a `AssetType.ETF_COMMODITY`, con
  una riga di commento.
  - Borsa Italiana usa la stessa etichetta per ETC ed ETN, e D-X7 le mappa tutte e due su `ETF_COMMODITY`.
  - **È un'approssimazione**: un ETN su un indice o su una valuta diventa `ETF_COMMODITY` anche lui, perché
    l'etichetta non li distingue. Il commento nel codice lo dice.
  - Test: un'asserzione in `test_borsa_italiana_errors.py::test_map_asset_type` (azione `services provider-errors`).
- **O-9**: i parametri di justETF e del CSS scraper si vedevano col nome della chiave (`current_css_selector`), perché
  i due `params_schema` non avevano `label`, e le descrizioni erano solo in inglese.
  - Nei due `params_schema` c'è ora un `label` inglese, come in Borsa Italiana: è il ripiego quando manca la
    traduzione.
  - Frammenti `assets.providerParams.<codice>.{label,description}.<chiave>` in 4 lingue: aggiunti al `justetf/i18n/`
    esistente (che aveva solo `pluginSettings`), e un `css_scraper/i18n/` nuovo.
  - Nessuna modifica al frontend: `ProviderAssignmentSection.paramText` legge già quelle chiavi.
  - I `placeholder` restano non tradotti: sono valori d'esempio.
- **Test** (test-author, 05:50, scritti e non lanciati):
  - K-16: due asserzioni in `test_map_asset_type` (`"ETC/ETN"` e `" etc/etn "` danno `ETF_COMMODITY`), con `"ETF"`
    che resta `ETF`.
  - O-9: tre test in `test_provider_contracts.py::TestAssetProviderContract`, un file già registrato (`services
    provider-contracts`):
    - **le traduzioni dei parametri coprono esattamente il modulo**, per ogni provider asset che ne ha, in tutte le
      lingue del catalogo: niente chiavi mancanti né vecchie, testi non vuoti;
    - **un controllo positivo**, perché il test di sopra non passi senza controllare niente;
    - **ogni campo del modulo ha un `label` inglese**, per Borsa, CSS scraper e justETF.
- **Effetto di K-16 sugli asset esistenti**:
  - `_map_asset_type` serve anche alla ricerca e a `fetch_asset_metadata`, quindi un ETC già salvato come `ETF`
    diventa `ETF_COMMODITY` al primo «Aggiorna metadati».
  - Lo fa **solo su richiesta dell'utente**: `refresh_assets_from_provider` è chiamato solo da
    `api/v1/assets/providers.py:387`, mai dallo scheduler. Il risultato mostra il vecchio e il nuovo valore.
- **Trovato da test-author, corretto nel lotto** (stesso tema di O-9): la descrizione di `codice_fondo` di Borsa
  Italiana nel backend aveva guadagnato «when the fund is not on the XMIL market API», e le 4 traduzioni no. In
  interfaccia vinceva la traduzione, quindi si leggeva il testo vecchio. Ora le 4 lingue sono allineate.
- **Prove** (06:49–06:53, ognuna dopo il controllo del carico, con `nice`, a carico 40–52):
  - `services provider-errors` → **182 passed**;
  - `services provider-contracts` → **442 passed, 4 skipped**: i tre provider senza traduzioni e un salto vecchio di
    mockprov;
  - `services borsa-italiana-search` → verde;
  - `utils gate-plugin-i18n-ownership` e `gate-plugin-layout` → verdi;
  - `i18n check` → strict, 4762 chiavi, 73 frammenti di plugin;
  - ruff e black sui 5 file Python → puliti, anche dopo la correzione del commento.
- **⚠️ Fuori pista**: il commento di K-16 diceva «quasi sempre su una materia prima», un'affermazione non verificata.
  L'ho corretto in «approssimazione per un ETN su un indice o una valuta» prima dell'handoff.
- K-16 e O-9 sono chiuse nel backlog 38 (`38_postReleaseBacklog/README.md`), come A ha fatto con K-17.

### CP13 — F21, C-90 e C-66: analisi preliminare (2026-10-16, 05:40, sola lettura; da mandare al coordinatore con l'ultimo pezzo del FE5c)

**F21 nella specifica** («Feature SaaS Readiness», righe 127–130):
- ogni provider ha `priority` e `tier`;
- la ricerca mostra prima i `premium` (badge «Premium»), poi le azioni «Non lo trovi? Segnalacelo» e «Prezzo manuale /
  import», e in fondo una sezione chiusa «Fonti non premium (community)»;
- alla prima apertura della sezione compare un avviso («fonte di terzi, configurata da te, nessuna garanzia»), e la
  scelta vale solo per quell'asset: nessuna cache condivisa;
- la specifica ha un terzo livello `advanced`. Il perimetro approvato ne ha due, e resto su due (§3).

**Disegno** (approvato in §4.6, D-X3 e D-X8):
- **Backend**:
  - nella base dei provider asset, `tier: ClassVar` (`premium` | `community`, default `community`) e
    `search_priority: ClassVar[int]`;
  - livello e priorità effettivi letti a ogni chiamata, con la sovrascrittura `LIBREFOLIO_ASSET_PROVIDERS_PREMIUM` /
    `…_ORDER` (non impostate = come dichiarato);
  - `FAProviderInfo` espone `tier` e `priority`, poi `api sync`;
  - la ricerca non in streaming ordina per gruppo e priorità **solo se almeno un premium è permesso**: altrimenti
    l'ordine resta quello di oggi.
- **Frontend** (`AssetSearchAutocomplete`): con almeno un premium attivo:
  - la sezione Premium col badge;
  - le due azioni;
  - la sezione community chiusa, con l'avviso alla prima apertura e la scelta per quell'asset soltanto.
  - Senza premium, niente cambia (D-X3). Oggi nessun provider è premium, quindi il self-hosted resta identico.
- **Prove**:
  - pytest in processo per la sovrascrittura (`monkeypatch` dell'ambiente);
  - Vitest dei gruppi;
  - E2E con le risposte dei provider instradate, per avere un premium senza toccare l'ambiente del server;
  - uno scatto in galleria, da concordare con G.
- **C-90**: in `ProviderAssignmentSection`, accanto all'esito di «Testa configurazione», la nota «prova sugli ultimi
  giorni: alla creazione LibreFolio scarica tutto lo storico». Una chiave i18n in `assets`.
- **C-66**: l'avviso nel dialogo di sync quando l'intervallo copre dati già presenti. Parte dal file finale di T
  (`SyncModalBase`, `PageSyncModal`, ~07:30).

**Domande per il coordinatore**, con le mie proposte:
1. **L'indirizzo di «Segnalacelo»**. Proposta: `LIBREFOLIO_SUPPORT_URL`, costruita come `LIBREFOLIO_BILLING_URL` (A,
   `config/accounts.py`, helper `_url`) e pubblicata in `GET /system/instance`. Non impostata, il link va alle issue
   di GitHub, che `HelpMenu` e `FixFlaggedStep` già usano.
   - Il nome e il proprietario li decide il coordinatore: potrebbe interessare anche `HelpMenu`, che non è mio.
2. **«Prezzo manuale / import» dentro la modale di creazione**. Proposta: un'azione «Continua senza fonte», che chiude
   la ricerca e lascia l'asset senza provider (la modale lo sa già fare), con una riga «i prezzi si aggiungono a mano
   o da un file». Niente salto all'import wizard da dentro la modale.

**Peso**: backend piccolo; frontend medio (ricerca, i18n, Vitest, E2E, galleria). C-66 dopo il lotto di T.

**Risposte del coordinatore (16/10, 07:07)**:
1. **`LIBREFOLIO_SUPPORT_URL`**:
   - è di **H** (configurazione d'istanza, `GET /system/instance`, pagina dei provider di hosting), ma la **scrivo io**
     nel CP13, sul modello di `LIBREFOLIO_BILLING_URL`;
   - va in un modulo `config/` della piattaforma, non in `accounts.py`, con la riga in `.env.example` e nella doc dei
     provider di hosting;
   - `HelpMenu` la adotta più tardi, in un lotto a parte; il coordinatore avvisa H.
2. **«Continua senza fonte»**: è una scelta di UX visibile, quindi va nella lista del mattino per il developer, con la
   mia proposta. Se il CP13 parte prima della risposta, la costruisco così, marcata «Decisione notturna, da rivedere».

**Preferenze di H per `LIBREFOLIO_SUPPORT_URL`** (H ne è il proprietario; coordinatore, 07:11):
- **Accessore**: `backend/app/config/platform.py`, `support_url() -> str | None`, con le regole di `billing_url()`:
  - vuota o fatta di spazi → `None`;
  - solo `http(s)://`;
  - via la barra finale;
  - `ValueError` per tutto il resto.
- **La validazione**: non si copia `_url()` di `config/accounts.py`, che è di A.
  - Diventa un helper pubblico in `config/__init__.py`, chiamato dai due accessori di A. Serve l'ok di A, che il
    coordinatore chiede all'avvio del CP13.
  - Se A dice di no, un import da `accounts`, mai una copia.
- **`GET /system/instance`**:
  - il campo di primo livello `support_url: str | None` in `InstanceConfigResponse` (default `null`; il frontend ricade
    sulle issue di GitHub);
  - una funzione di servizio che cattura il `ValueError`, lo registra una volta e restituisce `None`, come
    `billing_link()`;
  - facoltativo: il `ConfigCheck` `platform.support_url` (avviso), in coda a `CONFIG_CHECKS` in `config_audit.py`, che
    tocca anche A7.
- **`.env.example`**: una riga commentata in «Instance Profile», dopo `LIBREFOLIO_CSP_REPORT_ONLY`.
- **Doc**:
  - una riga in `admin/hosting_providers`;
  - una riga in «Main Options» di `admin/configuration.en.md`;
  - `support_url()` nell'elenco degli accessori di `platform.py` in `developer/architecture/settings.md`.
- **Prove**: `services config-package`, `config-env-example`, `api system`.
- **Il secondo giro di test** (test-author, 06:05, scritti e non lanciati), 130 test:
  - `assetDetailFxPair.test.ts` 24, con ogni caso confrontato con una copia alla lettera delle righe di prima;
  - `assetDetailFxRequirements.test.ts` 78: ordine, slug canonici, ogni stato, salti dei pari, eventi con forme vere
    di `FAAssetEventPointOut`, e il contratto di pigrizia (quali chiavi si leggono, ognuna col suo caso contrario);
  - componenti: `AssetChartModeToggle` 5, `AssetCalendarWindowControls` 10, `AssetDetailSignalsPanel` 4 (con
    l'imbracatura `src/__tests__/harness/AssetDetailSignalsPanelHarness.svelte`, che lega `open` come la pagina, nel
    commit del pezzo 7), `AssetDetailMeasuresSection` 9.
  - Rilettura del codice spostato: nessun difetto. Solo rami innocui ereditati dalla pagina, per esempio l'`if
    (input.displayCurrency)` attorno agli eventi, sempre vero.
- **In attesa fuori dall'albero** (06:08, `/tmp/libreFolio_x_fe5c_hold/`), con il loro percorso:
  - i componenti dei pezzi 3, 5, 7 e 8;
  - i loro 4 test di componente;
  - l'imbracatura.
- **Un commit per pezzo, con le sue registrazioni.**
  - **Il cancello dei colori** (`core-unit`) legge l'albero di lavoro: un `.svelte` nuovo e non tracciato, con classi di
    tavolozza, lo fa fallire. Per questo i componenti dei pezzi 3, 5, 7 e 8, con i loro test, aspettano in
    `/tmp/libreFolio_x_fe5c_hold/` e rientrano solo al loro innesto, nello stesso commit del `--split`.
  - I moduli `.ts` puri dei pezzi 4 e 6 restano al loro posto: non hanno classi, e `front check` li controlla subito.
  - **Le righe del runner**: test-author non registra il secondo giro; ogni riga entra col suo pezzo.

**Commit dei lotti del mattino**:
- FE5c-2: `a400a7cd1` + journal `ae25f0070`;
- K-16/O-9: `c21f050bc` + journal `a6b9faf81`, già in `dev_release2` con `bfc0db8aa` (treno 96), con la riga del
  CHANGELOG;
- X-R12/X-R13 in `dev_release2` con `92a0d4daf` (treno 94).

#### FE5c-3 · il pannello dei metadati ✅ (2026-10-16, 06:53–06:59)

> **Note implementazione**:
> - `AssetDetailMetadataPanel.svelte` è rientrato da `/tmp/libreFolio_x_fe5c_hold/` e innestato con
>   `/tmp/libreFolio_x_fe5c_splice.py 3 --apply`. La pagina passa da 3407 a 3308 righe.
> - Dagli import della pagina escono `Info`, `AllocationPieChart`, `GeographyMap` e `uiLocale`, che nessun'altra riga
>   usava; `ChevronDown` e `currentLanguage` restano, perché servono altrove.
> - Prettier ha cambiato solo il pannello: il bottone «Modifica», senza più `disabled`, sta su una riga. La pagina era
>   già formattata.
> - **`--split`**: la pagina scende da 312 a 258 classi di tavolozza, e il pannello ne prende 54. La somma resta 312:
>   nessuna classe persa né aggiunta, nessun elemento misto.
> - **Prove** (con `nice`, dopo il controllo del carico):
>   - `front check` → 0 errori, 0 avvisi (06:57, carico 64);
>   - `front-utility core-unit` → 177 file, 6343/6343, cancelli dei colori compresi (06:59);
>   - `git diff --check` pulito; porta 6183 libera.
> - Le E2E del pannello (`asset-detail.spec.ts:327`, `onboarding-guides`, la galleria) girano alla fine, nello slot
>   pesante.

FE5c-3 committed: `7c27785ae` + journal `89ef3e1e9`.

#### FE5c-4 · la logica della modale delle coppie ✅ (2026-10-16, 07:00–07:07)

> **Note implementazione**:
> - `/tmp/libreFolio_x_fe5c_splice.py 4 --apply`: tre `{@const}` diventano uno solo,
>   `fxCreateDefaults = fxPairCreateDefaults(…)`, e in `handleFxPairCreated` la scelta della valuta passa da
>   `displayCurrencyAfterFxPairCreated` (`!== null`, che copre anche il caso di un lato vuoto). `readonlyBase` resta
>   nella pagina.
> - Registrato `assetDetailFxPair.test.ts` in `core-unit`.
> - Prettier: nessuna modifica.
> - **Prove**:
>   - `front check` → 0/0;
>   - `core-unit` → **178 file, 6367/6367**, cioè +1 file e +24 test, quelli del modulo.
>   - Il wrapper ha aspettato che il carico scendesse da 113 a 55 prima di partire.
>   - `git diff --check` pulito.

FE5c-4 committed: `4c03a0e7b` + journal `3f220dbc5`.

#### FE5c-5 · l'intestazione ✅ (2026-10-16, 07:07–07:11)

> **Note implementazione**:
> - `AssetDetailHeader.svelte` è rientrato da `/tmp/libreFolio_x_fe5c_hold/` e innestato con `splice.py 5 --apply`. La
>   pagina passa da 3308 a 3247 righe.
> - Prettier ha messo la chiamata su una riga sola, perché ci sta nei 300 caratteri.
> - **Dagli import della pagina escono** `goBack`, `ArrowLeft`, `ExternalLink`, `AssetIcon`, `AssetBrowseNav`,
>   `getAssetTypeIconUrl`, `LiveUpdatesStatus`, `overflowScrollTextClass` e `scrollOnOverflow`.
> - **Restano nella pagina** `buildTransactionsFiltersUrl`, che calcola `transactionsHref`, e il tipo
>   `ActivePollingState`, che tipizza `liveUpdatesState`.
> - `use:guideAnchor={'asset.detail.header'}` resta sulla radice del componente.
> - **`--split`**: la pagina scende da 258 a 230, e l'intestazione ne prende 28. La somma resta 258.
> - **Prove**:
>   - `front check` → 0/0;
>   - `core-unit` → 178 file, 6367/6367;
>   - `git diff --check` pulito.

FE5c-5 committed: `ca0cf62b8` + journal `636c1559b`.

#### FE5c-6 · le coppie richieste e gli avvisi del banner ✅ (2026-10-16, 07:11–07:17)

> **Note implementazione**:
> - `splice.py 6 --apply`: al posto dei due `$derived.by` (≈195 righe) entrano due oggetti di getter
>   (`fxRequirementsState` e `assetDetailIssuesState`) e
>   `requiredFxPairs = $derived(buildRequiredFxPairs(fxRequirementsState))`, più lo stesso per `assetDetailIssues`.
> - I getter leggono lo stato negli stessi punti del corpo di prima. `$t` sta dentro il getter `eventsLabel` e dentro
>   `assetFallbackLabel`, così la dipendenza dal catalogo resta.
> - La pagina passa da 3247 a 3117 righe. Esce l'import di `getComparisonEventFxDependency`.
> - Registrato `assetDetailFxRequirements.test.ts` in `core-unit`.
> - Aggiornata la frase di `requiredFxPairs` in `developer/frontend/components/charts.md`.
> - **Prove**:
>   - `front check` → 0 errori, 0 avvisi: nessun avviso di Svelte sullo stato letto nel posto sbagliato, e
>     `AssetDetail` soddisfa l'ingresso del modulo;
>   - `core-unit` → **179 file, 6445/6445**, cioè +78 test, quelli del modulo, compreso il contratto di pigrizia.
>   - Il wrapper ha aspettato che il carico scendesse da 82.
>   - `git diff --check` pulito.
> - **La reattività vera della pagina la provano solo le E2E**: `asset-detail.spec.ts` (≈2769–3301) fa apparire e
>   sparire `data-quality-issue-FX_PAIR_NO_DATA`. Sono nello slot finale.

FE5c-6 committed: `260dbc321` + journal `d1bd1a508`.

**I due difetti della doc segnalati dal docs-writer di B** (07:18) **sono già corretti** in `dev_release2` dal CP11c
(`c8d23c544`, treno 91): «eight tabs; everyone has the first five…» e «two ask for one… justETF and Borsa Italiana».
Il docs-writer leggeva una base precedente. Restano indietro le **traduzioni**: `user/settings/index.{it,fr,es}` dice
ancora «quattro schede», e `admin/configuration.{it,fr,es}` non ha la sezione dei plugin. È un debito di traduzione
vero, che va ad Aphra su richiesta del developer; nessun commit della doc.

#### FE5c-7 · le cornici dei segnali e delle misure ✅ (2026-10-16, 07:19–07:25)

> **Note implementazione**:
> - Rientrati da `/tmp/libreFolio_x_fe5c_hold/`:
>   - `AssetDetailSignalsPanel.svelte` e `AssetDetailMeasuresSection.svelte`;
>   - i loro due test di componente;
>   - l'imbracatura `src/__tests__/harness/AssetDetailSignalsPanelHarness.svelte`.
> - `splice.py 7 --apply`: `ChartSignalsSection` e i due `MeasurePanel`, con i loro `bind:this`, restano nella
>   pagina come snippet `children` (N20). La pagina passa da 3117 a 3070 righe.
> - Registrati i due test in `component-unit`, dopo `AssetBrowseNav.test.ts`.
> - Prettier: nessuna modifica.
> - **`--split`**: la pagina scende da 230 a 198, le cornici ne prendono 13 e 19. La somma resta 230. L'imbracatura
>   sta sotto `__tests__`, che il cancello non misura.
> - **Prove**:
>   - `front check` → 0/0;
>   - Vitest dei due test di componente → **13/13**;
>   - `core-unit` → 179 file, 6445/6445;
>   - `git diff --check` pulito.
>   - Il `component-unit` intero gira dopo il pezzo 8, con le registrazioni di tutti e due i pezzi.

FE5c-7 committed: `086a50005` + journal `f4cd61273`.

#### FE5c-8 · il selettore della modalità e la finestra del calendario ✅ (2026-10-16, 07:26–07:36)

> **Note implementazione**:
> - Rientrati da `/tmp/libreFolio_x_fe5c_hold/`: `AssetChartModeToggle.svelte` e `AssetCalendarWindowControls.svelte`,
>   con i loro test. La cartella d'attesa ora è vuota.
> - `splice.py 8 --apply`:
>   - il selettore prende il posto delle **due** copie, quella con i dati e quella vuota;
>   - la finestra prende il posto del suo blocco;
>   - `calendarDurationOptions` esce dalla pagina e va nel componente;
>   - l'alias locale `AssetChartPrimaryMode` diventa l'export dello `<script module>` del selettore;
>   - escono `Percent`, `CompactDurationBadge`, `DocsLink` e `CALENDAR_RETURN_UNIT_LABEL_KEYS`.
>   - Prettier ha messo su una riga la chiamata della finestra. La pagina passa da 3070 a **2969 righe**.
> - Registrati i due test in `component-unit`.
> - **`--split`**: la pagina scende da 198 a 155, il selettore ne prende 20 e la finestra 11, per un totale di 186: 12 in
>   meno di prima, perché sono le classi della seconda copia del selettore, che non c'è più.
> - **Prove**:
>   - `front check` → 0/0;
>   - Vitest dei due test → **15/15**;
>   - `core-unit` → 179 file, 6445/6445;
>   - **`component-unit` intero** → **154 file, 4007/4007**, con i 4 test di componente del FE5c;
>   - `check-orphans` → tutti i test raggiungibili (469 in `frontend/src`);
>   - `git diff --check` pulito; porta 6183 libera.
>
> **Il taglio, finora**: la pagina è passata da 3603 a 2969 righe in otto pezzi, sette commit e la chiusura di X-R13.
> - **Restano**:
>   - il pezzo 9, cioè la barra degli strumenti, il caricamento e il polling in uno stato `.svelte.ts`, dopo le righe
>     di Z nella base;
>   - l'aggiornamento della base, che porta anche le classi di DV in `components/charts/`;
>   - lo slot E2E: `asset-detail`, `asset-data-editor`, `asset-event-delete`, `onboarding-guides`, e gli scatti della
>     galleria della pagina.

FE5c-8 committed: `103149654` + journal `95b0be788`. Backlog X-R17–X-R20 `c13cc2d1a`; base aggiornata con `dev_release2`
`7f58a6292`, HEAD `fa97791f6`.

**Verifica della base `fa97791f6`** (07:41–07:47):
- `api sync`; `front check` → 0/0;
- `core-unit` → rosso in `fxRoutesStore.test.ts`, che non è mio né del merge (2 su 6458);
- **triage**: con il carico a ~100 il primo caso ha superato i 5 s di Vitest, perché ogni caso fa un `import()` a
  freddo del grafo dello store, e il secondo caso ha ereditato la chiamata rimasta in sospeso. Da solo il file passa
  in 2,1 s;
- **verdetto: assunzione (il tempo)**, non «instabile». Aperta **X-R21**, la cura dopo il backend del CP13.
- `core-unit` va rilanciato a carico basso prima delle E2E del FE5c.

### CP13 — backend ⏳ (via del coordinatore 16/10, 07:37; il frontend aspetta P20)

Ordine: (1) `env_url` spostato, (2) `LIBREFOLIO_SUPPORT_URL`, (3) F21. Commit separati dal FE5c e fra loro.

1. ✅ (07:44–07:52) **`env_url(name)`** in `backend/app/config/__init__.py`, accanto a `env_secret`, con l'ok di A e di H.
   > **Note implementazione**:
   > - È il `_url()` di `config/accounts.py`, con le stesse regole: vuota o fatta di spazi → `None`; il valore,
   >   ripulito dagli spazi, deve cominciare con `http://` o `https://`; via una barra finale; altrimenti `ValueError`
   >   col nome della variabile.
   > - Gestisce gli spazi da sé, perché `_blank_to_none` resta ad A per gli altri accessori.
   > - In `accounts.py` sparisce `_url`, e `public_url()` e `billing_url()` chiamano `env_url`. Nient'altro toccato, come
   >   chiesto da A (A7a lavora lì).
   > - Doc: la docstring del pacchetto e `developer/architecture/settings.md`, con `env_url()` nella base e un punto
   >   sulla regola degli indirizzi.
   > - **Prove**:
   >   - `services registration` → **147 passed**: i test di A sugli accessori coprono spazi, barra finale, solo http(s)
   >     e il log del valore non valido;
   >   - `services config-package` → **694 passed**;
   >   - ruff e black puliti; `git diff --check` pulito.
   >   - I test diretti di `env_url` arrivano col passo 2, nello stesso file di quelli di `support_url`.

CP13-1 committed: `9c1161ff2` + journal `3a81f5238`. **Avviso del coordinatore**: A7a (prima di me nel treno) aggiunge in
`config/accounts.py` degli import e il blocco F02 dopo `billing_url()`. Al prossimo aggiornamento della base c'è un piccolo
conflitto, negli import e accanto a `billing_url()`: si tengono tutti e due, cioè i miei `env_url` nei due accessori e tutto
il blocco di A.

2. ✅ (07:53–08:25) **`LIBREFOLIO_SUPPORT_URL`**, con le preferenze di H.
   > **Note implementazione**:
   > - `config/platform.py::support_url()` → `env_url("LIBREFOLIO_SUPPORT_URL")`.
   > - `services/platform/instance_links.py` (nuovo, di H): `support_link()` cattura il `ValueError`, lo registra una
   >   sola volta (`functools.cache`, come `billing_link()`) e restituisce `None`.
   > - `InstanceConfigResponse.support_url: str | None = None`, riempito in `GET /system/instance`.
   > - `.env.example`: la riga in «Instance Profile», dopo `LIBREFOLIO_CSP_REPORT_ONLY`.
   > - **Doc**:
   >   - la riga in «Main Options» di `admin/configuration.en.md`, dopo `LIBREFOLIO_CSP_REPORT_ONLY`;
   >   - un punto in «For Each Instance» di `admin/hosting_providers.en.md`;
   >   - in `developer/architecture/settings.md`: la variabile fra le chiavi fuori da `Settings`, `support_url()`
   >     fra gli accessori di `platform.py`, e il ripiego per un valore non valido.
   > - **Non fatto**: il `ConfigCheck` facoltativo. Chiederebbe chiavi `instance.checks.*` nel sottosistema di H e una
   >   riga in `config_audit.py`, che sta toccando anche A7a. Il valore non valido resta comunque registrato una volta.
   > - **Prove finora**:
   >   - `api sync` (il campo è facoltativo nel client);
   >   - `front check` → 0/0;
   >   - `services config-env-example` → 38/38;
   >   - ruff e black puliti.
   > - **I test** (test-author, in `test_config_package.py` e `test_system_api.py`):
   >   - `env_url` diretto, 13 casi validi e 8 non validi;
   >   - `support_url()`;
   >   - `support_link()`: nessun log se è valido; un solo errore con `problem` e `consequence` anche se viene letto due
   >     volte;
   >   - `GET /system/instance`: dal vivo, `support_url` è `null`; in processo, con l'indirizzo dà il valore senza la
   >     barra, e con `ftp://` risponde 200 con `null`, mai un 500.
   > - **⚠️ Fuori pista**: il campo nuovo ha rotto tre test che controllavano le chiavi esatte del corpo. Due sono in
   >   `test_system_api.py`, di H; il terzo è INSTANCE-002 in `test_registration_api.py`, di A. Test-author li ha
   >   aggiornati; quello di A è una riga, segnalata al coordinatore.
   > - Aggiornata la docstring di `services/platform/__init__.py`, con `instance_links`.
   > - **Prove** (con `nice`, dopo il controllo del carico):
   >   - `services config-package` → **728**;
   >   - `api system` → **120**: la partenza del server della corsia ha ricostruito il frontend e la doc, rimasti
   >     indietro, e per questo ha impiegato 8 minuti;
   >   - `api registration` → **96**: l'unico avviso è una deprecazione di Starlette, vecchia;
   >   - `services config-env-example` → 38;
   >   - ruff e black puliti;
   >   - `mkdocs build` stretto ok, `check-links` 97 validi;
   >   - `git diff --check` pulito; porta 6183 libera.
   > - **Proposta per A e H**, non fatta: `env_url` controlla solo l'inizio del valore. `https://` da solo diventa
   >   `"https:/"` e viene pubblicato come link, e uno spazio interno passa. Le stesse regole di prima per
   >   `PUBLIC_URL` e `BILLING_URL`: chiedere un host sarebbe più severo, quindi va deciso da loro.
3. ⏳ **F21 backend** (disegno §4.6, D-X3, D-X8), da scrivere dopo l'handoff del CP13-2:
   - **Le dichiarazioni**: in `AssetSourceProvider`, `tier: ClassVar[FAProviderTier] = COMMUNITY` e
     `search_priority: ClassVar[int] = 100` (più basso = prima). Nessun provider di oggi è premium: il primo sarà quello a
     pagamento del F06.
   - **La sovrascrittura** in `config/plugins.py` (sezione di X):
     - `asset_providers_premium()` legge `LIBREFOLIO_ASSET_PROVIDERS_PREMIUM`: se è impostata, sono premium
       esattamente i codici elencati;
     - `asset_providers_order()` legge `LIBREFOLIO_ASSET_PROVIDERS_ORDER`: i codici elencati vengono prima, in
       quell'ordine, e gli altri dopo, per priorità dichiarata;
     - liste separate da virgole, senza maiuscole; vuota o fatta di spazi conta come non impostata.
   - **Il punto unico**: `services/assets/provider_policy.py` (nuovo), con il livello e la priorità effettivi e
     l'ordine di ricerca. È il posto dove arriveranno anche gli elenchi dei fornitori permessi del F05.
   - **`FAProviderInfo`** espone `tier` e `priority` effettivi.
   - **La ricerca non in streaming** ordina i provider prima del fan-out, per (gruppo premium se ce n'è almeno uno,
     priorità, posizione di oggi). Con tutto ai valori di default l'ordine resta identico a oggi (D-X3). Lo streaming
     resta per arrivo, e raggruppa il frontend con `tier`.
   - **Test**: unità pure in processo, con `monkeypatch` dell'ambiente; la lista dei provider dal vivo (`community`,
     100); l'ordine della ricerca con provider finti.
   - **Doc**:
     - `.env.example`, nella sezione «Plugins»;
     - `admin/configuration.en.md`;
     - `asset_plugin_guide.md` (le due dichiarazioni);
     - `search_link_finder.md` (l'ordine);
     - `settings.md` (gli accessori di `plugins.py`).

CP13-2 committed: `25d4c75c7` + journal `efd7b0174`.

2b. ✅ (08:27–08:36) **N48, `env_url` vuole un host** (decisione del coordinatore, «da rivedere»; avvisa A e H).
   > **Note implementazione**:
   > - **Rosso prima**: test-author ha aggiunto 7 casi non validi a `test_config_package.py`:
   >   - `https://` e `http://` da soli;
   >   - host vuoto (`https:///path`);
   >   - porta senza host;
   >   - spazio nell'host;
   >   - spazio o tab nel percorso.
   >   - Sul codice di prima: **7 failed, 733 passed**, esattamente quelli.
   > - Anche 4 controlli validi: IPv4 con porta, IPv6, query, maiuscole conservate.
   > - **La cura in `env_url`**:
   >   - lo spazio si controlla sul valore grezzo, perché `urlsplit` toglie tab e a capo prima di analizzare;
   >   - si chiede `urlsplit(value).hostname`, e non `netloc`, che per `https://:443` vale `:443`;
   >   - un `ValueError` di `urlsplit`, come una parentesi IPv6 non chiusa, diventa lo stesso errore che nomina la
   >     variabile;
   >   - il valore restituito resta quello scritto, maiuscole comprese.
   > - Messaggio: «expected an http:// or https:// address with a host name». I test di A non leggono il testo.
   > - Doc: il punto su `env_url` in `developer/architecture/settings.md`. Tolta dalla docstring del test la nota «Red
   >   until N48».
   > - **Prove**:
   >   - `services config-package` → **740 passed**;
   >   - `services registration` → 147;
   >   - `services email-links` → 74;
   >   - ruff e black puliti; `git diff --check` pulito.

N48 committed: `7d80a1098` + journal `c6d29c969`.

**STOP del developer** (08:46–10:32): tutto fermo, nessun controllo in corso; il test-author di F21 non aveva ancora
toccato file. Durante lo STOP:
- **risposto ad A** su `env_url` senza lanciare niente: vuota o fatta di spazi conta come non impostata (stessa regola di
  `_blank_to_none`); `registration` 147, `config-package` 740 ed `email-links` 74 erano già verdi sul codice di N48;
- **ricevuta da H, via coordinatore, X-R22** (ordine per reinserire un segreto illeggibile), aperta nel backlog alla
  ripresa.

**Ripresa (10:32)**:
- il developer non capisce il senso di «Prezzo manuale / import» (P20), perché gli asset manuali si creano già: **quella
  azione non si costruisce** finché non risponde. Il resto di F21 va avanti;
- T è entrato in `SyncModalBase`, `PageSyncModal`, `SyncResultRow`, nell'AI Export e nel data editor: le mie
  prenotazioni sono sciolte (C-66 parte dal file finale);
- il test-author di prima non esisteva più dopo la pausa: ne ho lanciato uno nuovo con lo stesso incarico.

3. ⏳ **F21 backend** (08:27–08:46, poi dalle 10:32).
   > **Note implementazione**:
   > - `schemas/provider.py`: `FAProviderTier` (`premium` | `community`), `DEFAULT_SEARCH_PRIORITY = 100`, e in
   >   `FAProviderInfo` i campi `tier` e `priority` (`ge=0`), con default che lasciano il contratto di oggi.
   > - `services/assets/base.py`: `tier: ClassVar` e `search_priority: ClassVar` sulla base dei provider, controllati
   >   alla definizione della classe (`_validate_search_declarations`, chiamato da `__init_subclass__`). Una stringa
   >   valida diventa l'enum; un valore sbagliato ferma l'import con un `TypeError` che nomina la classe.
   > - `config/plugins.py` (mio): `asset_providers_premium()` e `asset_providers_order()`, liste di codici separate da
   >   virgole, ripulite, minuscole, senza doppioni; vuota, fatta di spazi o di sole virgole conta come non impostata.
   > - `services/assets/provider_policy.py` (nuovo): il punto unico. `provider_tier`, `provider_priority` e
   >   `search_order`; le variabili si leggono a ogni chiamata; un codice sconosciuto si ignora e si registra una volta.
   > - `search.py`: la ricerca non in streaming ordina i provider prima del fan-out. Lo streaming resta per arrivo.
   > - `GET /assets/provider`: `tier` e `priority` effettivi.
   > - **Verifica in processo**: con tutto ai default l'ordine dei 6 provider registrati è identico a oggi, tutti
   >   `community` a 100 (D-X3).
   > - **Doc**:
   >   - `.env.example`, nella sezione «Plugins»;
   >   - `admin/configuration.en.md`, una sezione «The Order of the Price Providers in the Search» prima della ricerca
   >     web, con i codici dei provider distribuiti (verificati sul codice, perché nessuna pagina li mostra);
   >   - `asset_plugin_guide.md`, le due righe nella tabella e la sezione «Search Order»;
   >   - `developer/architecture/settings.md`, le due variabili e i due accessori di `plugins.py`.
   > - **Prove finora**:
   >   - `api sync`; `front check` → 0/0, dopo la correzione qui sotto;
   >   - `config-env-example` → 38; `config-package` → 740;
   >   - ruff e black puliti.
   >
   > **⚠️ Fuori pista**: il primo `front check` è uscito con un errore **nel client generato**,
   > `tier: FAProviderTier.describe(` «not callable».
   > - **La causa**: il generatore mette la docstring di più righe di un enum in un template literal JavaScript, senza
   >   proteggere i backtick. I doppi backtick di stile RST della docstring (``AssetSourceProvider.tier``) chiudevano il
   >   literal.
   > - **La cura**: niente backtick nella docstring di `FAProviderTier`, con una riga che spiega perché.
   > - Le descrizioni di una riga (`Field(description=…)`) vanno fra apici e non hanno il problema: riguarda solo le
   >   docstring di più righe dei modelli e degli enum usati come tipo di un campo. `front check` lo vede, quindi il
   >   cancello esistente basta; è una lezione per il wiki.

> **⚠️ Fuori pista (10:34)**: la macchina è stata riavviata durante lo STOP (`uptime` 31 minuti) e `/tmp` è stato
> svuotato:
> - è sparita la cartella dati della corsia, `/tmp/librefolio-r13-x`: il runner la ricrea al primo test backend;
> - sono spariti i log delle prove precedenti, già trascritti in questo piano;
> - sono spariti lo script dei controlli e quelli degli innesti del FE5c, che non servono più (pezzi 3–8 entrati).
>   Il wrapper `/tmp/libreFolio_x_fe5c_check.sh` è stato ricreato uguale.
>
> **`core-unit` rilanciato a carico basso (10:34, carico 19)**, come chiesto prima delle E2E del FE5c: **180 file,
> 6458/6458**, `fxRoutesStore.test.ts` compreso. Conferma il triage di X-R21: il rosso delle 07:45 era il tempo sotto
> carico, non un difetto.

**Decisione sul pezzo 9 (coordinatore, 10:45)**: **9a + 9b**.
- 9a: le azioni della barra (`actions` di `PageToolbar`) in `AssetDetailToolbarActions.svelte`;
- 9b: il polling (con le righe di Z spostate così come sono) e la testa dal vivo del grafico in
  `assetDetailLive.svelte.ts`;
- `loadChartData` e il caricamento dei confronti restano nella pagina: **X-R23** nel backlog, dopo la 1.3.

**Handoff intermedio del CP13-3 (10:48)**, chiesto dal coordinatore per aggiornare la base con Z7c-1 (`69c95454b`):
- consegnati il codice, la doc e il journal, con le prove leggere verdi;
- i test di F21 (test-author) e la riparazione di X-R21 (test-author) **non sono ancora scritti**: i due test-author sono
  fermi («HOLD») fino a dopo il merge, perché i file che toccheranno possono cambiare. Arrivano in commit separati.

Merge of `dev_release2` `69c95454b` (Z7c-1) committed: `950b94667`. Conflicts resolved by me: `themeRoles.baseline.tsv`
(`--resolve`, colour `--check` clean) and `charts.md` (my sentence on `parseAssetPriceQueryWithSignalIsolation()`, dev's
paragraph on the rolling return in the catalog; dropped the stale `catalog_visible = False`). Combined revision:
`api sync`, `front check` 0/0, `core-unit` 184 files 6630/6630.

**Nuove regole del coordinatore (10:55)**:
- **Aree dei colori**: sette workstream lavorano sulle classi. Prima di scrivere in un `.svelte` delle loro aree va
  chiesto al coordinatore; `assets/detail/**` e `assets/[id]` restano miei fino all'ingresso del FE5c.
- **`/tmp` si svuota al riavvio**: patch, script e log che servono di nuovo vanno nella cartella di sessione. Il
  wrapper dei controlli ora è `files/checks/check.sh`, con i log in `files/checks/logs/`.

#### X-R21 · la riparazione di `fxRoutesStore.test.ts` ✅ scritta e provata (11:02; commit dopo quelli di F21)

> **Note implementazione** (test-author):
> - un solo meccanismo di mock: via `vi.hoisted` e il `vi.mock` in cima; un `vi.fn()` nuovo per caso, installato con
>   `vi.doMock('$lib/api', …)`, così una lettura rimasta in sospeso chiama il mock del suo caso e non viene contata nel
>   successivo;
> - il grafo dello store si scalda una volta in `beforeAll` (60 s, come `GapFixStep` e `ParseDetailModal`):
>   `resetModules` butta i moduli valutati ma tiene il codice trasformato;
> - `afterEach` aspetta `vi.dynamicImportSettled()`, prima volta nel repo: un caso finisce solo quando i suoi import
>   sono finiti.
> - **Prova**: il file da solo → **5/5**; il primo caso passa da 437 ms a **57 ms**.
> - Il percorso della cascata sotto carico non si può osservare a carico basso: è argomentato dal sorgente di Vitest.
> - **⚠️ Fuori pista**: il test-author ha lanciato una volta `vitest --version` (nessun test). Innocuo, annotato.

#### FE5c-9a · le azioni della barra ✅ scritto e controllato (10:53–11:00; commit dopo F21 e X-R21)

> **Note implementazione**:
> - `lib/components/assets/detail/AssetDetailToolbarActions.svelte`, generato da `files/checks/fe5c_piece9a.py` (cartella
>   di sessione): il contenuto dello snippet `actions` di `PageToolbar` copiato alla lettera, con le proprietà al posto
>   dello stato della pagina. Contiene AI export, Modifica, Sincronizza (barrata con il motivo quando è bloccata) e
>   Aggiorna.
> - Lo snippet resta nella pagina come una sola chiamata.
> - I callback senza argomenti (`onedit`, `onrefresh`) si chiamano da una closure, così non ricevono l'evento.
>   `onsync={handleSync}` riceve l'evento come prima.
> - L'`onerror` dell'AI export è rimasto quello di prima, dentro il componente (`toasts` + `getAiExportErrorMessage`).
> - Dalla pagina escono gli import inutili: `RotateCw`, `Tooltip`, `AiExportMenu` e `getAiExportErrorMessage`.
> - La pagina passa da 2972 a 2937 righe.
> - **`--split`**: la pagina scende da 155 a 123, il componente ne prende 32. La somma resta 155.
> - **Prove**: `front check` → 0/0; Prettier → nessuna modifica.

#### FE5c-9b · la parte dal vivo ⏳ (modulo scritto alle 11:05; l'innesto aspetta il commit del 9a)

> **Note implementazione**:
> - `lib/components/assets/detail/assetDetailLive.svelte.ts`, generato da `files/checks/fe5c_piece9b_module.py` dai
>   blocchi della pagina, con sostituzioni esplicite, ognuna contata.
>   - La classe `AssetDetailLive` ha lo stato dal vivo (`currentPrice`, `conversionFailed`, `updatesState`,
>     `direction`, `flashToken`; privati il valore precedente e il timer del lampeggio).
>   - Il suo costruttore registra l'`$effect` del polling.
>   - `#pollLivePriceOnce` sono le righe di Z7c-1, così come sono, e con loro `#applyLiveSummary` e
>     `#applyLiveChartHead`, con la spiegazione I-bis #24.
>   - Legge la pagina da `AssetDetailLiveInput`, getter più il setter di `chartData` e `loadChartData`: le stesse
>     letture di prima.
> - L'innesto (`files/checks/fe5c_piece9b_splice.py`, prova a secco 2937 → 2757):
>   - l'istanza si crea **nel punto del vecchio `$effect`**, così il polling resta nell'ordine degli effetti della
>     pagina;
>   - `lastPrice` legge `live.currentPrice`; `reloadPage()` chiama `live.resetPrice()`;
>   - il template legge `live.updatesState`, `live.conversionFailed`, `live.direction` e `live.flashToken`;
>   - escono gli import del polling.

**P20 deciso dal developer (11:12, via coordinatore)**:
- **«Prezzo manuale / import» non si fa**: dalla creazione si salva l'asset senza fonte, e l'utente aggiunge i prezzi.
- **«Segnalacelo» resta**, e deve mandare una email con tutti i dati: cosa ha cercato, quali provider ha interrogato,
  valuta ed exchange se c'erano. Il supporto risponde spiegando come usare altri provider.

**Mia proposta** (11:15, in attesa dell'ok; serve anche quello di H per la variabile):
- **Il canale**: niente invio dal server.
  - Se il supporto è un indirizzo email: `mailto:` con oggetto e corpo precompilati.
  - Se è una pagina http(s): si apre la pagina e il rapporto va negli appunti.
  - Se non è impostato: una issue di GitHub precompilata, pubblica, che l'utente rivede prima di inviarla.
- **I dati**:
  - il testo cercato;
  - i provider interrogati con il loro esito, solo i codici;
  - valuta, tipo e identificativo del modulo, se c'erano;
  - versione, profilo e lingua.
  - **Mai**: utente, email, indirizzo dell'istanza, dati del portafoglio.
- **La configurazione**: una sola variabile. `LIBREFOLIO_SUPPORT_URL` accetta anche `mailto:<indirizzo>`, con una variante
  della regola; `env_url` resta solo http(s) per `PUBLIC_URL` e `BILLING_URL`.

**P20 approvato (coordinatore, 11:20)**:
- la segnalazione parte dal client dell'utente: `mailto:`, oppure la pagina con il rapporto negli appunti, oppure la
  issue di GitHub se non c'è niente di impostato;
- i dati proposti, senza dati personali;
- dopo ogni ricerca.
- `LIBREFOLIO_SUPPORT_URL` con `mailto:` aspetta l'ok di H; intanto il frontend presuppone la variabile unica.

**Il frontend dopo i lotti di AF** (decisione del developer: prima la migrazione dei colori, poi le funzioni nuove). AF
passa per primo sui file dei miei lotti futuri:
- lotto 1: `FxSyncModal`, per C-66;
- lotto 4: `AssetModal`, per O-20;
- lotto 5: `AssetSearchAutocomplete` e `ProviderAssignmentSection`, per F21 e C-90;
- lotto 6: `AssetDataEditorSection`, per O-8;
- lotto 8: `assets/+page.svelte`, per O-20.

Il frontend del CP13 e O-8, O-20 e C-66 partono quando il coordinatore lo dice. Restano ora: i test di F21, la correzione
dell'ordine con i duplicati, X-R21 e il pezzo 9; la pagina di dettaglio resta mia. I colori spostano su `data-lifecycle`
due miei test (`AssetTable.test.ts`, `e2e/assets/asset-list.spec.ts`), che non avevo aperti.

3b. ✅ (11:17–11:44) **Correzione di F21: la ricerca tiene i provider ripetuti** (trovata dal test-author).
   > **Note implementazione**:
   > - **Il difetto**: `search()` costruiva un dizionario codice → posizione e ordinava per codice. Con un codice ripetuto
   >   (`providers=a,b,a`) e nessuna sovrascrittura la ricerca diventava `[b, a, a]` invece di `[a, b, a]`, contro D-X3.
   >   `search_order` era giusto; il difetto era solo in `search.py`.
   > - **La cura**: `provider_policy.search_rank(code)`, cioè (0 premium | 1 community, priorità effettiva).
   >   `search_order` diventa `sorted(codes, key=search_rank)`, e `search.py` fa `valid_providers.sort(key=…search_rank)`.
   >   Un ordinamento stabile tiene i pari, i ripetuti compresi, nell'ordine dato.
   > - **Rosso prima**: `services provider-policy` sul codice di prima → **3 failed, 45 passed**, esattamente i 3
   >   previsti. Due cadono per `AttributeError` su `search_rank`; il terzo è la ricerca da capo a fondo con un provider
   >   ripetuto, che dava `standin_beta` prima di `standin_alpha`.
   > - Dopo la cura: **48/48**.

3c. ✅ **I test di F21** (test-author; 48 casi, 30 funzioni, nessun DB né server):
   > - `backend/test_scripts/test_services/test_provider_policy.py` (nuovo), registrato come `services provider-policy`,
   >   `isolation="pure"`, accanto a `provider-contracts`;
   > - una riga in `test_assets_crud.py::test_list_asset_providers`: ogni provider dal vivo è `community` a 100.
   > - **Coprono**:
   >   - gli accessori;
   >   - il livello e la priorità, dichiarati e sovrascritti, con un codice sconosciuto registrato una volta;
   >   - una variabile PREMIUM che elenca solo codici sconosciuti non rende premium nessuno;
   >   - `search_order` e `search_rank`, con il premium prima di ORDER e i ripetuti;
   >   - il controllo delle dichiarazioni (`"gold"`, `None`, `-1`, `True`, `"1"`, `1.0`);
   >   - la ricerca da capo a fondo, con solo `core.configured_provider` sostituito.
   > - **Due scostamenti del test-author, accettati**: `provider_policy.search_rank` letto dentro il test invece di un
   >   `getattr` (la regola B009 di ruff riscrive `getattr` con una stringa fissa), e `dict.fromkeys` (C420).
   > - **Prove**:
   >   - `services provider-policy` 48;
   >   - `api assets-crud` **35**, con l'asserzione dal vivo;
   >   - **le suite che chiamano la ricerca, verdi**: `services asset-source` 61, `rate-limit-results` 23,
   >     `plugin-settings-runtime` 120, `web-link-finder` 29;
   >   - ruff e black puliti sui 5 file.
   > - **Trovati in lettura, non corretti** (precedenti a F21): `mockprov` nella ricerca senza `providers` e una docstring
   >   vecchia, ora **X-R24**.

**Prove del lotto (F21 correzione e test, X-R21, 9a)**, 11:36–11:54, ognuna con `nice` dopo il controllo del carico. Il
carico è salito più volte a ~150 per gli slot pesanti delle altre corsie, e il wrapper ha aspettato.
- le suite della ricerca, come detto in 3c;
- `front check` → **0/0**, compresi il 9a e il modulo del 9b, non ancora innestato;
- `front-utility core-unit` → **184 file, 6630/6630**, con X-R21 e i cancelli dei colori del `--split` del 9a;
- `check-orphans` → tutti raggiungibili (488 test frontend, 356 backend, 134 E2E);
- Prettier pulito; `git diff --check` pulito; porta 6183 libera.

**Arrivati nel frattempo**:
- **Icone in Impostazioni › Plugin** (richiesta del developer, proposta approvata dal coordinatore alle 11:52), un lotto
  suo **dopo il 9b**:
  - `icon_url` in `PluginSettingsPluginRead`, letto dall'istanza del plugin con una tabella per famiglia (`asset` →
    `get_icon`, `fx` → `icon`);
  - `FAMILY_ICONS` (`ChartColumn`, `Coins`) accanto a `FAMILY_TITLE_KEYS`;
  - il ripiego `Puzzle` se l'icona manca o non si carica;
  - tre `data-testid`;
  - test di servizio e di componente.
  - Cambia lo scatto `settings/plugins` della galleria: il coordinatore avvisa i colori e G.
- **Skill `design-system`** (D-T29, `6e569084a`): da ora il markup nuovo la segue dall'inizio, solo ruoli `-lf-`.
  Arriva col prossimo aggiornamento della base; prima del lotto delle icone la leggo dal checkout principale, in sola
  lettura, come indicato dal coordinatore.
- **X-R25** (da J): il test della ricerca justETF in `all-backend` va in timeout; aperta nel backlog.

Commits of the batch: `1713d97bf` (F21 fix), `24f51cde3` (F21 tests), `914360874` (X-R21), `fedad56cb` (9a), `039ccc9d5`
(journal).

#### FE5c-9b · la parte dal vivo, innestata ✅ (12:02–12:45)

> **Note implementazione**:
> - `files/checks/fe5c_piece9b_splice.py --apply`: la pagina passa da **2937 a 2757 righe**. Prettier: nessuna modifica.
> - L'istanza `live = new AssetDetailLive({…getter…})` sta nel punto del vecchio `$effect` del polling, quindi
>   l'effetto resta nello stesso ordine fra gli effetti della pagina.
> - Il `$derived` `lastPrice` legge `live.currentPrice` in modo pigro, solo dopo l'inizializzazione: nessun problema
>   d'ordine.
> - Escono dalla pagina gli import del polling (`livePriceService`, `activePolling`, `cadence`).
> - **Prove**:
>   - `front check` → **0/0**: l'oggetto di getter soddisfa `AssetDetailLiveInput`;
>   - cancelli dei colori `--check` puliti, nessuna classe spostata, quindi niente `--split`.
> - **Test**: un test-author scrive `assetDetailLive.svelte.test.ts`, con il polling e le API sostituiti, lo stato
>   fermo, la conversione, le risposte vecchie, la testa del grafico e `resetPrice()`.
> - Le E2E che coprono il dal vivo, `asset-live-pause.spec.ts` e `asset-detail.spec.ts`, vanno nello slot del FE5c.

#### Icone in Impostazioni › Plugin ⏳ (backend scritto alle 12:07; il frontend dopo l'handoff del 9b, perché serve `api sync`)

> **Note implementazione**:
> - `PluginSettingsPluginRead.icon_url` (descrizione su una riga, senza backtick: va nel client generato);
> - `FAMILY_ICON_ATTRIBUTES = {"asset": "get_icon", "fx": "icon"}` accanto a `FAMILY_REGISTRIES`;
> - `_plugin_identity()` sostituisce `_plugin_name()`: nome e icona dalla stessa istanza; un'icona illeggibile o vuota
>   diventa `None`.
> - **Prova in processo**: `borsa_italiana` e `justetf` hanno la loro icona, `mockprov` (solo test) nessuna.
> - Un test-author scrive i test backend.

**FE5c-9b, chiusura (12:45)**:
> - **Il test unitario** `assetDetailLive.svelte.test.ts` (test-author), 63 casi:
>   - jsdom, con gli helper `$test/runes.svelte`;
>   - il polling e le API sostituiti, i servizi puri veri;
>   - l'effetto legge esattamente i 5 ingressi;
>   - lo stato fermo, la conversione, le risposte vecchie, la pausa del 429, la testa del grafico e `resetPrice()`.
>   - È registrato in `core-unit`, come gli altri test di store a rune senza componente.
> - Aggiornata la doc `developer/frontend/components/features/live-ticker.md` al modulo: stesso comportamento, nomi
>   nuovi.
> - **Prove**:
>   - il file da solo → **63/63** al primo giro;
>   - `core-unit` → **185 file, 6693/6693**;
>   - `mkdocs build` stretto ok;
>   - `front check` 0/0 e cancelli dei colori puliti (12:05).
> - **Trovati dal test unitario** (codice di prima, spostato così com'è, non toccato nel taglio); il coordinatore ha
>   approvato la correzione in un commit a parte, subito dopo il 9b, con i rossi prima (12:37):
>   1. su un grafico convertito, ogni poll ricarica tutto il grafico, perché la guardia confronta il `close` convertito
>      con il prezzo nativo: una 🐛 nel CHANGELOG;
>   2. il lampeggio può restare acceso quando l'effetto riparte, perché la pulizia non rimette `direction` a
>      `'neutral'`; con il movimento ridotto il prezzo resta colorato;
>   3. un commento di `app.css` (ridotto movimento) che cita `+page.svelte`. `app.css` è dei colori: aspetto il loro ok.
> - **⚠️ Fuori pista**: il controllo di `api plugin-settings` del lotto icone (12:28) è rimasto in attesa del carico, a
>   ~160. L'ho fermato prima che partisse, senza server né porta da pulire, per dare la precedenza alle prove del 9b. Lo
>   rilancio con il lotto icone.

### Quindicesimo aggiornamento di base: `dev_release2` (`0f3b9e3db`, lotti di H, W-B30, colori) nel ramo X ✅ (2026-10-16) — merge `42d25081d`

> - **Conflitto**: solo `backend/app/config/__init__.py`, sugli import (`cast` di H, `urlsplit` mio). Tenuti tutti e
>   due; messo in stage solo quel file.
> - **Prove combinate**, carico sotto 50:
>   - `api sync`; `front check` 0/0; `core-unit` 185 file, 6699/6699;
>   - `config-package` 739, `config-env-example` 38, `profile-defaults` 52;
>   - `plugin-settings-service` 96, `plugin-settings-runtime` 120, `api plugin-settings` 14.
>   - `config-package` aveva 740 casi alle 08:34. Il file di test non è cambiato nel merge, quindi la differenza
>     dovrebbe venire da una parametrizzazione derivata dal prodotto; 0 fallimenti. I log di confronto erano in `/tmp`
>     e il riavvio li ha cancellati.
> - **⚠️ Fuori pista (ambiente)**: il primo giro di `api plugin-settings` è finito 14/14 rossi, tutti sulla stessa
>   precondizione: «db populate non è girato su questa corsia».
>   - Causa: il riavvio delle 10:03 ha cancellato `/tmp/librefolio-r13-x`, e le unità `services` ricreano il DB vuoto.
>   - Rimedio: `test db --force populate` sulla mia data dir (7096 record); al secondo giro 14/14.
>   - Regola: dopo un giro di unità `services`, `populate` prima delle unità API.

### Sedicesimo aggiornamento di base: `dev_release2` (`1248b7908`, AF A+B+C dei colori e IM) nel ramo X ✅ (2026-10-16) — merge `668d27837`

> - **Conflitto**: solo `frontend/src/themeRoles.baseline.tsv`, fra le righe `--split` del 9a e i numeri di AF.
>   - Risolto **solo con lo strumento**: `node frontend/scripts/theme/theme-roles.mjs --resolve`, a tre vie dagli
>     stadi dell'indice. Nessun marcatore rimasto, `--check` pulito.
>   - Il risultato tiene i numeri più stretti di AF, le mie righe `detail/**`, la pagina a 123 e le cinque righe
>     `~split`.
>   - In stage **solo** quel file; il commit del merge è del coordinatore.
> - **Prove leggere sulla revisione combinata**, tutte verdi:
>   - `api sync`;
>   - `front check` 0/0;
>   - `core-unit` 185 file, 6699/6699 (13:28, con i cancelli dei colori).
> - **⏸️ PAUSA del developer (13:29)**: lo slot E2E 1 non è partito. Il copione è pronto in
>   `files/checks/fe5c_e2e_slot.sh` della cartella di sessione:
>   - `mkdocs build`;
>   - poi, uno alla volta, `front-asset` `asset-detail`, `live-pause`, `asset-mobile-layout`, `asset-data-editor`,
>     `asset-event-delete`;
>   - infine `front-utility onboarding-guides`, sulla porta 6183.
> - **Fuori dal merge, non in stage**: il backend del lotto icone, 4 file:
>   - `schemas/plugin_settings.py`, `services/plugin_settings/service.py`;
>   - i due file di test, `test_services/…` e `test_api/…`.
> - **Prossimo passo, al via**:
>   1. il coordinatore crea il commit del merge;
>   2. lo slot E2E del FE5c sulla revisione con AF;
>   3. le correzioni dal vivo 1 e 2, con i rossi prima;
>   4. il frontend del lotto icone.
> - **Ripresa (14:14)**:
>   - il coordinatore ha creato il commit del merge, `668d27837` (genitori `42d25081d` + `1248b7908`);
>   - lo slot E2E 1 è mio dalle 14:15, con cut-off alle 15:00;
>   - controllato prima di partire: HEAD giusto e sporchi solo i 4 file del lotto icone e questo piano.
> - **Ricevuti nella pausa**, da mettere nei lotti giusti (dettagli nella cartella di sessione):
>   - **la decisione di H su `LIBREFOLIO_SUPPORT_URL` con `mailto:`**, per il lotto CP13 che legge la variabile:
>     - una sola variabile, `mailto:` più un indirizzo, controllato con `EmailStr` senza DNS;
>     - rifiutati `?`, `#`, `%`, `,`, `;`, spazi, a capo e `mailto:` vuoto;
>     - `env_url` resta solo http(s);
>     - un valore illeggibile vale «non impostato»;
>     - il frontend ricontrolla lo schema, mai `javascript:`.
>     - Verificato in sola lettura che `EmailStr` da solo **accetta** `#`, `%` e `?` nella parte locale (ATEXT di
>       `email-validator`), toglie gli spazi ai bordi e accetta la forma `Nome<a@b.c>`. Quindi serve un controllo
>       esplicito dei caratteri prima di `EmailStr`.
>   - **Una regola dei colori** (T `a317392d4`): un campo nativo con classi `-lf-` nomina anche `text-lf-primary` e
>     `placeholder:text-lf-placeholder`. `INPUT_CLASS` delle impostazioni dei plugin la rispetta già.
>   - **L'ok dei colori al commento di `app.css`**, solo quella riga, nel commit delle correzioni dal vivo.
>   - **Le note di Z per lo stesso commit**:
>     - in `live-ticker.md`, i paragrafi «Price flash» e «Chart head»;
>     - i due difetti sono nella v1.2.1, quindi due righe 🐛 nel CHANGELOG;
>     - i test del lampeggio in `asset-detail.spec.ts` sono miei.
> - **⚠️ Fuori pista (metodo)**: lo slot gira sull'albero di lavoro, e il runner ricostruisce il frontend se un file
>   qualsiasi di `frontend/src` (test compresi) o `CHANGELOG*.md` è più nuovo della build (`cli_base.py`,
>   `check_frontend_needs_build`).
>   - Durante lo slot quindi non tocco né il frontend, né la documentazione, né il CHANGELOG: preparo le correzioni
>     nella cartella di sessione.
>   - Così ogni spec gira sulla stessa build di `668d27837`, e non se ne ricostruisce una a metà slot.

#### FE5c · lo slot E2E 1 ✅ (2026-10-16, 14:15–14:39, cut-off 15:00)

> - **Revisione**: `668d27837`, più il backend del lotto icone non in stage, che aggiunge un campo alle impostazioni
>   dei plugin e non tocca queste pagine.
> - **Esito, uno spec alla volta**, con `files/checks/fe5c_e2e_slot.sh`, porta 6183, data dir della corsia:
>
>   | Spec | Esito | Durata |
>   |---|---|---|
>   | `front-asset asset-detail` | 34/34 | 5,1 min |
>   | `front-asset live-pause` | 8/8 | 34 s |
>   | `front-asset asset-mobile-layout` | 21/21 | 58 s |
>   | `front-asset asset-data-editor` | 26/26 | 2,0 min |
>   | `front-asset asset-event-delete` | 4/4 | 17 s |
>   | `front-utility onboarding-guides` | 24/24 | 4,0 min |
>
>   In tutto **117/117**, 0 ritentativi. La build del frontend è stata rifatta una sola volta, al primo spec, dopo il
>   merge. Alla fine la porta 6183 era libera.
> - **⚠️ Fuori pista (base)**: il `mkdocs build` stretto prima dello slot è fallito su un'àncora di dev.
>   - Il link è `developer/backend/transactions/wac.md:592` → `split_promote.md#transfer-giving-leg`, arrivato con
>     `54880598b`: il cherry-pick W-B30 di un link a un'àncora che arriva solo con 47.
>   - Segnalato al coordinatore, che l'ha corretto su dev in `ed500643f`; mi arriva al prossimo aggiornamento di base.
>   - Effetto sullo slot: nessuno. `auto_build_mkdocs()` non controlla l'esito, e il sito interrotto aveva solo en e
>     it; nessuno spec ha chiesto una pagina in fr o es.
> - **Galleria (G, slot 1 dopo di me)**: ho proposto la coppia base **`1248b7908`** (dev con AF, senza FE5c) → testa
>   **`668d27837`**.
>   - Fra le due, `frontend/src` differisce solo per il FE5c (29 file).
>   - `039ccc9d5`, proposta come base, ha già i pezzi 2–9a e non ha AF: 78 file diversi.
>   - Aspetto la conferma del coordinatore.

#### Correzioni dal vivo 1 e 2, più il commento di `app.css` ✅ scritte e provate (2026-10-16, 14:40–14:57)

> - **Rossi prima** (test-author, solo `assetDetailLive.svelte.test.ts`): **4 rossi**, ciascuno sulla sua asserzione,
>   e 66 verdi.
>   1. Grafico convertito, prezzo nativo fermo: punto `{close: 92, original_close: 100}`, quotazione 100. Ricaricava:
>      `loadChartData` chiamato una volta.
>   2. Grafico convertito, prezzo nativo sceso proprio al `close` convertito (quotazione 92). Non ricaricava, e il
>      punto restava vecchio: è la seconda faccia del difetto 1, trovata dal test-author.
>   3. e 4. Il lampeggio, quando l'effetto riparte (cambio di valuta, oppure cambio d'asset diretto), restava `'up'`.
>   - **Guardie verdi**:
>     - un punto senza `original_close`, o con `null` (nessun cambio quel giorno);
>     - un prezzo nativo salito a 101: un'invalidazione, poi un `loadChartData(true)`.
>   - **Docblock del file**: tolto «Not pinned here, on purpose…»; il contratto ora è scritto nei punti «The summary»
>     e «The chart head».
> - **Correzioni** in `assetDetailLive.svelte.ts`:
>   1. La guardia confronta `Number(original_close ?? close)`. Il backend mette `original_close` solo quando converte
>      (`price_query.py` ~474–522), quindi il grafico non convertito resta identico.
>   2. La pulizia dell'effetto mette anche `direction = 'neutral'`. L'effetto non legge `direction`, quindi non
>      riparte per questo.
>   - Aggiornato anche il commento di testa del blocco.
> - **`app.css`**: solo la riga del commento, con l'ok dei colori: `+page.svelte` → `assetDetailLive.svelte.ts`.
> - **`live-ticker.md`**, con le note di Z:
>   - «Price flash»: la pulizia spegne anche il lampeggio;
>   - «Chart head»: il confronto avviene sul close nativo, e il grafico si ricarica solo se è cambiato;
>   - la riga del test unitario nella tabella «How it is tested», che mancava dal 9b.
> - **CHANGELOG**, `[Unreleased]` › 🐛 Fixed: due righe, il grafico convertito che si ricaricava ogni 30 s e il
>   lampeggio che restava acceso. Entrambi i difetti erano già nella v1.2.1.
> - **Prove**:
>   - il file da solo → **70/70**;
>   - `front check` → 0/0;
>   - `core-unit` → **185 file, 6706/6706** (+7);
>   - prettier e `git diff --check` puliti;
>   - `mkdocs build` stretto: c'è solo l'avviso noto di dev, corretto in `ed500643f` ma non ancora nella mia base, e
>     nessun avviso viene dalle mie modifiche.
> - **E2E non rifatti dopo le correzioni**: lo slot era già finito. Nessun E2E passa dai rami cambiati:
>   - i 4 test di «Live price direction flash» non fanno ripartire l'effetto a metà lampeggio;
>   - gli altri `/current` di `asset-detail.spec.ts` (righe 85 e 2330) rispondono senza prezzo.
> - **Note del test-author che non ho preso**:
>   - X-R26 va nel backlog: con un cambio d'asset diretto il primo tick si confronta col prezzo dell'asset di prima.
>     La pagina non ci arriva.
>   - Un commento esistente («The converted chart reloads on every landing poll», nel caso della conversione
>     arrivata tardi) resta vero per quel caso, il cui grafico non ha il punto di oggi.
> - **Committate** dal coordinatore: `2a038b362` (fix) e `cecaa144b` (diario).

#### Icone in Impostazioni › Plugin — frontend ✅ (2026-10-16, 15:03–16:23)

> - **Partenza**: HEAD `cecaa144b`, con il backend del lotto (4 file) ancora sporco dalle 12:07.
> - **Frontend**, con le sole classi di ruolo (skill design-system):
>   - `pluginSettingsApi.ts`: `PluginSettingsEntry.icon_url: string | null`, obbligatorio come ogni campo;
>     `entryOf` lo legge con `textOrNull`.
>   - `pluginSettingsForm.ts`: `FAMILY_ICONS` accanto a `FAMILY_TITLE_KEYS`, con `asset` → `ChartColumn` e `fx` →
>     `Coins`, le icone della home della documentazione. Una famiglia nuova aggiunge una riga.
>   - `PluginSettingsTab.svelte`: il titolo `<h3>` di ogni famiglia comincia con la sua icona, `aria-hidden`,
>     `data-testid="plugin-settings-family-icon"`, senza classi di colore: eredita il ruolo del titolo.
>   - `PluginSettingsForm.svelte`: il titolo `<h4>` comincia con
>     `<img alt="" referrerpolicy="no-referrer" data-testid="plugin-settings-plugin-icon">`; senza icona, o quando
>     l'immagine non si carica, con `Puzzle` (`text-lf-muted`, `aria-hidden`,
>     `data-testid="plugin-settings-plugin-icon-fallback"`).
>     - Un'immagine fallita registra il suo indirizzo (`failedIconUrl`): il ripiego resta finché il plugin non
>       pubblica un'altra icona.
>     - Con `alt=""` il nome accessibile del titolo, e quindi quello della sezione (`aria-labelledby`), resta il nome
>       del plugin.
> - **Documentazione**:
>   - user `settings/plugins.en.md`: le icone delle famiglie e quella del plugin, con il pezzo di puzzle quando manca;
>   - developer `patterns/plugin_settings.md`: `icon_url` nella tabella dell'API (con la sua fonte, la property
>     `get_icon` dei prezzi e `icon` dei cambi), nella mappa dei sorgenti, nell'interfaccia (`FAMILY_ICONS`, il
>     ripiego) e nei test del backend.
> - **CHANGELOG**: una frase in coda alla riga ✨ «Settings › Plugins» di `[Unreleased]`. La scheda è nuova in
>   questa versione, quindi nessuna riga a parte.
> - **Test**: il test-author lavora sui 5 file di test della cartella: fabbriche con `icon_url: null`, `entryOf`,
>   `FAMILY_ICONS`, l'icona per famiglia, l'icona del plugin, il ripiego, l'errore di caricamento.
>   - **Esito**: i 5 file passano da 284 a **304 casi**, tutti verdi; prettier pulito. Prima delle fabbriche
>     aggiornate, 11 casi rossi (i `toStrictEqual` di `entryOf` senza `icon_url`).
>     - `pluginSettingsApi`: da 119 a 128 casi. Ci sono anche un elenco come icona, che diventa `null`, e un'icona che
>       attraversa lo schema generato: un client generato vecchio toglierebbe le icone senza dire niente.
>     - `pluginSettingsForm`: da 116 a 118 casi, con `FAMILY_ICONS` controllata per identità e famiglia per famiglia.
>     - `PluginSettingsTab`: da 6 a 10 casi (PST-07…09). PST-08 e PST-09 confrontano il disegno dell'SVG: non usano né
>       classi né colori, solo il markup.
>     - `PluginSettingsForm.component`: da 34 a 39 casi (PSF-26…30). Fra questi PSF-29: dopo un errore, la stessa URL
>       tiene il ripiego, e una URL nuova riporta l'immagine.
>     - `PluginSettingsModal`: 9 casi, nessuno nuovo; cambiano solo le fabbriche.
>   - **Dal test-author, preso**: con `icon_url` `undefined` (fuori da `entryOf`), `showIcon` disegnava un `<img>`
>     vuoto, che non scatta mai `error`. Ora `showIcon` è `!!entry.icon_url && …`, che copre anche la stringa vuota.
> - **Prove fin qui**:
>   - la cartella, 304/304;
>   - `front check` 0/0. È partito alle 15:35:50 a carico 45 ed è finito alle 15:39:40, quando il carico era 166.
> - **⏸️ STOP del coordinatore (15:45)**: il carico alto faceva cadere il controllo della galleria di G sul FE5c. Ho
>   fermato il copione mentre aspettava di far partire `core-unit`, che quindi non è mai partito.
>   - **Regola nuova**: controlli leggeri solo con carico ≤ **50**, misurato subito prima di partire. Il cancello di
>     `files/checks/check.sh` ora parte da 50.
>   - Restano da fare, al via: `core-unit`, `component-unit` e `mkdocs build`.
> - **Ripresa (16:03)**, sempre con il cancello a 50; prove tutte verdi:
>   - `core-unit` → **185 file, 6717/6717** (+11);
>   - `component-unit` → **158 file, 4078/4078**, compresi `ProviderAssignmentSection`, `AssetSearchAutocomplete` e
>     `AssetModal.providerLifecycle`, che leggono le voci attraverso `entryOf`;
>   - `mkdocs build` stretto: c'è solo l'avviso noto di dev (`wac.md`), corretto in `ed500643f`, che arriva col
>     prossimo merge. Nessun avviso viene dalle due pagine.
>   - ruff, black, prettier e `git diff --check` puliti.
> - **Backend del lotto**: le prove delle 13:1x restano valide (`plugin-settings-service` 96, `plugin-settings-runtime`
>   120, `api plugin-settings` 14), perché il merge 16 non ha toccato `backend/`.
> - **Galleria**: lo scatto `settings/plugins` cambia, con le icone. Il coordinatore lo dice a colori e a G.
> - **Committato**: `aaff7df04` (feat, 16 percorsi) e `5579d1a19` (diario).

### Diciassettesimo aggiornamento di base: `dev_release2` (`17a531b45`) nel ramo X — merge aperto, combinato verde (2026-10-16, 16:27–16:48)

> - **Perché adesso**: G ha dato il verdetto sulla galleria del FE5c, immagini identiche entro il rumore e 0 classi
>   miste. Il FE5c può entrare, insieme a F21, CP13 e alle icone, per avanzamento rapido dopo questo merge. AF dei
>   colori aspetta il FE5c in dev per il suo lotto 9.
> - **Conflitti** (HEAD `5579d1a19`, MERGE_HEAD `17a531b45`, base comune `1248b7908`):
>   - `CHANGELOG.md`: due aggiunte in fondo alla stessa lista 🐛 Fixed. Tenute entrambe: prima quella di dev (W-B36b,
>     le modifiche ai trasferimenti), poi le mie due righe del dal vivo.
>   - `themeRoles.baseline.tsv`: solo `theme-roles.mjs --resolve`; `--check` pulito.
>   - In stage solo quei due file.
> - **Fusi da soli e controllati a occhio**, tutti toccati da entrambe le parti:
>   - `config/__init__.py`: P17 `LIBREFOLIO_CLIENT_IP_HEADER`, indipendente da `env_url`;
>   - `.env.example`, `configuration.en.md` e `hosting_providers.en.md`: una riga ciascuno per
>     `LIBREFOLIO_SUPPORT_URL` e per `LIBREFOLIO_CLIENT_IP_HEADER`;
>   - `app.css`: il blocco di IM e il mio commento, lontani;
>   - `live-ticker.md`: le aggiunte di Z, cioè «Updating prices…» e tre righe nella tabella dei test; i miei
>     paragrafi e la mia riga sono intatti, e la tabella è integra;
>   - i due file del runner si leggono senza errori; il backlog ha la sezione X intatta (X-R26…28) e nessun
>     marcatore.
> - **Prove sulla revisione combinata**, col cancello a ≤ 50:
>   - `api sync`;
>   - `front check` 0/0;
>   - `core-unit` **186 file, 6783/6783**;
>   - `component-unit` **158 file, 4079/4079**;
>   - `mkdocs build` stretto **verde, senza avvisi**: l'avviso di `wac.md` non c'è più su questa base;
>   - `config-package` 741, `config-env-example` 38;
>   - cancello dei colori pulito.

#### X-R27 e X-R28 — le chiavi delle cache degli asset ✅ scritti e provati (aperti il 16/10 alle 15:03, chiusi alle 18:13)

> - **X-R27**, dai colori: `currency_change.py` legge i campi del fornitore da `Asset`, dove non ci sono. Così
>   l'invalidazione delle cache, dopo un cambio di valuta, non avviene mai: l'`AttributeError` è preso e registrato.
> - **X-R28**, trovato misurando X-R27: `price_query.py:764` mette in cache il prezzo corrente senza l'hash dei
>   parametri, mentre `refresh.py` e le invalidazioni lo usano.
> - **Cura proposta**: una funzione unica della chiave in `services/assets/core.py`, usata nei quattro punti, con un
>   rosso per ciascun difetto prima della correzione. Le righe sono nel backlog, sezione X.
> - **Via del coordinatore (16:51)**, dopo l'ingresso del ramo in dev (`a44951cf5`). HEAD `89d276d1e`.
>   - Test-author lanciato per i rossi (16:53), in `utils provider-core-cache` o nei file vicini, col cancello a 50.
>   - Misurando ho trovato una terza divergenza: `refresh.py` tiene `identifier` così com'è (può essere `None`),
>     mentre `provider_management.py` lo scrive `identifier or ""`. La funzione unica sistema anche questa.
>   - Verificato prima di disegnare la cura:
>     - le due vie mettono nella cache del prezzo corrente lo stesso oggetto, il `FACurrentValue` del fornitore, quindi
>       condividere la chiave è sicuro e utile;
>     - c'è un'assegnazione per asset (`uq_asset_provider_asset_id`).
> - **⏸️ HOLD del coordinatore (17:22–~17:45)**: c'è la galleria completa dei colori, con carico 130–170.
>   - Niente prove nuove, solo scrittura e lettura. Ho detto al test-author di non lanciare altri giri.
>   - La cura è pronta in bozza, nella cartella di sessione (`files/xr27-xr28-fix-draft.md`), e si applica solo dopo
>     i rossi.
>   - La documentazione è già aggiornata:
>     - `backend/assets/architecture.md`: la riga di `core.py`, e il punto su `_asset_current_cache`, che
>       descriveva la divergenza come voluta;
>     - `plugin_settings.md`: le cancellazioni passano da `drop_asset_cache_entries()`.
> - **X-R28 è più grave** (17:35): tutti gli investimenti programmati condividono la stessa voce, perché hanno
>   l'identificativo `NULL`. `/current` salva anche i risultati presi dalla cache come prezzo di oggi, e lo scheduler
>   passa dalla stessa via. Sul backlog il peso è salito a «medio».
>   - **Decisione del developer**: correzione del codice più una riga 🐛 nel CHANGELOG, senza riparazione. La
>     sincronizzazione notturna riscrive gli ultimi 14 giorni.
>   - **Chiave**: il developer temeva una collisione fra due piani con parametri identici. Ho verificato che non
>     c'è:
>     - il plugin riceve solo `identifier`, il tipo, `provider_params` e le impostazioni;
>     - la liquidazione e gli eventi del piano stanno nei parametri.
>     - **Approvato** (17:40): la chiave è esattamente l'insieme degli ingressi della chiamata, costruita da un solo
>       `asset_cache_key()` nei quattro punti, senza `asset_id`.
>   - Riga 🐛 scritta nel CHANGELOG: chi è colpito, che cosa ha visto, e che le chiusure si correggono entro 2
>     settimane.
> - **Test-author**: 17 casi nuovi in `test_provider_core_cache.py`, 13 rossi attesi e 4 guardie, non ancora fatti
>   girare (hold). Il conteggio atteso del file è 33 verdi e 13 rossi.
> - **Rossi (17:52–17:55)**, un solo giro di `utils provider-core-cache`, a carico 20: **33 verdi e 13 rossi**, ogni
>   rosso sulla sua asserzione principale.
>   - X-R27:
>     - dopo la pulizia, le chiamate al fornitore restano (1, 1) invece di (2, 2);
>     - l'avviso «cache invalidation skipped» compare, con e senza assegnazione.
>   - X-R28:
>     - il secondo asset riceve 11 invece di 22;
>     - la sua chiusura di oggi è salvata a 11;
>     - le cancellazioni non raggiungono la voce del prezzo corrente;
>     - il refresh e il prezzo corrente chiedono due volte.
> - **Correzione**, quella approvata:
>   - `core.asset_cache_key()`: la chiave è l'insieme degli ingressi della chiamata, cioè codice, identificativo (con
>     `None` come ""), tipo, hash dei parametri e impostazioni;
>   - `core.drop_asset_cache_entries()`;
>   - usate in `refresh.py`, `price_query.py`, `provider_management.py` e `currency_change.py`.
>   - `currency_change.py` legge l'assegnazione prima del commit, come valori semplici, e toglie `json` e
>     `Optional`.
>   - Presa una nota del test-author: i due log della stessa funzione ora usano i campi di structlog invece di
>     `extra={…}`, che li annidava.
> - **Prove**, col cancello a 50:
>   - `utils provider-core-cache` **46/46**;
>   - `services asset-source` 61, `rate-limit-results` 23, `current-price-bootstrap` 8, `plugin-settings-runtime`
>     120;
>   - `db populate`, poi `api asset-currency-change` 4 e `api market-data-wipe` 5;
>   - ruff, black e `git diff --check` puliti.
>   - La documentazione si è costruita senza avvisi, nei prerequisiti del server.
> - **⚠️ Fuori pista (carico)**: la prima unità API ha avviato il server della corsia, e i suoi prerequisiti hanno
>   rifatto il frontend (svelte-check e build di debug) e la documentazione.
>   - Le build erano vecchie dopo il merge 17 e le mie pagine. Sono 5 minuti pesanti, partiti a carico 46.
>   - Regola per la prossima volta: prima di un'unità API su build vecchie, chiedere uno slot.

### O-20 e C-66 — la sync alla creazione, e l'avviso nel dialogo di sync ⏳ (2026-10-16, dalle 18:14)

> - **Partenza**:
>   - X-R27 e X-R28 sono in dev (`ccfabfd6d`), HEAD `f485c123a`;
>   - dev ha 38 commit in più, ma nessuno sui file di questi lotti.
>   - Ordine dato dal coordinatore: O-20 e C-66 insieme, poi F21/C-90, poi O-8.
> - **O-20, analisi**: creando un asset con un fornitore dalla pagina Asset partono due sync.
>   - La prima è quella di `AssetModal` (~1245): tutta la storia (`start: 'resume'`), in background, senza riscontro.
>   - La seconda è quella della pagina (`oncreated` → `handleSyncAsset`, ~1855): con l'intervallo della pagina, la
>     rotella, il toast dei conteggi e il ricaricamento.
>   - La modale salta i fornitori parametrici, e assegnarne uno non crea prezzi. Per un investimento programmato
>     creato dalla pagina Asset oggi la sync della pagina è quindi l'unica.
> - **O-20, decisione (coordinatore, 18:2x)**: la modale tiene **una sola** sync e la annuncia con
>   `onsynced(assetId, result)`, come fa `FxPairAddModal`. La pagina non sincronizza più.
>   - Dettaglio mio, comunicato: la sync della modale copre anche i parametrici (`resume`, cioè tutto il piano). Il
>     modulo delle transazioni e il wizard ne guadagnano.
>   - `oncreated` riceve un `{syncing}` facoltativo, così la rotella non resta accesa se una sync non parte.
>   - Il toast è estratto in `reportSyncResult()`; il tipo `AssetCreateSyncResult` sta in `syncHelpers.ts`.
>   - La cura è pronta come innesto, nella cartella di sessione (`files/checks/o20_splice.py`, 9 sostituzioni, tutte
>     verificate a vuoto). Si applica solo dopo il rosso.
> - **Rosso di O-20**: un E2E che conta le `POST /assets/prices/sync` dopo una creazione dalla pagina Asset, con la
>   rotta finta. Oggi sono 2, ne serve 1. Lo scrive il test-author, che non lo fa girare: gira nello slot 1 delle
>   18:45 (cut-off 19:15).
>   - Sequenza nello slot:
>     1. il rosso sull'albero pulito: `frontend/src` non è cambiato dalla build delle 18:07, quindi nessuna nuova
>        build;
>     2. l'innesto;
>     3. una build;
>     4. i verdi: lo spec di O-20 e gli spec degli asset che creano asset.
> - **C-66, decisione (coordinatore)**:
>   - **(A)** adesso: il conteggio dei punti salvati nell'intervallo viene dai dati che la pagina mostra già, senza i
>     riempiti all'indietro. `SyncModalBase` aggiunge una riga sotto la barra dell'intervallo.
>   - (B) è X-R29, un endpoint che conta le righe manuali.
>   - (C) è X-R30, una domanda al developer: la sync deve tenere i prezzi manuali?
>   - Verificato: oggi la sync sovrascrive anche i `MANUAL`. I cambi saltano le coppie solo `MANUAL`.
> - **C-66 non entra nello slot delle 18:45**: i conteggi vengono dai dati di tre pagine, e prima vengono i rossi di
>   Vitest. È circa un'ora di lavoro, e l'E2E va nello slot successivo.
>   - Non tocco `frontend/src` prima del rosso di O-20.
> - **Approvato (18:29)**: O-20 con l'effetto collaterale, cioè che un investimento programmato creato dal modulo
>   delle transazioni o dal wizard ha subito la sua storia. È un miglioramento: va nel piano e nella riga del
>   CHANGELOG.
> - **Risposta del developer a (C)**: vince il fornitore, i prezzi manuali non si tengono. L'avviso (A) basta, e il
>   testo dice «modifiche manuali comprese». X-R30 è chiusa.
> - AF è entrato in `assets/[id]` e in `components/assets/detail/` (punta `c179a5144`). `AssetModal.svelte` e la
>   pagina lista non sono toccati.
> - **La riga del CHANGELOG** si scrive subito dopo il rosso: `CHANGELOG*.md` fa scadere la build, e il rosso deve
>   girare senza ricostruirla.
> - **Slot 1 (18:37–18:49)**, anticipato perché H aveva finito:
>   - **Rosso di O-20** sull'albero pulito, senza ricostruire: `front-asset asset-modal O-20` dà 1/1 rosso, «Received
>     length: 2». Sono le due sync, quella della modale (`resume`) e quella della pagina (l'intervallo della pagina).
>     Il test è `asset-modal.spec.ts`, «NR — One price sync per asset creation (O-20)».
>   - Poi l'innesto (`o20_splice.py`, 3 file) e la riga 🐛 nel CHANGELOG, aggiunta dopo il rosso.
>   - **Verdi**, con una sola build e svelte-check 0/0:
>     - O-20 1/1;
>     - `asset-modal` 18/18, compreso Bug K, che legge la sync della modale;
>     - `asset-list` 28/28;
>     - `tx-import-resolution` 15/15: il wizard crea gli asset con la stessa modale.
>   - Alla fine la porta 6183 era libera; lo slot è stato restituito alle 18:49.
> - **Prove leggere**: `core-unit` 186 file, 6783/6783; `component-unit` 8 rossi in `AssetModal.test.ts`.
>   - **Verdetto: assunzione**. I casi fissavano `oncreated` chiamata con esattamente `[assetId]`, e il secondo
>     argomento `{syncing}` è voluto.
>   - Il test-author li aggiorna al contratto nuovo e aggiunge i casi di `onsynced`: risultato, `null` sul rifiuto,
>     nessuna chiamata senza sync, e il parametrico che ora sincronizza.
> - **C-66, analisi**: ogni punto delle pagine porta `backward_fill_info.days_back`. Un punto con `days_back` = 0, o
>   senza l'informazione, è una riga salvata; gli altri sono riempiti all'indietro. È questo il criterio dei
>   conteggi.
>   - Le modifiche a `syncHelpers.ts` (`SyncSection`) aspettano il commit di O-20, che tocca lo stesso file.
> - **`AssetModal.test.ts` riallineato** (test-author): da 32 casi, di cui 8 rossi, a **37/37**.
>   - Gli 8 aspettano `oncreated(id, {syncing})`. Nel percorso dell'assegnazione fallita resta `oncreated(id)`, senza
>     dettaglio, ed è fissato così.
>   - 5 casi nuovi in «the one price sync of a creation (O-20)»:
>     - `onsynced(id, results[0])` solo dopo la risposta;
>     - `null` se la richiesta fallisce;
>     - nessuna sync senza fornitore, né quando l'assegnazione fallisce;
>     - il parametrico ora sincronizza da `resume` con `{syncing: true}`.
> - **Dal test-author, preso**: `.then(onsynced).catch(…onsynced(null))` riferiva la sync una seconda volta, con
>   `null`, se il gestore del chiamante lanciava. Ora è `.then(ok, ko)`: `ko` vale solo per il rifiuto della
>   richiesta. Il file resta 37/37.
> - **Dal test-author, non preso**:
>   - la data `end` in UTC vicino alla mezzanotte, che c'era già prima;
>   - `results` vuoto che diventa `null`, come un errore. Va bene: per il chiamante significa «nessun risultato».
> - **O-20 committato**: `2b0be1d05` (fix) e `24242bdd2` (diario), in dev con il merge `967ddbda4` (treno 127).
>   - Il coordinatore ha portato il mio ramo a `967ddbda4` per avanzamento rapido: AF lotto 9 sulla pagina
>     dell'asset, `ModalBase`, `ConfirmModal`.

#### C-66 — l'avviso nel dialogo di sync ✅ scritto e provato in Vitest (19:30–20:09; E2E in uno slot)

> - **Rossi prima** (test-author): **26 casi**, tutti rossi per la ragione giusta, e i 104 esistenti verdi (6 file).
>   - 13 su `hasStoredPointInRange`, nel file nuovo `utils/sync/__tests__/syncHelpers.test.ts`, registrato in
>     `core-unit`.
>   - 1 su `extractDaysBack` esportato.
>   - 9 su `SyncModalBase`:
>     - un avviso per sezione, col titolo solo se le sezioni attive sono più d'una;
>     - nessun avviso senza intersezione;
>     - gli id che non sono bersagli vengono ignorati;
>     - l'avviso sparisce allo Start e non torna con i risultati, anche falliti; torna a una nuova apertura;
>     - la frase c'è nei 4 cataloghi.
>   - 1 per ciascun involucro (`AssetSyncModal`, `FxSyncModal`, `PageSyncModal`).
> - **Implementazione** (innesto `files/checks/c66_splice.py`, 30 sostituzioni, tutte verificate a vuoto):
>   - `extractDaysBack` esportato, unica casa della regola dei punti riempiti all'indietro;
>   - `SyncSection.existingIds` e `hasStoredPointInRange()` in `syncHelpers.ts`;
>   - `SyncModalBase` mostra un `InfoBanner` di avviso per sezione prima dello Start
>     (`{testId}-overwrite-warning`, con `data-section`, `data-existing` e `data-total`);
>   - le prop degli involucri: `withDataInRange`, `assetsWithDataInRange`, `fxPairsWithDataInRange`;
>   - le pagine calcolano gli id dai dati che mostrano:
>     - Asset ed FX dalle proprie store;
>     - le pagine di dettaglio dal grafico del proprio asset o della coppia, e dalle store delle coppie.
>   - Prese due note del test-author:
>     - le due pagine FX ora usano `extractDaysBack` invece della loro copia della regola;
>     - corretti i commenti che dicevano `PageSyncAllModal`.
> - **Non contati, documentati**: gli asset di confronto delle pagine di dettaglio; i dialoghi aperti dai pannelli
>   di rischio, dal modulo delle transazioni e dal PAC, che non passano id e quindi non avvisano.
> - **i18n**: `fx.sync.overwriteWarning` nelle 4 lingue, col vocabolario di `common.provider`; in FR c'è uno spazio
>   prima di «:», come nel resto del file.
> - **Documentazione**:
>   - user: `assets/index.en.md` e `fx/sync.en.md`, una frase ciascuno;
>   - developer: `core-ui/modals.md`, un paragrafo sull'avviso.
>   - CHANGELOG: una riga ✨ in `[Unreleased]`.
> - **Prove**, col cancello a 50:
>   - i 6 file **130/130**;
>   - `i18n check` rigoroso;
>   - `front check` 0/0;
>   - `core-unit` **189 file, 6848/6848**;
>   - `component-unit` **158 file, 4109/4109**;
>   - `mkdocs build` stretto, verde, senza avvisi.
> - **⚠️ Fuori pista (ambiente)**: il primo `front check` ha dato 1 errore in `pac-allocator/planner/source.ts:290`.
>   - Il client generato era delle 18:39, cioè di prima dell'avanzamento rapido, e il backend di dev ha aggiunto
>     `ESTIMATED_AT_COST` a quel campo.
>   - Dopo `api sync`: 0/0.
> - **Resta**: l'E2E del C-66, che il test-author scrive senza farlo girare, insieme all'E2E combinato `asset-modal` e
>   `asset-list` con AF lotto 9. Gireranno nello slot che il coordinatore assegna.
> - **E2E del C-66, scritti dal test-author e non ancora fatti girare** (20:2x). Sono 5 test, tutti col filtro
>   `C-66`:
>   - `front-asset asset-list C-66` (2): un periodo con prezzi salvati avvisa una volta, con `data-existing` fra 1 e
>     il totale e il testo uguale a quello del catalogo; un periodo futuro, riempito solo all'indietro, non avvisa.
>     Senza premere Start e senza richieste di sync.
>   - `front-fx fx-sync C-66` (2): lo stesso per le coppie.
>   - `front-asset asset-detail C-66` (1): la sezione `assets` conta l'asset della pagina, `data-existing="1"`.
>   - La fixture nuova `e2e/fixtures/sync-overwrite.ts` contiene:
>     - le precondizioni lette dall'API;
>     - la frase del catalogo, con `intl-messageformat`;
>     - il registro delle richieste di sync.
>   - `assets-helpers.ts`: `goToAssetsPage` e `goToAssetDetailPage` accettano `search`.
>   - Le `desc=` del runner per `asset-list`, `asset-detail` e `fx-sync` dicono la copertura C-66.
> - **Ritocco**: nella pagina FX, `syncModalWithData` usa un `Set` invece di `includes` dentro `filter`, che era
>   quadratico. Nota del test-author. `front check` 0/0.
> - ruff e black segnalano solo gli E701 già presenti nei file del runner, su righe non toccate. Il perimetro del
>   lint è `backend/`.
> - **Slot E2E** alle 20:45, cut-off 21:15, con il copione `files/checks/c66_e2e_slot.sh`:
>   1. `front-asset asset-list C-66`, poi `front-fx fx-sync C-66`, poi `front-asset asset-detail C-66`;
>   2. poi `front-asset asset-modal` e `front-asset asset-list` per intero, sulla revisione combinata con AF lotto 9.
> - **Slot 1 (20:32–20:48)**, anticipato perché J aveva finito. Porta 6183 libera alla fine.
>   - C-66:
>     - `asset-list C-66` 2/2;
>     - `fx-sync C-66` 2/2;
>     - `asset-detail C-66` 1/1.
>   - **Revisione combinata con AF lotto 9**: `asset-modal` 18/18, `asset-list` 30/30.
>   - **Pagine toccate dal C-66, per intero**: `fx-sync` 5/5, `fx-list` 12/12, `fx-detail` 17/17, `asset-detail` 35/35.
>   - Una sola build, al primo spec.
> - **C-66 ✅ pronto per l'handoff**. Le voci C-66 (sezione W/C del backlog) e O-20 (backlog 38) le chiude il
>   coordinatore, perché non sono nella mia sezione.
> - **C-66 committato**: `32c64bbd9` (feat) e `a335fa78d` (diario).

### Diciottesimo aggiornamento di base: `dev_release2` (`27994759a`, con Y11 `pageBusy`) nel ramo X — merge aperto, combinato verde (2026-10-16, 20:50–21:01)

> - **Conflitti** (HEAD `a335fa78d`, MERGE_HEAD `27994759a`):
>   - `assets/+page.svelte`, sugli import: tenuti sia `pageBusy` di Y sia il mio `hasStoredPointInRange`.
>     - I `pageBusy.track` di Y coprono il caricamento, i ricaricamenti, il periodo e gli aggiornamenti.
>     - I miei gestori della creazione (`handleAssetCreated`, `handleCreatedAssetSynced`) restano fuori dal
>       tracciamento, come vuole P3, e Y li ha già annotati.
>     - Rispetto a dev, il file differisce solo per le aggiunte del C-66.
>   - `CHANGELOG.md`: aggiuntivo. Prima le due righe ✨ di dev (`user set-email`, `LIBREFOLIO_BRIM_PREWARM`), poi la
>     mia.
>   - In stage solo quei due file.
> - **Prove leggere sulla revisione combinata**, col cancello a 50:
>   - `api sync`;
>   - `front check` 0/0;
>   - `core-unit` **190 file, 6866/6866**;
>   - `component-unit` **158 file, 4123/4123**.
> - **Prossimo**: lo slot 2 (~21:30, dopo E) con `front-asset asset-list` e `front-portfolio page-busy` sulla
>   revisione combinata, poi l'ingresso in dev.
> - **Merge 18 committato** dal coordinatore: `941704538`, più il diario in `910c8f962`.
> - **Slot 3 (21:01–21:12)**, preso in prestito, sulla revisione combinata `910c8f962`:
>   - `front-asset asset-list` **30/30**;
>   - `front-portfolio page-busy` **12/12**.
>   - La build del frontend ha preso circa 7 minuti con carico 66–71. Alla fine la porta 6183 era libera, e lo slot è
>     stato restituito subito perché Y aspettava.
> - **Prossimo**: F21/C-90, poi O-8.
> - **C-66 in dev**: merge `4b2e0df80` (treno 138). Il coordinatore ha chiuso C-66 e O-20 nei backlog.

### F21, C-90 e P20 — frontend e `mailto:` ✅ (2026-10-16, 21:15–00:05; sotto-lotti 1 e 2 in dev, il 3 consegnato)

> - **Tre sotto-lotti**, ciascuno col suo checkpoint:
>   1. **P20 backend**: `LIBREFOLIO_SUPPORT_URL` accetta `mailto:` e un indirizzo, secondo la specifica di H.
>      - L'indirizzo passa da `EmailStr`, senza DNS, dopo un controllo esplicito di `?`, `#`, `%`, `,`, `;`, `<`, `>`,
>        `"` e degli spazi, che `EmailStr` da solo accetterebbe o toglierebbe ai bordi.
>      - Lo schema vale con qualunque maiuscola e si salva `mailto:`; `env_url` resta solo http(s).
>      - Il rosso è del test-author, in `test_config_package.py`.
>   2. **C-90**: la nota accanto all'esito di «Testa configurazione».
>   3. **F21 e P20 nel frontend** (`AssetSearchAutocomplete`):
>      - con almeno un premium, la sezione Premium e la sezione community chiusa, con l'avviso alla prima apertura;
>      - «Segnalacelo» dopo ogni ricerca: `mailto:`, oppure la pagina col rapporto negli appunti, oppure la issue
>        di GitHub;
>      - il frontend ricontrolla lo schema, mai `javascript:`.
> - Z prende `assets/+page.svelte` e `assets/[id]/+page.svelte` (lotto A); i miei sotto-lotti non li toccano.
> - **Z-8 su `assetDetailLive.svelte.ts`**: ok, lo scrive Z. Gli ho segnalato che il test fissa gli ingressi
>   dell'effetto e che `live-ticker.md` va tenuto allineato.

1. ✅ **P20 backend: `mailto:` in `LIBREFOLIO_SUPPORT_URL`** (21:15–23:35; consegnato al coordinatore alle 23:36).
   > **Note implementazione**:
   > - **Il rosso** (test-author): 58 casi nuovi in `test_config_package.py` e due righe in
   >   `test_system_api.py::test_the_configured_support_address_is_answered`
   >   (`mailto:Help@Example.ORG` → `mailto:Help@example.org`; `mailto:help?cc=x@example.org` → `null`).
   >   Lanciato prima del codice: **12 rossi, 789 verdi**.
   > - **`config/platform.py`**:
   >   - `support_url()` toglie gli spazi ai bordi. Se il valore comincia con `mailto:`, con qualunque maiuscola,
   >     passa a `_mailto()`; altrimenti a `env_url()`, che resta solo http(s);
   >   - `_mailto()` rifiuta l'indirizzo vuoto, gli spazi, `? # % , ; < > " /` (`_MAILTO_FORBIDDEN`) e quello che
   >     `EmailStr` rifiuta (senza DNS). Il `ValueError` nomina la variabile e cita il valore;
   >   - il valore valido si restituisce come `mailto:` più l'indirizzo normalizzato da `EmailStr`.
   > - **`schemas/system.py`**: la descrizione di `InstanceConfigResponse.support_url` dice le due forme, e `null`
   >   quando non è impostata o non è valida.
   > - **Doc**: `.env.example`, con la nota «l'indirizzo è pubblico»; `admin/configuration.en.md`;
   >   `admin/hosting_providers.en.md`; `developer/architecture/settings.md`.
   > - **CHANGELOG**: la riga arriva col sotto-lotto 3, quando la segnalazione diventa visibile.
   > - **Due cose da dire a H**, che ha scritto la specifica:
   >   - la stretta oltre la specifica: anche `<`, `>`, `"` e `/` sono rifiutati;
   >   - `EmailStr` restituisce un dominio punycode in Unicode: `xn--bcher-kva.de` diventa `bücher.de`.
   > - **Prove**, con il carico a ≤ 50, una alla volta:
   >   - `services config-package` → **804/804**;
   >   - `services config-env-example` → **38/38**;
   >   - `api sync` → ok;
   >   - `mkdocs build` (stretto, 22:05–22:08) → verde, nessun avviso, 3076 URL relativi risolti.
   >
   > **⚠️ Fuori pista (21:50)**: `api system` avvia il server della corsia.
   > - Il server ricostruisce il frontend quando un file di `frontend/src` è più recente della build, file di test
   >   compresi (`cli_base.check_frontend_needs_build`).
   > - Il test-author del C-90 aveva già scritto in `ProviderAssignmentSection.test.ts` quando l'ho fermato: la build
   >   delle 21:03 è scaduta, e `api system` è diventato un passo pesante, che chiede uno slot.
   > - La catena è ripartita senza `api system`. Il test-author finisce i casi nel file, ma non lancia niente.
   > - **Lezione**: prima di far partire un test-author sul frontend, finire i test API che avviano il server.
   >
   > **Slot per `api system`** (coordinatore, 22:02): lo slot 1 va prima a W per l'FE8b, poi a me verso le 22:50. Il commit
   > del sotto-lotto 1 arriva dopo. Intanto vanno avanti i rossi del C-90 e il sotto-lotto 3, solo controlli leggeri.
   > Script dello slot: `files/checks/slot.sh <prefisso> "<cat> <azione> …" …` (log `files/checks/logs/<prefisso>_N.log`).
   >
   > **Slot 1** (23:26–23:33, carico 49–88):
   > - prima il Vitest di `AssetModal` (42/42), che prova che il codice compila prima della build pesante;
   > - poi `test db populate --force`, sulla corsia, che è il setup delle API;
   > - infine `api system` → **122/122**. Il server ha ricostruito il frontend in debug e la doc, scaduti dalle 21:50.
   > - Porta 6183 libera alle 23:33:30; il coordinatore è stato avvisato subito, perché Y aspettava.
   > - ruff e black puliti sui quattro file Python; `git diff --check` pulito.
   >
   > **Cosa resta fuori dal commit del sotto-lotto 1**:
   > - `admin/configuration.en.md`: il docs-writer del sotto-lotto 3 ha riscritto la riga di `LIBREFOLIO_SUPPORT_URL`,
   >   e ora punta all'ancora `#let-us-know`, che solo il sotto-lotto 3 aggiunge. Il file va col sotto-lotto 3, se no
   >   la build stretta di quel commit fallirebbe;
   > - la riga del CHANGELOG su `mailto:`, che sta in quella di «Let us know».

2. ✅ **C-90: la nota sulla portata della prova** (21:30–22:27) — committato dal coordinatore: `656667b86`, solo i suoi
   percorsi, ed entrato in `dev_release2` (22:35). Il journal va col commit del sotto-lotto 1.
   > **Note implementazione**:
   > - **Il rosso** (test-author): 8 casi nuovi in `ProviderAssignmentSection.test.ts`, nel blocco
   >   «the probe’s scope note (C-90)». Tre casi chiedono la nota dopo una prova manuale con una riga `history` riuscita,
   >   con un avviso, oppure riuscita mentre il prezzo corrente falliva. Cinque casi la vietano: prima della prova, durante,
   >   con la prova fallita in blocco, senza riga `history`, dopo una prova automatica.
   >   - Il testo si confronta col catalogo, e il caso controlla che la chiave esista.
   >   - Il test-author aveva toccato anche il `totalLineOf` dei casi M-18. Non serve, perché la nota sta fuori dalla lista
   >     dei risultati, e l'ha riportato com'era: il diff del file è di sole aggiunte (+173).
   >   - **Rosso confermato** (22:03, carico 47): **3 rossi, 56 verdi su 59**. I tre falliscono per la nota assente.
   > - **Il codice**:
   >   - `assets.probe.scopeNote` in 4 lingue, con `dev.py i18n add` (sorgente `i18n/assets/`);
   >   - in `ProviderAssignmentSection.svelte`, `showScopeNote`: una prova manuale conclusa con una riga `history`
   >     che non è un errore;
   >   - la nota è un `<p>` dopo la lista bordata, `data-testid="provider-test-scope-note"`, icona `Info`, solo ruoli
   >     (`text-lf-muted`);
   >   - una lettura della storia fallita davvero non mostra la nota: l'asset creato non avrebbe lo storico promesso.
   > - Prettier pulito sui due file.
   > - **CHANGELOG**: una riga in «✨ Added», dopo quella del C-66 («Test configuration says what it read…»). Il CHANGELOG
   >   non rende vecchio il sito della doc, che guarda solo `mkdocs_src/docs/**/*.md` (`dev.py:auto_build_mkdocs`).
   > - **Prove** (22:19–22:25, carico 41–47, una alla volta):
   >   - Vitest `ProviderAssignmentSection.test.ts` → **59/59**;
   >   - colori `theme-roles.mjs --check` → puliti;
   >   - `i18n check` → 4789 chiavi, rigoroso;
   >   - `front check` → **0 errori, 0 avvisi**.
   > - Nessuna E2E guarda la struttura dell'esito della prova (`asset-modal.spec.ts` clicca solo il pulsante), e nessuno
   >   scatto della galleria mostra una prova conclusa.

3. ✅ **F21 e P20 nel frontend** (22:10–00:03; consegnato al coordinatore alle 00:05).
   > **Disegno** (dentro il perimetro approvato; `AssetModal.svelte` concesso dal coordinatore alle 21:57 per una prop):
   > - **Due moduli puri** accanto al componente (FE5a li sposterà con gli altri):
   >   - `assetSearchSections.ts`: `searchRank`, `orderSearchResults` (stabile: premium prima, poi priorità più bassa;
   >     ai valori di default resta l'ordine d'arrivo, D-X3), `hasPremium`, `splitSearchResults`;
   >   - `assetSearchReport.ts`: `supportChannel` (ricontrolla lo schema: `mailto:` con un solo indirizzo senza
   >     `? # % , ; < > " /` né spazi, oppure http(s) con un host; tutto il resto → issue di GitHub),
   >     `buildSearchReport` e `reportHref` (`mailto:` con le righe in CRLF, RFC 6068; la issue con `title` e `body`;
   >     la pagina così com'è).
   >   - Prima i moduli sono **stub** con le firme definitive, che lanciano «not implemented»: i rossi falliscono caso
   >     per caso, non all'import. Le implementazioni aspettano in `files/drafts/`.
   > - **Le sezioni** si mostrano solo quando un provider **interrogato da questa ricerca** è premium:
   >   - un premium deselezionato lascia la lista com'era;
   >   - la sezione community parte chiusa, e all'apertura mostra l'avviso sopra i risultati;
   >   - l'apertura vale per l'istanza del componente (cioè per l'asset), non si salva da nessuna parte;
   >   - gli indici `asset-search-result-{i}` continuano dalla sezione premium a quella community.
   > - **La segnalazione** compare dopo ogni ricerca finita, anche con «nessun risultato» o con l'errore, mai durante.
   >   - Con le sezioni sta fra le due; altrimenti in fondo alla tendina.
   >   - Il rapporto è **in inglese, fisso**: lo legge il supporto, e una issue di GitHub è in inglese. Le scritte
   >     della UI sono tradotte.
   >   - Gli esiti per provider vengono dagli eventi dello stream (`provider_results`, `provider_error` con
   >     `error_code`) o dalle liste della risposta REST. Chi non ha risposto, per esempio per il timeout, compare come
   >     «no answer».
   >   - Il contesto (valuta, tipo, identificativi) arriva da `AssetModal`, con la prop `reportContext`.
   >   - Con il canale «pagina», il clic apre la pagina e copia il rapporto con `writeTextToClipboard`, seguito da un
   >     toast.
   > - **Chiavi i18n** (11, in `assets.search.*`): `premiumBadge`, `premiumEmpty`, `communitySection` (ICU, FR con
   >   `many`), `communityWarning`, `reportQuestion`, `reportAction`, `reportVia.{mailto,page,github}`, `reportCopied`,
   >   `reportCopyFailed`. Lo script è `files/checks/sublot3_i18n.sh`.
   > - **Bozza del componente**: `files/drafts/AssetSearchAutocomplete.svelte`. La riga del risultato è spostata così
   >   com'è nello snippet `resultRow`, con lo script `files/checks/sublot3_template.py`, che conta ogni sostituzione.
   >   - Il tooltip del link legge chiavi letterali (`REPORT_VIA_KEY`), non un template: l'audit i18n le vede tutte.
   >   - Il badge «Premium» usa la coppia `bg-lf-info-soft` / `text-lf-info-on-soft`, come gli altri badge dell'app.
   >     Non c'è un componente badge condiviso.
   > - **`AssetModal`**: `searchReportContext` derivato (valuta, tipo, identificativi non vuoti) sulle due chiamate.
   >   Lo script è `files/checks/sublot3_modal.py`.
   > - **Conflitto previsto** (coordinatore, 22:35): le 2 righe di registrazione in `_frontend_utility.py` toccano lo
   >   stesso file dell'FE8b di W, che cambia righe di percorso. Chi entra per secondo risolve: quasi certamente io,
   >   dopo l'FE8b.
   >
   > **I rossi** (test-author, 22:05–22:40, scritti e non lanciati):
   > - `assetSearchSections.test.ts` (nuovo, core-unit): 28 casi, 27 rossi attesi;
   > - `assetSearchReport.test.ts` (nuovo, core-unit): 70 casi, 69 rossi attesi. Contiene 44 righe di
   >   `supportChannel` e la privacy: niente campi fuori dall'input, niente `window.location`;
   > - `AssetSearchAutocomplete.test.ts`: 26 casi nuovi (F1–F9 e R1–R14), 24 rossi attesi. Il controllo D-X3 (F1) è
   >   già verde;
   > - `AssetModal.test.ts`: un caso eseguito sulle due chiamate della ricerca;
   > - nessun caso esistente toccato; i due file puri sono registrati nel `core-unit`.
   >
   > **Decisioni alla revisione** (22:45):
   > - **`notify()` al posto di `toasts`**, come vuole `frontend.instructions.md`, sul modello di `LinkShare`
   >   (`accounts.link.copied`). Gli eventi sono `assets.search.report.copied` e `assets.search.report.copyFailed`,
   >   con `detail: {channel: 'page'}`; i test leggono la metà strutturata. Ho chiesto al test-author di adattare R9 e R10.
   > - **Il rapporto resta raggiungibile** (R15, segnalato dal test-author). Oggi, dopo una ricerca vuota o fallita e un
   >   clic fuori, la tendina non si riapre finché non si scrive di nuovo, e il caso tipico della segnalazione si perde.
   >   Quindi `handleFocusIn` riapre quando una ricerca è finita, e svuotare la casella dimentica la ricerca.
   >   È una decisione dentro il perimetro di P20 («dopo ogni ricerca»).
   > - **Fuori perimetro**: con streaming e REST entrambi falliti il messaggio non è tradotto. Va nel backlog come
   >   **X-R31**.
   >
   > **⚠️ Fuori pista**: la prima corsa dei rossi era in coda al cancello del carico (150–190, slot di W). L'ho fermata
   > prima che partisse, per lanciare i rossi una volta sola, sui file finali.
   >
   > **Rosso confermato** (22:55, carico 45), una sola corsa sui quattro file: **124 rossi, 62 verdi (186)**, esattamente i
   > rossi attesi. Per file: Sections 27/28, Report 69/70, AssetModal 2/39, Autocomplete 26/49. I fallimenti sono
   > «not implemented» degli stub (41), chiavi assenti dal catalogo, ordine e sezioni non applicati; nessun errore
   > d'import.
   >
   > **Il codice** (22:57, `files/checks/sublot3_apply.sh`, che si ferma se un file è cambiato dopo la bozza):
   > - i due moduli puri, il componente, la prop in `AssetModal` (`sublot3_modal.py`), le 11 chiavi in 4 lingue
   >   (`sublot3_i18n.sh`); Prettier pulito sui quattro file di prodotto.
   > - **Verde** (23:01, carico 48): **186/186** al primo giro.
   > - `check-orphans` → ogni test registrato è raggiungibile; colori → puliti; `i18n check` → 4800 chiavi, rigoroso.
   >
   > **⚠️ Fuori pista (23:06)**: `front check` → **1 errore** di tipo. `instanceConfig.config.support_url` esce dal
   > client generato come `string | (string | null)[] | null`.
   > - È un difetto del generatore: ogni stringa nullable con descrizione riceve anche `Array<string | null>` nel tipo
   >   TypeScript (345 campi). Il validatore Zod a runtime accetta solo `string | null`.
   > - La cura sta nel punto d'uso: a `supportChannel` arriva solo una stringa, altrimenti `null`.
   > - Vitest non l'aveva visto, perché non controlla i tipi.
   >
   > **CHANGELOG**: due righe in «✨ Added» dopo quella del C-90, le fonti premium e «Let us know» con
   > `LIBREFOLIO_SUPPORT_URL`. La seconda copre anche il `mailto:` del sotto-lotto 1.
   >
   > **In corso** (in background):
   > - l'E2E di F21 e P20, scritto dal test-author in `asset-modal.spec.ts`, due casi con le risposte instradate, da
   >   lanciare in uno slot;
   > - la doc, scritta dal docs-writer: `user/assets/create-edit.en.md` (la nota C-90, la ricerca e «Let us know»),
   >   `asset_plugin_guide.md` «Search Order», `search_link_finder.md` «Frontend wiring», la riga di
   >   `LIBREFOLIO_SUPPORT_URL` in `admin/configuration.en.md`.
   >
   > **Effetto sulla galleria**:
   > - la galleria degli import risponde alla ricerca con un errore per ogni provider (`galleryReportSets.ts`): negli
   >   scatti della modale dell'asset precompilata, la riga della segnalazione comparirà sotto «nessun risultato»;
   > - nessuna spec della galleria la controlla. Va detto a G.
   >
   > **`front check` dopo la cura** (23:11–23:14): **0 errori, 0 avvisi**.
   >
   > **La doc** (docs-writer, 23:05–23:25, solo inglese, nessuna build lanciata):
   > - `user/assets/create-edit.en.md`:
   >   - il passo 2 della creazione rimanda a «Let us know»;
   >   - due sezioni nuove, `#search-online-results` e `#let-us-know`, con la tabella delle tre destinazioni e cosa
   >     contiene il rapporto;
   >   - la frase del C-90 nel passo 2 di «Connect a price provider»;
   > - `asset_plugin_guide.md` «Search Order», `search_link_finder.md` «Frontend wiring» (la prop `reportContext` e un
   >   paragrafo sul rapporto), la riga di `LIBREFOLIO_SUPPORT_URL` in `admin/configuration.en.md`;
   > - non timbrata: è contenuto nuovo, e il debito di traduzione resta vero. Le pagine developer non puntano alle ancore
   >   utente nuove, che in IT/FR/ES non esistono ancora.
   > - Fuori perimetro, non corretto: in `asset_plugin_guide.md`, «How It Works» dice che il frontend chiama `GET …/search`.
   >   In realtà usa prima lo streaming e il REST solo come ripiego.
   >
   > **⚠️ Fuori pista — le impostazioni predefinite nel rapporto** (segnalato dal docs-writer, 23:20):
   > - un modulo nuovo e vuoto parte con valuta = valuta base dell'utente e tipo = STOCK, quindi il rapporto diceva
   >   «In the form: currency EUR, type STOCK» anche se l'utente non li aveva scelti: un indizio falso per il supporto;
   > - il developer aveva detto «valuta ed exchange **se c'erano**»;
   > - **regola nuova**: il rapporto nomina valuta e tipo solo in modifica, se li ha riempiti l'import, se li ha scelti
   >   l'utente (`currencyUserSet`) o se sono diversi dai valori del modulo vuoto, registrati in `resetForm`
   >   (`blankCurrency`, `blankAssetType`). Gli identificativi restano come prima;
   > - **i rossi** (test-author): tre casi nuovi in `AssetModal.test.ts`:
   >   - (c) creazione senza precompilazione: nessuna riga «In the form»;
   >   - (d) modifica: `currency USD, type STOCK`;
   >   - (e) tipo cambiato in ETF: solo `type ETF`.
   >   Attesi rossi (c) ed (e). Il codice è pronto in `files/checks/sublot3_modal_defaults.py`;
   > - la valuta base si legge una sola volta, in `resetForm` (`get(userSettings)`), quindi il valore registrato lì
   >   resta coerente anche se le impostazioni arrivano dopo;
   > - la doc utente è già allineata: «unless they are still the defaults of a new, blank form».
   > - **Rosso** (23:22, carico 38): (c) ed (e) rossi, 2 su 91 insieme al file ASA. I 49 casi ASA verdi confermano anche
   >   il restringimento di `support_url`.
   > - **Il codice** (23:24): `blankCurrency` e `blankAssetType` sono registrati in `resetForm`.
   >   - ⚠️ Fuori pista: il derivato stava alla riga ~218 e leggeva `currencyUserSet` e `blankCurrency`, dichiarati circa
   >     170 righe più sotto. A runtime va bene, perché `$derived` è pigro, ma svelte-check vede l'espressione sul posto
   >     (rischio TS2448). L'ho spostato dopo le dichiarazioni (riga 393).
   > - **Verde** (23:26, all'inizio dello slot 1): `AssetModal.test.ts` **42/42**.
   >
   > **Sotto-lotto 1 committato ed entrato** (coordinatore, 23:40): `62933bf46` (codice) e `b3e2fae02` (journal). Il
   > coordinatore ha risolto `hosting_providers.en.md`, tenendo la mia riga del supporto e quella di B sulla politica di
   > riavvio. Al prossimo aggiornamento di base va unito a mano `_frontend_utility.py` (FE8b di W più le mie 2 righe).
   >
   > **L'E2E** (test-author, 23:05–23:25, scritto, non ancora lanciato): un blocco in fondo a
   > `e2e/assets/asset-modal.spec.ts`, due test.
   > 1. **Premium prima**:
   >    - nello stream instradato il premium risponde per ultimo, così l'ordine viene dal livello e non dall'arrivo;
   >    - la segnalazione sta in mezzo; la community è chiusa (`data-count` 1), e aperta mostra l'avviso e il risultato #2;
   >    - il link GitHub decodificato contiene l'URL della issue, `Search:`, le righe dei provider della ricerca
   >      instradata, e la riga `LibreFolio …`, con profilo e `html[lang]`, letta con `expect.poll`.
   > 2. **`mailto:` e riapertura**:
   >    - `/system/instance` instradato con `mailto:support@example.org`, ricerca vuota;
   >    - l'href `mailto:` ha CRLF e oggetto;
   >    - un clic sul campo del nome chiude la tendina, il focus la riapre in `empty` con la riga, senza una seconda
   >      ricerca.
   >
   > - **Le rotte**:
   >   - solo i percorsi esatti, solo GET;
   >   - le risposte vere riscritte, togliendo `content-encoding` e `content-length`, perché il backend comprime in
   >     gzip da 1 KB in su;
   >   - premium = il primo codice cercabile in ordine di codice (oggi `borsa_italiana`), community = il secondo
   >     (`justetf`).
   > - Visto dal test-author, fuori perimetro: la vecchia rotta «Bug G» su `/settings/user`, nello stesso file, fa
   >   `fulfill({response, json})`. Si romperebbe allo stesso modo se quella risposta arrivasse a 1 KB.
   > - **Slot 2** chiesto per `front-asset asset-modal` (tutto il file) e `front-utility plugin-settings` (la ricerca
   >   con «Configure» e 👑), circa 20 minuti. La build del frontend fatta nello slot 1 contiene già il codice finale: fino
   >   allo slot non tocco `frontend/src` né il CHANGELOG.
   > - **La galleria** (via coordinatore): G riceve la nota sulla riga della segnalazione negli scatti degli import, e
   >   lo scatto delle sezioni premium da pianificare.
   >
   > **Slot 2** (23:41–23:48, carico 51–75, porta 6183):
   > - `front-asset asset-modal` → **20/20**: tutto il file, compresi i due test nuovi di F21 e P20 (19 e 20);
   > - `front-utility plugin-settings` → **5/5**: la ricerca con «Configure» e la legenda della 👑 passano per la stessa
   >   tendina;
   > - nessuna ricostruzione: la build dello slot 1 conteneva già il codice finale;
   > - porta libera alle 23:48:02; il coordinatore è stato avvisato subito, perché Y aspettava.
   >
   > **⚠️ Fuori pista (23:41)**: prima dello slot l'unico file più recente della build era `frontend/src/.DS_Store`.
   > - È un file di Finder, scritto alle 23:37, ignorato da `frontend/.gitignore` e non tracciato.
   > - `check_frontend_needs_build` guarda tutti i file sotto `src` e avrebbe ricostruito il frontend per niente (6–7
   >   minuti sotto carico): l'ho tolto. Finder lo ricrea quando serve.
   > - Detto al coordinatore all'inizio dello slot.
   > - Il controllo potrebbe ignorare i file di sistema come `.DS_Store`: si annota, non è un lavoro di X.
   >
   > **Controlli finali** (23:49–00:03, carico ≤ 50, uno alla volta):
   > - `front check` → **0 errori, 0 avvisi**, sul codice finale (dopo lo spostamento del derivato in `AssetModal`);
   > - `mkdocs build` stretto → verde, nessun avviso, nessuna riga INFO su ancore; 3076 URL relativi risolti;
   > - `mkdocs check-links` → **97** link validi;
   > - colori → puliti; `git diff --check` → pulito; porta 6183 libera.
   >
   > **Per dopo**:
   > - lo scatto di galleria delle sezioni premium (il DoD lo chiede), da fare con G: serve un provider premium
   >   instradato, come nell'E2E;
   > - la traduzione di `create-edit` (le ancore `#search-online-results` e `#let-us-know`) e della riga di
   >   `LIBREFOLIO_SUPPORT_URL` in `configuration`, alla prossima corsa di Aphra.

### Diciannovesimo aggiornamento di base e ingresso del sotto-lotto 3 ⏳ (2026-10-17, dalle 00:04)

> - **Commit del coordinatore**: `2c6fa9cfb` (codice del sotto-lotto 3) e `2a77ce1e5` (journal). Poi il merge di
>   `dev_release2` `91d89bce6` nel ramo X, senza conflitti (anche `_frontend_utility.py` e CHANGELOG): HEAD
>   **`ce8480897`** (genitori `2a77ce1e5` + `91d89bce6`), verificato, worktree pulito.
>   - Le mie 2 righe del `core-unit` sono ancora al loro posto dopo l'FE8b di W (righe 105–106).
>   - `481a93f1c` di H è ora nella base: X-R22 si può fare.
> - **Prove sulla revisione combinata** (richiesta del coordinatore), leggere, a carico < 50, una alla volta: `api sync`,
>   `front check`, Vitest dei 4 file della ricerca più `AssetModal` e `ProviderAssignmentSection`, `mkdocs build`
>   stretto, `check-links`. Poi `front-asset asset-modal` nello slot 2 dopo Y (dev ha portato le modali di import di T e
>   le pagine asset di Z). Verde → ingresso. Dopo l'ingresso, O-8 (prima di toccare `AssetDataEditorSection` va chiesto
>   al coordinatore: W ha il via sulle righe `step` per C-97b).
> - **Regola della notte** (coordinatore, 00:04): una domanda che solo il developer può sciogliere va scritta qui e
>   mandata al coordinatore, poi si passa alla voce dopo.

### X-R22 — l'ordine per reinserire un segreto illeggibile: proposta ⏳ (2026-10-17, 00:10; serve l'ok di H)

**Stato verificato** (su `ce8480897`):
- il testo dell'interfaccia, `pluginSettings.secret.unreadable` (`frontend/src/lib/i18n/pluginSettings/*.json:31`): «Saved,
  but this instance's key cannot read it: enter it again.». Lo vede chi guarda il campo: l'amministratore per i segreti
  d'istanza, l'utente per i propri. Quindi la frase deve funzionare per entrambi;
- la riga della mia pagina `user/settings/plugins.en.md:119` (solo inglese, nessuna traduzione) cita quel testo e dice
  «Type the secret again and save it»;
- la pagina di H, `admin/configuration.en.md` § «Saved Secrets and the Instance Key» (`#plugin-secrets`, riga 315), cita
  alla lettera il testo dell'interfaccia; subito dopo dice già l'ordine giusto («If you still have the old key, put it
  back before anyone enters them again»). Le pagine IT/FR/ES di `configuration` non hanno questa sezione: nessun debito
  di traduzione in più;
- nessun test confronta il testo: `PluginSettingsForm.component.test.ts` guarda `data-problem` e il tipo della nota.

**Proposta**:
- la chiave, in 4 lingue:
  - EN «Saved, but this instance's key cannot read it. If an administrator can put the old key back, that comes first;
    otherwise enter it again.»
  - IT «Salvato, ma la chiave di questa istanza non riesce a leggerlo. Se un amministratore può rimettere la vecchia
    chiave, va fatto prima; altrimenti inseriscilo di nuovo.»
  - FR «Enregistré, mais la clé de cette instance ne peut pas le lire. Si un administrateur peut remettre l'ancienne clé,
    c'est à faire d'abord ; sinon, saisissez-le à nouveau.»
  - ES «Guardado, pero la clave de esta instancia no puede leerlo. Si un administrador puede volver a poner la clave
    anterior, eso va primero; si no, vuelve a introducirlo.»
- la mia riga: la citazione nuova, e in «What to do» prima la vecchia chiave (con il link a `#plugin-secrets`), poi il
  reinserimento;
- la pagina di H: solo la citazione, sostituita con il testo nuovo. Serve l'ok di H, chiesto al coordinatore.

**Via del coordinatore** (00:21): tutte e tre le modifiche, citazione di H compresa; H rivede al checkpoint.

> **Note implementazione** (00:25–00:40):
> - la chiave, con `dev.py i18n update` in 4 lingue (`files/checks/xr22_i18n.sh`), dopo lo slot dell'E2E, per non
>   rendere vecchia la build dello slot;
> - le due pagine dal docs-writer: la riga di `user/settings/plugins.en.md` (la citazione nuova; in «What to do»
>   prima la vecchia chiave, poi il reinserimento) e, in `admin/configuration.en.md`, solo la citazione dopo «The tab
>   says so under each one:». La frase di H resta parola per parola.
> - **⚠️ Fuori pista**: il primo `mkdocs build` stretto è fallito: «Doc file 'user/settings/plugins.en.md' contains a
>   link '../../admin/configuration.md#plugin-secrets', but the doc 'admin/configuration.it.md' does not contain an
>   anchor».
>   - `user/settings/plugins` esiste solo in inglese, quindi in ogni lingua si serve la pagina inglese, e le sue ancore
>     si controllano contro `configuration.it|fr|es.md`, che non hanno ancora la sezione di H.
>   - La cura: il link alla pagina senza ancora, con il nome della sezione («Saved Secrets and the Instance Key»), come
>     fa già la riga 87.
>   - Lezione: da una pagina solo inglese, mai un'ancora che le traduzioni della pagina di arrivo non hanno.
> - **Fuori perimetro**: `admin/backup_restore.en.md:33`, la pagina di B, dice «reported as set but unreadable: enter
>   it again» con parole sue, senza l'ordine di H-3. Va segnalato al coordinatore.
> - **Prove** (carico ≤ 50): `i18n check` → 4924 chiavi, rigoroso; Vitest `features/plugin-settings/` → **304/304**
>   (nessun test confronta il testo); `mkdocs build` stretto → verde dopo la cura.

**X-R22 committato ed entrato** (coordinatore, 00:38): `375d09db3` (fix) e `4576a6968` (journal), dev `618563949`, il
mio ramo portato avanti con un fast-forward. Il coordinatore ha controllato la citazione nella pagina di H e passa a B la
nota su `backup_restore.en.md:33`.

### X-R37 — le 4 note di E su P20 ✅ (2026-10-17, 00:40–01:15; consegnato al coordinatore)

**Contratto** (coordinatore 00:20, decisione notturna N61 compresa):
1. `supportChannel(value, {githubFallback})` legge l'indirizzo già analizzato: una pagina http(s) torna come `url.href`
   normalizzato, così `https:host` non si risolve più sull'istanza; un indirizzo con utente o password conta come
   mancante.
2. **N61**: il ripiego sulla issue pubblica di GitHub solo con la configurazione letta e il profilo `selfhosted`. Su
   `managed` senza un indirizzo valido, o con `/system/instance` non letto, la riga della segnalazione non compare: una
   issue pubblica pubblicherebbe `managed`, i codici dei provider e gli identificativi. Un indirizzo valido funziona sui
   due profili.
3. Utente o password nell'indirizzo → mancante (punto 1).
4. La doc dice che in modifica il rapporto porta anche gli identificativi dell'asset, la sua valuta e il suo tipo.

> **Note implementazione**:
> - **I rossi** (test-author, scritti alle 00:20–00:39):
>   - `assetSearchReport.test.ts`: il blocco di `supportChannel` riscritto, da 44 a 56 casi, ognuno con e senza
>     ripiego, più la coppia che mostra il difetto (`https:host` come href si risolve su un percorso dell'istanza);
>   - `AssetSearchAutocomplete.test.ts`: 11 casi nuovi (ASA-S1–S8): managed senza indirizzo in ogni stato,
>     configurazione non letta (richiesta fallita, oppure non ancora arrivata), utente e password, la modalità a sezioni
>     senza canale (il pulsante della community subito dopo la sezione Premium), `https:help.example.org/assets`;
>   - `AssetModal.test.ts`: i 5 casi P20 resi deterministici con lo store vero (`instanceConfig.load({force: true,
>     fetchConfig})` in `beforeEach`, i valori predefiniti in `afterEach`);
>   - E2E: un test nuovo (managed senza indirizzo: nessuna riga, nessun link a `github.com`), e il primo test di
>     F21/P20 ora instrada `profile: 'selfhosted'` in modo esplicito.
> - **Rosso confermato** (00:41, carico 48): **56 rossi, 128 verdi (184)**, esattamente i 47 + 9 attesi.
> - **Il codice** (`files/checks/xr37_code.py`, 5 + 7 sostituzioni contate):
>   - `supportChannel` con `SupportChannelOptions` restituisce `SupportChannel | null`;
>   - il componente calcola `githubFallback` dallo store;
>   - `reportPlacement` è `null` senza canale; lo snippet `reportRow` riceve il canale come parametro.
> - **CHANGELOG**: la riga «Let us know» ora dice che la issue di GitHub c'è solo su un'istanza self-hosted, e che su
>   un'istanza di un provider di hosting il link compare quando il provider imposta un indirizzo.
> - **Doc**: affidata al docs-writer: `create-edit.en.md`, la riga di `LIBREFOLIO_SUPPORT_URL` in
>   `configuration.en.md`, il punto su `LIBREFOLIO_SUPPORT_URL` in `hosting_providers.en.md`, `search_link_finder.md`.
> - **Verde** (00:46, carico 47): **184/184** sui tre file; `front check` → **0/0**.
> - **⚠️ Fuori pista** (segnalato dal docs-writer): tre testi del backend dicevano ancora «the app links to GitHub
>   issues», che su `managed` non è più vero:
>   - la docstring di `support_url()` in `config/platform.py`;
>   - `_DEFAULT_SUPPORT` in `services/platform/instance_links.py`, cioè la `consequence` scritta nel log d'errore: a un
>     provider di hosting avrebbe detto una cosa falsa. Il modulo è di H, che lo rivede al checkpoint;
>   - la descrizione OpenAPI di `support_url` in `schemas/system.py`, seguita da `api sync`.
>   I test leggono `_DEFAULT_SUPPORT` per nome, quindi restano verdi. I testi dei test, `test_config_package.py` e
>   `test_system_api.py:917`, li ha aggiornati il test-author di X-R35, e vanno col suo commit.
> - **La doc** (docs-writer): `create-edit.en.md` (la issue di GitHub solo su self-hosted; su managed, o con la
>   configurazione non letta, niente link; in modifica gli identificativi dell'asset, la sua valuta e il suo tipo);
>   la riga di `configuration.en.md` (con «un indirizzo con utente o password conta come non impostato»); il punto di
>   `hosting_providers.en.md` (senza la variabile la ricerca non offre «Let us know»; altri link d'aiuto, come
>   `HelpMenu` e `FixFlaggedStep`, puntano ancora a GitHub); `search_link_finder.md` (`githubFallback` e N61).
> - **Prove**:
>   - `api sync`; ruff e black puliti sui tre file Python;
>   - `mkdocs build` stretto → 0 avvisi, nessuna riga INFO su ancore; `check-links` → 97;
>   - **slot 2** (01:03–01:11, con la ricostruzione): `front-asset asset-modal` → **21/21**, i tre test di F21/P20
>     compresi (19, 20, 21);
>   - `git diff --check` pulito; porta 6183 libera.

**X-R37 committato ed entrato** (coordinatore, 01:12): `c7434f00c` e `983612ed5`, dev `908fe6c90`, il mio ramo
portato avanti con un fast-forward. `instance_links.py` l'ha rivisto il coordinatore: solo testo, senza bisogno di H.

### X-R35 — `env_url` rifiuta utente e password ✅ (2026-10-17, 01:00–01:23; consegnato al coordinatore)

> **Note implementazione**:
> - **I rossi** (test-author, 00:43–01:05), 28 + 4 casi, tutti con `user_info` nel nome:
>   - `test_config_package.py`: `env_url` rifiuta l'utente nell'autorità (13 forme, IPv4 e IPv6 comprese), non cita
>     mai utente e password nemmeno quando un'altra regola rifiuta l'indirizzo (8 righe, comprese quelle senza `//` e
>     con la parentesi IPv6 aperta), accetta una `@` fuori dall'autorità (controlli verdi); `support_url()` fa lo
>     stesso, ma un `mailto:` resta valido; `support_link()` non pubblica l'indirizzo e nessun record del log lo
>     contiene;
>   - `test_registration_service.py`: lo stesso per `public_url` e `billing_url`, e per i loro link;
>   - via una vecchia riga che chiedeva a `env_url` di citare `mailto:help@a.example`: contraddiceva la regola nuova;
>   - i testi N61 di tre test aggiornati (`test_config_package.py` due volte, `test_system_api.py:917`).
> - **⚠️ Fuori pista**: la prima corsa di `config-package` (01:12:33) è caduta in un `ImportError`
>   (`HoldingGroupGainLoss`). Il nome esiste: la corsa era partita proprio mentre il coordinatore portava avanti il mio
>   ramo, e Python ha letto un albero aggiornato a metà. Rilanciata sull'albero fermo. Lezione: dopo un handoff, non
>   lanciare finché il coordinatore non dice il nuovo HEAD.
> - **Rosso confermato** (01:14): `config-package` **23 rossi, 820 verdi**; `registration` **4 rossi, 147 verdi**. Tutti
>   i rossi sono i casi `user_info`.
> - **Il codice** (`files/checks/xr35_code.py`): in `config/__init__.py`, `env_url` rifiuta una `@` nell'autorità
>   (`urlsplit(value).netloc`); il `ValueError` non cita il valore se contiene una `@` da qualche parte, altrimenti resta
>   il messaggio di oggi. ruff e black puliti.
> - **Verde** (01:15–01:19, carico ≤ 50): `config-package` **843/843**, `registration` **151/151**, `email-links`
>   **74/74**, `email-checks` **87/87**. Gli ultimi due passano da `links_state()`, che prende il `ValueError`.
> - **Doc**: al docs-writer, la regola di `env_url` in `developer/architecture/settings.md` e una frase nelle righe di
>   `LIBREFOLIO_PUBLIC_URL` e `LIBREFOLIO_BILLING_URL` in `admin/configuration.en.md`. Quelle due righe sono di A: le
>   rivede il coordinatore.
>   - Il docs-writer ha corretto anche il paragrafo sotto la tabella (il log non mostra un valore con una `@`) e le due
>     righe dei valori sbagliati. La nota «non mostrato» vale solo per gli indirizzi: gli errori di
>     `LIBREFOLIO_REGISTRATION` e `LIBREFOLIO_MAX_USERS` mostrano ancora il valore.
> - **Fuori perimetro, per E**: in `services/email/links.py` la docstring di `_usable_base` dice ancora che
>   `public_url()` «checks the scheme only»; il suo controllo delle credenziali ora è ridondante.
> - **Prove della doc**: `mkdocs build` stretto → 0 avvisi, nessuna riga INFO su ancore; `check-links` → 97;
>   `git diff --check` pulito.
> - **CHANGELOG**: niente, perché le tre variabili sono nuove della 1.3 e nessuna versione rilasciata è esposta.

**X-R35 committato ed entrato** (coordinatore, 01:27): `4e06d78ff` e `59be85f21`, dev `67668f5ce`, il mio ramo portato
avanti con un fast-forward. Il coordinatore ha rivisto le righe di A in `configuration.en.md` e passa a E la nota su
`links.py`. W-B58 non è ancora in dev: prima O-8, poi X-R38 quando W-B58 entra.

### O-8 — i messaggi del salvataggio nell'editor dei dati dell'asset ✅ (2026-10-17, 01:28–02:06; consegnato al coordinatore)

**Via del coordinatore**: `AssetDataEditorSection.svelte` è libero (stanotte niente lotti dei colori lì). Le righe
`step` di W (73–77 e 99) restano come sono: W le cambia nel C-97b, dopo W-B58.

**Stato verificato** (su `67668f5ce`): oltre alle tre stringhe del backlog («Asset data:», «Failed to save:», «Save
failed:»), il toast si costruisce con frammenti inglesi: `N prices saved`, `N prices deleted`, `N skipped (invalid)`,
`N events saved`. Solo `events.deleteSuccess` passa dal catalogo. Il ripiego `'unknown error'` è inglese. Nessun test
controlla questi testi, e il componente non ha un file di test.

**Disegno**:
- un modulo puro `assetDataSaveSummary.ts` (core-unit): i conteggi danno le parti non nulle, nell'ordine del
  salvataggio, ognuna un plurale ICU del catalogo (`assets.dataEditor.{pricesSaved,pricesDeleted,pricesSkipped,
  eventsSaved}` e `events.deleteSuccess`), unite da «, » dentro `assets.dataEditor.saved`; tutto a zero dà `null`;
- il componente passa a `notify()`: `assets.data.saved` con i conteggi in `detail` (l'evento sempre, il toast solo
  quando c'è qualcosa da dire); l'errore usa `dataEditor.saveFailed` (`{error}`) per il messaggio in linea e per il toast
  (`assets.data.saveFailed`), con il ripiego `common.unknownError`;
- le prove: il modulo puro con un `translate` finto e con il catalogo vero (EN e IT); l'E2E `asset-data-editor` legge
  l'evento (`waitForEvent`) in uno scenario di salvataggio, mai il testo del toast.
- Codice e chiavi pronti: `files/checks/o8_code.py` (le ancore corrispondono, verificato a secco),
  `files/checks/o8_i18n.sh`.

> **Note implementazione** (01:28–01:50):
> - **Fine del congelamento dei segnali** (coordinatore, 01:33): il CP-10b di J è in dev `b36e3873f`; il runtime ora sta
>   in `services/signals/{service,runtime,annotations,series,base,risk_adapters}.py`, e `risk/signal_helpers.py` non
>   esiste più. `signals/service.py` resta di J fino all'ingresso del CP-10c. O-8 e X-R38 non toccano questi file.
> - **I rossi** (test-author):
>   - `assetDataSaveSummary.test.ts` (nuovo, core-unit), 32 casi:
>     - un `translate` finto, per l'ordine delle parti e il separatore;
>     - il catalogo vero in EN e in IT: le chiavi esistono, i plurali con 1 e 2, i riassunti interi confrontati con
>       le parole del catalogo;
>     - una guardia su `events.deleteSuccess`, che deve leggere `n`.
>   - E2E `asset-data-editor.spec.ts`:
>     - un test nuovo: un salvataggio di prezzi rifiutato da un 500 instradato, poi il nuovo tentativo, su un asset
>       proprio, cancellato in ogni caso;
>     - due test esistenti sugli eventi estesi: leggono l'evento con `waitForEvent`, mai il testo.
>     - Nessuno scenario salvava prezzi, per questo il test è nuovo.
>   - Lo chiede il test-author: `data-testid="asset-editor-error"` sul banner d'errore.
> - **Rosso confermato** (01:45, carico 34): **30 rossi, 2 verdi (32)**. I due verdi sono la guardia su
>   `events.deleteSuccess`, in EN e in IT.
>   - Gli E2E rossi sono strutturali: né gli eventi né il testid esistono nel codice prima della modifica (verificato
>     con grep). Non ho speso uno slot per vederli fallire.
> - **Il codice**: `files/checks/o8_code.py`, con 1 + 10 sostituzioni contate, testid compreso. Nessun blocco del diff
>   tocca le righe di W (73–77, 99).
> - **Le chiavi**: `files/checks/o8_i18n.sh`, le 5 nuove `assets.dataEditor.*` più l'aggiornamento di
>   `events.deleteSuccess`.
>   - Diceva «{n} event(s) deleted»; ora è un plurale ICU vero, perché nel riassunto stava accanto agli altri plurali.
>   - L'editor è il suo unico utente, e la chiave continua a leggere `n`.
> - **Verde** (01:46–01:49): Vitest **32/32**; `i18n check`; colori puliti; `check-orphans`; `front check` → **0/0**.
> - **Backlog**: le stranezze già presenti finiscono in **X-R39** (conteggi asimmetrici, scritture parziali, intervallo
>   allargato dalle righe scartate, `onsave` non atteso, il banner dei cambi senza testid).
> - **Slot 2** (01:57–02:03, con la ricostruzione): `front-asset asset-data-editor` → **27/27**, compresi il test
>   nuovo (24: un salvataggio rifiutato, poi il nuovo tentativo) e i due test estesi sugli eventi. Porta 6183 libera.
> - **CHANGELOG**: una riga 🐛 in coda a «Fixed» di `[Unreleased]`: i messaggi del salvataggio erano in inglese in ogni
>   lingua (il difetto c'è nella 1.2).
> - **Il congelamento FE8b** (coordinatore, 01:49): W cambia solo le righe d'import di `AssetDataEditorSection` (le sue
>   righe 27 e 29) e di `_frontend_utility.py`. Le mie (22–23 e una riga del `core-unit`) sono separate: l'ho detto al
>   coordinatore.
> - **W-B58 entrato** (dev `4e9d1815f`): via libera a X-R38. Le mie due note alla revisione di `price_query.py` sono
>   diventate **X-R40**. Ordine: O-8 → X-R38 → X-R40.

**O-8 committato ed entrato** (coordinatore, 02:06): `9c3b9d803` e `b2c31632c`, dev `b1b4960c4`. Il CHANGELOG era in
conflitto in coda a «Fixed» (H-28, Z-14, MF-E1): il coordinatore ha messo la mia riga dopo le loro.
- **⚠️ Fuori pista**: il fast-forward del mio ramo è fallito. La modifica facoltativa del test-author in
  `scripts/test_runner/_backend_services.py` (la descrizione di `provider-policy`) si sovrapponeva a quella di Z-21 in
  dev. L'ho tolta (il patch è in `files/checks/xr24_runner_desc.patch`). HEAD resta `b2c31632c`: il coordinatore
  committa X-R24/25 e poi porta dev nel mio ramo, con `max_integer_digits` di W-B58. Poi X-R38, poi X-R40.

### X-R24 e X-R25 — la ricerca senza `providers`, e il test di justETF ✅ (2026-10-17, 01:55–02:20; consegnato, due corse aspettano lo slot)

> **Note implementazione**:
> - **I rossi** (test-author):
>   - `test_provider_policy.py`, sezione 6: `search()` e `search_stream()` senza `providers` non devono chiedere i
>     provider `test_only`. Due controlli verdi: un provider `test_only` nominato nella richiesta si chiede ancora.
>     Tutto in processo, con il registro vero e un sostituto per codice;
>   - `test_search_to_prices.py` (X-R25): al passo 1 `providers=justetf`, con un timeout tutto suo di 90 s, come in
>     `test_assets_provider.py`. Inoltre `test_search_provides_all_required_fields` ora chiede `providers=mockprov`:
>     senza, dopo la cura sarebbe diventato rosso, perché contava sui risultati del mock;
>   - aggiornati i commenti vecchi («mockprov also returns Apple», il paragrafo F21 su `search_rank`).
> - **Rosso confermato** (02:07): `services provider-policy` → **2 rossi, 50 verdi**, esattamente i due casi senza
>   `providers`.
> - **Il codice**:
>   - in `services/assets/search.py`, `_default_search_codes()`: ogni provider registrato tranne quelli `test_only`,
>     come li elenca `GET /assets/provider`. Lo usano i due rami. Il flag si legge con
>     `getattr(get_plugin(code), "test_only", False)`, così un codice che il registro non conosce resta (ci conta un
>     test di `asset-source`);
>   - la docstring di `services/assets/__init__.py` ora dice che `AssetSourceProvider` e `AssetSourceError` stanno in
>     `base.py`;
>   - in `api/v1/assets/providers.py`, le descrizioni OpenAPI del parametro `providers` (la lista e le due ricerche)
>     dicevano «default: all»: ora «every registered provider but the test-only ones». Va lanciato `api sync`.
> - **Verde** (02:08): `provider-policy` **52/52**, `asset-source` **61/61**; ruff e black puliti.
> - **Doc** (docs-writer): `asset_plugin_guide.md` «How It Works»:
>   - passo 2: il frontend chiama lo streaming con i `providers` scelti, e il REST solo come ripiego. **Chiude
>     X-R34**;
>   - passo 3: senza `providers`, ogni provider registrato tranne quelli di test.
> - **Manca**: `api sync`, `mkdocs build` stretto, `check-links`; poi uno slot per `api assets-provider` (le ricerche
>   dal vivo senza `providers`) ed `e2e search-to-prices` (X-R25, con la rete).
> - **Congelamento per la galleria** (coordinatore, 02:17), fino alle 03:30 circa: niente passi pesanti; i controlli
>   leggeri solo a carico < 50, ma il carico era 170. Il coordinatore chiede il checkpoint subito, con le corse di rete
>   segnate come non lanciate: le fa nello slot sulla revisione combinata, prima dell'ingresso. Così il merge di dev porta
>   `max_integer_digits` e parte X-R38.
>   - Ho fermato `api sync`, che aspettava al cancello, prima del commit, per non lanciare niente durante il merge.
>   - Non lanciati: `api sync` (il client generato non è tracciato), `mkdocs build` stretto e `check-links` (si fanno
>     quando il carico lo permette), `api assets-provider` ed `e2e search-to-prices` (nello slot).

**X-R24/25 committato** (coordinatore, 02:25): `e22251856` e `cdcf1325b`. **Ventesimo aggiornamento di base**: dev
`b1b4960c4` unito senza conflitti, HEAD **`30918aed6`**, pulito, con `max_integer_digits` di W-B58. Le due corse di
rete (`api assets-provider`, `e2e search-to-prices`) si fanno nello slot dopo il congelamento della galleria, sulla
revisione combinata, prima dell'ingresso.

**Slot 1** (03:31–03:37, porta 6183): `db populate --force` ✅; `api assets-provider` **24/24** ✅ (43 s), su `30918aed6`
più l'X-R38 non committato (tocca solo i cambi, nulla della ricerca degli asset). `e2e search-to-prices` **non partito**:
alle 03:35 il blocco della galleria dei colori è cominciato in anticipo, e il coordinatore ha chiesto di finire il pezzo in
corso e di non avviare il successivo.
> **⚠️ Fuori pista**: per fermare il ciclo di `slot.sh` senza uccidere il pezzo in corso, ho dato a `check.sh` un
> controllo su un file `STOP`, sostituendolo con una rinomina atomica (l'istanza in esecuzione tiene il vecchio inode), e
> ho creato il file. Il pezzo 3 si è fermato da solo. Poi ho tolto il file. Il pre-bind di questo pezzo ha ricostruito il
> frontend, vecchio dopo il ventesimo aggiornamento di base: circa 5 minuti dei 6.

### X-R38 — i tassi di cambio che nessuna colonna può tenere ✅ (2026-10-17, 02:25–03:45; consegnato, le corse `api` aspettano lo slot)

**Stato verificato** (su `30918aed6`):
- `FxRate.rate` è `Numeric(24, 10)`: 14 cifre prima della virgola e 10 dopo.
- **Le scritture**:
  - `upsert_rates_bulk` controlla solo che la valuta di base sia diversa da quella quotata e che il tasso sia positivo,
    poi inverte se `base > quote`, senza controlli;
  - l'endpoint `POST /fx/currencies/rate` inverte anche lui prima di chiamare il servizio;
  - la sync dei provider e i tassi a catena passano da `truncate_fx_rate`, che solleva un'eccezione da circa 1E+50.
- **Le letture**:
  - `convert_bulk` moltiplica o divide per il tasso salvato (righe ~249–251), e `compute_chain_rate` divide (~62):
    uno 0 salvato dà `DivisionByZero` (un 500), un `inf` dà importi infiniti;
  - i confronti della sync passano un valore salvato a `truncate_fx_rate`, che con un valore vecchio enorme solleva
    un'eccezione.

**Disegno** (direzione del coordinatore: la stessa di W-B58):
- `storable_fx_rate(value)` in `db/precision.py`, accanto a `storable_price` di W. È un'aggiunta; ora è uno stub che
  solleva `NotImplementedError`. Restituisce il valore troncato, oppure `None` se non è finito, se ha più di 14 cifre
  intere, o se troncato dà 0;
- **scritture**:
  - manuale: dopo la normalizzazione, un `ValueError` che nomina coppia, data e limiti, e niente scritto della
    chiamata; l'endpoint risponde con un errore per voce, e 400 se tutte falliscono, mai 500;
  - provider e catene: l'osservazione si salta, con un solo avviso per sync;
- **letture**: un valore vecchio inutilizzabile conta come «tasso mancante» in `convert_bulk` e come leg mancante in
  `compute_chain_rate`; nei confronti della sync conta come cambiato, così il valore nuovo lo sovrascrive.
- **I rossi**: affidati al test-author (02:28), solo scrittura finché dura il congelamento.

**Rossi confermati** (03:03, carico 38–42, una categoria alla volta, prima del codice): `utils real-decimal` 23/230
rossi, `services fx-core` 11/37, `services fx-sync-service` 23/34, `services fx-conversion` 26/44; nessun altro rosso, e
ogni rosso per la ragione giusta (lo stub che solleva `NotImplementedError`; tassi salvati oggi, o che sollevano
`InvalidOperation`, `DivisionByZero`, `Overflow`). `api fx-unit` (13 casi, 12 rossi previsti) aspetta uno slot: la categoria
`api` avvia il server della corsia.

> **⚠️ Fuori pista (03:10) — lo schema del tasso manuale, approvato dal coordinatore.** I 4 casi «non finito» di
> `api fx-unit` servono il router dei cambi su un `FastAPI()` proprio (in processo, senza server): l'handler globale di
> A7b-2, installato in `main.py`, non li raggiunge. In più, misurato in processo: `coerce_rate` (`schemas/fx.py`) chiamava
> `Decimal(v)` da sé, quindi `"abc"`, `true` e `"0x10"` sollevavano `InvalidOperation`, che non è un `ValueError` e passa
> oltre Pydantic (500, che A7b-2 non copre); e un rifiuto rimandava `Decimal('Infinity')`, che il renderer JSON non sa
> scrivere (500). Proposta al coordinatore, approvata: le stringhe e gli interi vanno a Pydantic così come sono, un float
> finito come prima, un float non finito come testo; ogni rifiuto diventa un 422 con un `input` serializzabile, senza
> bisogno di A7b-2 (che resta la rete per tutta l'app). Il test-author ha aggiunto 3 rossi (`"abc"`, `true`, `"0x10"`: 422,
> `loc` sul `rate`, niente salvato) e una guardia (un numero JSON `1.5` e un intero `2` accettati come prima).

**Codice** (03:20, script a sostituzioni contate `files/checks/xr38_code.py`: 28 sostituzioni in 6 file, ogni ancora
verificata unica prima di scrivere e di nuovo prima di ogni sostituzione):
- `db/precision.py`:
  - `storable_fx_rate` = `storable_value(…, FxRate, "rate")` più «mai 0»;
  - `fx_rate_limits_text()`, i limiti a parole letti dal modello (14 cifre, 10 decimali);
  - `usable_fx_rate_bounds()` = (`1E-10`, `1E+14`), per l'SQL delle letture.
- `services/fx/storage.py`:
  - `normalize_storable_rate`: la normalizzazione che non solleva mai; `None` se il tasso non è finito, se non è sopra
    0, o se l'inverso va in overflow;
  - `fx_rate_refusal`: coppia, data e limiti;
  - `upsert_rates_bulk`: il controllo «positivo» solo sui finiti, poi la normalizzazione e `storable_fx_rate`;
    `ValueError` prima di scrivere qualsiasi cosa della chiamata. Il valore salvato resta quello normalizzato, come
    prima: niente cambia per i tassi validi.
- `api/v1/fx/currencies.py`: l'inversione entra nel `try` della voce, tramite `normalize_storable_rate`.
- `schemas/fx.py`: `coerce_rate`, come sopra.
- `services/fx/conversion.py`:
  - `compute_chain_rate`: una gamba inutilizzabile dà `None` (`_usable_rate`);
  - `convert_bulk`: il filtro SQL `rate >= 1E-10 AND rate < 1E+14`, sia nell'ancora del riempimento all'indietro sia
    nella finestra. Nessun controllo per riga in Python: ogni double in quell'intervallo si rilegge conservabile, e il
    percorso è caldo (conversioni giornaliere del portafoglio).
- `services/fx/sync.py`:
  - in `ensure_rates_multi_source`, una sola passata di normalizzazione, che salta e raccoglie per coppia; l'inserimento
    usa le osservazioni tenute; il vecchio valore si confronta con `storable_fx_rate`, e `None` conta come cambiato;
  - in `sync_pairs_bulk`:
    - fase 2: `_collect_leg_rates` mette da parte (`leg_unusable`) ciò che non si normalizza;
    - fase 3: un passo singolo e le catene (`_storable_chain_rates`) saltano ciò che la colonna non tiene;
    - un solo avviso per coppia e per sync (`_warn_unusable_rates`), che unisce le date delle gambe e del tasso salvato;
  - `_count_actual_changes` confronta con `storable_fx_rate`;
  - il messaggio PARTIAL dice «nessun tasso che il database possa tenere» quando tutte le date sono state saltate.
- Ruff segnalava C901 su due chiusure (11 > 10). Invece di un `noqa`, ho estratto due funzioni di modulo
  (`_collect_leg_rates`, `_storable_chain_rates`).
- Controlli: ruff e black puliti sui 6 file; `import backend.app.main` ok.
- Limite noto, scritto nella docstring: SQLite tiene il tasso come double, quindi un tasso a pochi millesimi sotto
  `1E+14`, con più cifre di quante un double ne tenga (`99999999999999.999`), si salva come `1E+14`, e le letture lo
  saltano. Il test vuole `storable_fx_rate("99999999999999.99999999999")` conservabile: lascio il limite sulle cifre,
  com'è per W-B58.

**Verdi** (03:17–03:27, una categoria alla volta, carico < 50, corsia 6183):
- i quattro file dei rossi: `utils real-decimal` 230/230, `services fx-core` 37/37, `services fx-sync-service` 34/34,
  `services fx-conversion` 44/44;
- i vicini: `schemas fx-routes` 34, `db fx-rates` 6 (`ensure_rates_multi_source`), `services fx-catalog` 8,
  `rate-limit-results` 23, `rate-limit-errors` 55, `rate-limit-boundaries` 33, `financial-math` 825 (consumatori di
  `convert_bulk`).
- Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6183 --data-dir
  /tmp/librefolio-r13-x <cat> <azione>`, tramite `files/checks/check.sh`. Log in `files/checks/logs/xr38_*`.
- **Non girati** (la categoria avvia il server della corsia, quindi serve uno slot): `api fx-unit` (17 casi X-R38: 13 del
  primo giro, più i 3 rossi di `"abc"`/`true`/`"0x10"` e la guardia dei numeri JSON), `api fx`, `api fx-sync`,
  `api fx-signals`, `api fx-compress-errors`; facoltativi `front-fx fx-editor` e `fx-sync-mock`.

**Backlog** (sezione X): aggiunte X-R43 (impostazioni dei plugin, un intero di 401 cifre dà 500; dal coordinatore), X-R44
(`mockprov` nominabile e assegnabile in produzione; dalla revisione R13-SEC5 di E, prima del rilascio, dopo X-R38; più la
nota per F05: chiudere anche il fornitore *nominato*) e X-R45 (i lettori diretti di `fx_rates` che non saltano i tassi vecchi
inutilizzabili: una migrazione di dati, col via del developer, oppure il filtro in ogni lettore).
> **⚠️ Fuori pista**: avevo dato il numero X-R44 ai lettori diretti; il coordinatore l'ha assegnato a `mockprov`, quindi
> i lettori diretti sono diventati X-R45.

**CHANGELOG**: una riga 🐛 in coda a «Fixed» di `[Unreleased]`: tassi rifiutati, saltati nella sync, letture che li
saltano, 422 invece di 500.

**Documentazione** (docs-writer, solo EN, 03:20–03:42):
- `developer/architecture/database/index.md`: la riga `fx_rates.rate` ora dice 14 cifre; la fine del punto «Read.»; un
  punto nuovo, «Exchange rates.»;
- `developer/backend/fx/configuration.md`, «📅 Chain Dates, Writes and Counters» e la tabella degli stati: le gambe
  inutilizzabili, ciò che la colonna tiene, i rifiuti manuali, l'endpoint, i contatori, `partial`;
- `developer/backend/fx/architecture.md`: il riempimento all'indietro sui soli tassi utilizzabili, i limiti SQL della
  finestra, il limite noto dei double;
- `user/fx/detail/data-editor.en.md`: due frasi in «💾 Save your changes». La pagina è stata timbrata con
  `translate-stamp`; le pagine IT, FR ed ES non hanno le due frasi (si portano a mano, se si vuole).
- `mkdocs build` stretto ✅ (03:37, carico 34, 71 s, nessun WARNING) e `check-links` ✅ (97 link validi). Durante lo slot
  avevo chiesto al docs-writer di non scrivere sotto `mkdocs_src/`: il pre-bind del server ricostruisce la documentazione
  a ogni avvio.
> **⚠️ Fuori pista — X-R46, trovato dal docs-writer.** L'editor dei cambi (`FxDataEditorSection.svelte`, `handleSave()`)
> non mostra i rifiuti del server. Con un 400 mostra «Request failed with status code 400»; con un 200 che porta `errors`
> conta il tasso rifiutato fra i salvati. Con X-R38 questi rifiuti diventano raggiungibili dall'editor. È lavoro di
> frontend, fuori dal lotto: va nel backlog, proposto subito dopo X-R38. La frase della pagina utente dice solo «rifiutato
> e non salvato», che è vero lato server.

**Consegna** (03:45, FROZEN): 19 file tracciati, nessun file nuovo; ruff e black puliti su tutti gli 11 file Python;
`git diff --check` pulito; porta 6183 libera. Non girati: `api fx-unit`, `fx`, `fx-sync`, `fx-signals`,
`fx-compress-errors` (dopo il blocco della galleria). Commit proposti: `fix(fx): refuse or skip unstorable rates`
(codice, test, documentazione, CHANGELOG, hash delle traduzioni) e `docs(journal): X-R38, backlog X-R43–X-R46`.

**X-R38 committato** (coordinatore, 03:42): `80f5c65ff` e `a90f40d75`. **Ventunesimo aggiornamento di base**: dev
`d93de2899` unito; il CHANGELOG è andato in conflitto in coda a «Fixed» (la riga di E-11), e il coordinatore le ha tenute
entrambe. HEAD **`812194d37`**, pulito, verificato. Dopo il blocco della galleria: slot 1 per `api fx-unit fx fx-sync
fx-signals fx-compress-errors` ed `e2e search-to-prices`, poi l'ingresso di X-R24/25 e X-R38 insieme. X-R45 è dal
developer, insieme a W-B63; X-R46 dopo X-R40.

### X-R40 + W-B62 (+ X-R50) — prezzo corrente: la quotazione che nessuna colonna può tenere non torna come prezzo dal vivo ✅ (2026-10-17, 03:45–04:55; consegnato, entra insieme a X-R24/25 e X-R38)

**Stato verificato** (su `812194d37`), in `services/assets/price_query.py`, `get_current_prices_bulk`:
- `_fetch_one` restituisce il valore del provider così com'è, sia dalla cache (`core._asset_current_cache`, 2 minuti, che
  anche `refresh.py` riempie col valore grezzo) sia dalla chiamata, con sorgente `provider:<codice>`.
- Il controllo di W-B58 (`storable_price`) sta solo nel passo di salvataggio (~862): una quotazione da 1E+60, o 1E-13,
  non si salva, ma la risposta la restituisce lo stesso, e la UI la mostra come prezzo dal vivo. Il controllo vale solo
  per le quotazioni datate oggi: una con un'altra data passa senza controllo.
- L'avviso (~865) si ripete a ogni interrogazione: lo scheduler ogni 10 minuti, più ogni pagina aperta.
- Un valore non finito non arriva mai: `FACurrentValue` lo rifiuta alla costruzione, e il provider fallisce. Restano i
  valori finiti con più di 12 cifre intere, e quelli sopra 0 che troncati a 12 decimali danno 0.
- Il test di W-B58 `test_an_unstorable_current_quote_is_not_persisted` (`test_asset_digit_limits.py` ~874) usa come
  barriera `item.source == "provider:…"`, cioè proprio il comportamento che X-R40 cambia: va riscritto.

**Disegno**:
- Una quotazione che `storable_price` rifiuta vale come un provider che ha fallito: non torna come prezzo dal vivo, e
  l'asset ricade sull'ultimo prezzo salvato (`db:last_known`), oppure su «No price data available». Il controllo vale
  sia per il valore in cache sia per quello appena chiesto, qualunque sia la data.
- La cache resta com'è, col valore grezzo, così il provider non viene chiamato più spesso di oggi (una volta ogni due
  minuti per asset).
- L'avviso si scrive una volta per processo per ogni (asset, provider, valore): `functools.lru_cache` limitato, sul
  modello di `_report_invalid`.
- Un valore valido torna come oggi, grezzo; il passo di salvataggio tiene il suo controllo, ora senza avviso.
- Nessun codice d'errore nuovo in `FACurrentPriceItem`: il frontend non cambia.

> **⚠️ Fuori pista (03:50) — X-R40 si fonde con W-B62, e il disegno cambia.** Il coordinatore ha visto che X-R40 e W-B62
> (l'analisi di W, piano 04) sono lo stesso buco, e me li ha dati insieme (sono file miei: `price_query.py`,
> `refresh.py`). La proposta concordata con W sostituisce il mio disegno sopra:
> - `storable_price` subito dopo la chiamata: una quotazione non memorizzabile **non entra in cache** e ricade sul
>   database (prima tenevo la cache col valore grezzo, per non chiamare il provider più spesso);
> - una quotazione valida si serve **troncata** come la tiene il database;
> - il delta `changed_points` della sync si filtra col predicato di `price_store` (`_unstorable_provider_point`);
> - il ripiego sul database salta una chiusura che si rilegge `None` (un +inf salvato), invece di sollevare
>   `Decimal(str(None))` e far cadere tutta la richiesta.
> W ha passato i suoi rossi (17 più 2 guardie, girati alle 03:46, tutti per la ragione giusta) in una cartella della sua
> sessione, autorizzata dal coordinatore: vanno in un **file nuovo**, mentre nel file di W (`test_asset_digit_limits.py`)
> cambia solo la barriera.

**Disegno finale** (03:55):
- `price_store.storable_current_value(cv, asset_id, provider_code)` è l'unico controllo di una quotazione dal vivo, usato
  sia da `price_query` sia da `refresh` prima della cache:
  - restituisce `None` se `storable_price` rifiuta il valore; il rifiuto si scrive una volta per processo per ogni
    (asset, provider, valore), con `functools.lru_cache(maxsize=1024)` e il testo del valore accorciato (`1E+50000000`
    scritto per intero è 50 MB);
  - altrimenti restituisce la quotazione nella sua forma, se il troncamento non la cambia (`101.5` resta `101.5`: nessuna
    differenza nel JSON delle risposte di oggi), o troncata, se la cambia.
- `price_query`:
  - `_live_quote_item` (estratto da `_fetch_one`, per la complessità) mette in cache solo dopo aver costruito l'item;
  - `_last_readable_price` legge prima la riga più recente da sola, poi le più vecchie a pagine di 32, finché una
    chiusura si rilegge;
  - il passo di salvataggio tiene il controllo, ora senza avviso;
  - `FACurrentPriceItem` si importa in cima al modulo: l'import locale «contro il ciclo» era superato (`schemas.prices`
    era già importato in cima).
- `refresh`:
  - il valore corrente passa da `storable_current_value` prima della cache e prima di diventare il punto di oggi;
  - `_persist_refresh_item` conta e annuncia solo i punti che l'upsert tiene (`kept_items`). Così anche `new_count` e
    `changed_count` escludono le date saltate, e un 1E+60 non fa più cadere `_count_actual_price_changes` nel ripiego
    «tutto è nuovo».
- Script a sostituzioni contate: `files/checks/xr40_code.py`, 13 sostituzioni più una fetta fra due marcatori. Provato a
  secco su una copia in `/tmp`: ruff (C901 ≤ 10, isort) e black puliti.

**X-R50** (03:58, tre note della revisione R13-SEC5 di E su X-R38, nello stesso lotto):
1. `storable_fx_rate` chiede anche `float(stored) < 1E+14`. Misurato: `99999999999999.995` diventa il double `1E+14`,
   mentre `.992` no.
2. `normalize_storable_rate` restituisce `None` se l'inverso va a 0. Misurato: `1/1E+1000027` dà `0E-1000026`.
3. BOE, SNB e FED: `ArithmeticError` negli `except` per riga, così un valore ostile salta la sua riga e non fa fallire
   tutto il fetch. FED ha lo stesso buco, anche se E non l'ha nominato.
- Script `files/checks/xr50_code.py`: 6 sostituzioni in 5 file, provato a secco, pulito.
- Il caso X-R38 `99999999999999.99999999999` («tenuto») diventa «rifiutato»: va riscritto coi rossi di X-R50.

**Rossi di X-R40/W-B62** (test-author, 03:55–04:10): file nuovo `test_current_price_storable.py`, runner `services
current-price-storable`.
- Contenuto: gli aiuti di W copiati alla lettera (con asset e codici di provider propri); il blocco W-B62 identico (17
  rossi più 2 guardie, verificato con `diff`); i miei 3 rossi X-R40 (avviso una volta per valore; il refresh non mette
  in cache, non salva e non annuncia un valore corrente non memorizzabile; il refresh mette in cache quello valido già
  troncato) e una guardia (una quotazione che entra si serve nella sua forma).
- Nel file di W solo la barriera (`current_calls >= 1`), il contatore e il suo incremento.
- Rossi alle 04:13: `services current-price-storable` **20 rossi, 5 verdi** (le guardie), tutti per la ragione giusta:
  quotazioni servite o messe in cache grezze, il delta con la data saltata, `Decimal(str(None))` che solleva
  `ConversionSyntax` (500), 3 avvisi invece di 2. `services asset-digit-limits` 76/76, con la nuova barriera.
- Nota del test-author: `_count_actual_price_changes` solleva su una chiusura da `1E+48` in su quando la data ha già una
  riga, e il ripiego annuncia tutto. Con la cura i punti non memorizzabili non arrivano più lì (`kept_items`).

**Codice** (04:14): `xr40_code.py` applicato (13 sostituzioni più la fetta); ruff e black puliti; `import
backend.app.main` ok.

**Verdi** (04:14–04:16, carico < 50): `current-price-storable` 25/25, `asset-digit-limits` 76, `current-price-bootstrap`
8, `asset-source-refresh` 18, `asset-sync-counts` 1, `rate-limit-results` 23, `scheduler-jobs` 73, `utils
provider-core-cache` 46, `asset-source` 61. Per lo slot: `api current-price-persistence`, `api prices-sync-delta`.

**Documentazione di X-R40/W-B62** (docs-writer, 04:15–04:28; solo EN, pagine sviluppatore senza traduzioni):
`developer/backend/assets/architecture.md` (il punto Current Price, il paragrafo del refresh, la sezione «💹 Current
Quotes and Today's OHLC», il punto `_asset_current_cache`), `developer/frontend/components/features/live-ticker.md` (il
diagramma e i punti della sezione Backend), `developer/api/overview.md` («Resolution strategy»). `mkdocs build` stretto ✅
(carico 22) e `check-links` ✅ (97). **CHANGELOG**: una riga 🐛 dopo quella di X-R38.
> **⚠️ Fuori pista — una regressione trovata dal docs-writer, che diventa X-R51.** Prima, una quotazione corrente rifiutata
> arrivava all'upsert, e il risultato del refresh era PARTIAL col motivo («rejected 1 date(s) … no price column can
> keep»). Ora la quotazione si scarta prima, e il motivo resta solo nel log: con lo storico il risultato è OK senza
> messaggio; senza storico (CSS Scraper, o un intervallo che è solo oggi) è FAILED con «No price data available from
> provider». La cura (una nota in `_FetchedRefreshData`, che finisce negli `errors` del risultato) è pronta in
> `files/checks/xr51_code.py`, provata a secco. I rossi del test-author (e, f) sono in
> `files/drafts/xr51_refresh_note_tests.py`. Non entra in questo checkpoint: il coordinatore fa entrare tutto insieme,
> provato da questo slot, e la cura applicata dopo non sarebbe provata. È il prossimo lotto.

**X-R50, rossi e verdi**:
- Rossi del test-author: 16 rossi e 6 guardie, in `test_real_decimal.py`, `test_fx_core.py`, `test_fx_sync_service.py`,
  `test_fx_api_unit.py`, `test_snb_errors.py` e nel file nuovo `test_fx_parse_errors.py` (BOE e FED, PURE, registrato in
  `PROVIDER_ERROR_TEST_PATHS`). Il caso di X-R38 `14-integer-digits-cut-at-10-decimals` («tenuto») è passato fra i
  rifiutati, con la nota.
- Rossi alle 04:30, prima del codice: `real-decimal` 4/235, `fx-core` 3/41, `fx-sync-service` 1/35, `provider-errors`
  6/191. Nessun altro rosso, tutti per la ragione giusta (il double `1E+14` tenuto; `0E-1000026` restituito;
  `InvalidOperation` che esce dal `try` per riga). I 2 rossi di `api fx-unit` girano nello slot.
- Codice (04:31): `xr50_code.py`, 6 sostituzioni in 5 file; ruff, black e import puliti. Nel runner: il commento e la
  descrizione di `provider-errors`, che ora nominano sei provider.
- Verdi: `real-decimal` 235, `fx-core` 41, `fx-sync-service` 35, `provider-errors` 191, `fx-conversion` 44.
- Nota del test-author: per SNB il danno era maggiore. `_parse_json` gira fuori dal `try` di `fetch_rates`, quindi un
  valore ostile faceva perdere tutto il fetch SNB, ogni valuta; BOE e FED perdevano solo la valuta.

**Slot 1** (dalle 04:33; porta 6183): `db populate`, `e2e search-to-prices`, `api fx-unit fx fx-sync fx-signals
fx-compress-errors`, poi `api current-price-persistence prices-sync-delta`. L'albero è `812194d37` più X-R40/W-B62 e X-R50
non committati, l'ho detto al coordinatore: non si può isolare `812194d37` senza uno stash o un altro worktree. Il
coordinatore ha deciso (04:35) di far entrare insieme X-R24/25, X-R38, X-R40/W-B62 e X-R50, in un solo merge provato da
questo slot. A fine slot consegno il checkpoint FROZEN.

**Slot 1, risultati** (04:32–04:42, tutto verde):
- `db populate` ✅;
- `e2e search-to-prices` 3/3 (X-R25);
- `api fx-unit` 48/48, di cui 17 casi X-R38 e 2 X-R50;
- `api fx` 21, `fx-sync` 10, `fx-signals` 8, `fx-compress-errors` 6;
- `api current-price-persistence` 5, `prices-sync-delta` 5 (X-R40/W-B62).
- Porta 6183 libera alle 04:42.
- Log in `files/checks/logs/slot2_*`.
> **⚠️ Fuori pista**: nella consegna di X-R38 avevo scritto «21 casi X-R38» in `fx-unit`: sono 17, cioè 13 del primo giro,
> 3 di `"abc"`/`true`/`"0x10"` e la guardia dei numeri JSON.

**Dopo lo slot**:
- documentazione di X-R50 (docs-writer: il limite del double, l'underflow, i parser);
- CHANGELOG: una frase sui parser di BOE, SNB e FED in coda alla riga di X-R38;
- ruff e black puliti sui 17 file Python, `git diff --check` pulito.

**Documentazione di X-R50** (docs-writer, 04:43–04:53):
- `developer/backend/fx/architecture.md`: il «limite noto» di X-R38 sostituito dalla regola del double;
- `developer/architecture/database/index.md` (punto «Exchange rates.») e `developer/backend/fx/configuration.md` («What
  the column keeps», più l'underflow nei punti del manuale, dell'endpoint e del provider);
- `developer/architecture/patterns/fx_plugin_guide.md`: una frase sui parser, nel Flow.
- `mkdocs build` stretto ✅ e `check-links` ✅ (97).
- Note del docs-writer, nel backlog e non in questo checkpoint, perché lo slot non le avrebbe provate:
  - il testo dei limiti non nomina la regola del double (con X-R51);
  - la docstring di `_collect_leg_rates` (con X-R51);
  - ECB perde una valuta su un valore che non è un numero (X-R52).

**Consegna** (04:55, FROZEN): HEAD `812194d37`; 25 file tracciati e 2 nuovi (`test_current_price_storable.py`,
`test_fx_parse_errors.py`); ruff e black puliti sui 17 file Python; `git diff --check` pulito; porta 6183 libera. Commit
proposti:
- `fix(assets): serve only storable live quotes` (X-R40/W-B62: codice, test, runner, docs degli asset, CHANGELOG);
- `fix(fx): double limit, underflow, parser skips` (X-R50: codice, test, docs dei cambi, frase nel CHANGELOG);
- `docs(journal): X-R40/W-B62, X-R50, backlog X-R47–X-R52`.

**Entrati** (coordinatore, 05:00): X-R24/25, X-R38, X-R40/W-B62 e X-R50 in dev `fd6886bb0` (commit `a7b572ce2`,
`243ab6150`, `03a79bce8`). Il CHANGELOG è andato in conflitto in coda a «Fixed» con la riga di B4b, e il coordinatore le ha
tenute entrambe. HEAD avanzato a `fd6886bb0`, pulito, verificato. Nel backlog ho chiuso X-R24, X-R25, X-R34, X-R38,
X-R40 e X-R50, coi loro SHA.

### X-R51 — il refresh dice perché scarta un valore corrente ✅ (2026-10-17, 05:02–05:15; consegnato)

Seguito di X-R40/W-B62 (vedi sopra, «Fuori pista»):
- **Cura**: `files/checks/xr51_code.py`, 12 sostituzioni in 4 file, provata a secco sul nuovo HEAD:
  - `price_store.unstorable_quote_reason(value)`: il valore accorciato e i limiti, letti dal modello;
  - `_FetchedRefreshData.notes`;
  - in `_fetch_refresh_item`, `refused_note` quando il valore corrente è rifiutato. Senza altri punti diventa l'errore
    del fetch, quindi FAILED col motivo; altrimenti è una nota che `_persist_refresh_item` aggiunge agli `errors`, dopo
    lo scarto per valuta, quindi PARTIAL col motivo, come faceva l'upsert prima di X-R40;
  - nella docstring di `storable_current_value`, «above 0» diventa «not 0», come fa `storable_price`.
- Due ritocchi dal docs-writer di X-R50:
  - `fx_rate_limits_text()` nomina anche il limite sotto `100000000000000`;
  - la docstring di `_collect_leg_rates()` nomina l'underflow.
- **Rossi**: (e) e (f) dal test-author di X-R40, dal file di bozze a `test_current_price_storable.py`; il testo dei limiti
  dal test-author di X-R50, in `test_fx_core.py`.
- Rossi alle 05:00, prima del codice, tutti per la ragione giusta:
  - `current-price-storable` 2/27: (e) OK senza messaggio; (f) «No price data available from provider»;
  - `fx-core` 1/42: il rifiuto non nomina `100000000000000`.
- Codice (05:01): `xr51_code.py` applicato, 12 sostituzioni in 4 file; ruff, black e import puliti.
- Verdi (05:01–05:03, carico < 50): `current-price-storable` 27, `fx-core` 42, `asset-source-refresh` 18,
  `asset-digit-limits` 76, `fx-sync-service` 35, `asset-sync-counts` 1, `scheduler-jobs` 73, `db fx-rates` 6,
  `utils real-decimal` 235.
- Non girati, perché la categoria `api` vuole uno slot. Per costruzione non cambiano: `api fx-unit` cerca solo i numeri 14
  e 10 nel rifiuto, e il nuovo testo li tiene; `prices-sync-delta` e `current-price-persistence` non hanno valori
  assurdi.
- Documentazione: il docs-writer sul paragrafo del refresh (`backend/assets/architecture.md`) e sulla frase citata del
  rifiuto (`backend/fx/configuration.md`).
- CHANGELOG: nessuna riga. La regressione non è mai uscita, e la riga di X-R40 dice già cosa vede l'utente.
- Documentazione (docs-writer, 05:04–05:14):
  - `backend/assets/architecture.md`, paragrafo del refresh (190–198): PARTIAL col motivo; FAILED col motivo come unico
    errore. Nel caso FAILED `message` resta `None`, come per ogni errore di fetch;
  - `backend/fx/configuration.md` (263–269): la frase del rifiuto citata col nuovo testo.
  - `mkdocs build` stretto ✅, `check-links` ✅ (97).
  - Non toccata: la pagina utente `user/fx/detail/data-editor.en.md`, che non nomina il limite sotto `1E+14`. È un caso
    limite, e la modifica andrebbe fatta in 4 lingue.
- **Consegna** (05:15, FROZEN): HEAD `fd6886bb0`; 10 file tracciati, nessun file nuovo; ruff e black puliti sui 6 file
  Python; `git diff --check` pulito; porta 6183 libera. Commit proposti: `fix(assets): refresh names a refused live quote`
  (codice, test, documentazione) e `docs(journal): X-R51, backlog closures`.

**X-R51 entrato** (coordinatore, 05:08): dev `b3cae6e0e` (commit `ce798e36a`, `584f147f8`); HEAD avanzato, pulito. Le 3
corse `api` non girate vanno nel prossimo cancello del coordinatore. Ordine: X-R52 → X-R47 → X-R48 → X-R44 → X-R49. Nel
backlog: X-R51 chiusa; aggiunta X-R53 (usare il campo dei periodi fissi che MF porta nel backend, quando MF manda il
contratto).

### X-R52 — ECB: un valore che non è un numero fa perdere tutta la valuta ✅ (2026-10-17, 05:10–05:35; consegnato)

**Stato verificato** (su `b3cae6e0e`, `fx_providers/ecb/plugin.py` ~188–251):
- il ciclo delle osservazioni fa `Decimal(str(obs_value[0]))` senza un `try` per osservazione;
- un valore che non è un numero (anche un `null` JSON, che diventa `Decimal("None")`) solleva `InvalidOperation`, che
  l'`except (KeyError, IndexError, ValueError)` di `_fetch_one` non cattura;
- il ciclo seriale lo prende con `except Exception` («ECB fetch failed for X, skipping») e mette la valuta a `[]`. Si
  perdono tutte le date di quella valuta, non tutto il fetch: il docs-writer di X-R50 diceva il giusto.

**Disegno**: un `try` attorno al solo `Decimal(...)`: con `ArithmeticError` si salta l'osservazione (log a debug, col
valore), come per BOE, SNB e FED in X-R50. Un problema di struttura (indice, chiave) resta come oggi, «Unexpected ECB
response format». Script `files/checks/xr52_code.py`, una sostituzione, provato a secco: ruff e black puliti.
**Rossi**: al test-author di X-R50, in `test_fx_parse_errors.py`, con `httpx` doppiato: mai l'ECB vero.
- Rossi (05:14, prima del codice): `services provider-errors` 3/195 (`abc`, `1.2.3`, `null`): `{'USD': []}`, tutta la valuta
  persa, per la ragione giusta. Il test-author ha riusato il doppio HTTP di ECB di `test_rate_limit_http_providers.py`.
- Codice (05:15): `xr52_code.py` applicato. Nel runner: ECB e X-R52 nella descrizione di `provider-errors`.
- Verdi: `provider-errors` 195, `rate-limit-http-providers` 18, `fx-sync-service` 35.
- Documentazione: la frase di `patterns/fx_plugin_guide.md` (L71) nomina anche ECB, e il suo «prima». `mkdocs build`
  stretto ✅, `check-links` ✅.
- CHANGELOG: «European Central Bank» aggiunto alla frase sui parser, nella riga di X-R38.
> **⚠️ Fuori pista (05:20) — MF-P2.** MF mi ha chiesto la forma del campo dei periodi fissi (X-R53). Ho risposto: endpoint
> dedicati; `as_of` = la fine dell'intervallo (le serie sono giornaliere e riempite all'indietro, quindi i numeri restano
> quelli di oggi); la regola delle colonne resta; il cambio di ogni giorno. MF scrive il backend, in modo additivo, e io
> lo rivedo; il frontend è mio. L'ho detto al coordinatore, e i dettagli sono nel backlog, X-R53.
- **Consegna** (05:35, FROZEN): commit proposti `fix(fx): ECB skips a non-number day` e `docs(journal): X-R52, X-R53`.

**X-R52 entrato** (coordinatore, 05:24): dev `56d13a448`; HEAD avanzato, pulito. Il congelamento di FE8b è finito
(`31335fe26`): ho controllato che le mie tre registrazioni Vitest in `_frontend_utility.py` sono intatte in dev.

### X-R47 — il rapporto di uno SPLIT non è mai validato ✅ (2026-10-17, 05:25–06:00; consegnato, W e J rivedono)

**Decisioni del coordinatore** (05:25 e 05:32):
- lo scrivo io, da capo a fondo: backend (`event_store.py`, `events.py`) e frontend (il `case` in `eventSaveError.ts`, la
  chiave `events.saveError.invalidSplitRatio` in 4 lingue con `dev.py i18n`, un caso Vitest);
- W rivede, J per la convivenza con P-10;
- gli SPLIT già salvati con un rapporto ≤ 0 sono di MF (MF-D4): il motore li tratterà come mancanti, con un avviso di
  qualità dei dati, invece di sollevare.

**Disegno**:
- manuali: `_reject_invalid_split_ratios(item.events)` subito dopo `_reject_too_many_digits`. Copre creazioni, upsert e
  modifiche sul posto, perché una modifica porta la riga intera (anche quando un altro tipo diventa SPLIT). Usa
  `financial_math.splits.is_valid_split_ratio`, lo stesso del motore. Il rifiuto è `EVENT_INVALID_SPLIT_RATIO`, coi
  dettagli per evento (indice, data, tipo, rapporto); tutto o niente;
- provider: `_storable_events` scarta uno SPLIT non valido, con un avviso a parte;
- `events.py`: 400 in `_REFUSAL_STATUS`, più un punto nella docstring;
- frontend: il `case` col primo evento e `more`, come per `EVENT_TOO_MANY_DIGITS`; i testi usano `{type}` (l'etichetta
  tradotta), `{date}`, `{ratio}` e un plurale ICU, con il ramo `many` in francese.
- Script: `files/checks/xr47_code.py` (backend, 8 sostituzioni; la prima prova a secco ha trovato l'import mancante di
  `AssetEventType`, aggiunto) e `files/checks/xr47_frontend.py` (il `case`, poi `i18n add`). Entrambi provati a secco:
  ruff, black e prettier puliti.
- **Rossi**: un test-author per il backend (file nuovo `test_event_split_ratio.py`, runner `services event-split-ratio`:
  i file di test degli eventi restano di W), un altro per il caso Vitest in `eventSaveError.test.ts`.
- **Rossi** (prima del codice, tutti per la ragione giusta):
  - Vitest `eventSaveError.test.ts` 1/71 (oggi la chiave generica col testo inglese del server);
  - `services event-split-ratio` 27/51 (file nuovo, 662 righe: creazioni, upsert, modifiche sul posto, un DIVIDEND che
    diventa SPLIT, tutto o niente, la rotta in processo con 400 e `ratio` come stringa, la mappa degli stati, gli eventi
    dei provider con l'avviso); le 24 guardie verdi.
- **Codice** (05:46): `xr47_code.py` (8 sostituzioni) e `xr47_frontend.py` (il `case`, poi `i18n add`: la chiave è
  finita nel sottosistema `assets`, 4 lingue, una riga per lingua); ruff, black, import puliti.
- **Verdi** (05:46–05:50, carico < 50):
  - `event-split-ratio` 51/51, `asset-event-store` 71 (il file di W, con P-10 di J), `asset-digit-limits` 76;
  - `utils gate-i18n-catalog` 176, `gate-i18n-usage` 195, `dev.py i18n check` stretto (4970 chiavi);
  - Vitest 88/88 (`eventSaveError` più `catalogIcuLocale`);
  - `front check`: svelte-check 0 errori e 0 avvisi, prettier pulito.
- Non girati, perché vogliono uno slot: `api assets-events` e `events-suggest`. La rotta è provata in processo nel file
  nuovo.
- CHANGELOG: una riga 🐛 in coda a «Fixed».
- Documentazione: un docs-writer su `backend/assets/events.md` (più le pagine frontend che citano i codici).
> **⚠️ Fuori pista (05:50) — MF-P2 pronto.** MF ha mandato il contratto del backend dei periodi fissi. Le note per il mio
> lotto frontend sono nel backlog, X-R53: l'esclusione da `isPortfolioAffectingMutation`, la correzione dell'ora legale
> con la sua riga nel CHANGELOG, e le altre differenze. Lo rivedo quando me lo chiede il coordinatore.
- Documentazione (docs-writer, 05:50–06:00): `backend/assets/events.md` (i rifiuti del salvataggio manuale, gli eventi
  dei provider, la riga della tabella dei codici) e `frontend/components/core-ui/data-editor.md` (il codice nel punto «A
  refused save»). `transaction-form.md` non è toccata: la modale «+ New event» non può mandare uno SPLIT. `mkdocs build`
  stretto ✅, `check-links` ✅.
- Nota del docs-writer: MF-D4 non è ancora in questo albero, quindi uno SPLIT già salvato con un rapporto ≤ 0, se
  collegato, fa ancora fallire il report. La documentazione non ne parla finché MF-D4 non entra.
- **Consegna** (06:00, FROZEN): commit proposti `fix(events): refuse a split ratio not above 0` e `docs(journal): X-R47,
  X-R53 contract`.

> **⚠️ Fuori pista (06:05) — R13-SEC7-1, dentro X-R47, dalla revisione di E.** Il 409
> `EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST` di P-10 (`475bb9270`, di J) restituiva i `transaction_ids` delle rettifiche
> senza costo di **ogni** utente collegate allo SPLIT, e chiunque poteva provocarlo su un asset globale. Cura:
> - `bulk_upsert_events(…, *, current_user_id=None)` porta il chiamante fino a `_reject_split_retype_without_costs`.
>   Con un chiamante, `transaction_ids` tiene solo le transazioni che lui vede (`BrokerUserAccess`, come
>   `delete_events_bulk`) e `hidden_transactions_count` conta le altre; il messaggio dà solo il totale;
> - senza chiamante (test, codice interno), i dettagli restano come prima: i test di servizio di J non cambiano. Se E
>   preferisce che senza chiamante non si mostri nessun id, servono ritocchi alla fixture di W;
> - la rotta tiene il nome `_current_user`, come le altre del file, e passa `getattr(_current_user, "id", None)`.
>   Rinominarlo avrebbe rotto le due chiamate dirette di `test_asset_digit_limits.py` (di W), segnalate dal test-author.
> - Rossi (06:15): 2 su 54, per la ragione giusta (la keyword sconosciuta; il 409 che mostra `[3, 4]`). Verdi: 54/54,
>   `asset-event-store` 71, `asset-digit-limits` 76. `test_portfolio_wac.py:636` (di J, `api`) prende
>   `"hidden_transactions_count": 0` e va provato in uno slot.
> - Niente CHANGELOG: P-10 non è mai uscito.
- **Consegna di X-R47 con R13-SEC7** (06:20, FROZEN). Commit proposti: `fix(events): refuse a split ratio not above 0`,
  `fix(events): P-10 refusal shows only the caller's transactions`, `docs(journal): X-R47, X-R53, X-R55`.
- **Commit e base** (06:19): il coordinatore ha committato `5f68a8db0` (fix, X-R47 + R13-SEC7) e `65ae9f925` (journal),
  poi l'aggiornamento di base `dace18918` = X + dev `d107b6f26`, pulito.
- **Slot 3** (06:19–06:26, sul `dace18918`, carico a 5 minuti < 50), tutto verde: `db populate --force` ✅,
  `api portfolio-wac` 12, `api assets-events` 45, `api events-suggest` 9, `services event-split-ratio` 54,
  `services asset-event-store` 71; porta 6183 libera.

> **⚠️ Fuori pista (06:20) — X-R47 non entra: rosso bloccante della regola (d) dei confini dello strato.** J l'ha trovato
> in `services financial-math` sulla revisione combinata: `test_layer_boundaries.py::test_only_the_split_loader_names_the_split_event_type`.
> `AssetEventType.SPLIT` si può nominare in `backend/app` solo in `financial_math/splits.py` e
> `transactions/event_suggestions.py`; `event_store.py` lo nominava alle righe 108, 416 e 422 (i due controlli di X-R47).
> La regola è entrata con dev `d107b6f26`, quindi il mio slot non poteva vederla. Rosso confermato da me (06:27):
> 1 fallito, 870 passati.
> **Cura (proposta di J, adottata dal coordinatore)**:
> - un predicato `is_split_event_type(value) -> bool` in `financial_math/splits.py`, accanto a `is_valid_split_ratio`
>   (file di J: lo scrivo io, J rivede). Vero solo per un testo che, tolti gli spazi e in maiuscolo, è `SPLIT` (il membro
>   dell'enum è un testo); falso per tutto il resto, `None` compreso; non solleva mai;
> - i tre usi di `event_store.py` passano da lì; il `type` dei dettagli è la stringa normalizzata dell'evento; tolto
>   l'import ormai inutile di `AssetEventType`;
> - `event_store.py` **non** entra in `SPLIT_EVENT_TYPE_HOMES`.
> Script `files/checks/xr47c_code.py` (6 sostituzioni in 2 file), provato a secco insieme a `xr47b_code.py`: ruff e black
> puliti, il matcher della regola (d) non trova più righe in `event_store.py`.

### X-R47b — senza chiamante il rifiuto di P-10 non nomina nessuna transazione ✅ (2026-10-17, 06:20–06:54; stesso lotto della cura della regola d, consegnato)

**Origine**: la revisione di E su `5f68a8db0` («sound», più una LOW). Il default era fail-open: senza chiamante il rifiuto
mostrava tutti gli id. **Decisione del coordinatore**: nello stesso lotto della cura della regola (d), perché è la stessa
funzione.
- la rotta passa `_current_user.id`, senza il ripiego `getattr(…, None)`;
- `current_user_id=None` → nessun id (`transaction_ids` vuoto), `hidden_transactions_count` li conta tutti; il messaggio
  non cambia (solo il totale);
- i test P-10 di J nel file di W, che fissano quali transazioni, rispondono a un utente che le vede: J e W rivedono.

**Disegno**: script `files/checks/xr47b_code.py` (4 sostituzioni in 2 file: due docstring, il ramo dei dettagli sempre con
il conteggio, la rotta).
- **Rossi** (test-author, solo scrittura, 06:35):
  - nel mio `test_event_split_ratio.py`: la guardia «senza chiamante, tutti gli id» diventa il rosso «senza chiamante,
    nessun id, contati tutti»; i casi del predicato, rossi per assenza (letto al momento del test, così il file raccoglie);
  - nel file di W `test_asset_event_store.py`: un secondo utente con accesso al broker dell'unità (`holder_id`), che i tre
    test P-10 passano come chiamante; i dettagli attesi prendono `hidden_transactions_count: 0`. L'utente dell'unità
    resta senza accesso, perché `test_delete_keeps_the_in_use_breakdown_of_its_own_events` ci conta;
  - nel file di W `test_asset_digit_limits.py`: le due chiamate dirette della rotta prendono un chiamante finto
    (`SimpleNamespace(id=0)`).

> **⚠️ Fuori pista (06:38) — X-R55 passa a Z.** Il coordinatore alleggerisce la mia coda: gli intervalli senza tetto
> (`price_query.py`, il `convert` dei cambi) li scrive Z, che è libera; io li rivedo al checkpoint di Z, perché i file
> sono miei. Coda: la cura della regola (d) con X-R47b → X-R43 → X-R53 → X-R48 → X-R44 → X-R49.
- **Rossi** (06:40, prima del codice, per la ragione giusta):
  - `services event-split-ratio` 25 falliti su 78: i 24 casi del predicato («`financial_math.splits` has no
    `is_split_event_type`») e il rosso senza chiamante, che oggi mostra `[5, 6]` invece di `[]`;
  - `services asset-event-store` 71 e `asset-digit-limits` 76 verdi, prima e dopo, come previsto;
  - `services financial-math`: la regola (d), 1 fallito su 871 (06:27).
- **Codice** (06:41): `xr47b_code.py` (4 sostituzioni) e `xr47c_code.py` (6); ruff e black puliti su 7 file;
  `import backend.app.main` ok. Il test-author ha segnalato la descrizione del runner `event-split-ratio` rimasta
  indietro: aggiornata (mia voce nel file condiviso), con X-R47b e il predicato.
- **Verdi** (06:42–06:45, carico < 50): `services financial-math` 871 (la regola d di nuovo verde),
  `event-split-ratio` 78, `asset-event-store` 71, `asset-digit-limits` 76; slot 4 (carico a 5 minuti 37):
  `api portfolio-wac` 12, `api assets-events` 45; porta 6183 libera.

> **⚠️ Fuori pista (06:43) — la nota LOW di W sulla revisione di X-R47.** In `eventSaveError.ts` il `ratio` arrivava
> crudo dal server (`-0.5`), mentre in italiano, francese e spagnolo l'app scrive «-0,5». Il coordinatore: se costa poco,
> nello stesso lotto. Costa poco: `formatExactDecimal` (`utils/core/formatFixed.ts`) esiste già, la sua doc nomina
> proprio «a split ratio»; scrive la stringa decimale nella lingua dell'interfaccia senza passare da un float.
> Script `files/checks/xr47d_frontend.py` (2 sostituzioni: l'import e la chiamata), provato a secco, prettier pulito.
> Rosso Vitest affidato a un test-author (solo scrittura): it, fr, es → `-0,5` e `-0,000001`; l'inglese come guardia.
- **La nota di W, chiusa** (06:51–06:53):
  - Rosso Vitest 6 su 82: it, fr, es ricevono `-0.5` dove aspettano `-0,5` (e `-0.000001` per `-0,000001`). Il
    test-author ha trovato che Node 26 ha un `navigator` globale, che segue la lingua della macchina (`en-US` qui): il
    blocco lo toglie (`vi.stubGlobal`), come `uiLocale.test.ts`, e ogni test controlla la lingua prima della frase.
  - Codice: `xr47d_frontend.py` (2 sostituzioni). Verdi: Vitest 139 (`eventSaveError` più `formatFixed`),
    `front check` (svelte-check 0 errori, 0 avvisi), prettier pulito. Il segnaposto è un `{ratio}` semplice nelle 4
    lingue (nessun `number` ICU che rileggerebbe il testo).
  - Documentazione: nessuna modifica. `data-editor.md` dice che la frase nomina il rapporto, e resta vero; P-10 non è
    documentato in MkDocs (è di J).
- **Corsa in più** (06:53): `services asset-source-guards` 29 (chiama `bulk_upsert_events` senza chiamante, nessun
  P-10). `git diff --check` pulito, porta 6183 libera.
- **Consegna** (06:54, FROZEN): commit proposti `fix(events): split predicate; P-10 fails closed` e
  `docs(journal): X-R47b, X-R55 to Z`. Revisioni: J (`splits.py` e il blocco P-10 nel file di W), W (`event_store.py`,
  `events.py`, i due file di test, il frontend), E (X-R47b).
- **Commit e base** (06:55): il coordinatore ha committato il lotto (`1b6d65da7` fix, `8914eacf3` journal) e aggiornato
  la base: `61229b9a4` = X + dev `38adbfde0` (W-B60, che cambia `test_asset_digit_limits.py`, fuso da solo; H-37; SEC7-2
  di MF). Verificato: HEAD `61229b9a4`, genitori `8914eacf3` e `38adbfde0`, albero pulito; nessuna nuova chiamata
  diretta della rotta senza chiamante; `AssetEventType.SPLIT` di nuovo solo nelle due case.
- **Revisione combinata** (06:55–06:56, carico < 50), tutto verde: `services financial-math` 1076, `event-split-ratio`
  78, `asset-event-store` 71, `asset-digit-limits` 78 (2 nuovi di W-B60), Vitest `eventSaveError` 82; porta 6183
  libera. Riferito al coordinatore: pronto per l'ingresso. Revisioni: J (predicato e blocco P-10), E (X-R47b).
- Il messaggio «O-8 sbloccato» era superato: O-8 è entrato alle 02:06 (`b1b4960c4`); i chip `<code>` delle due modali
  d'importazione sono AF-5, non miei.

### X-R43 — impostazioni dei plugin: un intero enorme dà un 500 ✅ (2026-10-17, 06:57–07:32; consegnato)

**Decisione del coordinatore**: esito **per campo** (`INVALID_VALUE`, come il resto del contratto bulk), niente 422.
Per E conta che non ci sia un 500 e che quel campo non venga scritto.

**Stato verificato** (su `952c68cd5`): `validate_value` chiama `math.isfinite(value)` prima dei limiti; su un `int`
oltre il double (circa 309 cifre) solleva `OverflowError`, che nessuno prende. Le strade sono quattro, non una:
1. la scrittura (`service.py`, `_check_item`, prende solo `SettingValueError`): `PATCH /plugins/settings/bulk` con un
   intero JSON di 401 cifre → **500**. FastAPI legge il corpo con `json.loads`, che accetta fino a 4300 cifre; oltre,
   FastAPI stesso risponde 400 («There was an error parsing the body»), e non arriva al mio codice;
2. l'ambiente (`resolver._from_environment` → `parse_env_value`, `int(…)` poi `validate_value`): una variabile con un
   intero di 401 cifre per un campo INTEGER di sistema fa fallire la risoluzione del plugin (catalogo e uso). Un campo
   NUMBER no: `float()` dà `inf`, già rifiutato;
3. la riga salvata (`resolver._from_row`, prende `ValueError` e `SettingValueError`): un `value_json` di 401 cifre (solo
   se scritto a mano) fa fallire la risoluzione;
4. le dichiarazioni: un limite o un default di 401 cifre danno `OverflowError` invece di `SettingsDeclarationError`.

**Disegno** (`files/checks/xr43_code.py`, 4 sostituzioni, provato a secco anche sulla base nuova):
- `MAX_SAFE_INTEGER = 2**53 - 1`, l'ultimo intero che un numero JavaScript (la pagina delle impostazioni) e un double
  tengono esatti; `_holdable_number()` non solleva mai;
- in `validate_value`, dopo i controlli di tipo e prima dei limiti: un `int` oltre quel valore, per i campi INTEGER e
  NUMBER, è «too large: at most 9007199254740991 in absolute value» (mai il valore nel messaggio); un float non finito
  resta «expected a finite number»;
- i limiti dichiarati usano lo stesso controllo; un default oltre il limite diventa `SettingsDeclarationError`;
- le quattro strade ne seguono senza altro codice: la scrittura risponde col rifiuto che la rotta ha già (422,
  `detail.results` per voce, `INVALID_VALUE` sulla voce enorme, niente scritto: la scrittura è tutto o niente);
  l'ambiente dà `invalid_env`; la riga salvata è ignorata come ogni riga che il campo oggi rifiuta.
- Cambia anche un caso che oggi passa: un intero fra 2^53 e il limite del double, su un campo senza massimo, veniva
  accettato; ora è rifiutato. Nessun campo dei plugin rilasciati ne è toccato (le impostazioni dei plugin escono con la
  1.3).
- **Rossi** affidati a un test-author (06:58), nei quattro file delle impostazioni: contratto (valori e dichiarazioni),
  risoluzione (ambiente e riga salvata), servizio (scrittura), API (il 422 al posto del 500; 5000 cifre come guardia).

> **⚠️ Fuori pista (07:05) — X-R53: la lista dei file al coordinatore, e il via.** Mandata in anticipo (07:02), mentre
> il test-author scrive i rossi di X-R43. **Via dopo X-R43**, con le condizioni del coordinatore dei colori:
> - `fx/+page.svelte`: non toccare le righe **1141–1142** (le 4 classi nella baseline, AF-3 aspetta il designer); le
>   mie righe sono lontane (174–260);
> - `AssetTable.svelte`: se devo toccarlo, le 12 classi di colore di `txScope` (AF-2) restano come sono, e **prima lo
>   dico** al coordinatore;
> - `assets/+page.svelte`: zero classi di palette, e non ne aggiungo;
> - `theme-roles --check` pulito, nessuna classe di palette nuova da nessuna parte. Nessun worktree dei colori tocca
>   quei file.
- **Rossi** (test-author, 06:58–07:15; 575 righe in 4 file, tutti miei):
  - il test-author segnala che la rotta vera è `PATCH /api/v1/settings/plugins/bulk` (la costante `BULK` del file), non
    `/plugins/settings/bulk` come scrivevo; `MAX_SAFE_INTEGER` letto con `getattr` al momento del test, così il file
    raccoglie prima della cura; i valori enormi del servizio e dell'API sono interi casuali di 401 cifre, per provare
    davvero che il messaggio non li contiene; `_Lane.call` prende un `content=` facoltativo (JSON grezzo: `json.dumps`
    di Python rifiuta un intero oltre 4300 cifre, e la guardia delle 5000 cifre ne ha bisogno).
  - **Rossi confermati** (07:17–07:22, per la ragione giusta): `plugin-settings-contract` 22 su 229
    (`OverflowError`, oppure 2^53 accettato), `plugin-settings-runtime` 4 su 127 (`OverflowError` dall'ambiente e dalla
    riga salvata), `plugin-settings-service` 3 su 103 (`OverflowError` dalla scrittura); slot 5 (carico a 5 minuti 28):
    `api plugin-settings` 1 su 16, «answers 500 'Internal Server Error'»; la guardia delle 5000 cifre verde (400 di
    FastAPI).
- **Codice** (07:22): `xr43_code.py`, 4 sostituzioni in `fields.py`; ruff, black e `import backend.app.main` puliti.
- **Verdi** (07:22–07:24): `plugin-settings-contract` 229, `-runtime` 127, `-service` 103, `-crypto` 30, `-guards`
  25; slot 6: `api plugin-settings` 16; porta 6183 libera.
- **Documentazione** (docs-writer, dalle 07:25): `developer/architecture/patterns/plugin_settings.md`, la tabella
  «Types and Validation» e le regole di registrazione dicono il limite. Pagina solo inglese.
- Niente CHANGELOG: le impostazioni dei plugin escono con la 1.3, mai rilasciate.
- **Documentazione fatta** (07:25–07:31): `plugin_settings.md`, 8 righe aggiunte e 6 tolte (le righe `number` e
  `integer` della tabella, una frase sul perché del limite e sul messaggio, la regola dei limiti alla registrazione).
  `mkdocs build` stretto ✅ (3085 URL relativi risolti), `check-links` ✅.
- **Consegna** (07:32, FROZEN): `git diff --check` pulito, porta 6183 libera. Commit proposti
  `fix(plugin-settings): refuse integers past 2^53` e `docs(journal): X-R43`. Revisione: E (la sua R13-SEC7-2).
