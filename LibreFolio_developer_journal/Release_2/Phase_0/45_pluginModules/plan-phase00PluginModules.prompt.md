# U · Plugin modulari e traduzioni per sottosistema

> - **Workstream**: U, coordinato dal «Coordinatore release 2» (`c8328a01-f208-4ade-a352-0486d1f14de2`).
> - **Worktree**: `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-cautious-umbrella`, ramo `e-alfy-u-plugin-modulari-e-traduzioni`.
> - **Base d'esecuzione**: HEAD `c3b33a8fb605d28331a9fad30c52be1a7daa1ce4` (treno 55) ✔, verificata al passo U-0. Da
>   `f0f3de0d9`, su cui è stata scritta l'analisi, entrano solo doc (wiki di W, pagina Scalable di M, una riga del
>   CHANGELOG): nessuna delle superfici di U.
> - **Corsia**: porta `6174`, dati `/tmp/librefolio-r2-u-plugins`, un comando alla volta.
> - **Stato**: IN ESECUZIONE dal 12/10. Un checkpoint FROZEN per passo; i commit li fa il coordinatore.
> - **Storia**: v1 (12/10, su `784b35766`) superata. La v2 recepisce le decisioni del developer del 12/10: D-1
>   (`plugin.py`), D-4 (ripiego in build, audit severo); D-2, D-3 e D-7 accettate; D-5 e D-6 sostituite dalla divisione per
>   sottosistema.

### Il via del developer (12/10, relayato dal coordinatore, testuale)

- **D-A**, la mappa: «La mappa così com'è».
- **D-B**: «le traduzioni di sistemi core in frontend è il punto corretto, mentre per i plugin e il resto le metterei nelle
  cartelle dei plugin come detto».
  - I 17 sottosistemi e la `base` stanno in `frontend/src/lib/i18n/<x>/`.
  - I frammenti dei plugin stanno nelle cartelle dei plugin.
- **D-C**: «Sì, procedi: nessuna rinomina di chiavi, tag verso il 19–20/10».
- **Scelte del coordinatore, approvate**:
  - i `prefixes.txt`;
  - il file singolo solo per le fixture e i test dei registri;
  - `_safe_filename` → `<plugin>/plugin.py`, con `schemas/tools.py:319` e `api sync` nello stesso passo; il client
    generato va elencato nel checkpoint;
  - `absorb`;
  - la compatibilità con Python 3.9.
- **Ordine**: U-1 e U-2 subito. U-3 (`split`) solo dopo il via del coordinatore, quando saranno entrate le chiavi di I
  (M-17, il pannello di sicurezza, il CHANGELOG localizzato).

## 0. La richiesta e le decisioni già prese

- **Plugin**: ogni plugin è una cartella col suo Python e le sue traduzioni; le traduzioni si uniscono a build time.
- **Sottosistemi** (developer, 12/10): «oltre che nei plugin, anche nella traduzione "base" creerei vari file, uno per ogni
  sotto sistema importante, lasciando il base attuale solo le cose common o comunque le chiavi generaliste/generiche […]
  L'obiettivo è splittare il più possibile ora che ci sono pochi agenti al lavoro».
- **D-1, decisa dal coordinatore su delega**: `__init__.py` con la sola docstring e nessun re-export; il codice in
  `<plugin>/plugin.py`, nome fisso, caricato per convenzione; gli helper accanto (`_*.py`); import e `patch()` riscritti
  nella stessa rinomina, così una patch dimenticata fallisce in rosso. In backlog il limite dei plugin montati a runtime.
- **D-4**: in build una lingua mancante ripiega sull'inglese con un avviso; l'audit del repo resta severo.
- **D-2, D-3, D-7**: il file unito resta al percorso di oggi, generato e ignorato; ogni ingresso lo genera; icone e
  `sample_reports/` restano dove sono.

## 1. Stato reale (su `f0f3de0d9`)

Invariato rispetto alla v1, che resta il riferimento dettagliato (§1.1–1.7). In sintesi:

- **84 plugin** (BRIM 33, asset 6, FX 6, rischio 15, segnali 23, tools 1); scoperta unica `provider_registry.py:135-170`
  (`glob("*.py")`, `spec_from_file_location`); ordine di registrazione = ordine dei nomi, identico passando a cartelle.
- **Catalogo**: 4 349 chiavi × 4 lingue, 46 namespace di primo livello, impaginazione identica nelle 4 lingue.
- **Lettori dal disco**: 53 file (38 Vitest, 5 E2E, 6 test backend, script); restano invariati con il file unito al
  percorso di oggi, tranne i 6 test backend.
- **Docker** non builda il frontend: la fusione è in `dev.py front build`.
- **Trappole**: `scripts/docs_links.py:238` (`check-links` passerebbe senza controllare niente), `test_brim_providers.py:5961`,
  `optionFilter.test.ts:205-218`, `pac_allocator.py:69` (`parents[3]`).

### 1.1 Gli usi dei namespace nel codice (base della mappa)

Ogni namespace è già usato quasi solo dall'area del suo nome (scansione dei letterali e dei template in `frontend/src`):
`tools` da `features/tools` (44 file), `risk` da `components/risk` (35), `importWizard` da `components/transactions`,
`brokers` da `components/brokers`, `onboarding` da `features/onboarding`, `aiExport` da `features/ai-export`… I namespace
trasversali sono il vocabolario generico: `common` (in 9 aree), `datePicker`, `dataEditor`, `table`, `filter`, `sectors`,
`prices`, `header`, `nav`. Log: `files/ns_usage.log`.

### 1.2 Dove vivono i testi degli errori

330 chiavi d'errore, avviso o problema. **Non c'è un `errors.*` globale**: stanno già nel namespace del loro sottosistema.

| Gruppo | Chiavi | Chi le produce |
|---|---|---|
| `tools.pacAllocator.planner.issues` / `.problems` / `.result.failure` / `.source.errors` | 81 / 40 / 9 / 2 | motore del PAC |
| `transactions.errors` | 38 | validazione delle transazioni (backend, `message_i18n_key`) |
| `risk.warnings` / `risk.errors` | 35 / 19 | analytic e `RiskErrorCode` |
| `dataQuality.*` | 35 | qualità dei dati (backend, banner in 4 aree) |
| `importWizard.*.warning|error` | 17 | wizard di import |
| `tools.errors` | 12 | piattaforma tools |
| `csvImport.errors` | 11 | import CSV generico degli editor |
| `providerErrors.*` | 10 | errori dei provider di prezzo (solo `components/assets/resolveProviderError.ts`) |
| `onboarding.errors` | 7 | onboarding |
| `error.*`, `common.error` | 6 + 1 | pagina d'errore dell'app |

Nel vocabolario generico ce ne sono 18 (`csvImport.errors` 11, `error.*` 6, `common.error`), ma sono generici davvero.
**Senza rinomine** ogni gruppo finisce nel file del suo sottosistema, perché un sottosistema può dichiarare più
namespace (§2.3): `providerErrors` va negli asset, `dataQuality` in un file suo. **Rinomine necessarie: zero.** Una sola
sarebbe cosmetica: `providerErrors` → `assets.providerErrors`, 10 chiavi e 3 file (`resolveProviderError.ts`, il suo test,
un test backend). La sconsiglio; `dataQuality` costerebbe ~25 file.

### 1.3 I riferimenti ai moduli dei plugin (conteggio AST)

Con `<plugin>/plugin.py` il modulo diventa `backend.app.services.<famiglia>.<plugin>.plugin`. Da riscrivere:

- **80** `from backend.app.services.<famiglia>.<plugin> import X`, in 31 file di test;
- **27** `from backend.app.services.<famiglia> import <plugin> [as mod]`: importano il **modulo** per `patch.object` e
  `monkeypatch`. Sono i più insidiosi, perché dopo la mossa importerebbero il pacchetto vuoto;
- **4** stringhe: il logger `tool_plugins.pac_allocator` (`test_pac_planner_tool_api.py:469`), i due `PLUGIN_MODULE`
  (`test_brim_danske_bank.py:63`, `test_brim_degiro.py:73`), il `__module__` (`test_signal_registry.py:668`);
- **1** import nell'app: `api/v1/fx.py:71` (`fx_providers.manual`).

Totale **112 modifiche in 32 file**. I plugin non si importano fra loro; i loro helper restano alla radice della famiglia
(`_brim_io`, `_brim_output`, `_scalable`, `signal_plugins/base.py`), quindi gli import interni non cambiano. Log:
`files/pkg_imports.log`.

Altri punti, oltre al §1:

- `_safe_filename()` (`tools/registry.py:60`) scriverebbe «plugin.py» per ogni tool: diventa `<plugin>/plugin.py`. Serve
  allargare il pattern a `/`, che oggi è `^[A-Za-z0-9_.-]+$` (`schemas/tools.py:319`, `_MODULE_STEM_PATTERN` `:25`).
  L'allargamento è compatibile; poi un `api sync`.
- Il comando di debug di `snb` diventa `python -m …fx_providers.snb.plugin` (solo il commento).

## 2. Il disegno

### 2.1 Il plugin

```text
backend/app/services/brim_providers/
    _brim_io.py, _brim_output.py, _scalable.py   helper della famiglia, invariati
    static/, sample_reports/                     invariati
    broker_directa/
        __init__.py                              solo docstring
        plugin.py                                = broker_directa.py (git mv, rinomina al 100 %)
        _parsing.py …                            helper del plugin, quando servono
        i18n/en.json it.json fr.json es.json      {"brimPlugins": {"broker_directa": {"name": …, "description": …}}}
```

**Scoperta**: una cartella con `plugin.py` si carica come `<namespace>.<cartella>.plugin`; il pacchetto prima, con
`submodule_search_locations`, così gli import relativi funzionano. Il file singolo resta accettato per le fixture e i
test dei registri (`fixtures/signal_plugins/`, `test_signal_registry.py`, `test_provider_registry_misc.py`,
`test_tools_registry.py`), che così non cambiano. Ordine per nome; filtri `_*` e stem ignorati come oggi.

**Due guardie** (test-author):

- **convenzione**: nelle 6 famiglie di prima parte nessun plugin a file singolo, nessun `__init__.py` con codice, nessuna
  cartella senza `plugin.py`;
- **import**: in app, test e script nessun `from <famiglia> import <plugin>` e nessun `<famiglia>.<plugin>.<nome>` senza
  `.plugin`. È la garanzia del «rosso» estesa agli import di modulo.

### 2.2 Il catalogo

```text
frontend/src/lib/i18n/
    base/{en,it,fr,es}.json            vocabolario generico (288 chiavi)
    <sottosistema>/{en,it,fr,es}.json  uno per sottosistema (17 cartelle, §2.4)
    <sottosistema>/prefixes.txt        i prefissi dichiarati, uno per riga
    {en,it,fr,es}.json                 GENERATI = base ⊕ sottosistemi ⊕ frammenti dei plugin; ignorati, sola lettura
    .generated                         stamp sha256 (non .json, i gate che fanno readdir non lo vedono)
    index.ts                           invariato
```

- Un'unica implementazione, `scripts/i18n_catalog.py`. Usa solo la stdlib ed è **compatibile con Python 3.9**, perché gli
  hook npm la chiamano con il `python3` di sistema, che sul Mac può essere il 3.9 di Apple: niente `tomllib`, manifest in
  testo semplice.
- Sorgenti: `base/`, le cartelle dei sottosistemi e i frammenti `i18n/` dei plugin (`*_providers/*/i18n`, `*_plugins/*/i18n`).
- **Ripiego (D-4)**: in build, una lingua o una chiave mancante in un frammento si riempie con l'inglese e stampa un avviso;
  l'inglese è obbligatorio. `dev.py i18n check --strict` (audit e gate) fallisce invece su qualunque sorgente del repo che
  non abbia le 4 lingue con chiavi identiche.
- **Guardia**: un file generato modificato a mano ferma la build e dice dove spostare la modifica. Si scrive solo se il
  contenuto cambia.

### 2.3 La proprietà delle chiavi

**Regola**: ogni chiave vive nel sorgente indicato dal **prefisso dichiarato più lungo**.

- I sottosistemi dichiarano i loro prefissi in `prefixes.txt`.
- La `base` non dichiara niente: prende tutto il resto.
- I frammenti dei plugin possiedono le **chiavi esatte** che contengono, e vincono sui prefissi dei sottosistemi. Per
  esempio `risk.analytics.stress.*` sta nel plugin, il resto di `risk.*` nel sottosistema `risk`.
- Il gate backend controlla che quelle chiavi stiano nello spazio dei nomi del plugin: BRIM `brimPlugins.<cartella>`, asset
  `assets.providerParams.<code>`, segnali il namespace di `display_name_key`, rischio e tools quello di `name_i18n_key`.

**Gate**:

- **PURE**, `utils gate-i18n-catalog`:
  - nessuna chiave in due sorgenti, né foglia contro ramo;
  - nessun prefisso dichiarato da due sottosistemi;
  - ogni chiave nel file che la regola indica, altrimenti è «fuori posto» e il messaggio dice dove va;
  - 4 lingue identiche per sorgente;
  - lo stamp.
- **Backend**: le chiavi dei frammenti stanno nello spazio dichiarato dal plugin; nessuna chiave di plugin altrove.

**Dove scrive `dev.py i18n add`** una chiave nuova:

1. se tutte le chiavi sotto il suo antenato esistente più profondo stanno in un solo frammento di plugin, lì;
2. altrimenti nel sottosistema col prefisso più lungo;
3. altrimenti in `base`, con un avviso: «namespace nuovo in base: è generico? altrimenti `--into`».

`--into <cartella>` crea un sottosistema o il frammento di un plugin nuovo. Sotto un antenato diviso fra più plugin, come
`risk.analytics.*`, chiede `--into`. Il comando stampa sempre il file in cui ha scritto.

Altri comandi:

- `move PREFISSO --into` sposta un sottoalbero nelle 4 lingue;
- `split` applica i `prefixes.txt` ed è rieseguibile;
- `absorb --base REV --theirs REV` (§5);
- `check [--strict] [--against REV]`;
- `audit`, `search`, `tree` e i duplicati lavorano sulla vista unita e mostrano il sorgente di ogni chiave.

### 2.4 La mappa dei sottosistemi

Criterio: un sottosistema per ogni area di prodotto con codice proprio. Conteggi dopo aver tolto le chiavi dei plugin.

| Cartella | Prefissi dichiarati | Chiavi |
|---|---|---|
| `pacAllocator` | `tools.pacAllocator` | 813 |
| `risk` | `risk` | 452 |
| `importWizard` | `importWizard` | 449 |
| `assets` | `assets`, `assetDetail`, `providerErrors`, `events` | 316 |
| `brokers` | `brokers` | 274 |
| `transactions` | `transactions` | 253 |
| `onboarding` | `onboarding` | 200 |
| `settings` | `settings` | 199 |
| `aiExport` | `aiExport` | 166 |
| `charts` | `chartSettings`, `chart`, `measure`, `signals` | 163 |
| `dashboard` | `dashboard` | 146 |
| `tools` | `tools` | 102 |
| `fx` | `fx`, `fxDetail` | 83 |
| `files` | `uploads`, `fileStatus`, `files` | 74 |
| `app` (guscio: about, supporto, changelog, aggiornamenti, sicurezza della connessione) | `changelog`, `support`, `updateCheck`, `donationPopup`, `help`, `connectionSecurity` | 71 |
| `auth` | `auth` | 46 |
| `dataQuality` | `dataQuality` | 35 |
| **`base`** | — (`common` 119, `datePicker` 44, `csvImport` 31, `dataEditor` 21, `sectors` 16, `table` 10, `import` 9, `prices` 7, `assetPicker` 7, `error` 6, `header` 6, `filter` 4, `sharedResource` 4, `nav` 2, `date` 2) | 288 |
| **plugin** | 71 frammenti (BRIM 66, segnali 112, rischio 31, asset 8, tools 2) | 219 |

Somma: 4 349 ✓. La base scende al 6,6 % del catalogo di oggi; il file più grande è il PAC (813).

### 2.5 Centrali o accanto al codice

| | **Centrali** `lib/i18n/<sottosistema>/` (raccomandato ora) | Accanto al codice `lib/features/<x>/i18n/` |
|---|---|---|
| Dove sono | un posto solo, facile da scorrere e da indicare agli agenti | vicino al codice che le usa, come i plugin |
| Copertura oggi | tutti i 17 | solo 5 feature esistono (`ai-export`, `changelog`, `onboarding`, `tools`, `update-check`); brokers, transazioni, asset, rischio, dashboard e settings sono sparsi fra `components/`, `routes/` e `stores/` |
| Futuro | quando T-FE crea le cartelle di feature (post-1.2), `git mv` della cartella più un glob: i prefissi non cambiano | si sposterebbero di nuovo con T-FE |
| Strumenti | una radice | più radici |

Raccomandazione: centrali ora. Il formato è identico, quindi spostarli accanto al codice resterà una rinomina.

### 2.6 Come si combinano coi plugin

Un unico generatore, un'unica regola: i frammenti dei plugin ritagliano chiavi esatte dentro i namespace dei
sottosistemi (`risk.analytics.*` dentro `risk`, `signals.<ns>` dentro `charts`, `assets.providerParams.borsa_italiana`
dentro `assets`, `tools.pacAllocator.{name,description}` dentro `pacAllocator`); `brimPlugins` non ha sottosistema.

## 3. Superfici da aggiornare

| Area | File | Passo |
|---|---|---|
| Plugin | 84 `git mv x.py x/plugin.py` + 84 `__init__.py` (docstring); scoperta in `provider_registry.py`; `_safe_filename` e pattern in `schemas/tools.py:319` (+ `api sync`); `pac_allocator/plugin.py:69` → `parents[4]` | U-1 |
| Riferimenti | 112 modifiche in 32 file (§1.3); glob: `docs_links.py:238`, `test_brim_providers.py:5961`, `optionFilter.test.ts:205-218`; commenti con percorsi (7 frontend, 2 runner, `snb`) | U-1 |
| Docstring | `fx.py:68,105` (BU2 è entrato), `brim_provider.py` (`:11`, `:125`, `:294`), `asset_sources/core.py:447`, gli `__init__.py` delle famiglie | U-1 |
| Catalogo | `scripts/i18n_catalog.py` (nuovo); i 4 cataloghi in `base/` (rinomina pura); `frontend/.gitignore`; `frontend/package.json` (`predev`, `prebuild`, `precheck`); `frontend/vitest.config.ts` + `globalSetup` | U-2 |
| CLI | `frontend/scripts/i18n-audit.py` (lettura, scrittura per proprietario, `build`, `move`, `split`, `absorb`, `check`); `dev.py` (`cmd_fe_build`, `cmd_fe_check`, `cmd_fe_dev`); `scripts/cli_base.py` (staleness: sorgenti e frammenti) | U-2 |
| Test | 6 lettori backend → `load_catalog()`; gate PURE `utils gate-i18n-catalog`; gate backend di proprietà; guardie del §2.1; caso cartella in `test_docs_links_gate.py`; registrazione in `_backend_utils.py` | U-1…U-3 |
| Diagnostica | `diagnostics/ai_export_real_prompt_probe.py`: `build()` prima del bridge | U-2 |
| Divisione | 17 `prefixes.txt` e `dev.py i18n split`; 71 frammenti di plugin | U-3 |
| Doc EN | `developer/frontend/i18n.md` (riscritta: sorgenti, regola, comandi, ripiego); `patterns/registry_pattern.md`; guide dei plugin `brim`, `asset`, `fx`, `signal`, `tool_plugins.en`; `backend/risk/architecture.md`; le pagine con i percorsi della v1; nota sul limite dei plugin montati a runtime | U-4 (docs-writer) |
| `.github` | `frontend.instructions.md` (i18n); `backend-providers-{asset,brim,fx}`; `backend-{risk,signals,tools}`; skill `brim-plugin`, `asset-plugin`, `tool-plugin`, `signal-plugin`, `risk-plugin`, `devpy-i18n`, `devpy`; `agents/project-historian.agent.md` | U-4 |
| Fuori da U | `day-count.{en,it,fr,es}.md:10` (M); devWiki 84 citazioni in 47 pagine (historian); `TODO_FUTURI.md` | backlog |

## 4. Conteggi

- **Python**: 84 file spostati, 84 `__init__.py` nuovi, **112 modifiche in 32 file**, più 4 consumatori di glob e la
  scoperta.
- **Catalogo**: 4 349 chiavi per lingua divise in `base` (288) + 17 sottosistemi (3 842) + 71 frammenti di plugin (219).
  Sono 89 sorgenti × 4 lingue = 356 file JSON, più 17 `prefixes.txt`. Rinomine di chiavi: zero.
- **Lettori**: 53 invariati, 6 test backend all'helper.

## 5. Conflitti con chi aggiunge chiavi

Con la divisione in molti file, git non riconosce più la rinomina di `en.json`: il pezzo più grande è sotto il 50 %. Un
ramo che modifica il vecchio `en.json` dà quindi un conflitto «modificato/cancellato», non un merge automatico. Tre misure.

1. **Ordine**:
   - la divisione (U-3) è prodotta da `dev.py i18n split` a partire dai `prefixes.txt`, quindi si rifà in pochi minuti su
     qualunque base;
   - si fa entrare **prima** ciò che I e M hanno già sui cataloghi: M-17 («Last updated:», che finirà in `settings`), il
     CHANGELOG localizzato (`changelog.*`, in `app`), il resto di I (grafici in `dashboard`/`charts`, `connectionSecurity`
     in `app`);
   - poi il coordinatore porta U sulla base nuova e U rifà `split` e la prova di equivalenza. Nessun conflitto da
     risolvere a mano.
2. **Dopo** (rami ancora sul layout vecchio): `dev.py i18n absorb --base <merge-base> --theirs <commit>` legge con
   `git show` i due cataloghi monolitici e porta il loro delta (aggiunte, modifiche, rimozioni, lingua per lingua) nei file
   proprietari, con la stessa regola di `add`. Il conflitto si risolve tenendo cancellato il vecchio `en.json` e lanciando
   `absorb`; `check --against <commit>` prova che non si è perso niente. Lo fa U quando risolve i merge, oppure chi
   possiede il ramo.
3. **Avviso**, appena U-3 entra, a I, M e V:
   - le chiavi si aggiungono con `dev.py i18n add`, che sceglie il file da sé;
   - `lib/i18n/<lang>.json` è generato e in sola lettura;
   - la mappa è nei `prefixes.txt`.

M-18 (`toFixed` → `formatPercent`) è solo codice e non tocca i cataloghi. V non tocca i cataloghi: `fixtures/i18n-data.ts`
legge il file generato, quindi resta invariato. Se M deve toccare `dev.py`, passa dal coordinatore.

## 6. Piano d'esecuzione

Ogni passo è un checkpoint FROZEN; i commit li fa il coordinatore.

| Passo | Contenuto | Gate |
|---|---|---|
| **U-0** | piano nel journal; base: `all-backend` sulla 6174, tutte le azioni Vitest, `front check`, `front build` (oggetti dei chunk delle 4 lingue), `i18n audit`, conteggio dei riferimenti di `check-links`, ruff/black/dead-code, hash di `api sync` | — |
| **U-1** «refactor(plugins): one folder per plugin» | 84 rinomine + `__init__.py` + scoperta + 112 riscritture + glob + `_safe_filename` + docstring + guardie | `all-backend` identico per invocazione (più i nuovi test); `front-utility core-unit`; `gate-docs-links` e conteggio `check-links` uguale; ruff, black, dead-code uguali; `api sync` con la sola differenza del pattern; ordine dei 6 registri uguale; `git log --follow` su 3 campioni |
| **U-2** «feat(i18n): catalogue built from sources» | libreria, inneschi, CLI, cataloghi in `base/` (rinomina pura), 6 lettori, gate PURE | generato = base; tutte le Vitest; `front check` uguale; build con chunk uguali; `i18n audit` uguale (0 mancanti, 0 morte, 3 non verificate); `gate-i18n-catalog`, `gate-i18n-usage`, `dev-cli-image` |
| **U-3** «refactor(i18n): one catalogue per subsystem and plugin» | 17 `prefixes.txt`, `split`, gate di proprietà | **prova di equivalenza su tutti i file**; `check --strict`; proprietà; `signal-plugin-matrix`, `risk-all`, `external brim-providers`; Vitest; chunk e audit uguali |
| **U-4** «docs: plugin folders and translation sources» | doc developer (docs-writer), istruzioni, skill | `mkdocs build`, `check-links`, `check_source_paths.py` |
| **U-5** | gate finali e handoff | `all-backend`; Vitest; `front check`; build; E2E mirati (`front-utility auth` per il cambio lingua, segnali in `front-asset`, select dei plugin in `front-broker`); porta libera |

**Prova di equivalenza**, su tutti i file:

- per ogni lingua, `flatten(git show <base>:frontend/src/lib/i18n/<lang>.json)` == `flatten(load_catalog(lang))`, chiavi e
  valori;
- ogni sorgente contiene solo chiavi della base, con gli stessi valori, e la loro unione è disgiunta e completa;
- gli oggetti dei chunk di lingua della build sono uguali a U-0;
- si ripete a ogni nuova base; resta come `dev.py i18n check --against <rev>`.

**Fatto quando**:

- gli 84 plugin hanno la forma `cartella/plugin.py` con le due guardie, e l'ordine di registrazione non cambia;
- la base ha 288 chiavi generiche, ci sono 17 sottosistemi con prefissi dichiarati e 71 frammenti di plugin, e nessuna
  chiave è fuori posto;
- il catalogo unito è uguale alla base nelle 4 lingue;
- c'è un generatore solo, chiamato da ogni ingresso, con ripiego e avviso in build e audit severo;
- `dev.py i18n` è completo, compresi `absorb` e `check --against`;
- i gate sono verdi e identici alla base;
- doc, istruzioni e skill sono aggiornate; le voci di backlog sono scritte; la porta 6174 è libera.

**Stima**:

| Passo | Durata |
|---|---|
| U-0 + U-1 | ¾ di giorno (le 112 riscritture, le guardie, due `all-backend` da ~25 min) |
| U-2 | 1½ giorni (prefissi, ripiego, `absorb`, `check --against`) |
| U-3 | ½ giorno |
| U-4 | ¾ di giorno, in parallelo a U-3 |
| U-5 | ½ giorno |

Totale ≈ **4–4½ giorni**: partendo il 13/10, pronto il 16–17/10, e il tag scivolerebbe al 19–20/10, dentro il limite del
22–23/10. Ripiego, se serve: U-1 e U-2 nella 1.2; U-3 si rifà dopo il tag con `split`, che è rieseguibile.

## 7. Le decisioni che restano al developer

| # | Domanda | Raccomandazione |
|---|---|---|
| D-A | La mappa del §2.4: 17 sottosistemi + `base` | approvarla; i punti discutibili sono il PAC separato da `tools`, il gruppo `app` e `dataQuality` in un file suo invece che in `base` |
| D-B | Sottosistemi centrali (`lib/i18n/<x>/`) o accanto al codice | **centrali ora**, accanto al codice con T-FE |
| D-C | Rinomine cosmetiche (`providerErrors` → `assets.providerErrors`, 10 chiavi, 3 file) | **nessuna**: i prefissi dichiarati bastano |

**Le scelte del coordinatore** sono la regola del prefisso più lungo con i `prefixes.txt`, il file singolo accettato solo
per fixture e test, `_safe_filename` con `/` nel pattern, `absorb` e l'ordine di ingresso con I e M (§5).

## 8. Selettori (corsia 6174)

Prefisso: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6174 --data-dir /tmp/librefolio-r2-u-plugins`.

- **Backend**:
  - l'intera suite: `all-backend`;
  - `services`: `provider-registry`, `provider-registry-misc`, `signal-registry`, `signal-plugin-matrix`, `risk-all`,
    `tools-registry`, `brim-provider-base`, `asset-source`;
  - `external`: `brim-providers`, `brim-degiro`, `brim-scalable`, `brim-danske-bank`;
  - `utils`: `gate-i18n-usage`, `gate-docs-links`, `dev-cli-image`, `gate-i18n-catalog` (nuovo).
- **Frontend**:
  - tutte le azioni Vitest: `front-utility core-unit|component-unit|onboarding-component-unit`, `front-ai-export unit`,
    `front-asset asset-unit`, `front-broker broker-unit`, `front-fx fx-unit`, `front-portfolio risk-*-unit`,
    `front-transaction tx-unit`, `front-user user-unit`… (l'elenco esatto a U-0);
  - gli E2E di U-5.
- **Senza porta**: `pipenv run python dev.py front check|front build|i18n audit|mkdocs build|mkdocs check-links|lint`.

## 9. Backlog post-1.2 (sezione U)

- **U-B1 · Traduzioni dei plugin montati a runtime.** Un plugin montato con un volume di docker-compose ha il codice
  caricato ma non le traduzioni, che si uniscono al build, quindi mostra il nome del backend. Servirà un'unione a runtime:
  il backend serve i frammenti, il frontend li aggiunge con `addMessages`.
- **U-B2 · Sottosistemi accanto al codice**, quando T-FE crea le cartelle di feature (`git mv` più un glob).
- **U-B3 · Icone per plugin**: `static/` nella cartella, `uploads.py`, `generate_static_url` nelle 3 basi.
- **U-B4 · `sample_reports/` per plugin**: 25 percorsi E2E e backend.
- **U-B5 · `day-count` × 4 (M); devWiki, 84 citazioni (historian).**

## Appendice A — righe dei plugin (identiche nelle 4 lingue)

- BRIM: blocco `brimPlugins` intero, righe 5519–5652.
- Asset: `assets.providerParams.borsa_italiana`, righe 364–377.
- Rischio: blocco `risk.analytics` intero, righe 3184–3246.
- Tools: righe 4059–4060.
- Segnali:

  | Plugin | Righe | Plugin | Righe |
  |---|---|---|---|
  | `ema` | 2712–2716 | `atr` | 2780–2784 |
  | `sma` | 2717–2721 | `adx` | 2785–2794 |
  | `rsi` | 2722–2731 | `natr` | 2795–2799 |
  | `macd` | 2732–2741 | `aroon` | 2800–2809 |
  | `bollinger` | 2742–2746 | `donchian` | 2810–2814 |
  | `roc` | 2747–2751 | `cci` | 2815–2824 |
  | `stoch_rsi` | 2752–2764 | `obv` | 2825–2829 |
  | `kama` | 2765–2769 | `mfi` | 2830–2839 |
  | `ppo` | 2770–2779 | `drawdown` | 2844–2850 |
  | `rolling_volatility` | 2851–2856 | `rolling_sharpe` | 2863–2868 |
  | `rolling_beta` | 2869–2875 | | |

  `signals.riskRollingReturn`, condiviso da due plugin, va nel sottosistema `charts`.

## 10. Avanzamento

### U-0 — Base (in corso, 12/10)

- ✅ HEAD `c3b33a8fb` verificata; worktree pulita; piano creato in questo file.
- **⚠️ Fuori pista — `all-backend` rossa prima di pytest.**
  - Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6174 --data-dir /tmp/librefolio-r2-u-plugins --log-file /tmp/libreFolio_u0_all_backend.log all-backend`.
  - Fase: avvio del backend condiviso, prima della raccolta dei test. Messaggio: «Shared backend exited during startup (code 1)».
  - Causa: `dev.py server --test` builda il frontend prima di partire (`dev.py:228`) e nella worktree nuova mancava `frontend/node_modules`.
  - Toccati: il DB della corsia, `.testLog/` (ignorato da git), uno snapshot in `.testLog/00_archive/`. Nessun test eseguito.
  - Rimedio: `npm ci` in `frontend/`, dal lock, approvato dal coordinatore. Exit 0; npm 11 avvisa che 5 script
    d'installazione non sono coperti da `allowScripts` (esbuild, fsevents, es5-ext). Poi la base è ripartita.
- ✅ **`all-backend`** sulla 6174, su `c3b33a8fb`, dopo `npm ci`: 7/7, **12 411 passati, 28 saltati, 0 falliti**, in 23
  invocazioni (24 min 18 s). Comando: quello sopra, con `--log-file /tmp/libreFolio_u0_all_backend_2.log`. Conteggi per
  invocazione nei file della sessione (`u0_all_backend_counts.txt`).
- ✅ **Client generato** dalla build del server di test (`api sync` dentro `cmd_fe_build`), sha256:
  - `openapi.json` `d64f7502…`
  - `generated.ts` `04abce23…`
  - `tool-contracts.openapi.json` `efe2e307…`
  - `generated-tools.ts` `c4e16c66…`
  - `tool-contract-map.generated.ts` `1558b4e3…`
- ✅ **Cataloghi**: i 4 file sono già byte per byte `json.dumps(indent=2, ensure_ascii=False)` più un a capo, il formato
  del generatore. In U-2, con un solo sorgente, il file generato dovrà quindi essere identico byte per byte, e così i chunk
  di lingua della build.
  - sha256 dei file: en `41a957cb…`, it `9c899bbc…`, fr `39e91da7…`, es `a6681e5f…`.
  - Chunk (build di debug del server di test): en `DQ50wwvC.js`, it `DaUZjbBs.js`, fr `DoRGLzK7.js`, es `S8wa8JSW.js`.
- ✅ **`docs_links.collect_backend`**: 66 link, 64 percorsi, 66 file d'origine. Dopo U-1 devono restare 66/64/66.
- ✅ **Frontend e statici**, in sequenza sulla 6174 (script `/tmp/libreFolio_u0_frontend_baseline.sh`, log nella sessione,
  `u0_fe_logs/`):
  - **Vitest**: le 19 azioni del registro sono verdi, 10 769 test;
  - **`front check`**: 0 errori, 0 avvisi;
  - **`i18n audit`**: 4 349 chiavi × 4, 0 mancanti, 0 morte, 3 non verificate, 1 famiglia backend senza chiavi;
  - **`lint`** (ruff): pulito;
  - **`lint --dead-code`**: exit 1 già sulla base, 121 righe di risultati, salvati per il confronto
    (`u0_dead_code.txt`).
- ✅ U-0 chiuso il 12/10.

### U-1 — Una cartella per plugin (in corso, 12/10)

- ✅ **Spostamento**: `files/scripts/u1_move.py` della sessione, con `mv` (niente `git mv`: lo staging è del
  coordinatore). 84 file `<famiglia>/<nome>.py` → `<famiglia>/<nome>/plugin.py`, più 84 `__init__.py` con la sola docstring.
- ✅ **Riscrittura**: `files/scripts/u1_rewrite.py`, 112 modifiche in 32 file come contato in analisi:
  - 81 `from …<plugin> import` (80 nei test, `api/v1/fx.py:71`);
  - 27 `from <famiglia> import <plugin>` → `from …<plugin> import plugin as <alias>`;
  - 4 stringhe.

  Più 13 percorsi `<famiglia>/<nome>.py` in 11 file: commenti, `pac_allocator/planner.py:45` e due tabelle funzionali
  dei test (`test_data_quality_thresholds.py:67`, `test_risk_warnings_i18n.py:69`).
  - Esclusi gli alberi sintetici a file singolo di `test_docs_links_gate.py` e `test_i18n_usage_gate.py`.
  - In più a mano il commento di debug di `snb/plugin.py` (`python -m …snb.plugin`).
- ✅ **Scoperta** (`provider_registry.py`):
  - `PLUGIN_MODULE_NAME`, `_plugin_entry_name`, `_load_module_from_file`, `_load_plugin_folder`, `_plugin_module_name`.
  - Una cartella con `__init__.py` e `plugin.py` si carica come `<ns>.<nome>.plugin`, il pacchetto prima; una cartella
    incompleta, o un nome presente sia come file sia come cartella, è un errore di scoperta; il file singolo resta per
    fixture e test.
  - **⚠️ Fuori pista**: ruff C901 (complessità 11 > 10) su `_discover_modules`. Ho estratto `_plugin_module_name`.
- ✅ **Tools**: `_safe_filename(module_name, namespace)` → `<nome>/plugin.py`; `_resolve_claim` riceve il namespace. In
  `schemas/tools.py:319` il pattern diventa `^[A-Za-z0-9_.-]+(?:/plugin\.py)?$` e `max_length` passa a 138.
- ✅ **Altro**: `docs_links.py` usa `rglob("*.py")`; `pac_allocator/plugin.py:69` → `parents[4]`; docstring di layout in
  `fx.py:68` e negli `__init__.py` delle 6 famiglie.
- ✅ **Verifiche statiche**:
  - le 6 famiglie caricano 84 plugin con 0 errori di scoperta (FX 7 codici: `mockfx` ne registra due) e moduli tutti
    `.plugin`;
  - `collect_backend` dà 66/64/66, con le origini in `plugin.py`;
  - `dev.py lint` è pulito dopo `ruff --select I --fix` sui 7 file di test con gli import da riordinare;
  - black uguale alla base: 29 file già fuori formato, `docs_links.py` con gli stessi 3 blocchi di prima;
  - `pytest --collect-only` sui file riscritti: 1 836 test raccolti, 0 errori d'import.
- ✅ **`api sync`**: cambiano i 5 file generati (ignorati da git), e le differenze sono tutte spiegate. Invertendo in
  memoria solo pattern e `maxLength` del `filename`, la versione `-dirty` di `openapi.json` (la worktree è modificata) e
  l'hash del contratto dei tools (`e839b191…` contro `efe2e307…`), i 5 file tornano **identici byte per byte** alla base
  (script `files/libreFolio_u1_api_reverse*.py`). Nuovi sha256: `openapi.json` `986946e0…`, `generated.ts` `a1051f44…`,
  `tool-contracts.openapi.json` `e839b191…`, `generated-tools.ts` `1ba2fb59…`, `tool-contract-map.generated.ts` `0d316152…`.
- ⏳ test-author in corso: test della scoperta a cartelle, gate `utils gate-plugin-layout`, `_safe_filename`, caso
  cartella di `docs_links`, riparazioni di `test_brim_providers.py:5961` e `optionFilter.test.ts`.
- ✅ **Test di test-author** (12/10), che non ha eseguito suite. Comandi e conteggi sono nel gate qui sotto.
  - `test_provider_registry_misc.py`: 10 test della scoperta a cartelle.
  - Nuovo `test_utilities/test_plugin_layout_gate.py` (PURE, 491 righe, 33 test), registrato come
    `utils gate-plugin-layout`:
    - la convenzione nelle 6 famiglie;
    - gli import e le stringhe che arrivano al pacchetto invece che a `.plugin`;
    - la coincidenza fra famiglie e registri;
    - 7 controlli che il gate sa fallire.
  - `test_tools_registry.py`: `filename` `<nome>/plugin.py` e i rifiuti dello schema.
  - `test_docs_links_gate.py`: il caso a cartelle.
  - Riparazioni: `test_brim_providers.py`, il cui controllo della codifica legge `broker_*/*.py`, e
    `optionFilter.test.ts`, che legge `broker_*/plugin.py` in ordine di cartella.
- **⚠️ Fuori pista — tre rilievi di test-author, applicati:**
  1. Lo schema accettava `../plugin.py` e `./plugin.py`: `.` e `..` passavano come nome di cartella. Il pattern
     diventa `^(?:[A-Za-z0-9_.-]+|[A-Za-z0-9_-]+/plugin\.py)$` (`max_length` 138), coerente con ciò che `_safe_filename`
     può produrre; dopo, di nuovo `api sync`.
  2. Con `x.py` e `x/` insieme, quale dei due si caricava dipendeva dall'ordine del file system. Ora l'ordine è
     `(nome, is_dir())`: prima il modulo, poi la cartella.
  3. `_backend_external.py:51` (`_discover_provider_codes`) faceva `glob("*.py")`: l'aiuto di `--providers` elencava
     «(none)». Ora fa `glob("*/plugin.py")`, e l'aiuto elenca di nuovo asset 6, FX 6, BRIM 33. Insieme, il percorso nel
     `print_info` di `_backend_services.py:814`. Il coordinatore mi ha assegnato i due file il 12/10.
- ✅ **`api sync` finale**: la prova d'inversione (`files/scripts/u1_api_reverse.py`) riporta tutti e 5 i file generati a
  quelli di U-0, byte per byte. Nuovi sha256:
  - `openapi.json` `e9403390…`
  - `generated.ts` `723f3992…`
  - `tool-contracts.openapi.json` `202402e5…`
  - `generated-tools.ts` `4630bb93…`
  - `tool-contract-map.generated.ts` `62798d0c…`
- ✅ **Gate mirati** sulla 6174 (`/tmp/libreFolio_u1_targeted.sh`):

  | Selettore | Risultato |
  |---|---|
  | `services provider-registry-misc` | 23 passati |
  | `services provider-registry` | 7 |
  | `utils gate-plugin-layout` | 33 |
  | `services tools-registry` | 109 |
  | `utils gate-docs-links` | 63 |
  | `external brim-providers test_no_plugin_opens_files_with_a_fixed_encoding` | 1 |
  | `services signal-registry` | 65 |
  | `check-orphans` | verde |
  | `front-utility core-unit` | 3 736/3 736, alla seconda corsa |

- **⚠️ Fuori pista — `core-unit` rosso alla prima corsa**: 1 timeout di 5 s su 3 736, in
  `src/htmlInterpolation.gate.test.ts › flags every character reference the parser decodes`.
  - **Triage** (skill `test-triage`): la macchina aveva un carico medio di 60 su 10 core, per le altre corsie.
  - Tutta l'unità era 4 volte più lenta della base: 80,5 s contro 20,4 s; trasformazione 144 s contro 44 s; test 41,5 s
    contro 9,4 s.
  - Il test passa 8 stringhe a `translationMarkup` e non legge niente che U-1 tocchi.
  - Rilancio con carico 41–50: 3 736/3 736 in 26,9 s.
  - **Verdetto: ambiente.**
- ✅ **Ordine di registrazione** identico alla base nelle 6 famiglie (confronto con i nomi dei file in `HEAD`).
- ✅ **Rinomine**: 82 `plugin.py` identici byte per byte al file di `HEAD`; `snb` e `pac_allocator` differiscono di una
  riga ciascuno. Git le vede come rinomine, quindi `git log --follow` resta continuo dopo il commit.
- **⚠️ Fuori pista — `all-backend` su U-1** (6174, `--log-file /tmp/libreFolio_u1_all_backend.log`, 30 min 38 s con
  carico medio 40–60): 6/7, **10 rossi, tutti per una causa**.
  - Il test è `test_data_quality_thresholds.py::test_consumers_import_the_thresholds_from_the_shared_module[…risk_plugins/<nome>.py…]`.
  - Alla riga 68 un f-string, `f"backend/app/services/risk_plugins/{name}.py"`, costruisce ancora il vecchio percorso.
    La regola letterale di `u1_rewrite.py` non poteva vederlo; una ricerca mirata di modelli f-string e join su tutto il
    repo non ne ha trovati altri.
  - Riparazione affidata a test-author (stessa sessione).
  - **Il resto è identico alla base**:
    - 21 invocazioni su 23 uguali al conteggio;
    - servizi: +26 test (+10 `test_provider_registry_misc`, +16 `test_tools_registry`), 6 423 passati e 10 rossi;
    - utility: +36 (+33 `test_plugin_layout_gate`, +3 `test_docs_links_gate`).
- **Nota per U-3**: dopo lo `split`, il catalogo generato ha le stesse chiavi e gli stessi valori ma un altro ordine
  (prima `base`, poi i sottosistemi, poi i plugin). A runtime l'ordine non conta (nessun `$json(`, ricerca per percorso).
  - La prova di U-3 resta l'uguaglianza di chiavi e valori per lingua (`check --against`).
  - L'uguaglianza byte per byte dei chunk vale solo per U-2, quando c'è un solo sorgente.
  - Per U-3 i chunk si confrontano come oggetti.
- ✅ **Riparazione** di test-author: `test_data_quality_thresholds.py:68` → `f"…/risk_plugins/{name}/plugin.py"`.
- ✅ **`all-backend` sulla 6174** (`--log-file /tmp/libreFolio_u1_all_backend_2.log`, 29 min 49 s): 7/7, **12 473
  passati, 28 saltati, 0 falliti**, cioè la base, 12 411, più i 62 test nuovi.
  - 21 invocazioni su 23 sono identiche alla base.
  - Servizi: 6 433 passati, contro 6 407 (+26).
  - Utility: 1 714, contro 1 678 (+36).
- ✅ **Statici**:
  - `dev.py lint` è pulito;
  - black è uguale alla base (gli stessi 29 file);
  - `git diff --check` è pulito, e i file nuovi non hanno spazi a fine riga;
  - la porta 6174 è libera.
- ✅ **Manifest** con i blob: `files/u1_manifest.txt` della sessione.
  - 59 file modificati;
  - 84 cancellati, che sono rinomine: 82 identici byte per byte, 2 con una riga cambiata;
  - 170 aggiunti: 168 file dei plugin, il gate e questo piano.
- ✅ **Backlog**: la sezione U in `BACKLOG_POST_1.2.md`, con U-B1, U-B3, U-B4 e U-B5.
- ✅ U-1 chiuso il 12/10. Checkpoint mandato al coordinatore; stato FROZEN.
