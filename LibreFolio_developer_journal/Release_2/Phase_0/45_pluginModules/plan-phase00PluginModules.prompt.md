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

### U-2 — Il catalogo costruito dalle sorgenti (chiuso il 12/10, checkpoint inviato)

- ✅ **Base**: HEAD `bd8ee8e4d`, il treno 61, che contiene U-1 (`2eed3d26c`, `170d16333`), la modifica di T a
  `cli_base.py` e il CHANGELOG localizzato. Il via è del coordinatore, il 12/10.
- ✅ **Vincolo di sequenza**, chiesto dal coordinatore: lo spostamento dei 4 cataloghi in `base/` è una **rinomina pura**,
  nello stesso commit e senza altre modifiche, così le modifiche di I e T sui file di oggi seguono la rinomina al merge.
  - Verificato su `bd8ee8e4d`: i 4 file sono già `json.dumps(indent=2, ensure_ascii=False)` più un a capo, quindi il
    file generato coincide con la sorgente byte per byte.
  - sha256 della base: en `47e03ab0…`, it `9e1fb276…`, fr `36dde70e…`, es `8c5d07e7…`.
- ✅ **File in più assegnati** (12/10): `frontend/.prettierignore`, il nuovo `frontend/scripts/i18n-catalog-build.mjs`,
  `frontend/.gitignore`, e `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py` per una riga in
  `FrontendBridge.__enter__`.
- ✅ **Basi del frontend su `bd8ee8e4d`** (`/tmp/libreFolio_u2_baseline.sh`; log nella sessione, `u2_base_logs/`):
  - `front build` di produzione, chunk di lingua: en `Dnh_D_O3.js` `5fa1863d…`, it `D-aHihPl.js` `e6c71af9…`,
    fr `iHe4svMs.js` `4bb36828…`, es `BbCwz7lE.js` `8f997afd…`;
  - `front check`: 0 errori, 0 avvisi;
  - `i18n audit`: 4 350 chiavi, 0 mancanti, 0 morte, 3 non verificate, 1 famiglia backend;
  - Vitest: le 19 azioni verdi, 10 858 test;
  - `lint --dead-code`: exit 1, 121 righe, come prima.
- ⏳ **Base `all-backend`** su `bd8ee8e4d`, sulla 6174. Il coordinatore non ha i conteggi del treno 61.
- ✅ **test-author, fase A** (12/10): `backend/test_scripts/test_utilities/test_i18n_catalog_gate.py`, PURE, 49 funzioni
  e 106 casi, non ancora registrato. Eseguito in-process: 96 verdi e 10 rossi. Cinque rossi sono i controlli sull'albero
  reale, che passano solo con `base/`. Gli altri cinque sono difetti della libreria.
- ✅ **Libreria corretta** (12/10), `scripts/i18n_catalog.py`:
  - **D1**: un testo in una sorgente contro un ramo in un'altra faceva sollevare `set_nested` dentro `_merge_language`,
    perdendo gli altri problemi. Inoltre il controllo per vicini ordinati non vedeva chiavi con caratteri minori di `.`.
    Ora `_owners` controlla ogni antenato di ogni chiave, e `_merge_language` salta la voce in conflitto (`_settable`).
  - **D2**: `--into` accettava qualunque cartella dei servizi con `plugin.py`, comprese quelle che la scoperta non legge;
    `move` perdeva le chiavi. Ora vuole esattamente `<famiglia>/<plugin>`, con la famiglia `*_providers` o `*_plugins`.
  - **D3**: un prefisso ripetuto nello stesso `prefixes.txt` ora dice «declared twice in 'X'».
  - **D4**: una revisione sconosciuta ora dà `CatalogError` invece di un traceback (`git rev-parse --verify`).
  - **Ripiego opzionale**: `merge(fill=…)` e `load_catalog(lang, fallback=…)`. I 6 lettori useranno `fallback=False`,
    così i loro controlli «tradotto in ogni lingua» possono ancora fallire. `catalogs_at` e `check --against`
    confrontano senza ripiego.
  - **`route`**: la regola «unico plugin sotto l'antenato» mandava `assets.providerParams.<nuovo>` a `borsa_italiana`.
    Ora va al plugin solo se l'antenato sta dentro il ramo del plugin (`plugin_namespace`, il prefisso comune dei
    genitori delle sue chiavi); altrimenti chiede `--into`.
  - **`absorb` a tre vie**, per chiave e lingua: base, nostro, loro. Un conflitto c'è quando il nostro valore differisce
    da entrambi. Senza `--prefer` li elenca tutti e non scrive niente; con `--prefer ours|theirs` li risolve.
    I conteggi sono per chiave.
  - Prova: `files/scripts/u2_git_rehearsal.sh`, con il Python 3.9 di Apple, su un repository usa e getta:
    - `split` più le 71 mosse danno contenuto identico;
    - `check --against` è identico su A e su B;
    - `absorb` A..B: 1 aggiunta, 2 modifiche, 1 rimozione;
    - la guardia del file generato tiene;
    - il ripiego in build funziona e il `check` severo fallisce;
    - `route` dà 2 plugin e 4 rifiuti attesi;
    - il conflitto viene rifiutato senza scrivere niente; `prefer ours` e `prefer theirs` funzionano;
    - una revisione sconosciuta viene rifiutata; `--into` dà 4 rifiuti e 2 accettazioni.

    ruff e black sono puliti; il file si analizza come Python 3.9.
- ✅ **test-author, adattamento del gate** (12/10, 18:00): 137 verdi su 142. I 5 rossi sono i controlli sull'albero
  reale, che aspettano `base/`. Sulla copia del repo con `base/` passano, e la build è identica byte per byte. Il gate
  diventa rosso su 46 mutanti della libreria su 46. Ha trovato:
  - **A1, difetto**: `--prefer` non poteva risolvere una chiave rimossa da una parte mentre l'altra ne cambiava una
    traduzione. Il conflitto stava in una lingua sola, mentre l'inglese seguiva la rimozione: ne usciva una chiave senza
    inglese, rifiutata dalla fusione finale con un messaggio che non nominava il conflitto.
    - **Corretto**: un conflitto di questo tipo vale per la chiave intera, ed è `_removal_conflicts`, che gira prima
      del giro per lingua.
    - Senza `--prefer` lo segnala con le lingue e i valori. `ours` lascia le sorgenti come sono. `theirs` rimuove la
      chiave ovunque, oppure la riporta con le lingue che ha loro.
    - Una parte che ha solo tolto traduzioni non è in conflitto con la rimozione.
  - **A3, latente**: `_shown()` cadeva su un valore che non è una stringa, e un `null` valeva come chiave assente.
    Corretto così:
    - `ABSENT` è un sentinella;
    - `_shown()` regge qualsiasi valore;
    - la fusione rifiuta ogni foglia che non sia una stringa: «value(s) not a string».
  - **Il messaggio di `route` dentro `absorb`** ripeteva la chiave e usciva una volta per lingua. Ora esce una volta sola,
    con il suggerimento di creare la chiave con `add --into` e poi rilanciare `absorb`.
  - **A2, nessun cambio**: un plugin con chiavi in due rami non ha uno spazio dei nomi, quindi `route` chiede `--into`.
    È la risposta prudente, e in U-3 il gate di proprietà la rende impossibile: tiene ogni frammento nello spazio dichiarato
    dal plugin.

  Dopo le correzioni, in-process: ruff e black puliti, sintassi 3.9 valida. Restano rossi solo i 5 controlli sull'albero
  reale e i 2 test che fissavano i messaggi vecchi, da aggiornare a cura di test-author.
- ✅ **Preparato in `files/scripts/u2_apply.py`**:
  - la rinomina dei 4 cataloghi in `base/`;
  - le copie in `frontend/`;
  - 3 modifiche in `dev.py`: l'import, `cmd_fe_build` prima di svelte-check e `cmd_dead_code` prima di knip;
  - 2 in `cli_base.py`: l'import, più la libreria e i frammenti dei plugin fra gli input di staleness;
  - 2 nel probe: l'import e `build()` prima di `Popen`.

  Le precondizioni sono verificate senza scrivere niente. Va lanciato solo a corsia ferma.
- ✅ **Docker**: l'immagine copia `scripts/` e `backend/`, quindi la libreria e i frammenti ci sono. Il container avvia
  `uvicorn` direttamente, senza `dev.py server`, quindi nessuna build automatica. `dev.py docker build` usa la staleness
  dell'host, che ora vede i frammenti.
- > **⚠️ Fuori pista** (12/10): il `brew upgrade` dello sviluppatore ha rotto `node` (`libsimdjson.33.dylib`). Su ordine
  > del coordinatore niente comandi frontend (npm, vite, vitest, svelte-check, il wrapper `.mjs`) finché non lo dice lui.
  > `all-backend` in Python continua. I rossi che ne derivano sono di ambiente e non vanno triagiati.
- > **⚠️ Fuori pista** (12/10, 17:27): `node` è tornato (v26.11.1), ma brew ha portato anche Python da 3.13.15 a 3.13.16.
  > La base `all-backend`, partita alle 16:53, ha attraversato il cambio, quindi non vale come confronto. L'ho fermata
  > alle 17:28, dopo 3 invocazioni verdi; la porta 6174 è libera. Log tenuti come
  > `/tmp/libreFolio_u2_base_all_backend_INVALID_py-switch.*`.
- ✅ **Build di base rifatta con `node` 26.11.1** (17:29–17:34, `/tmp/libreFolio_u2_base2/`): i 4 chunk di lingua hanno gli
  stessi nomi e gli stessi sha256 della base presa con `node` 26.8.2, quindi la toolchain nuova non cambia il bundle.
- ✅ **Base `all-backend` rifatta** su `bd8ee8e4d` con Python 3.13.16 (17:34–18:13, 39 min): 7 categorie su 7, EXIT 0,
  **12 497 passati e 28 saltati** in 23 invocazioni. Conteggi per invocazione in `files/u2_base_all_backend_counts.txt`,
  log in `files/u2_base_logs/all_backend_bd8ee8e4d_py31316.console`. La porta 6174 è libera.
- ✅ **U-2 applicato** (18:14, `files/scripts/u2_apply.py`):
  - i 4 cataloghi spostati in `base/`, hash invariati;
  - 6 file copiati in `frontend/`;
  - 11 modifiche in 4 file: `dev.py`, `cli_base.py`, `_backend_utils.py` e il probe.
- ✅ **Gate locali** (`u2_gates.sh local`):
  - la build con Python 3.14 riscrive le 4 lingue; quella con il 3.9 di Apple non riscrive niente;
  - il `check` severo con il 3.9 dà 4 350 chiavi e 1 sorgente;
  - i file generati e `base/` hanno gli **sha256 della base**;
  - i file generati sono in sola lettura (0444), lo stamp no;
  - le regole di `.gitignore` coprono i 4 JSON e `.generated` (verifica con `--no-index`), mentre `base/` non è ignorata.
- > **Nota**: i 4 JSON generati restano tracciati nel mio indice finché il coordinatore non lancia il `git rm --cached`
  > al checkpoint. Per questo `git status` li vede invariati e `git check-ignore` senza `--no-index` non li dà per
  > ignorati. Il test di test-author usa già `--no-index`.
- ✅ **Gate frontend, primi risultati** (`u2_gates.sh frontend`):
  - `front check`: 0 errori e 0 avvisi; l'hook `precheck` gira;
  - `front build` di produzione: l'hook `prebuild` gira, e i **4 chunk di lingua hanno nomi e sha256 della base**;
  - `i18n audit`: identico alla base (4 350 chiavi, 0 morte, 3 non verificate, 0 chiavi backend mancanti). Cambiano solo
    le righe delle sorgenti («Source problems: 0») e la data.
- ✅ **Lint dei file toccati, confrontato con HEAD** (`dev.py`, `cli_base.py` e `i18n-audit.py` falliscono black e ruff
  già nella base):
  - `dev.py`: stesse segnalazioni di ruff e stesse 340 righe per black. Spostare la build del catalogo in
    `_run_knip_on_generated_catalogue` evita il +1 di complessità su `cmd_dead_code`.
  - `cli_base.py`: invariato.
  - `i18n-audit.py`: ruff dà 32 segnalazioni contro 34; black resta a 205 righe. Il controllo delle sorgenti sta in
    `_check_sources`, il nome del proprietario in `_owner_names`, e la `CatalogError` di caricamento si gestisce in
    `run_from_args`, così `run_audit` e `cmd_search` non salgono di complessità.
  - I sottocomandi `add`, `remove`, `update`, `search` e `tree` passano da `_guarded`: una sorgente illeggibile dà un
    messaggio, non un traceback.
  - `i18n_catalog.py`, `_backend_utils.py` e il probe sono puliti. `git diff --check` è pulito.
- ✅ **Backlog**: U-B6, il server di sviluppo che non segue le sorgenti modificate a mano.
- ✅ **Vitest** (`u2_gates.sh frontend`, 18:18–18:26): **18 azioni su 19 verdi, ognuna con i conteggi della base**.
  `front-utility onboarding-component-unit` è stata interrotta dallo STOP e il dead-code non è partito.
- > **⏸ STOP del developer** (12/10, 18:26, relayato dal coordinatore): tutto fermo, stato FROZEN fino a «riparti».
  > - **Fermato**: lo script dei gate frontend, alla 19ª azione Vitest. Nessun processo rimasto, porta 6174 libera, nessun
  >   server. La base `all-backend` era già finita, verde, alle 18:13.
  > - **test-author** era a metà turno: adattava il gate per A1 e A3, con il via alla fase B. Non si può interrompere da
  >   strumento, quindi lo STOP gli è stato accodato e lo leggerà a fine turno.
  >   - Alle 18:27 non aveva ancora toccato `_backend_utils.py` (nessuna registrazione) né i 6 lettori.
  >   - Il suo resoconto dirà quali file ha cambiato e se qualcuno è a metà.
  > - **Worktree**: 18 file sporchi (11 modificati, 7 nuovi), tutti di U-2. Fra i nuovi ci sono il gate di test-author e i
  >   4 file di `base/`. I 4 JSON generati sono identici a HEAD, quindi git non li vede.
  > - **18:3x, test-author si è fermato**: prima di leggere lo STOP aveva **completato** il suo turno, e nessun file è a
  >   metà. Ha registrato `gate-i18n-catalog` in `_backend_utils.py`, con una sostituzione unica che lascia byte per byte
  >   le mie 3 descrizioni, e ha portato i 6 lettori su `load_catalog(lang, fallback=False)` con import al livello del
  >   modulo. ruff e black sono puliti.
  >   - I suoi conteggi in-process: gate 160 su 160, compresi i 5 controlli sull'albero reale; test del catalogo nei
  >     lettori 9 + 2 + 1 + 1 + 8 + 12, tutti verdi.
  >   - **Worktree ora: 24 file sporchi** (17 modificati, 7 nuovi). Porta 6174 libera.

  **Fatto in U-2:**
  - la libreria, con D1–D4, A1 e A3, il ripiego opzionale, `route` e `absorb` a tre vie;
  - il CLI `dev.py i18n`;
  - gli inneschi: npm, Vitest, `front build`, dead-code, il probe;
  - la staleness;
  - le 3 descrizioni chieste da M;
  - la base `all-backend`;
  - l'applicazione;
  - i gate `local`;
  - `front check`, `front build` con i chunk, `i18n audit` e 18 Vitest su 19;
  - il lint;
  - la voce U-B6 nel backlog.

  **A metà:** nessuna modifica. Restano solo i gate da finire (sotto). La fase B di test-author è completa ma non
  ancora verificata nella corsia.

  **Alla ripartenza, nell'ordine:**
  1. rileggere il diff della fase B di test-author (`_backend_utils.py` e i 6 lettori);
  2. rilanciare `i18n audit`, perché `i18n-audit.py` è cambiato dopo il gate: errori di caricamento, `_guarded`,
     `_owner_names`;
  3. la Vitest `front-utility onboarding-component-unit`;
  4. `lint --dead-code`;
  5. `u2_gates.sh targeted fresh cli`;
  6. `u2_gates.sh backend` (`all-backend`), da confrontare per invocazione con la base, 12 497 passati e 28 saltati;
  7. il manifest (`files/scripts/u2_manifest.sh`), poi il checkpoint U-2 e FROZEN.
- ✅ **Ripartenza** (12/10, 19:24, «riparti» del coordinatore). HEAD è ancora `bd8ee8e4d`, con Python 3.13.16 e `node`
  26.11.1; la porta è libera. La base `all-backend` di oggi resta valida, dato lo stesso interprete.
- ✅ **Fase B di test-author riletta**:
  - `gate-i18n-catalog` è registrato, con `isolation="pure"`, accanto a `gate-i18n-usage`. Le mie 3 descrizioni sono
    intatte.
  - I 6 lettori leggono con `load_catalog(lang, fallback=False)`, con import al livello del modulo. Sono circa 30
    chiamate in tutto, quindi il costo è trascurabile anche in U-3.
  - Il gate controlla anche l'indice: segnala un problema solo se `base/en.json` e i JSON generati sono tracciati
    insieme. Oggi quindi passa, e diventa rosso se al checkpoint si dimentica il `git rm --cached`.
- ✅ **Gate mirati** (`u2_gates.sh targeted`, 19:25–19:28), tutti verdi:

  | Selettore | Esito |
  |---|---|
  | `utils gate-i18n-catalog` | 160 passati |
  | `utils gate-i18n-usage` | 195 |
  | `utils dev-cli-image` | 31 |
  | `utils gate-plugin-layout` | 33 |
  | `utils ai-export-probe-helpers` | 73 |
  | `external brim-providers` | 705 + 1 saltato, come nella base |
  | `external brim-degiro` | 169, come nella base |
  | `external brim-scalable` | 145, come nella base |
  | `schemas risk` | 69 |
  | `services risk-all` | 896 |
  | `services signal-plugin-matrix` | 92 |
  | `check-orphans` | tutti raggiungibili da un `all` (261 file backend, 347 Vitest, 109 E2E) |
- ✅ **Checkout pulito** (`fresh`), tutto verde:
  - cancellati i file generati e lo stamp, li riscrivono a turno una Vitest (`front-utility core-unit`), `front check`
    e `dev.py i18n build`, ogni volta con gli **hash della base**;
  - `check_frontend_needs_build()` risponde «needs build: True» quando mancano;
  - la guardia rifiuta un `it.json` modificato a mano; `--force` lo riscrive e gli hash tornano quelli della base.
- ✅ **CLI** (`cli`), tutto verde:
  - `where`;
  - `add common.zzU2Probe`, che scrive in `base/` e lo dice;
  - `where` sulla chiave nuova;
  - `search`, con la colonna «Source»;
  - `update`, `remove`;
  - dopo il giro **`base/` e i file generati tornano agli hash della base**;
  - `check`, `tree`.
- ✅ **Ripresa** (`resume`, 19:31–19:33):
  - `i18n audit` rilanciato con l'`i18n-audit.py` finale: identico alla base;
  - Vitest `front-utility onboarding-component-unit`: 434, come la base. **Le 19 azioni Vitest hanno quindi tutte i
    conteggi della base**;
  - `lint --dead-code`: output identico alla base (exit 1, 132 righe), e knip non segnala né il `.mjs` né il
    `globalSetup`.
- > **⚠️ Fuori pista** (19:25): ho modificato `u2_gates.sh` (aggiungendo `part_resume`) nella stessa batch di chiamate
  > parallele che lo lanciava.
  > - Cosa è successo: bash aveva già letto la versione vecchia, quindi `resume` è risultato «command not found» e la
  >   catena è proseguita con `targeted`, `fresh` e `cli`, le cui definizioni non erano cambiate. A fine loop bash ha
  >   ripreso a leggere dal vecchio offset nel file modificato: ha trovato un frammento («ead_code: command not found»),
  >   poi un errore di sintassi, e si è fermato con EXIT 2 senza eseguire niente. Worktree e porta sono intatti.
  > - Rimedio: `resume` rilanciato da solo, in un processo nuovo.
  > - Regola per me: mai modificare uno script nella stessa batch che lo lancia, né mentre gira.
- ❌ **`all-backend` di U-2, prima prova** (19:33–19:53, fermata da me dopo 3 invocazioni):
  - servizi: 6 436 + 1 saltato, uguale alla base;
  - utils: **3 falliti** e 1 892 passati, contro 1 735 nella base: i 160 in più sono il gate nuovo;
  - la terza invocazione: 1 705, uguale alla base.
- > **⚠️ Fuori pista, difetto mio**: i 3 rossi sono `test_runtime_isolation.py::TestFrontendBuildStaleness`:
  > `test_a_frontend_source_newer_than_the_build_needs_a_rebuild` e
  > `test_a_root_changelog_newer_than_the_build_needs_a_rebuild[inline-english|lazy-translation]`.
  > - **Causa**: il loro fixture `frontend_project` costruisce un progetto senza sorgenti i18n. Il mio nuovo controllo
  >   in `check_frontend_needs_build()` chiamava `generated_catalogs()`, che senza `base/en.json` sollevava
  >   `CatalogError`. L'`except Exception` della staleness la ingoiava e rispondeva «nessuna build serve».
  > - **Perché i miei gate non l'hanno visto**: `fresh_staleness` gira sull'albero vero, che `base/` ce l'ha, e
  >   `runtime-isolation` non era fra i selettori mirati.
  > - **Correzione**: `generated_catalogs()` restituisce `[]` dove non c'è un `base/` da cui generare. Poi
  >   `utils runtime-isolation` **158/158**.
  > - **Run fermata** perché da rifare comunque dopo la correzione: le invocazioni rimaste non avrebbero aggiunto niente.
  > - **Test nuovi chiesti a test-author** (20:0x), per le aggiunte alla staleness e per `generated_catalogs`:
  >   - un catalogo generato mancante → serve la build;
  >   - un frammento di plugin più recente della build → serve la build;
  >   - `scripts/i18n_catalog.py` più recente → serve la build;
  >   - senza `base/` il controllo risponde sugli altri input.
- ✅ **Test nuovi di test-author** (12/10, sera):
  - in `test_runtime_isolation.py::TestFrontendBuildStaleness` il fixture fratello `frontend_catalogue` aggiunge `base/`,
    i 4 file generati, il frammento di un plugin e la libreria, tutti più vecchi della build. Casi nuovi:
    - `test_without_catalogue_sources_the_other_inputs_still_decide`;
    - `test_a_catalogue_older_than_the_build_leaves_it_up_to_date`;
    - `test_a_missing_generated_catalogue_needs_a_rebuild_though_the_bundle_is_fresh`, uno per lingua;
    - `test_a_catalogue_input_newer_than_the_build_needs_a_rebuild`, per sorgente base, frammento e libreria.

    Il file passa da 158 a 167 test.
  - nel gate:
    - `test_generated_catalogs_are_none_without_an_english_base`;
    - `test_generated_catalogs_follow_the_languages_of_base_english_first`.

    Il file passa da 160 a 163 test.
  - 4 mutanti della staleness danno 4 rossi, compreso il mio `generated_catalogs` vecchio che sollevava.
  - ruff e black sono puliti; nella corsia `utils runtime-isolation` dà **167** e `utils gate-i18n-catalog` **163**.
- ✅ **`all-backend` finale** (19:59–20:47, 47 min 43 s, con il carico della run con coverage del coordinatore):
  - 7 categorie su 7, EXIT 0: **12 669 passati, 28 saltati, 0 falliti**;
  - **22 invocazioni su 23 identiche alla base**. Diversa solo utils, da 1 735 a 1 907: i 172 in più sono 163 del gate
    nuovo e 9 della staleness, esattamente l'atteso;
  - conteggi in `files/u2_all_backend_counts.txt`; porta 6174 libera.
- ✅ **Manifest** (`files/u2_manifest.txt`): 18 modificati, 7 nuovi, 4 percorsi da togliere dall'indice. Le 4 rinomine
  `<lang>.json → base/<lang>.json` hanno blob identici. I file generati hanno i blob di HEAD e sono ignorati per regola.
  `git diff --check` è pulito.
- ✅ **Commit proposti**: `/tmp/libreFolio_commit_u2.txt` («feat(i18n): build the catalogue from its sources») e
  `/tmp/libreFolio_commit_u2_docs.txt` per piano e backlog.
- ✅ **U-2 chiuso il 12/10.** Checkpoint mandato al coordinatore con lo staging esplicito: prima `git rm --cached` dei 4
  vecchi percorsi, poi `git add` di `base/` e del resto. Stato FROZEN. Il prossimo passo, U-3, aspetta il via del
  coordinatore dopo le chiavi di I.
- ✅ **Committato dal coordinatore** (12/10, 20:54): `1b31f9057`, con le 4 rinomine al 100 % verificate, e `0a5285dc0`,
  con piano e backlog. Prima del commit ha provato su un clone: albero finale identico, i 4 file generati restano sul
  disco ignorati e in sola lettura, la worktree pulita.
- ✅ **Merge del target** `8d0b222d3`, pulito: ora sono a **`7a065caed`**, albero `ae31f8455`. Il backlog, unico file
  toccato da entrambi i lati, si è fuso da solo. Il target non aveva toccato i cataloghi dopo `bd8ee8e4d`.
  - `catalogIcuLocale.test.ts` (T, M-18) importa i 4 cataloghi generati, che il `globalSetup` scrive prima.
  - Il suo `readdirSync` cerca solo file `.svelte`, quindi `base/` non lo tocca.
  - Il target aggiunge 5 file Vitest ad azioni esistenti e un E2E (`docs-offline-math`): le azioni Vitest restano 19.
- ✅ **Revisione combinata `7a065caed` validata** (20:55–21:17, `files/scripts/u2_combined.sh`, corsia 6174, una prova
  alla volta; log in `/tmp/libreFolio_u2c/`). Tutto verde:
  - **catalogo**: la build risponde «up to date»; i file generati e `base/` hanno gli sha256 della base.
  - **pytest**, con gli stessi conteggi della U-2 su `bd8ee8e4d`:

    | Selettore | Passati |
    |---|---|
    | `gate-i18n-catalog` | 163 |
    | `runtime-isolation` | 167 |
    | `gate-i18n-usage` | 195 |
    | `brim-degiro` | 169 |
    | `brim-providers` | 705 + 1 saltato |
    | `brim-scalable` | 145 |
    | `schemas risk` | 69 |
    | `risk-all` | 896 |
    | `signal-plugin-matrix` | 92 |

    `check-orphans` è verde: 261 file backend, 352 Vitest (+5 del target), 110 E2E (+1 del target).
  - **`front check`**: 0 errori, 0 avvisi.
  - **Le 19 Vitest**, 11 070 test:
    - 16 azioni identiche alla U-2;
    - 3 cresciute per i 13 file Vitest cambiati dal target (U-2 non ne cambia nessuno): `risk-frame-component` da 17 a 20,
      `component-unit` da 2 992 a 3 006, `core-unit` da 3 766 a 3 961, che comprende `catalogIcuLocale.test.ts`.
  - **Build di produzione**: i 4 chunk di lingua hanno nomi e sha256 della base.
  - **`i18n audit`**: stessi verdetti (4 350 chiavi, 0 morte, 3 non verificate, 0 chiavi backend mancanti, 0 problemi
    di sorgente). Le chiavi usate letteralmente nel codice sono 3 711 contro 3 710: un uso in più nel sorgente del target.
  - **`lint --dead-code`**: output identico (exit 1). Cambia solo un numero di riga in `user_service.py`, file toccato
    dal target.
  - `git status`: solo questo piano. Porta 6174 libera.
- ✅ **Handoff mandato** (21:2x). Stato FROZEN: U-2 entra nel prossimo treno, U-3 aspetta il lotto 48 di I nel target.
- ✅ **Staleness della build** (preparato in `u2_apply.py`): `check_frontend_needs_build()` risponde «sì» anche quando
  manca un file generato con il bundle fresco. Gli E2E leggono il catalogo generato e passano da `auto_build_frontend`,
  quindi una pulizia dei file ignorati non li lascia senza. Per questo la libreria espone `generated_catalogs()`.
- ✅ **Verificato chi legge il catalogo generato senza hook**:
  - la CI passa sempre da `dev.py` (`front build`, `test all`, `mkdocs gallery`);
  - il runner lancia Vitest con `vitest.config.ts`, dove c'è il `globalSetup`;
  - `dev-cli-image` copia `scripts/`, che è un pacchetto, quindi gli import nuovi reggono anche nell'immagine;
  - Docker non costruisce il frontend.
- ✅ **Prettier**: il catalogo contiene solo stringhe, e prettier con `tabWidth: 2` scrive come il generatore. Le sorgenti
  restano quindi sotto prettier; `.prettierignore` esclude solo i file generati.
- ✅ **Script dei gate U-2** pronto: `files/scripts/u2_gates.sh`, a parti separate.
  - `local`: build con Python 3.14 e 3.9, `check` severo, hash, permessi, ignore, stato git.
  - `targeted`: 11 selettori e `check-orphans`.
  - `frontend`: `front check`, la build con il confronto dei chunk, `i18n audit`, le 19 Vitest, il dead-code.
  - `fresh`: i file generati vengono cancellati e poi riscritti da Vitest, da `front check` e dal CLI; la staleness; la
    guardia sulle modifiche a mano.
  - `cli`: un giro `add`/`update`/`remove` del CLI, dopo il quale `base/` e i file generati devono tornare identici byte
    per byte.
  - `backend`: `all-backend`.
- ✅ **Descrizioni di tre unità in `_backend_utils.py`**, chieste da M tramite il coordinatore (12/10, 17:56). Cambia solo
  il testo di `desc`, nessun selettore. Sono preparate in `u2_apply.py`:
  - `js-cache-fail-loud`: il testo di M, aggiunto in coda (le dipendenze della libreria JS, cioè i font di MathJax);
  - `translation-cache` e `translation-validator`: il CHANGELOG tradotto per pezzi e validato capitolo per capitolo.
    Testo mio, ricavato dai test di `e63cfb074`. M l'ha confrontato affermazione per affermazione con i test e col
    codice (12/10, 17:59): corrisponde.

  I test descritti entrano col treno 66 (`2aecd5a6f`, `e63cfb074`, `92fb9c83e`) e non sono nella mia base. Fra
  `bd8ee8e4d` e `dev_release2` (`b91d6d902`) nessun file di U-2 è cambiato, compresi i 4 cataloghi, quindi il merge è
  pulito.

### U-3 — Un catalogo per sottosistema e per plugin (chiuso il 12/10, checkpoint inviato)

- ✅ **Preparazione in sola lettura** (12/10, 21:30–21:40, prima del via), su sandbox estratte con `git archive` in `/tmp`.
  Dettaglio in `files/u3_prep.md`, mappe chiave → sorgente in `files/u3_dry/`.
  - **Dry run** (`files/scripts/u3_dry.py`) sul target `c57acf510` (treno 71) e sull'anteprima del treno 72 (il ramo di I,
    `0a148a109`):
    - l'**equivalenza** delle 4 lingue, chiavi e valori, è IDENTICA, e `check --strict --against` esce con 0;
    - il piano delle mosse è ancora valido: 71 frammenti, 219 chiavi, ogni prefisso col numero previsto, nessun plugin
      nuovo con chiavi;
    - `base` ha 288 chiavi, i 15 namespace del piano;
    - i 17 sottosistemi hanno i conteggi del §2.4, tranne `app` a 72 per `changelog.notTranslated`;
    - i file sono 356 JSON più 17 `prefixes.txt`.
  - **I tre cambi di I**: `importWizard.brokerMismatch.remove` e `.move` vanno in `importWizard`,
    `assets.probe.copyErrorDetail` va in `assets`.
  - **Le chiavi dichiarate nei metadati dei plugin** sono 130: 105 stanno nel frammento del loro plugin. Le altre 25
    stanno in un sottosistema:
    - 22 `risk.warnings.*`, in `risk`;
    - `signals.reference.zero`, condivisa da 8 plugin, e `signals.riskRollingReturn.*`, condivisa da 2, in `charts`.

    `rolling_return` e `calendar_rolling_return` quindi non hanno frammento.
  - **Chiavi di plugin usate per nome dall'interfaccia**: 9 `risk.analytics.*`, nel pannello del rischio.
  - **Prova sui chunk**: `files/scripts/locale_chunk_objects.py check-against <REV>`. Fa importare a Node i 4 chunk di
    lingua e li confronta, come oggetti, col catalogo alla revisione. Serve perché lo split cambia l'ordine delle chiavi,
    e quindi byte e nomi dei chunk. Collaudato sulla build di U-2 contro `c57acf510`: uguale.
- ✅ **Decisioni del coordinatore** (12/10, 21:39), annotate per il developer come informazione:
  - **D-U3-1**: le 22 `risk.warnings.*` restano nel sottosistema `risk`, come vocabolario unico degli avvisi;
  - **D-U3-2**: le 9 `risk.analytics.*` usate dall'interfaccia restano nei frammenti, come da piano;
  - il debito di U-2 sull'avviso di `add` (§2.3) si chiude in U-3;
  - il gate di proprietà R1–R4 lo scrive test-author.
- ✅ **Via** (12/10, 22:02): il treno 72 (lotto 48 di I + 2b di V) è nel target `0071b9703`. Il coordinatore mi ha portato
  a **`f16bb7958`**; il piano 45 resta sporco e entra nel primo checkpoint di U-3. Rispetto a `7a065caed` sono cambiati
  solo i 4 `base/<lang>.json` (lotto 48): 4 351 chiavi. T non aggiunge chiavi fino allo split.
- ✅ **L'avviso di `add`** (§2.3):
  - la nuova `base_namespace_notice(key, target, owners)` della libreria restituisce l'avviso quando una chiave apre un
    namespace nuovo in `base`;
  - `where()` lo aggiunge alla risposta;
  - `dev.py i18n add` lo stampa solo senza `--into`, perché un `--into` esplicito è già la scelta dell'autore.

  Il lint è pulito; in `i18n-audit.py` ruff e black restano invariati rispetto a HEAD.
- ✅ **Basi pre-split** su `f16bb7958` (`files/scripts/u3_base.sh`, 22:05–22:27, corsia 6174; conteggi in
  `files/u3_base_counts.tsv`):
  - backend:

    | Selettore | Passati |
    |---|---|
    | `runtime-isolation` | 167 |
    | `gate-i18n-usage` | 195 |
    | `gate-plugin-layout` | 33 |
    | `brim-degiro` | 169 |
    | `brim-providers` | 705 + 1 saltato |
    | `brim-scalable` | 145 |
    | `schemas risk` | 69 |
    | `risk-all` | 896 |
    | `signal-plugin-matrix` | 92 |

    `check-orphans` è verde, con 354 file Vitest.
  - `gate-i18n-catalog`: 162 passati e 1 rosso atteso. Il caso `test_where_…[a-new-key-for-base]` fissava `"(new key)"`,
    mentre ora `where()` aggiunge l'avviso del §2.3; l'aggiornamento è affidato a test-author;
  - `front check` 0/0; le 19 Vitest verdi, **11 134 test**;
  - `i18n audit`: 4 351 chiavi, 0 morte, 3 non verificate, 3 712 usate letteralmente;
  - il dead-code è identico alla validazione combinata.
- ✅ **Split applicato** (22:29, `files/scripts/u3_apply.py`, corsia ferma):
  - 17 `prefixes.txt`, con un'intestazione commentata;
  - `split`: 3 997 chiavi da `base` ai sottosistemi;
  - 71 `move`: 219 chiavi nei frammenti;
  - risultato: `base` 288 chiavi, 17 sottosistemi con 3 844, 71 frammenti con 219;
  - l'**equivalenza** con le sorgenti pre-split, nelle 4 lingue, chiavi e valori, senza ripiego, è **IDENTICA**.

  I file nuovi sono 369 (284 JSON dei frammenti, 68 JSON dei sottosistemi, 17 `prefixes.txt`); i modificati sono i 4
  `base/<lang>.json`. Ogni frammento conserva l'ordine delle chiavi di ciascuna lingua.
- ✅ **Prova** (`u3_gates.sh proof`):
  - `check --strict`: 4 351 chiavi, base 1, sottosistemi 17, plugin 71;
  - **`check --against f16bb7958`: identico nelle 4 lingue**;
  - la build legge 89 sorgenti e riscrive le 4 lingue: cambia solo l'ordine delle chiavi;
  - i file generati restano ignorati, le sorgenti nuove no.
- ✅ **Gate frontend dopo lo split** (`u3_gates.sh frontend`, 22:30–22:43), tutti uguali alla base pre-split:
  - `front check` 0/0;
  - **le 19 Vitest hanno i conteggi della base, azione per azione: 11 115 test**;
  - **i chunk di lingua** cambiano nome (`_e6AbF90.js`, `BfFDKEV1.js`, `pTQFMpK5.js`, `9ZmZb55i.js`), perché l'ordine
    delle chiavi è cambiato. Decodificati da Node, sono **uguali al catalogo a `f16bb7958`** e ai file generati;
  - `i18n audit` è identico alla base, con «4 351 keys from 89 source(s)» e «1 base, 71 plugin, 17 subsystem»;
  - il dead-code è identico: knip non segnala i JSON nuovi.
- ✅ **test-author** (22:40):
  - il nuovo `test_plugin_i18n_ownership_gate.py` (45 test) legge i registri veri e prova le regole R1–R4 in tutti e due
    i sensi, con una sentinella che fallisce se un registro pubblica un campo di chiave che il gate non legge. Sull'albero
    reale le 4 regole non trovano problemi: delle 261 chiavi dichiarate dai registri, 210 stanno nel frammento del loro
    plugin, 36 in `charts`, 15 in `risk`;
  - `test_i18n_catalog_gate.py` passa a 176 test: l'avviso di `base_namespace_notice` e `where()`, con il caso
    `[a-new-key-for-base]` aggiornato;
  - ruff e black puliti.
- ✅ **Registrazione** di `utils gate-plugin-i18n-ownership` (`isolation="pure"`) in `_backend_utils.py`, accanto a
  `gate-plugin-layout`. L'ho fatta io a corsia ferma, con sostituzione atomica, perché il runner importa il modulo a ogni
  avvio.
- ✅ **CLI sul layout nuovo** (`u3_gates.sh cli`, 22:44):
  - `where` nomina la sorgente giusta per una chiave di `base`, di sottosistema e di plugin;
  - una chiave nuova di plugin va nel suo frammento; una chiave con namespace nuovo va in `base` **con l'avviso del §2.3**;
  - `add` scrive in `assets` per una chiave di sottosistema e in `broker_directa/i18n` per una di plugin;
  - `search` mostra la colonna Source; `update` e `remove` funzionano;
  - `split` rilanciato risponde «Every key is already in place»;
  - **dopo il giro gli sha256 di tutte le sorgenti sono quelli di prima**;
  - `check` severo verde.

  La colonna Source di `search` andava a capo sui nomi di plugin: l'ho allargata da 28 a 40 caratteri.
- ✅ **Gate mirati dopo lo split** (`u3_gates.sh targeted`, 22:45–22:48), tutti verdi:
  - con gli stessi conteggi della base: `runtime-isolation` 167, `gate-i18n-usage` 195, `gate-plugin-layout` 33,
    `brim-degiro` 169, `brim-providers` 705 + 1 saltato, `brim-scalable` 145, `schemas risk` 69, `risk-all` 896,
    `signal-plugin-matrix` 92;
  - `gate-i18n-catalog` passa a **176**, cioè i 163 di prima più i casi nuovi;
  - il nuovo **`gate-plugin-i18n-ownership`** dà **45**;
  - `dev-cli-image` 31;
  - `check-orphans` è verde: ora 262 file backend, uno in più col gate nuovo.
- > **⚠️ Fuori pista, ambiente** (22:48–22:53): la prima `all-backend` è uscita dopo 5 minuti con «Shared backend did
  > not answer within 300s», prima di pytest. Il database era stato creato bene.
  > - **Causa**: all'avvio il server condiviso ha dovuto ricostruire il frontend in debug, perché l'ultima build, dei miei
  >   gate frontend, era di produzione. La build in debug è finita alle 22:52:14, come mostra `.build-debug`; poi uvicorn
  >   doveva ancora avviare l'app con load average 36, e i 300 s scadevano alle 22:53:30.
  > - Il server non ha lasciato processi, e la porta è libera.
  > - **Verdetto**: ambiente e lentezza, non U-3. La build in debug dura circa 3,7 minuti, come prima di U-3, e lo split
  >   non tocca ciò che svelte-check e Vite processano.
  > - **Rimedio**: con la build in debug ormai fresca, `all-backend` rilanciata senza altri cambi (22:55).
  > - **Per la prossima volta**: `all-backend` prima della build di produzione, non dopo.
- ✅ **`all-backend`, seconda prova** (22:55–23:41, 40 min 47 s): il server condiviso è partito senza ricostruire. 7
  categorie su 7, EXIT 0: **12 857 passati, 28 saltati, 0 falliti**. Rispetto alla `all-backend` finale di U-2
  (`bd8ee8e4d` + U-2), 21 invocazioni su 23 sono identiche; le 2 diverse sono spiegate per intero:
  - utils fa **+184**: +13 casi del gate catalogo, +45 del gate di proprietà, +126 dei test entrati col treno 66, che
    sono 94 della traduzione del CHANGELOG (`e63cfb074`) e 32 delle dipendenze di MathJax (`92fb9c83e`);
  - API fa **+4**: i 4 test nuovi di `test_auth_api.py` (`0d6aee67c`, le password fuori dall'event loop), del target.

  Conteggi in `files/u3_all_backend_counts.txt`; porta 6174 libera.
- ✅ **Controlli statici**: `git diff --check` è pulito. La libreria, i due gate e `_backend_utils.py` sono puliti con
  ruff e black, e la libreria resta compatibile con la sintassi 3.9. In `i18n-audit.py` ruff e black sono invariati
  rispetto a HEAD.
- ✅ **Manifest** (`files/u3_manifest.txt`): 9 file modificati e 370 nuovi (284 JSON dei frammenti, 68 JSON dei
  sottosistemi, 17 `prefixes.txt`, il gate di proprietà).
- ✅ **Commit proposti**:
  - `/tmp/libreFolio_commit_u3.txt`, «refactor(i18n): catalogue per subsystem and plugin»;
  - `/tmp/libreFolio_commit_u3_docs.txt`, per questo piano.
- ✅ **U-3 chiuso il 12/10.** Checkpoint mandato al coordinatore, stato FROZEN. Il prossimo passo è U-4, la documentazione.

### U-4 — La documentazione (prima parte chiusa il 13/10, checkpoint inviato; `i18n.md` dopo)

- ✅ **Via** (12/10, 23:48), dopo che U-3 è entrato nel treno 74 (`bcd502912`, commit `f2a394a0f` e `bcd4f6fe4`). Vincolo
  del coordinatore: **`developer/frontend/i18n.md` per ultima**. Il CP3a di T (`133259913`) aggiunge ~130 righe sulla
  regola dei numeri e delle date, ed è entrato col treno 75 (`104ba23d0`). Protocollo:
  1. checkpoint U-4 senza `i18n.md`;
  2. il coordinatore lo committa e mi porta il target;
  3. scrivo `i18n.md` sopra le righe di T.
- ✅ **Scansione aggiornata** sull'albero di oggi:
  - percorsi vecchi `<famiglia>/<nome>.py`: 25 file, più i 3 con segnaposto;
  - istruzioni sul catalogo e comandi `dev.py i18n`: `.github`, `dev_workflow.en.md`, `brim_plugin_guide.md`;
  - gate da elencare: `test-walkthrough/utils.md`.

  Le 4 pagine `day-count` erano già corrette (`18e872872`, «docs: point day-count at the plugin's module»).
  `admin/cli_tools.*.md` cita solo `i18n audit`, che resta valido. I test frontend che leggono `en.json` usano il
  catalogo generato, allo stesso percorso.
- ✅ **Nessun conflitto col ramo di T**: dei suoi 127 file, le doc sono solo `i18n.md` e `app-state.md`; niente `.github`,
  niente sorgenti del catalogo.
- ✅ **docs-writer**: 21 pagine MkDocs EN, nessuna con traduzioni, quindi nessuno stamp e nessun debito.
  - `registry_pattern.md` ha la scoperta riscritta per le cartelle, e cinque sezioni nuove a cui rimandano le guide:
    «Plugin Folder Layout», «Importing and Patching a Plugin», «A Plugin's Translations» (lo spazio di ogni famiglia e
    le chiavi condivise), «Adding a Plugin's Keys» (`add`, `--into`, `where`, `move` e l'instradamento) e «The Ownership
    Gate» (R1–R4, più il limite U-B1).
  - Le guide BRIM, asset, FX, segnali e tools, e le architetture di rischio e BRIM: cartella, traduzioni nel frammento,
    percorsi, passi «Adding a …».
    - L'esempio BRIM diventa `broker_mybroker`, perché il gate vuole il codice uguale alla cartella.
    - La guida asset nota che lo spazio usa il codice del provider, non la cartella (`yahoo_finance/` registra
      `yfinance`).
    - Gli FX non hanno chiavi.
  - Le correzioni di una riga: `provider_yahoo_finance`, `credit_agricole`, `danske_bank`, `scalable`, `ecb`,
    `risk-lab`, `data-quality-banner` (2 righe), `fx-chain-algorithm`, `runner_architecture`, `brokers/forms`,
    `provider_scheduled_investment` (dopo la scansione dei nomi nudi).
  - `dev_workflow.en.md`: il catalogo generato e i 13 comandi `dev.py i18n`.
  - `test-walkthrough/utils.md`: le righe di `gate-plugin-layout`, `gate-i18n-catalog` e `gate-plugin-i18n-ownership`.
  - `mkdocs build` (strict) senza avvisi; `check-links`: 95 validi, 0 rotti.
  - La riga «Plugin folder» della guida dei segnali usava i due spazi finali come a capo, e faceva fallire
    `git diff --check`: ora è un paragrafo a sé.
- ✅ **Scansione dei nomi nudi dei moduli** (`stress.py`, `ecb.py`, …), che la prima scansione non vedeva perché le
  mancava la famiglia nel percorso. Corretti:
  - 5 in `TODO_FUTURI.md`;
  - 1 nella skill `testing-backend`;
  - 1 pagina MkDocs, tramite docs-writer;
  - **14 nei commenti di 7 file E2E**, sempre `X.py` → `X/plugin.py`, con i numeri di riga invariati perché le rinomine
    di U-1 hanno contenuto identico: `risk-lab.spec.ts` (8), `risk-analysis.spec.ts`, `tx-bulk-import-handoff.spec.ts`,
    e i fixture della galleria `galleryOfflineData.ts` (2), `galleryProviderCompare.ts`, `galleryRiskLab.ts`.

  Prettier è verde sui 7 file E2E. Dopo, nessun percorso vecchio resta nelle doc, in `.github`, in `TODO_FUTURI.md` e
  negli E2E.
- ✅ **Backlog U-B7**: `dev.py i18n add` non conosce gli spazi dei plugin. Senza `--into`, la prima chiave di un segnale
  o di un tool nuovo va nel sottosistema. La soluzione è un avviso in `route()`.
- **Divergenze trovate da docs-writer, fuori da U**, passate al coordinatore:
  - `test-walkthrough/utils.md` e `dev_workflow.en.md` documentano `dev.py test utils --list`, che fallisce: il CLI
    vuole `<categoria> <azione> --list`, e lista i nomi dei test, non le unità;
  - `risk-lab.md:371` cita `L4Replay.svelte:203` per `excludedHeader()`, che è alla riga 204;
  - `runner_architecture.md:359` cita `asset_source.py`, ora uno strato di compatibilità su `asset_sources/core.py`.
    È una nota storica, lasciata così.
- ✅ **Checkpoint U-4, prima parte** (13/10): 46 file modificati, `git diff --check` pulito. Stato FROZEN.
  - Il prossimo passo è `developer/frontend/i18n.md`, sopra le righe di T, dopo che il coordinatore mi porta il target.
  - Poi U-5.
- ✅ **Mia parte** (`.github`, `TODO_FUTURI.md`, commenti E2E, backlog):
  - le istruzioni `backend-providers-{asset,brim,fx}` (tabelle «File», passi «Adding a New …» con cartella, `plugin.py`,
    import e patch, `i18n/` con `add --into`) e `backend-{risk,signals,tools}` («one folder per …», con le chiavi
    condivise che restano nel sottosistema);
  - le skill `asset-plugin`, `brim-plugin`, `risk-plugin`, `signal-plugin` e `tool-plugin`: percorsi, codice di
    riferimento, il passo delle traduzioni nel frammento;
  - `frontend.instructions.md`, sezione i18n e tabella «Where to Find Things»: il catalogo generato e le sorgenti;
  - la skill `devpy-i18n`: comandi, la sezione «The Catalogue: Sources and the Generated File», i gate, il formato,
    la regola 0 per le chiavi nuove, la `description`;
  - le 4 citazioni dei provider ECB e FED nell'agente historian;
  - 7 citazioni in `TODO_FUTURI.md`;
  - i commenti di `galleryPac.ts` e `risk-analysis.spec.ts`. Quest'ultimo citava `asset_risk_return.py:61`, già sbagliata
    prima dello spostamento: ora nomina `supported_scopes`/`supported_modes` in `…/asset_risk_return/plugin.py`;
  - nel backlog, U-B5 è chiusa per `day-count`; restano le pagine del devWiki.
