# 14 — Il lavoro residuo, classificato per complessità

> **Report trasversale.** Gli altri tredici report sono organizzati *per sottosistema*:
> ognuno chiude con la propria lista di interventi. Questo report fa l'operazione opposta:
> prende tutte quelle liste, le **deduplica** e le riordina **per complessità e rischio**,
> ignorando a quale sottosistema appartengono.
>
> Serve a rispondere a una domanda che nessuno degli altri report può rispondere da solo:
> *da dove si comincia, e cosa non va toccato senza prepararsi.*

---

## Sintesi

I tredici report elencano complessivamente **86 voci di intervento**. Molte però sono la
stessa cosa vista da due angolazioni diverse — l'`open()` bloccante di `uploads.py:377`
compare sia nel report dell'API sia in quello trasversale, gli N+1 compaiono in tre report,
i `logger.error` in due.

Dopo deduplicazione restano **74 voci distinte** — di cui 4 già chiuse durante l'audit,
quindi **70 di lavoro residuo**, così distribuite alla chiusura dell'audit:

| Livello | Cosa caratterizza il livello | Voci | Chiuse al 2026-08-05 |
|---|---|---:|---:|
| **S0** | Già eseguito durante l'audit | 4 | 4/4 |
| **S1** | Meccanico — lo fa uno strumento, nessun giudizio | 5 | 3/5 (+1 voce nulla, +1 esclusa) |
| **S2** | Atomico — un punto solo, correttezza autoevidente | 16 | 15/16 (+1 esclusa) |
| **S3** | Rimozione tracciata — diff ampio, logica invariata | 9 | 7/9 (+1 in lavorazione, +1 esclusa) |
| **S4** | Da misurare prima — serve un dato che non abbiamo | 12 | 1/12 (bonus, fuori banda) |
| **S5** | Decisione di prodotto — l'ingegneria non decide da sola | 14 | 1/14 (bonus, fuori banda) |
| **S6** | Refactor strutturale — pianificazione, più sessioni | 14 | 0/14 |

**Il 30 % del lavoro residuo (S1+S2, 21 voci) non richiede alcuna decisione** e si chiude in
poche ore. Il **37 % (S4+S5, 26 voci) non è affatto lavoro di codice**: è lavoro di
**accertamento e di scelta**, e provare a farlo come se fosse codice è il modo più rapido
per sbagliarlo. Questa era la fotografia alla chiusura dell'audit.

> **Aggiornamento 2026-08-05 — esecuzione S1–S3.** Una fleet di 9 agenti paralleli ha
> eseguito l'intera banda S1–S3 (30 voci) in un solo ciclo, più 4 voci fuori banda
> dell'audit mkdocs e una regressione segnalata dall'utente. Esito, ricontato voce per
> voce e non copiato dal totale precedente: **25 chiuse** dentro la banda assegnata, **2
> chiuse fuori banda come effetto collaterale** (4.5, 5.6 — vedi sotto), **1 rivelatasi
> nulla** (1.2 — nessuna configurazione esisteva), **4 ancora aperte** per scelta
> deliberata o lavorazione parallela (1.5, 2.2, 3.8, 3.9). Delle 70 voci residue
> originarie il lavoro ancora da fare scende quindi da 70 a **42** (70 − 25 − 2 chiuse −
> 1 nulla). Racconto completo, correzioni ai reperti dell'audit e lezioni trasversali in
> [15 — Esecuzione S1–S3](15_esecuzione_s1_s3.md).

---

## Come leggere questa classificazione

### Due assi, non uno

La richiesta era "dal più atomico e sicuro al più complesso". Nel costruire la lista è
emerso che **atomico e sicuro non sono lo stesso asse**, e trattarli come se lo fossero è
la trappola principale di qualunque backlog di pulizia.

- **Complessità** = quanto lavoro costa, quante decisioni servono, quante sessioni occupa.
- **Rischio** = cosa succede se lo sbagli, e quanto tempo passa prima che qualcuno se ne
  accorga.

Nella maggior parte dei casi i due assi vanno insieme. **Nei casi in cui divergono sta il
valore di questo report**, e li ho isolati in una sezione dedicata più sotto.

### La scala

| | Livello | Reversibilità | Chi può eseguirlo |
|---|---|---|---|
| **S1** | Meccanico | Immediata (`git checkout`) | Chiunque, anche uno script |
| **S2** | Atomico | Immediata | Chiunque legga il punto |
| **S3** | Rimozione tracciata | Immediata ma il diff è grande | Chi ha letto la tracciatura d'assorbimento |
| **S4** | Da misurare | N/A — prima si misura | Chi sa eseguire la misura |
| **S5** | Decisione di prodotto | N/A — prima si decide | **Solo il proprietario del progetto** |
| **S6** | Refactor strutturale | Difficile | Chi può dedicarci sessioni intere |

---

## S0 — Già eseguito durante l'audit

Elencato per evitare che venga riproposto leggendo i report originali, che in alcuni punti
lo danno ancora come da fare.

| Intervento | Esito verificato |
|---|---|
| 77 autofix `ruff` (`PIE790` 54, `RUF010` 23) su 20 file | `PIE790` e `RUF010` ora a **0**; baseline `./dev.py lint` invariata a **36** |
| I 6 `pass` superflui dei provider ([04](04_providers.md) #3) | Assorbito dagli autofix `PIE790` |
| Fattorizzare il fallback `'standard'` ([13](13_ai_export.md) #4) | `resolveDefaultDetailLevel()` adottata nei 5 siti; `svelte-check` 0 errori, 106/106 test |
| `isDatasetCatalogEntry` ([13](13_ai_export.md) #5) | Diagnosi corretta (non era un *DRY orfano*) e funzione rimossa |

> **Nota sui 111 `RUF100`**: non sono un residuo da smaltire. Sono stati **lasciati
> deliberatamente** — documentano un'intenzione. Vedi [11](11_crosscutting.md) K8.
> Questo include i 2 di [06](06_db_models.md) #5, che quindi **non** vanno rimossi.

### S1–S3 eseguite il 2026-08-05

Le 25 voci chiuse in banda più le 2 chiuse fuori banda **non sono ripetute qui riga per
riga**: restano elencate, annotate `✅`, nelle rispettive sezioni S1/S2/…/S5 più sotto,
per non perdere la classificazione di complessità originale. Qui c'è solo il conto e le
correzioni che l'esecuzione ha imposto ai reperti dell'audit stesso — non al codice, alla
**diagnosi**:

| Livello | Chiuse | Rimaste aperte |
|---|---:|---|
| S1 | 3/5 | 1.2 voce nulla (nessuna config trovata), 1.5 esclusa (condizionale a `TRY`) |
| S2 | 15/16 | 2.2 esclusa (da discutere con l'utente) |
| S3 | 7/9 | 3.8 in lavorazione parallela, 3.9 esclusa (bloccata su 4.2) |
| S4 | 1/12 (bonus) | 4.5 chiusa fuori banda; le altre 11 restano da misurare |
| S5 | 1/14 (bonus) | 5.6 chiusa fuori banda; le altre 13 restano decisioni di prodotto |

- **1.2 era un rilievo nullo.** Nessuna configurazione `max-complexity`, `C901` o
  mccabe esiste in `pyproject.toml`, `ruff.toml` o `setup.cfg` — i primi due non
  contengono la voce, il terzo non esiste nel repository. Il report descriveva una
  configurazione inesistente.
- **3.1 aveva un conteggio finale più alto, ma il report originale era corretto.** Il
  report 09 elencava già **12** percorsi di barrel e il suo rimedio diceva
  esplicitamente «rimuovere tutti e 12 (11 sotto `components/` più `src/lib/index.ts`)»;
  solo il titolo della voce I3 diceva «11», per un errore di etichetta sul proprio
  elenco. L'esecuzione ne ha rimossi **13**: i 12 previsti più `tanstack-table/index.ts`,
  che nell'elenco non c'era.
- **3.7 era mal contato.** Il report indicava 8 bandiere `isXLoaded`/`isXLoading`; il
  codice ne esporta 12, e knip **ri-eseguito dopo** la rimozione dei barrel morti (non
  prima — la misura era inattendibile finché i barrel esistevano) ne ha confermate **9**
  davvero orfane. `isCurrenciesLoaded` è viva (usata da `currencyGraphStore.ts`) ed è
  stata **tenuta**.
- **4.5 e 5.6 si sono chiuse da sole.** Erano classificate S4/S5 — "da misurare" e "da
  decidere" — proprio perché la tracciatura dell'assorbimento non era conclusiva mentre
  i barrel morti erano ancora in mezzo. Rimossi quelli, `FxProviderConfig.svelte` e
  `LiveTicker.svelte` si sono rivelati pienamente assorbiti: nessuna decisione di
  prodotto è stata necessaria. Vedi la correzione anche in [`INDEX.md`](INDEX.md).

Racconto completo, incluse le due scoperte non previste da nessun report e la
regressione dell'utente risolta nello stesso ciclo, in
[15 — Esecuzione S1–S3](15_esecuzione_s1_s3.md).

---

## S1 — Meccanico

*Nessun giudizio richiesto. Uno strumento o quattro righe di configurazione. Se sbagli, te
lo dice subito il linter o il type checker.*

| # | Intervento | Dove | Costo |
|---|---|---|---|
| 1.1 | ✅ **fatto** — **Licenza `MIT` → `AGPL-3.0`**, + versione `0.6.x` → `1.1.0`, Python `>=3.11` → `>=3.13`, maturità `Alpha` → `Beta` | `pyproject.toml:7-22` | 4 righe |
| 1.2 | 🚫 **voce nulla** — `max-complexity` 20 → 25 | `pyproject.toml` | 1 riga |
| 1.3 | ✅ **fatto** — Correggere il docstring `get_provider` → `get_provider_instance` | `fx_providers/__init__.py` | 1 riga |
| 1.4 | ✅ **fatto** — Prefissare con `_` gli argomenti inutilizzati dei listener SQLAlchemy | `db/` | ~4 righe |
| 1.5 | ⏳ *non eseguita — condizionale*: se si adotta `TRY` in ruff, mettere `TRY003` in `ignore` | `pyproject.toml` | 1 riga |

> **1.1 è il primo intervento dell'intero backlog e non è tecnico: è legale.** Quattro righe
> di metadati che oggi dichiarano MIT su un progetto AGPL-3.0. Il progetto ha appena
> completato il lavoro sulle licenze di terze parti (`THIRD_PARTY_LICENSES.md`, attribuzioni
> in quattro lingue): dichiarare male la **propria** licenza vanifica quel lavoro. Costa meno
> di tutto il resto e vale più di tutto il resto.
>
> **Eseguito il 2026-08-05, con un dettaglio da correggere in corsa**: il primo tentativo
> ha scritto un classifier Trove inesistente (`...v3 or later`); l'elenco ufficiale PyPI
> ammette solo `GNU Affero General Public License v3` o `...v3 or later (AGPLv3+)`.
> Corretto in `...v3` — che è quanto dichiarano `LICENSE`, `README.md:193` e le quattro
> pagine `credits-legal.*.md`, tutte **senza** "or later".

> **1.2 si è rivelata una voce nulla.** Nessuna configurazione `max-complexity`, `C901` o
> mccabe esiste in nessun punto del progetto (`pyproject.toml`, `ruff.toml`, `setup.cfg`
> sono tutti silenti in merito — gli ultimi due non esistono nemmeno). Il rilievo
> descriveva una configurazione che non c'è: niente da alzare da 20 a 25.

> **1.5 va deciso prima di attivare `TRY`, non dopo.** I 515 `TRY003` dell'AI Export sono
> messaggi diagnostici dentro eccezioni già tipizzate: adottare `TRY` senza escludere
> `TRY003` produrrebbe una campagna di "pulizia" che cancella 515 messaggi utili.
> Vedi [13](13_ai_export.md) M5. **Non toccata in questo ciclo**, resta condizionale.

---

## S2 — Atomico

*Un punto solo, correttezza verificabile leggendo il punto stesso, coperto da test esistenti
o banalmente testabile. Qui stanno i quattro bug veri dell'audit.*

### I bug

| # | Intervento | Dove | Perché |
|---|---|---|---|
| 2.1 | ✅ **fatto** — Trattenere il riferimento al task di pre-warm | `main.py:251` | `asyncio.create_task()` senza salvare il riferimento → il task può essere **garbage-collected a metà esecuzione** |
| 2.2 | ⏳ *esclusa, da discutere* — Correggere `get_global_setting()`: funzione, ordine argomenti e chiave | `portfolio_engine.py:1947` (riga spostata dalle rimozioni di 3.2/2.7 nello stesso file; era `:1960` all'apertura dell'audit) | Argomenti invertiti **e** un positional di troppo → `TypeError` garantito sul ramo di fallback |
| 2.3 | ✅ **fatto** — `open()` → `await asyncio.to_thread(...)` | `uploads.py:377` | Unica violazione della **Async I/O Rule** del progetto: blocca l'event loop |
| 2.4 | ✅ **fatto** — Applicare `is_registration_enabled()` in `register()` | `api/v1/auth.py:189` | L'interruttore *"Allow new user registration"* è esposto nella UI e **non viene mai letto** |

> **2.4 conteneva una micro-decisione**: cosa fare quando il registro è vuoto e si registra il
> **primo utente**. È l'unico grado di libertà; il resto è meccanico. **Risolta il
> 2026-08-05**: `register()` rifiuta con **403** quando la registrazione è disabilitata e il
> richiedente non è il primo utente; il percorso di bootstrap resta aperto così
> un'installazione vuota può sempre creare il proprio amministratore. Questo è lo stesso
> difetto della voce mkdocs `05 A1` — due audit indipendenti, uno documentale e uno di
> codice, convergenti sulla stessa riga.

> **La chiave `"base_currency"` non è qui.** Il quinto bug — la valuta base configurata
> silenziosamente ignorata su 3 call site — richiede prima di decidere la semantica fra
> `base_currency` e `default_currency`. Sta in **5.2**. **Esclusa deliberatamente da questo
> ciclo**: l'utente vuole discuterla a parte. La riga (`portfolio_engine.py:1947`) contiene
> in realtà **tre** problemi distinti, non uno solo: gli argomenti sono invertiti e uno di
> troppo rispetto alla firma reale `get_global_setting(key, session)` (un `TypeError`
> garantito); viene usato il registro sbagliato, perché `get_setting_value(session, key,
> default)` vive in `global_settings_service.py:30`; e la chiave stessa è sbagliata, perché
> la chiave globale è `default_currency` (`schemas/settings.py:131`) mentre `base_currency`
> è una colonna per-utente (`db/models.py:343`). **5.2 è la stessa riga di 2.2** — il
> backlog la elenca due volte sotto tier di complessità diversi.

### La suite di test

| # | Intervento | Dove | Effetto |
|---|---|---|---|
| 2.5 | ✅ **fatto** — Restringere la guardia `'"fast"'` a `params_schema` | `test_signal_plugins_close_only.py:107` | Chiude l'**unico test rosso** del progetto. Collide con il nuovo `ai_export_temporal_rules` sul plugin ROC: è la guardia a essere troppo larga, non il codice a essere sbagliato |

### Pulizia a rischio nullo

| # | Intervento | Dove | Righe |
|---|---|---|---:|
| 2.6 | ✅ **fatto** — Log agli 11 `try/except/pass` silenziosi (`S110`), priorità a `yahoo_finance` e `provider_registry` | `system.py` ×3, `version.py` ×2, `yahoo_finance.py` ×2, `asset_source.py` ×2, `provider_registry.py`, `uploads.py` | +11 |
| 2.7 | ✅ **fatto** — Rimuovere gli alias `valuation_price*` e `signed_quantity_by_broker` | `services/` | −~10 |
| 2.8 | ✅ **fatto — rimossa, non adottata** — `unique_computation_count`: rimuovere **o** usarla nei log — è `len(self.computations)`, e il campo è pubblico e vivo | `signals/` | −3 |
| 2.9 | ✅ **fatto** — Rimuovere `transitive_dependencies` e `summary_position_count` | `ai_export/components/registry.py:97`, `payloads/portfolio_broker.py:877` | −14 |
| 2.10 | ✅ **fatto** — Rimuovere i 3 helper di staleness superati | `aiExportOptions.ts:200-210` | −11 |
| 2.11 | ✅ **fatto — rimossa, non adottata** — Rimuovere o adottare `AI_EXPORT_DOMAIN_ORDER` | `ai-export/catalog/shared.ts` | −1 |
| 2.12 | ✅ **fatto — rimossa, non adottata** — Adottare o rimuovere `signalLabelToText` | `charts/signals/` | ±5 |
| 2.13 | ✅ **fatto** — Verificare l'unico tipo esportato inutilizzato di `charts/` | `charts/` | −1 |
| 2.14 | ✅ **fatto** — Rimuovere `e2e/fixtures/db-helpers.ts` | `frontend/e2e/` | −file |
| 2.15 | ✅ **fatto** — Rimuovere `get_optional_user` se non è previsto un endpoint a visibilità mista | `api/deps` | −~8 |
| 2.16 | ✅ **fatto** — Rimuovere le 6 dipendenze npm inutilizzate | `frontend/package.json` | −6 righe |

**2.9 merita una nota**: `transitive_dependencies` è una DFS topologica che vive **40 righe
sotto** `_detect_cycles`, una DFS viva sullo stesso identico grafo. Due visite dello stesso
grafo, una usata e una no.

> **Esito verificato (2026-08-05)**: `S110` in `backend/app/` è ora **0**. Per 2.8, 2.11 e
> 2.12 il verdetto è stato **rimuovere**, non adottare: `unique_computation_count` era
> letteralmente `len(plan.computations)` e i punti di log non necessitavano di un'API
> dedicata; `AI_EXPORT_DOMAIN_ORDER` e `signalLabelToText` sono stati investigati per il
> caso *DRY orfano* e non si applicava — nessun consumatore ricalcola a mano
> un'ordinazione di dominio o un formattatore di etichette, quindi non c'era nulla in cui
> adottarli. Per 2.13, l'unico export inutilizzato era una **ri-esportazione ridondante**
> di `SignalStyle` da `charts/signals/registry.ts`: non era l'unico punto di accesso al
> tipo (la casa canonica resta `ChartSignal.ts`, ri-esportato dal barrel documentato
> `signals/index.ts`), quindi non era un punto di estensione plugin deliberato. Per 2.16,
> `katex` **è stato tenuto** (usato da `inlineMath.ts` e `FilePreviewModal.svelte`); solo
> `@types/katex` è stato rimosso perché katex v2 include i propri tipi. `package-lock.json`
> resta da rigenerare.

---

## S3 — Rimozione tracciata

*Il diff è ampio — centinaia di righe — ma la logica non cambia: ogni simbolo è stato
tracciato fino al suo sostituto. Il costo è **leggere la tracciatura**, non decidere.*

| # | Intervento | Righe | Assorbito da |
|---|---|---:|---|
| 3.1 | ✅ **fatto — 13 rimossi** — Rimuovere i barrel morti del frontend (i **12** elencati dal report 09 più `tanstack-table/index.ts`) | — | Import diretti |
| 3.2 | ✅ **fatto** — Rimuovere il blocco pre-engine di `portfolio_service` (+ i suoi test) | −130 (+ −176 test) | `portfolio_engine.build_history()` |
| 3.3 | ✅ **fatto** — Rimuovere `src/lib/tanstack-table/` + `@tanstack/table-core` | −file | Implementazione tabelle propria sotto `components/ui/` |
| 3.4 | ✅ **fatto** — Rimuovere `HoldingsPanel.svelte` | −file | `PositionsPanel.svelte` (vista "Holdings / Table" + 3 viste in più) |
| 3.5 | ✅ **fatto** — Rimuovere `BrokerImportFiles.svelte` | −file | `BrokerImportFilesModal.svelte` |
| 3.6 | ✅ **fatto** — Rimuovere `get_session_ttl` / `get_session_ttl_sync` | −~15 | `global_settings_service.get_session_ttl_hours` |
| 3.7 | ✅ **fatto — 9, non 8** — Rimuovere le 8 bandiere `isXLoaded` / `isXLoading` | −~30 | Stato derivato |
| 3.8 | ⏳ *in lavorazione parallela* — Rimuovere i test orfani insieme al codice che coprono | — | Vedi [12](12_test_coverage.md) L7 |
| 3.9 | ⚠️ Rimuovere `fifo_utils.py` — **solo dopo** 4.2 | −~120 | `fifo_lot_engine.py` |

> **Esiti verificati (2026-08-05)**: 3.2 ha rimosso **−130 righe** dal codice sorgente e
> **−176** dai test (306 righe totali, non le ~156 stimate all'apertura dell'audit — la
> stima copriva solo il codice, non anche i test). 3.7: knip ri-eseguito **dopo** la
> rimozione dei barrel morti (3.1) ha confermato **9** bandiere davvero orfane, non le 8
> stimate — `isCurrenciesLoaded` è viva ed è stata tenuta; una delle 9,
> `isLoggedIn`, non è nemmeno una bandiera di caricamento ma un predicato di
> autenticazione finito nell'elenco per somiglianza di nome — rimovibile perché
> `isAuthenticated = derived(auth, $auth.user !== null)` codifica già la stessa cosa
> (`routes/(app)/+layout.svelte:97,112`). Bonus nella stessa rimozione:
> `getConfiguredCurrencies` in `fxRoutesStore.ts`, superata da
> `getConfiguredCurrencySet()`/`getConfiguredPairSlugs()`, che sono ciò che i
> consumatori reali usano. 3.8 resta aperta: la lavorazione è in corso in un ciclo
> parallelo, non confermata chiusa da questa esecuzione.

> ### 3.1 va prima di tutto il resto del frontend
>
> Finché i 12 barrel morti esistono, **l'analisi del codice morto sul frontend non è
> attendibile**: stanno tenendo artificialmente in vita simboli che nessuno usa davvero.
> Rimuoverli e **rieseguire knip** cambierà l'elenco degli orfani — probabilmente in
> aumento. Qualunque decisione presa sugli orfani frontend *prima* di questo passo va
> considerata provvisoria.
>
> **Confermato il 2026-08-05**: la previsione era esatta. Rimossi i 12 barrel e
> rieseguito knip, l'elenco è cambiato in aumento su più di un fronte — le bandiere di
> caricamento di 3.7 sono risultate 12 esportate invece delle 8 stimate, e due
> componenti (`FxProviderConfig.svelte`, `LiveTicker.svelte`) sono passati da "orfani da
> discutere" (S4/S5) a "assorbimento tracciato" nello stesso passaggio. Vedi
> [15](15_esecuzione_s1_s3.md).

> ### 3.9 è l'eccezione che dimostra la regola dei due assi
>
> È una `git rm` — l'azione più atomica che esista — ma è l'unica rimozione dell'intera
> lista classificata a **rischio medio**. La logica FIFO è stata riassorbita
> dall'engine, ma i **casi limite** non sono stati verificati uno per uno. Un errore qui
> non produce un'eccezione: produce un **costo di carico sbagliato**, cioè un numero
> plausibile ma falso in un portafoglio reale.
>
> Appartiene a S3 per complessità e a S4 per prerequisito.

---

## S4 — Da misurare prima

*Non sappiamo ancora se c'è qualcosa da fare. Il lavoro qui **è** la misura. Trattarli come
interventi di codice significa decidere a caso.*

### Prerequisiti di release

| # | Cosa misurare | Perché adesso |
|---|---|---|
| 4.1 | **Eseguire `002_identifier_other_json_list.py` su un DB 1.0.1 reale** | È l'**unica migrazione che toccherà installazioni esistenti**. Vale più di qualunque pulizia stilistica di questo backlog |
| 4.2 | Verificare i casi limite FIFO sull'engine | Sblocca 3.9 |

### Possibili difetti latenti

| # | Cosa misurare | Sospetto |
|---|---|---|
| 4.3 | Crescita della cache degli store per asset | `removeAssetPriceStore`, `invalidateCurrencyGraph`, `destroyPriceProcessingPool` non sono **mai chiamate**: creazione e lettura funzionano, la rimozione no → possibile **crescita monotona della memoria** |
| 4.4 | Verificare i 38 candidati N+1, in ordine di N atteso, partendo da `asset_source.py:4034` (7 query per elemento), `portfolio_api.py:49`, `fx.py:984` | Il candidato 1 è il **miglior rapporto valore/costo dell'audit**: poche righe, effetto misurabile sulla latenza degli endpoint bulk |
| 4.5 | ✅ **fatto, fuori banda** — Verificare `FxProviderConfig.svelte` (314 righe): esiste ancora una vista d'insieme delle rotte FX con priorità, o è una **regressione**? | Il file è orfano ma descrive una funzionalità che dovrebbe esistere |
| 4.6 | Tracciare `uploadBrimFile` e `downloadFxBackup` | Orfani secondo knip, ma sono percorsi utente |

> **4.5 si è chiusa da sola durante l'esecuzione S1–S3, non era nella banda assegnata.**
> Non era una regressione: `FxProviderConfig.svelte` è assorbito da `FxPairAddModal` in
> `editMode` → `FxProviderSelect.svelte`, costruito sullo stesso primitivo
> `OrderableList` e con in più il pathfinding/ricerca DFS (un superset). La pagina stessa
> lo documenta in `fx/[pair]/+page.svelte:11`: *"Provider Config: via modal (not inline
> panel)"*. La misura non era più necessaria: bastava tracciare l'assorbimento, cosa
> impossibile finché i barrel morti (3.1) confondevano il grafo delle dipendenze. Vedi
> [15](15_esecuzione_s1_s3.md).

### Accertamenti che possono ridimensionare il backlog

| # | Cosa misurare | Effetto potenziale |
|---|---|---|
| 4.7 | Campionare i **43 tipi orfani** frontend contro `generated.ts` | Se duplicano lo schema generato, il problema non è che sono inutilizzati: è che **esistono** |
| 4.8 | Campionare i **32 tipi orfani** dei componenti | Idem |
| 4.9 | Misurare la copertura frontend dopo il merge AI Export, incrociandola con knip | Codice morto frontend ad alta confidenza |

### Salute della suite

| # | Intervento | Costo |
|---|---|---|
| 4.10 | Rendere idempotente l'inserimento FX in `test_lots_analysis_service.py` (upsert o fixture di cleanup) — elimina un flaky **order-dependent** | 20 min |
| 4.11 | Configurare `COVERAGE_PROCESS_START` per vedere `spawn_worker.py` — rimuove **32 falsi 0 %** permanenti | 45 min |
| 4.12 | Test per `build_history_sync_entry` (29 stmt, 0 %) e per `_infer_country_from_issuer` / `_infer_sector` (euristiche che sbagliano **in silenzio**) | 1 h |

---

## S5 — Decisione di prodotto

*Il codice qui non ha difetti evidenti. La domanda non è "come si scrive", è **"lo
vogliamo?"** — e non può rispondere chi scrive il codice.*

Questa è la sezione che l'audit ha isolato applicando la regola concordata: *se la logica di
un simbolo morto non è stata riassorbita, non si rimuove — si discute.*

### Con potenziale impatto sui dati degli utenti

| # | Decisione | Posta in gioco |
|---|---|---|
| 5.1 | **`merge_other_identifiers`** — requisito reale o abbandonato? | La semantica di import **additiva** non è applicata da nessuna parte: in produzione gli identificativi vengono **sostituiti**. Copertura **0 %**: mai eseguita, né in produzione né nei test. Se il requisito è reale, questo è un **difetto funzionale**, non codice morto |
| 5.2 | ⏳ **esclusa, da discutere** — `base_currency` vs `default_currency` — quale è la chiave vera? | La chiave `"base_currency"` **non esiste** fra i global settings: la valuta base configurata è silenziosamente ignorata e si usa sempre `"EUR"`. È un bug, ma la correzione dipende da quale delle due semantiche è quella voluta. 3 call site da allineare |

> **5.2 è la stessa riga di 2.2** — il backlog la elenca due volte sotto tier di
> complessità diversi. Vedi la nota completa a 2.2 in S2: tre problemi distinti nella
> stessa chiamata, esclusa deliberatamente da questo ciclo perché l'utente vuole
> discuterla a parte.

### Funzionalità complete ma non esposte

| # | Decisione | Cosa c'è già |
|---|---|---|
| 5.3 | `compute_wac_iterative_multi_broker` — cablare o rimuovere | Posizione unificata cross-broker, **completa e testata**, cablata a nulla. `compute_wac_iterative` lavora su un solo broker |
| 5.4 | `AssetMetadataService` (3 metodi) — cablare il diff o rimuovere | Diff campo-per-campo per audit. Oggi la classificazione di un asset si aggiorna **senza storico** |
| 5.5 | `cache_utils` (3 funzioni) — endpoint admin o rimuovere | Non esiste alcun endpoint di gestione cache: oggi l'unico modo per invalidarne una è **riavviare il servizio** |
| 5.6 | ✅ **fatto, fuori banda** — `LiveTicker.svelte` (233 righe) — ripristinare o rimuovere | La striscia prezzi in tempo reale **non esiste più** nell'interfaccia, ma **tre commenti** nel codice la descrivono ancora come consumatore attivo. Vanno corretti in entrambi i casi |
| 5.7 | `require_email_verification` — implementare o togliere dalla UI | Come 2.4: la UI promette qualcosa che il sistema non fa |

> **5.6 si è chiusa da sola durante l'esecuzione S1–S3, non era nella banda assegnata.**
> Non era una decisione di prodotto da prendere: rimosso, perché entrambi i suoi punti
> d'uso documentati si sono allontanati da lui nel tempo — la Dashboard è stata
> ridisegnata nel commit `6c009e6b`, e `AssetPriceSummary.svelte` oggi prende prop
> semplici. La capacità sottostante vive già inline in `assets/+page.svelte` e
> `assets/[id]/+page.svelte`, entrambi con lo stesso `livePriceService.ts`. Anche qui, la
> tracciatura era impossibile finché i barrel morti (3.1) confondevano il grafo. Vedi
> [15](15_esecuzione_s1_s3.md).

### Punti di estensione: documentare invece di rimuovere

| # | Decisione | Nota |
|---|---|---|
| 5.8 | `ensure_rates_multi_source` (`fx.py:399`) | Implementa il routing esplicito per valuta base, che `sync_pairs_bulk` non fa. È l'**impalcatura prevista per il primo provider multi-base**: documentarla come tale, non rimuoverla |
| 5.9 | `get_provider` / `list_plugin_classes` — rimuovere o documentare | Idem |
| 5.10 | `get_version_info` — va esposta con la 1.1.0? | Decisione di release |

### Logica di dominio

| # | Decisione | Perché serve chi conosce il modello |
|---|---|---|
| 5.11 | `txStoreGet*` (4 accessori) | Toccano il modello **main/partner** delle transazioni collegate: logica di dominio, non infrastruttura |
| 5.12 | `removeAssetPriceStore`, `invalidateCurrencyGraph`, `destroyPriceProcessingPool` | Dipende dall'esito di 4.3: se la memoria cresce sono un **difetto**, altrimenti sono ciclo di vita mai richiesto |
| 5.13 | Le 11 property `*_cur` — adottare o rimuovere | 8 costruzioni `Currency(...)` inline le duplicano: è *DRY orfano*, quindi la risposta giusta è quasi certamente **adottare** |
| 5.14 | `availableLanguages`, `currentLanguageFlag`, `currentLanguageName` | Stesso pattern: il selettore lingua ricalcola bandiera e nome per conto proprio |

---

## S6 — Refactor strutturale

*Pianificazione, più sessioni, rischio di regressione reale. Nessuno di questi va infilato in
un ciclo di pulizia generale.*

### Ripristini di contratto — alto valore

| # | Intervento | Perché vale |
|---|---|---|
| 6.1 | Cablare le classi `*Response` come `response_model` sui **17 endpoint** che ne sono privi, poi `./dev.py api sync` | **Il più redditizio della categoria**: ripristina la tipizzazione end-to-end che è la ragione per cui il progetto usa Zodios. Gli schemi sono **già scritti** |
| 6.2 | Esporre `is_chain` via API e togliere il calcolo inline dal frontend; usare `providers_used` in `fx.py:1000,1108` chiarendo la semantica `MANUAL` | Non riduce le righe — le **sposta**. Il guadagno è che la definizione di "catena" torna a esistere in **un posto solo** (oggi è in 5) |

### Riduzione di complessità

| # | Intervento | Complessità attuale |
|---|---|---:|
| 6.3 | Far usare a `build_data_quality_report()` i quattro `aggregate_*` già esistenti | — |
| 6.4 | Estrarre le 3 fasi di `bulk_refresh_prices` in metodi privati | — |
| 6.5 | Far usare `get_asset_provider` ai chiamanti inline | — |
| 6.6 | Ridurre `get_history_value` in `yahoo_finance.py` | 31 |
| 6.7 | Rendere dichiarativa la matrice di `validate_status_matrix`, e valutare lo stesso per i validatori di `schemas/risk.py` | — |
| 6.8 | Pianificare la scomposizione di `execute_batch` | **112** |

> **6.7 va affrontato solo quando quei validatori diventeranno un ostacolo** — per esempio
> all'aggiunta di un nuovo `SignalStatus`. Sono miglioramenti di leggibilità su codice che
> funziona.

### Campagne diffuse

| # | Intervento | Ampiezza |
|---|---|---:|
| 6.9 | Convertire i `TRY400` in `logger.exception` | 53 punti |
| 6.10 | Migrare `BrokerSharingPanel.svelte` alle Runes | 20 `$:` |
| 6.11 | Convertire i 17 `assert` strutturali dell'AI Export in `if ... raise` tipizzati | 17 righe — **🔵 bassa priorità**, vedi [13](13_ai_export.md) M2 |

### Da pianificare a parte, non in un ciclo di pulizia

| # | Intervento | Perché |
|---|---|---|
| 6.12 | Valutare il consolidamento dei due `*settings_service` | Duplicazione strutturale reale, ma tocca configurazione globale |
| 6.13 | Scindere `asset_source.py` (**4 800 righe**) in gestione provider / prezzi / metadata / bulk | Oltre ogni soglia ragionevole, ma è un intervento invasivo |
| 6.14 | ⛔ **Estrarre helper condivisi dai `parse` BRIM** | Vedi sotto |

> ### 6.14 è l'unico intervento che l'audit sconsiglia
>
> La duplicazione fra i parser BRIM è reale e misurabile. Ma i provider BRIM sono la
> superficie che tocca i **dati reali degli utenti**, e un errore di parsing **non si
> manifesta come eccezione**: si manifesta come **transazione importata sbagliata**, che
> nessuno nota finché non guarda un saldo.
>
> Se lo si affronta: **un provider alla volta**, con i test del provider verdi prima e dopo,
> mai come parte di una campagna trasversale.

---

## Dove complessità e rischio divergono

**Questa è la sezione da leggere se se ne legge una sola.** L'ordinamento per complessità è
utile per pianificare, ma è ingannevole nei punti dove il rischio non lo segue.

### Costo minimo, valore massimo

| Intervento | Costo | Perché è il primo di tutti |
|---|---|---|
| **1.1** licenza in `pyproject.toml` | 4 righe | L'unico rischio **legale** dell'audit |
| **4.4** il primo N+1 (`asset_source.py:4034`) | poche righe | Miglior rapporto valore/costo dell'intero audit |

### Azione minima, rischio non minimo

| Intervento | Sembra | È |
|---|---|---|
| **3.9** `git rm fifo_utils.py` | Una cancellazione | Rischio **medio**: un errore non produce un'eccezione, produce un **costo di carico sbagliato** |
| **5.2** `base_currency` | Tre righe da allineare | Cambia quale valuta usa il sistema: va deciso, non corretto d'istinto |
| **5.13 / 5.14** *DRY orfano* | Rimozione di codice morto | Rimuovere **elimina il reperto e lascia la duplicazione**. La mossa giusta è **adottare** |
| **6.14** dedup BRIM | Refactor ordinario | Il fallimento è **silenzioso** e colpisce i dati importati |

### Il caso in cui il linter consiglia male

`AI_EXPORT_DEFAULT_DETAIL_LEVEL` era segnalato come orfano da knip, e la reazione istintiva
sarebbe stata rimuoverlo. Ma il letterale `'standard'` era ridigitato in **cinque punti**:
rimuovere la costante avrebbe cancellato l'unica traccia dell'intenzione e consolidato la
duplicazione.

**Regola generale**: davanti a una costante o a un predicato di una riga segnalati come
orfani, **cercare prima il valore duplicato a mano**. Vedi la sezione *DRY orfano* di
[`INDEX.md`](INDEX.md).

---

## Vincoli di ordine

Non tutto è parallelizzabile. Sei dipendenze reali:

```
4.1 verifica migrazione su DB 1.0.1 ──▶ (prerequisito di release, prima di tutto)

3.1 rimuovere i barrel morti ──▶ rieseguire knip ──▶ 4.7, 4.8, e ogni decisione     [✅ 3.1 + knip fatti]
                                                     sugli orfani frontend

4.2 verifica casi limite FIFO ──▶ 3.9 rimuovere fifo_utils.py

4.3 misura crescita memoria ──▶ 5.12 decidere sui 3 metodi di ciclo di vita

1.2 max-complexity a 25 ──▶ 6.6, 6.8 (altrimenti il linter blocca il lavoro in corso)  [🚫 VOID]

1.5 TRY003 in ignore ──▶ 6.9 conversione TRY400
```

> **Due vincoli aggiornati al 2026-08-05**: il primo ramo (3.1 → knip) è stato
> percorso per intero — i barrel sono stati rimossi e knip rieseguito **dopo**, non
> prima. 4.7 e 4.8 restano da fare, ma ora possono partire da un elenco di orfani
> attendibile invece che gonfiato dai barrel morti. Il vincolo `1.2 → 6.6, 6.8` è invece
> **caduto**: non esiste alcuna configurazione `max-complexity` da alzare a 25, quindi
> 6.6 e 6.8 non sono bloccati da un linter — restano vincolati solo dal giudizio di chi
> li affronta.

---

## Sequenza suggerita

Non è un piano, è un ordine di attacco che rispetta i vincoli qui sopra.

| Sessione | Contenuto | Esito atteso |
|---|---|---|
| **1** — un'ora | ✅ **fatta** — S1 completo + 2.1 → 2.5 | Chiuso il rischio legale, **4 bug su 5**, la violazione Async I/O e l'**unico test rosso** |
| **2** — mezza giornata | ✅ **fatta** — 2.6 → 2.16, poi 3.1 + rieseguire knip | Pulizia a rischio nullo; elenco orfani frontend finalmente **attendibile** |
| **3** — prima della release | 4.1, 4.10, 4.11 | Migrazione verificata su installazione reale, suite senza flaky, copertura senza falsi 0 % |
| **4** — misure | 4.3 → 4.9 | Si scopre **quanto backlog era reale**: 4.7 e 4.8 possono cancellare 75 voci o promuoverle a S6 |
| **5** — con te | Tutto S5 | 14 decisioni. 5.1 e 5.2 per prime: sono le uniche che toccano i dati |
| **6** — dopo le decisioni | ✅ **S3 residuo anticipato ed eseguito** (tranne 3.8, 3.9) + 6.1, 6.2 ancora aperti | Rimozioni sbloccate; tipizzazione end-to-end ripristinata |
| **7+** — pianificato | Il resto di S6 | Una voce per volta, mai in campagna |

> **Nota di esecuzione**: la Sessione 6 era pianificata *dopo* le decisioni S5, perché
> quasi tutto S3 sembrava logicamente a valle. Rileggendo i vincoli, in realtà **solo
> 3.9** dipende da una voce non-S3 (4.2); il resto di S3 non dipendeva da nessuna
> decisione S5. L'esecuzione lo ha quindi anticipato ed eseguito insieme a S1+S2, senza
> violare alcun vincolo — 6.1 e 6.2 (voci S6 vere e proprie) restano intatti e aperti.

---

## Nota finale

La lettura per sottosistema e la lettura per complessità danno due impressioni molto
diverse dello stesso lavoro.

Per sottosistema il progetto sembra avere **86 cose da fare**. Per complessità ne ha
**21 che si chiudono in poco più di una giornata senza decidere nulla** (S1+S2), **12 che
non sono lavoro di codice ma di misura** (S4) — e fra queste ce ne sono due, 4.7 e 4.8, che
possono **cancellare 75 voci del backlog o riscriverle da capo**.

Il resto è materiale per una discussione (S5) o per una pianificazione (S6), e nessuna delle
due cose si fa aprendo un editor.

> **Aggiornamento 2026-08-05**: quella era la fotografia a fine audit. Da allora S1+S2
> sono state eseguite per intero tranne 3 voci deliberatamente lasciate aperte (1.2 si è
> rivelata nulla, 1.5 e 2.2 restano da decidere), e l'intero S3 è stato anticipato ed
> eseguito con loro tranne 3.8 (lavorazione parallela) e 3.9 (bloccata su 4.2). Delle 70
> voci residue all'apertura dell'audit, **42 restano aperte** oggi — nessuna di codice
> meccanico: solo misure (S4), decisioni di prodotto (S5) e refactor pianificati (S6),
> più le 4 eccezioni appena elencate (1.5, 2.2, 3.8, 3.9 — 1.2 non è fra queste perché è
> nulla, non aperta). Il numero corretto è lo stesso della Sintesi in apertura di questo
> report (70 − 25 − 2 − 1 = 42); una versione precedente di questa nota riportava 44,
> un errore aritmetico per aver dimenticato di sottrarre le 2 chiusure fuori banda (4.5,
> 5.6) — corretto qui. Dettaglio in [15 — Esecuzione S1–S3](15_esecuzione_s1_s3.md).

---

*Report 14 di 16 — sintesi trasversale. Torna a [`INDEX.md`](INDEX.md) ·
prosegue in [15 — Esecuzione S1–S3](15_esecuzione_s1_s3.md).*
