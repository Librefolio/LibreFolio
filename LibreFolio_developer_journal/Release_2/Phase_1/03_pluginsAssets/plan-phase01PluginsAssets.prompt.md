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
>   **Ancora al developer**: D-X2 e D-X4 (non servono al CP1; nel documento delle decisioni sono le voci 18 e 19).
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

- `LIBREFOLIO_ASSET_PROVIDERS_ALLOWED`, `LIBREFOLIO_FX_PROVIDERS_ALLOWED` (+ `_FILE` non serve: non sono segreti), letti con
  un accessore in `backend/app/config/<sezione>.py` (regola di H, sotto §6) e scritti in `.env.example`. **Non impostate = tutti permessi** (self-hosted invariato). Profilo gestito (interruttore di
  H) e non impostate = solo i fornitori **non scraper** (D-X4). `MANUAL` sempre permesso; i fornitori di test esclusi.
- Ogni fornitore dichiara `is_scraper` (asset: yfinance, justETF, Borsa Italiana, CSS scraper = sì; scheduled_investment = no;
  FX: banche centrali = no). Default **prudente**: un fornitore che non lo dichiara conta come scraper, così un plugin di terzi
  montato non entra da solo in un'istanza gestita. È un attributo distinto dal `tier` di F21: «community» non vuol dire
  scraper (una futura API ufficiale gratuita, come OpenFIGI, sarebbe community ma non scraper). Facoltativo: un flag
  dichiarato «solo test» sostituisce i nomi scritti a mano (`api/v1/assets.py:419`, `api/v1/fx.py:129`).
- Nel profilo gestito senza elenchi espliciti la ricerca degli asset resta senza fornitori finché non arriva il fornitore a
  pagamento (F06) o l'operatore ne permette qualcuno: è la specifica («scraper disattivati di default»), da sapere.
- Un punto unico per famiglia (`registry.is_allowed(code)`), controllato a: elenco, ricerca, probe, assegnazione, sync, prezzo
  corrente, metadati. **Asset già legati a un fornitore non permesso** (D-X5): l'assegnazione resta nel DB; sync e prezzo
  corrente lo saltano con esito per voce `PROVIDER_NOT_ALLOWED` (niente 500, niente spam nello scheduler); le letture delle
  assegnazioni espongono `provider_allowed: false`; la UI mostra un avviso con «Cambia fonte» o prezzi manuali; mai
  cancellazioni né riassegnazioni automatiche. FX: il fornitore non permesso esce dalla catena di ripiego della coppia,
  l'esito della gamba lo dice; nessuna modifica alle rotte salvate (l'ambiente può tornare indietro).
- Facoltativo, se H offre l'area avvisi: «N asset usano fonti non permesse su questa istanza» per l'admin.
- Dal giro di sicurezza di H (coordinatore, 14/10), nello stesso lotto: il `css_scraper` segue i redirect su URL scelti
  dall'utente; vanno bloccati loopback, reti private, link-local e metadati del cloud, anche dopo un redirect.

### 4.4 Impostazioni dei plugin

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
non più dichiarati: ignorate. Id della revisione `006_plugin_settings` (19 caratteri, sotto il limite di 32).

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
| F05 | `assets/registry.py`, `fx/registry.py`, choke point nei servizi, schemi `provider_allowed` | nuovi pytest | sezione X di `.env.example`; testo per `admin/configuration` (H) |
| Impostazioni | `plugin_settings/*`, `db/models.py` (un modello), `alembic/versions/006_plugin_settings.py`, `api/v1/plugin_settings.py`, `schemas/plugin_settings.py`, basi di famiglia, justETF/Borsa; frontend `lib/features/plugin-settings/*`, una riga nel registro schede di A, «Configura» | pytest servizi/API/migrazione/sicurezza; Vitest; E2E; galleria | pagina dev `patterns/plugin_settings.md`; admin (sicurezza e variabili); utente `user/settings/plugins.md`, pagine dei fornitori |
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
| D-X2 | Segreti personali e backup (§10 n. 5) | ammessi, scrittura sola dal proprietario; zip della UI con la chiave d'istanza solo se protetto da password, altrimenti senza chiave e segreti da reinserire (con B) |
| D-X3 | F21 senza fornitori premium attivi | lista come oggi: gruppi e avviso solo se almeno un premium è permesso |
| D-X4 | Default degli elenchi nel profilo gestito | solo fornitori non scraper (flag dichiarato); `MANUAL` sempre |
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
| F05 | medio | scheduler rumoroso, UX degli asset orfani | esiti per voce, test dello scheduler, avviso |
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
8. **CP6 — F05**: elenchi, `is_scraper`, punto unico, esiti `PROVIDER_NOT_ALLOWED`, `provider_allowed`, sezione `.env.example`;
   avviso minimo nella UI (asset e cambi). K-16 e O-9 (backend, piccoli) viaggiano qui o in un treno qualunque.
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
- F05: default invariato nel self-hosted provato da test; profilo gestito provato; asset orfani gestiti.
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
- **F05**: `services provider-policy` (nuovo, in processo), `scheduler-jobs`, `asset-source-refresh`, `fx-sync-service`;
  `api assets-provider`, `fx-sync` (comportamento di default, invariato).
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
