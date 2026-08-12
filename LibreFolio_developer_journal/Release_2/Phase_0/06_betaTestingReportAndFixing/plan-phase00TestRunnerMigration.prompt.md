# P8 — Migrazione del test runner a un'architettura parallelizzabile

> **Nasce da** [`plan-phase00FrontendCoverage.prompt.md`](plan-phase00FrontendCoverage.prompt.md)
> (P7), da cui eredita la macchina di coverage, e dai piani P1/P3 di beta testing: la scrittura
> massiccia di test E2E ha reso il tempo di corsa il collo di bottiglia.
>
> **Stato**: 🟢 **Tappa 0.3 e 0.4 completate** (bug di raggiungibilità corretto e presidiato).
> ⏳ Tappe 0.1–0.2 e 1–6 aperte.
>
> **Natura**: piano di **migrazione strutturale**, non di ottimizzazione mirata. L'obiettivo non è
> «rendere più veloce la corsa dei test» ma **separare tre responsabilità che oggi sono fuse in una
> sola funzione**, perché è quella fusione — non la mancanza di un flag — a rendere il parallelismo
> impossibile.

---

## 1. La tua domanda diretta: la coverage frontend non ha un suo database?

**No, e la differenza è strutturale — non è una svista da correggere.**

| | **Python** | **JS/Svelte** |
|---|---|---|
| Formato | **database SQLite** (`.coverage_data/backend`, `.coverage_data/frontend`) | **file JSON grezzi** V8, uno per `add()` (`coverage-js/e2e/raw/coverage-<random>.json`, oggi 109) |
| Contenuto | tabelle `file`, `line_bits`, `arc`, `context` — 243 file tracciati | dump di byte-offset dentro il **bundle compilato** |
| Accumulo | **nativo**: `--cov-append` e `coverage combine` | **nessuno**: i file vengono riprocessati e riproiettati sui sorgenti via source-map |
| Legame con il build | nessuno: i numeri di riga stanno nei `.py` | **totale**: gli offset valgono solo per *quel* bundle |

Da qui discende tutto il resto:

- **Python può accumulare**, quindi servono dei secchi separati (`backend` e `frontend`) e dei flag
  per svuotarli.
- **JS non può accumulare attraverso una ricostruzione.** Se i dati grezzi sopravvivessero a un
  rebuild del frontend, gli offset verrebbero riproiettati su sorgenti spostate e il report
  **mentirebbe senza fallire**. È il difetto che in P7 mi è costato più tempo (fuori pista 8).
  Per questo `_clean_js_coverage_dirs()` cancella `coverage-js/` **incondizionatamente** a ogni corsa
  con `--coverage js|all`: non è una dimenticanza, è l'unica politica sicura.

### Quindi: no, non esiste né un terzo né un quarto flag

Ce ne sono due, ed **entrambi puliscono coverage Python**:

| Flag | Cosa cancella davvero | Il nome è onesto? |
|---|---|---|
| `--cov-clean-backend` | `htmlcov-backend` + `.coverage_data/backend` — Python dai test backend | ✅ sì |
| `--cov-clean-frontend` | `htmlcov-backend-e2e` + `.coverage_data/frontend` — **Python dagli E2E** | ❌ no |

Il secondo nome è rimasto indietro rispetto a P7: là ho rinominato la **cartella**
`htmlcov-frontend` → `htmlcov-backend-e2e` proprio perché ingannava, ma il **flag** ha conservato il
nome vecchio. Oggi è l'unica cosa nel sistema che chiama «frontend» una misura di Python.

**Proposta**: rinominare `--cov-clean-frontend` → `--cov-clean-backend-e2e` (con alias deprecato);
lasciare `--cov-clean-backend` com'è; aggiungere `--cov-clean-js` **solo come utilità manuale**,
documentando che durante una corsa la pulizia avviene comunque da sola. Nessun flag per i vitest:
la loro coverage sta in `coverage-js/unit/`, sotto lo stesso ombrello.

### E una nota sulla metrica

Hai ragione: **«quanti test» e «quanto tempo» non sono comparabili** se cambia cosa si testa. Nel
resto del piano uso quindi **confronti a parità di test** e, dove non è possibile, lo dico. La
grandezza che conta davvero non è il tempo totale ma **il costo fisso per invocazione** — quello sì
confrontabile, perché non dipende da cosa c'è dentro il test.

---

## 2. Diagnosi: perché oggi non si può parallelizzare

Non è un problema di prestazioni. È che **una funzione-azione fa cinque mestieri insieme**:

```python
def front_fx_list(...):
    print_section("Frontend FX List Page Tests")   # 1. riporta
    if not _ensure_frontend_build(): return False  # 2. prepara l'ambiente
    if not _ensure_db_populated():   return False  # 3. prepara i dati
    if not _ensure_test_users():     return False  # 4. prepara gli utenti
    return _run_playwright("fx/fx-list.spec.ts")   # 5. esegue, in un processo suo
```

Ripetuta **219 volte** (148 backend + 71 frontend). Da questa fusione discendono, come conseguenze
necessarie, tutti i problemi:

| Conseguenza | Perché è inevitabile con questa struttura |
|---|---|
| **Il setup si ripete a ogni azione** | è dentro l'azione: non c'è un posto dove metterlo «una volta» |
| **Un processo per azione** | l'azione *è* la chiamata a `subprocess.run` |
| **Non si può schedulare** | nessuno sa cosa lancerà un'azione finché non l'ha lanciata |
| **Non si può isolare** | le risorse (DB, porta, file di coverage) sono globali e implicite |
| **`--resume` è per azione, non per test** | l'unità di riporto è l'azione, e coincide col processo |
| **Le liste `all` divergono** | sono scritte a mano perché non esiste un inventario da cui derivarle |

> Il parallelismo non è una funzionalità da aggiungere: è ciò che **emerge** quando le tre
> responsabilità — *cosa esiste*, *come raggrupparlo*, *come eseguirlo isolato* — vengono separate.
> Finché stanno fuse, qualunque `--workers N` sarebbe una toppa sopra una struttura che non lo regge.

### Il costo fisso, misurato

Ogni azione frontend paga, prima di provare qualunque cosa:

| Passo | Costo |
|---|---|
| `_ensure_db_populated()` | **8,56 s** |
| `_ensure_test_users()` — 8 sottoprocessi × 2,15 s | **~19 s** |
| `globalSetup` di Playwright: **rifà** popolamento + 3 utenti | **~15 s** |
| avvio/spegnimento del webServer | variabile |

Il database viene popolato **due volte per spec**, gli utenti creati **due volte per spec**: circa
**11 avvii a freddo di Python per ogni file di test**. Sul backend il costo fisso è più basso ma la
struttura è identica: **2,21 s** di sola importazione per ciascuna delle 148 invocazioni pytest.

Il confronto onesto, a parità di test, su `front-fx`:

> `./dev.py test front-fx all` esegue **42 test in 502,6 s** con 7 invocazioni Playwright.
> Una sola invocazione (`npx playwright test fx/`) esegue **quegli stessi 42 test più altri 21** —
> 63 in tutto — **in 218,6 s**.

Non è che il parallelismo manchi: è che **il 55–85 % del tempo non è tempo di test**.

---

## 3. L'architettura di arrivo

Tre livelli separati, con un contratto esplicito fra loro.

```
┌─ INVENTARIO ────────────────────────────────────────────────┐
│  Cosa esiste. Derivato, non scritto a mano.                 │
│  unità di test → { percorso, categoria, classe-isolamento,  │
│                    durata storica, risorse richieste }      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌─ POLITICA / SCHEDULER ───▼──────────────────────────────────┐
│  Come raggrupparlo. Input: inventario + --workers N.        │
│  Output: piano d'esecuzione (gruppi, ordine, risorse).      │
│  Rispetta le classi di isolamento. Bilancia per durata.     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌─ ESECUTORE + BROKER DI RISORSE ─▼───────────────────────────┐
│  Come eseguirlo. Ogni worker riceve un lotto di risorse:    │
│  { COVERAGE_FILE, DATABASE_URL, TEST_PORT, utente E2E }.    │
│  Restituisce esiti strutturati per unità, non per azione.   │
└─────────────────────────────────────────────────────────────┘
```

**Le 219 funzioni-azione non spariscono e non vengono riscritte**: smettono di essere *lanciatori di
processo* e diventano **selettori sull'inventario**. `./dev.py test front-fx fx-list` continuerà a
funzionare identico; cambia solo che chiede allo scheduler di eseguire un'unità invece di lanciare
`subprocess.run` da sé.

### 3.1 · Il concetto portante: le classi di isolamento

È la parte che risponde alla tua domanda sul frontend, e che **unifica backend e frontend sotto la
stessa regola**. Ogni unità di test dichiara *di cosa ha bisogno per non disturbare gli altri*:

| Classe | Significato | Può girare insieme a… | Risorsa dedicata |
|---|---|---|---|
| **PURE** | non tocca né DB né server | qualunque cosa, senza limite | solo `COVERAGE_FILE` |
| **READ** | legge dati condivisi, non scrive | altri READ, quanti se ne vuole, **sullo stesso backend** | nessuna |
| **WRITE-SCOPED** | scrive **solo** dati che appartengono al proprio utente/broker | altri WRITE-SCOPED **con un utente diverso** | un utente E2E |
| **WRITE-GLOBAL** | scrive superfici condivise (asset, FX, prezzi, impostazioni) | **niente** | un DB intero |

Questa non è una categoria inventata: viene dal **modello dati reale**, che ho verificato.

Su 12 tabelle, **solo 2 sono per-utente** (`UserSettings`, `BrokerUserAccess`). Le altre — `Asset`,
`Transaction`, `PriceHistory`, `FxRate`, `Broker`, `GlobalSetting`, `AssetEvent`,
`FxConversionRoute`, `AssetProviderAssignment` — **sono globali**. Le transazioni *sembrano*
per-utente ma non lo sono: `Transaction` non ha `user_id`, è legata a `broker_id`, e l'isolamento
avviene **a livello di servizio** (`transaction_service._get_accessible_broker_ids(user_id)`).

Da cui:

- un test che crea transazioni **sui propri broker** non disturba un test che usa broker di un altro
  utente → **WRITE-SCOPED**, parallelizzabile, e gli 8 utenti E2E già esistenti sono esattamente il
  lotto di risorse che serve;
- un test che crea un **asset** o cambia un **tasso FX** tocca una tabella globale → **WRITE-GLOBAL**,
  e come dici tu **deve restare seriale**, tanto più se ha bisogno di un `db populate` fresco.

> È il punto in cui la tua intuizione sul frontend e il difetto §5.2 sul backend si rivelano **lo
> stesso problema**: entrambi sono «scritture su superficie condivisa». Una sola regola li governa.

### 3.2 · Il broker di risorse

Un worker non riceve «il permesso di girare»: riceve un **lotto di risorse esclusive**.

| Risorsa | Oggi | Dopo | Serve a |
|---|---|---|---|
| `COVERAGE_FILE` | globale, con copia dentro/fuori di `.coverage` | `.coverage_data/parts/.coverage.wN` | **tutti** i worker |
| `DATABASE_URL` | `app.db` unico e condiviso | `app_wN.db` | WRITE-GLOBAL |
| `TEST_PORT` | `settings.TEST_PORT` fisso | `TEST_PORT + N` | worker backend con server in-process |
| utente E2E | tutti usano `e2e_test_user` | uno degli 8 utenti, per worker | WRITE-SCOPED |

La copia dentro/fuori di `.coverage` in `run_command` (righe 313–364) è **il punto di
serializzazione forzata** dell'architettura attuale: è un file globale mutabile, due processi non
possono condividerlo. Sostituirla con `COVERAGE_FILE` per worker + un `coverage combine` finale è
il singolo cambiamento che sblocca la coverage in parallelo — ed è **già stato provato** (§4).

### 3.3 · L'inventario deve essere derivato, non scritto

Oggi l'inventario **non esiste**: è disperso in 219 funzioni. Ho verificato che si può ricavare
senza eseguire niente, perché le funzioni-azione sono **produttrici di comando quasi pure**:
sostituendo `run_command` e `_run_playwright` con dei raccoglitori ho ispezionato tutte e 15 le
categorie `all` **senza lanciare un solo test**, in meno di un secondo.

È così che ho trovato il difetto §5.1. Ed è anche il meccanismo con cui lo scheduler saprà cosa
lanciare prima di lanciarlo.

---

## 4. Le prove sul campo

Nulla di quanto segue è una previsione.

### Frontend: il parallelismo funziona con **un solo** backend

Quattro spec di **sola lettura**, stesso backend, stesso DB:

| Configurazione | Tempo | Esito |
|---|---|---|
| 1 worker | **108,7 s** | 22 passati |
| 4 worker, parallelismo per file | 96,5 s | 22 passati |
| 4 worker, **`--fully-parallel`** | **74,1 s** | **22 passati** ✅ |

**1,47×** sul totale — e poiché ~35 s sono costo fisso di avvio, sul solo tempo di test è **~2×**.
Con `fullyParallel: false` il guadagno quasi sparisce (1,13×): il file più lento fa da pavimento.
**La tua intuizione è corretta e misurata**: più pagine sullo stesso backend, per i test di lettura,
funziona.

### Frontend: le scritture: il problema non è il parallelismo

Quattro spec di **scrittura** su transazioni:

| Configurazione | Tempo | Esito |
|---|---|---|
| 1 worker | 149,5 s | **1 fallito**, 28 passati |
| 4 worker `--fully-parallel` | **92,2 s** | **1 fallito**, 28 passati |
| `tx-delete` **da solo**, dopo `db populate` | — | **15 passati** ✅ |

Il risultato è più interessante di quanto sembri:

> Il rosso **c'era già a 1 worker**, ed è comparso **perché ho messo insieme quattro spec**. Il
> parallelismo a 4 vie **non ha aggiunto nemmeno un fallimento** — ha solo dato 1,62×.
>
> Quindi l'inquinamento **non è causato dal parallelismo: è causato dal consolidamento**. È lo stesso
> fenomeno del backend (§5.2), sullo stesso identico meccanismo — stato condiviso non ripulito — e va
> risolto comunque, anche se decidessimo di non parallelizzare nulla.

### Backend: il parallelismo rende, ma serve isolamento

| Prova | Esito |
|---|---|
| 2 processi su suite senza DB (`test_utilities` + `test_schemas`) | ✅ verdi |
| 4 processi su `test_services` (round-robin per nome) | **163 s → 85 s (1,9×)**, ma **2 falliti**, uno `database is locked` |
| Sbilanciamento dei gruppi round-robin | 83,7 s contro 32,2 s → **metà del guadagno teorico perso** |

### Coverage sotto parallelismo: verificata, non assunta

| Verifica | Esito |
|---|---|
| 2 processi pytest-cov con `COVERAGE_FILE` separato | exit `[0,0]`, 2 file integri da 110 KB |
| `coverage combine` sui due | «Combined 2 files», report 17,88 % coerente |
| `.coveragerc` | ha **già** `parallel = true` e `sigterm = true` |
| Coverage JS in parallelo | monocart scrive `coverage-<random>.json` a ogni `add()` → **i worker non possono collidere per costruzione** |

### Costo fisso, a parità di test

| Confronto | Risultato |
|---|---|
| `utils all` (12 invocazioni) vs un solo `pytest test_utilities/` | **32,6 s → 16,7 s** (stessi test) |
| 8 invocazioni vitest vs un solo `npx vitest run` | tutti i 630 test dei 56 file in **4,5 s** |
| avvio a freddo pytest (`--collect-only`) | **2,21 s** × 148 invocazioni |

---

## 5. Difetti strutturali trovati durante l'indagine

Non li cercavo. Sono tutti conseguenze della fusione descritta in §2.

### 5.1 · 259 test registrati che nessun `all` esegue — **è un bug, e va corretto subito** 🐛

Le liste `all` **frontend** sono scritte a mano: nessuno dei 9 moduli usa
`_get_category_tests_for_all()`, l'helper che le deriva dal registry — che invece il backend usa.

Cercando la deriva ho trovato **6 azioni registrate e irraggiungibili**, non 2:

| Azione | Categoria | Contenuto | Test | In `all`? |
|---|---|---|---|---|
| `fx-csv-import` | `front-fx` | `fx/fx-csv-import.spec.ts` | 21 | ❌ |
| `utilities` | `front-utility` | `utilities.spec.ts` | 32 | ❌ |
| `core-unit` | `front-utility` | 6 file vitest | ~70 | ❌ |
| `tx-unit` | `front-transaction` | 7 file vitest | ~90 | ❌ |
| `user-unit` | `front-user` | 2 file vitest | ~30 | ❌ |
| `store-unit` | `front-portfolio` | 2 file vitest | ~30 | ❌ |
| | | **totale** | **~273** | |

Verificato eseguendoli: **53 test E2E** (21 + 32 fra desktop e mobile) e **17 file vitest / 222
test**. Tutte e sei le azioni erano **regolarmente registrate** e invocabili a mano: solo, nessun
`all` le raggiungeva.

E c'è una nota rassicurante: **passano tutti**. Quindi la correzione non nasconde un debito, è pura
riconquista.

Su `gallery.spec.ts` (79 test) avevi ragione: è già escluso **esplicitamente** in `check-orphans`
(riga 198), con tanto di commento, perché lo esegue `./dev.py mkdocs gallery`. Quello è l'unico caso
corretto.

**E hai ragione anche sull'aspettativa**: `check-orphans` *avrebbe dovuto* vederli. Ho letto come
funziona (riga 141) e il motivo per cui non li vede è preciso — fa un **grep testuale** dei nomi
`*.spec.ts` dentro i file del runner:

```python
for m in re.finditer(r"([a-z_-]+\.spec\.ts)", content):
    registered_specs.add(m.group(1))
```

`fx-csv-import.spec.ts` **è** citato in `_frontend_fx.py`, come azione `fx-csv-import`. Quindi il
controllo lo considera registrato — e formalmente lo è. Verifica *la presenza della stringa*, non la
**raggiungibilità**. Sono due garanzie adiacenti, e i 259 test stanno esattamente nel buco fra le due.
Per i file vitest il controllo è ancora più debole: cerca i percorsi `*.test.ts` citati, e quelli
*sono* citati — dentro azioni che nessuno chiama.

> **Questo difetto ha due rimedi, e servono entrambi.**
> Il primo è **immediato e indipendente dalla migrazione**: rendere raggiungibili le 6 azioni,
> aggiungendole alle liste `all` (tappa 0.3). Sono 259 test che tornano a girare **subito**, senza
> aspettare nulla.
> Il secondo è **strutturale**: derivare le liste dall'inventario (tappa 1.4), così che «registrato
> ma irraggiungibile» smetta di essere uno stato esprimibile. Senza il secondo, il primo si
> ri-degrada alla prossima azione aggiunta a mano.

### 5.2 · Inquinamento dello stato condiviso ⚠️

`pytest test_services/` in **un solo processo** → **3 falliti, 2669 passati**; gli stessi tre
**passano isolati**. Causa: `UNIQUE constraint failed: fx_rates.date, fx_rates.base, fx_rates.quote`
— righe `('2025-02-01','EUR','USD')` lasciate da un test che committa.

Il meccanismo: la fixture `session` usa `get_async_engine()`, un **singleton di processo che punta al
file SQLite condiviso**, non a `:memory:`. Solo 16 file usano `:memory:`; **56 usano il file
condiviso**.

E come mostrato in §4, **lo stesso identico fenomeno esiste sul frontend**. Non sono due problemi: è
un problema solo, che il disegno attuale — un processo per azione — **nasconde**. Consolidare lo
**espone**.

> Come dici tu: se un'unità scrive su superficie condivisa **deve essere seriale**, a maggior ragione
> se pretende un `db populate` fresco. Nell'architettura di arrivo questo non è una rinuncia: è la
> classe **WRITE-GLOBAL**, dichiarata e rispettata dallo scheduler.

### 5.3 · Il fail-fast è incompatibile con un pool

`_run_test_suite` fa `break` al primo fallimento. Con N processi già avviati, «fermarsi» non può più
significare «interrompere». Va ridefinito — ed è esattamente ciò che hai chiesto (§6.2).

### 5.4 · La run cache non regge la scrittura concorrente

`mark_passed`/`mark_failed` fanno **leggi-modifica-scrivi** sull'intero `.run_cache.json`: due worker
che finiscono insieme si sovrascrivono. Nell'architettura di arrivo **scrive solo il padre**, e i
worker restituiscono esiti — che è anche ciò che serve per il `--resume` che hai chiesto (§6.3).

---

## 6. Il contratto della CLI

Le tre cose che hai chiesto esplicitamente, messe per iscritto perché sono **contratto**, non
dettaglio implementativo.

### 6.1 · `--workers N`, default **1**

- **`--workers 1` (default) = comportamento seriale.** Non «simile»: lo scheduler produce un piano a
  un gruppo, e il percorso è quello di oggi. È la via di fuga permanente, e va verificata a ogni
  fase.
- `--workers N` attiva il parallelismo, **rispettando le classi di isolamento**: un'unità
  WRITE-GLOBAL resta seriale anche con `--workers 8`.
- `--workers auto` → `cpu_count/2`, perché la macchina di sviluppo non è dedicata ai test.

### 6.2 · Comportamento sul fallimento

> «i task già avviati devono finire, ma non ne dovrebbero essere fatti altri»

- **Default**: al primo rosso lo scheduler **smette di assegnare nuovo lavoro**; i worker in corso
  **arrivano a fine lotto** e riportano. Nessuna terminazione brutale — anche perché uccidere un
  worker a metà **perde la sua coverage**, che è il modo in cui in P7 si perdevano dati in silenzio.
- `--no-fail-fast`: esegue tutto e riporta l'elenco completo dei rotti. Utile quando si vuole sapere
  quanto è ampio un danno invece di scoprirlo un pezzo per volta.

### 6.3 · `--resume` per unità, non per azione

Oggi la cache è indicizzata per *azione*: se un'azione contiene 20 test e ne fallisce uno, al riavvio
si rieseguono tutti e 20.

Dopo, la chiave è l'**unità di test** (file spec / file pytest), e l'esito arriva dai reporter
strutturati — `--junit-xml` per pytest, reporter JSON per Playwright. Riprendendo, **le unità già
verdi non vengono rieseguite**, comprese quelle finite in worker diversi da quello che ha fallito.

---

## 7. Il percorso di migrazione

Sei tappe. Ognuna lascia il sistema **funzionante e coerente**: si può fermare la migrazione dopo
qualunque tappa senza restare a metà del guado.

La **tappa 0 vale da sola**: contiene una correzione di bug (259 test che tornano a girare) che non
ha alcuna dipendenza dal resto del piano e può essere consegnata anche se la migrazione non partisse
mai. Se vuoi, si può fare quella e fermarsi lì a decidere.

### Tappa 0 — Correzione del bug, fotografia e rete di sicurezza

- **0.1** Cronometrare `all-backend` e `all-frontend` come sono oggi, con e senza `--coverage all`,
  conservando l'output. Serve come metro di paragone e come elenco degli esiti attesi.
- **0.2** Registrare **quali test passano oggi**, unità per unità. Senza questo, dopo non si
  distingue «rotto dalla migrazione» da «già rosso».
- **0.3** 🐛 **Correggere il bug di raggiungibilità** (§5.1) — *indipendente dalla migrazione,
  consegnabile da solo*. Le 6 azioni registrate ma mai eseguite vanno inserite nelle rispettive
  liste `all`:

  | Azione | Va aggiunta a | Test recuperati |
  |---|---|---|
  | `fx-csv-import` | `front_fx()` | 21 |
  | `utilities.spec.ts` *(serve anche l'azione: oggi non esiste)* | `front_utility_all()` | 16 |
  | `core-unit` | `front_utility_all()` | ~70 |
  | `tx-unit` | `front_transaction_all()` | ~90 |
  | `user-unit` | `front_user_all()` | ~30 |
  | `store-unit` | `front_portfolio_all()` | ~30 |

  Vanno eseguiti **prima** di inserirli, così un eventuale rosso è attribuito a loro e non alla
  migrazione. I 222 vitest sono già stati provati e sono **tutti verdi**; restano da provare i 37
  E2E.
- **0.4** **Rendere `check-orphans` capace di accorgersene**: aggiungere il controllo di
  raggiungibilità (ogni azione registrata è eseguita da un `all`?) accanto a quello di registrazione
  che già esiste. È il guardiano che impedisce la ricomparsa fra la tappa 0 e la 1.4, e serve
  comunque anche dopo. `gallery` resta esclusa esplicitamente, come già è.

> ### ✅ Tappa 0.3 e 0.4 — completate
>
> **Note implementazione**
>
> - **0.3 — esecuzione preventiva.** `fx-csv-import` → **21/21 verdi**; `utilities.spec.ts` →
>   **32/32 verdi** (desktop + mobile); i 17 file vitest → **222/222 verdi**. Il rischio §8 «il
>   wizard è stato riscritto senza che quel file girasse mai» **non si è materializzato**.
> - **0.3 — correzione.** Sei aggiunte, una per modulo:
>   `front_fx()` ← `fx-csv-import`; `front_utility_all()` ← `core-unit` + `utilities.spec.ts`;
>   `front_transaction_all()` ← `tx-unit`; `front_user_all()` ← `user-unit`;
>   `front_portfolio_all()` ← `store-unit`.
> - **0.4 — controllo di raggiungibilità.** Nuovo modulo `scripts/test_runner/_reachability.py` con
>   `collect_reachable()`: esegue le azioni `all` con i punti di lancio sostituiti da raccoglitori e
>   riporta cosa *verrebbe* lanciato. `_check_unreachable_tests()` in `_cli.py` lo confronta con i
>   file su disco; `check-orphans` ora esegue **entrambi** i controlli.
> - **Verifica finale**: 59 spec, 56 unit test, **175 file backend** — tutti raggiungibili.
>   `front-user all` eseguito end-to-end: 3/3, con «User Store Unit» ora presente nella suite.
>
> **⚠️ Fuori pista 1 — il collector ha cancellato il database di test.**
> `db_all` → `db_create` fa `TEST_DB_PATH.unlink()` *davvero*: non compone un comando, agisce. La
> prima passata di raccolta l'ha eseguito e ha svuotato `backend/data/test/sqlite/app.db`. Dato
> rigenerabile, nessun danno permanente, ma il difetto era serio perché **silenzioso**.
> Due rimedi, entrambi in piedi:
> 1. `_SIDE_EFFECTING` — `db create` e `db populate` vengono neutralizzate nel registry *e* nel
>    modulo che le definisce (le suite `all` tengono un riferimento diretto all'oggetto funzione,
>    quindi rattoppare solo il modulo non basta). Nessuna delle due esegue file di test: saltarle
>    non perde informazione.
> 2. **Guardia su `Path.unlink`** durante la raccolta, che solleva un errore con scritto cosa fare.
>    È la rete che copre le azioni *future*: verificata svuotando `_SIDE_EFFECTING`, il DB è
>    sopravvissuto e l'errore ha indicato il rimedio.
>
> **⚠️ Fuori pista 2 — il primo controllo dava 22 falsi positivi sul backend.**
> Là pytest viene invocato anche **per directory** (`test_services/test_financial/`), non solo per
> file. Il collector scartava i percorsi non-`.py`, quindi 15 file sembravano irraggiungibili.
> Corretto registrando anche le directory e considerando raggiunto ciò che sta sotto.
> Gli altri 7 falsi positivi erano `test_db_config.py`, `test_server_helper.py`, `test_utils.py`:
> **helper condivisi, non suite** — `pytest --collect-only` su di essi restituisce «no tests
> collected». La lista delle directory di suite è ora in `_BACKEND_SUITE_DIRS`, **condivisa** fra i
> due controlli perché non possano divergere.

### Tappa 1 — Costruire l'inventario *(nessun cambiamento di comportamento)*

- **1.1** Introdurre la struttura dell'unità di test: percorso, categoria, tipo di motore
  (pytest / playwright / vitest), classe di isolamento, durata storica.
- **1.2** Popolarlo con la **passata di raccolta** già provata: `run_command` e `_run_playwright`
  sostituiti da raccoglitori. Le eccezioni note (`db create`, `db populate`, `api_test` fanno lavoro
  vero, non solo comporre comandi) vanno riconosciute e marcate.
- **1.3** **Classificare** ogni unità. Le classi PURE e WRITE-GLOBAL sono deducibili staticamente
  (uso di `get_async_engine`, di `test_server_helper`, scritture su tabelle globali); la distinzione
  READ / WRITE-SCOPED va **dichiarata**, perché l'euristica testuale che ho provato dà 6 READ su 60 e
  sbaglia (classifica `fx-csv-import` come non-FX). Meglio un metadato esplicito e verificabile che
  un indovinello.
- **1.4** Far derivare le liste `all` dall'inventario, frontend compreso — così la correzione manuale
  della tappa 0.3 diventa **strutturalmente non ripetibile**: se le liste sono proiezioni
  dell'inventario, «registrato ma irraggiungibile» non è più uno stato che esiste.
- **1.5** Portare il controllo di raggiungibilità della tappa 0.4 **sull'inventario** invece che sul
  grep di stringhe, estendendolo anche ai file `*.test.ts` dei vitest. `gallery` resta esclusa
  esplicitamente, come già è.

> A fine tappa 1 il comportamento è **identico a oggi**. Cambia solo che il sistema *sa* cosa
> contiene. È la tappa che rende possibili tutte le altre.

### Tappa 2 — Estrarre il setup dall'azione

- **2.1** `_ensure_db_populated` / `_ensure_test_users` diventano operazioni del **livello risorse**,
  eseguite dal padre una volta per corsa. Le 8 creazioni utente diventano **una** invocazione batch
  invece di 8 avvii a freddo.
- **2.2** Rendere condizionale la parte duplicata di `globalSetup` (variabile `LF_SETUP_DONE`),
  **conservando** il percorso attuale per chi lancia `npx playwright test` a mano.
  ⚠️ `globalSetup` inizializza anche le impostazioni globali via API, cosa che il lato Python **non**
  fa: quella parte resta sempre.
- **2.3** Consolidare le invocazioni: una per categoria invece di una per azione (Playwright, pytest
  e vitest). **Attenzione**: è qui che l'inquinamento §5.2 emerge — la tappa 3 è il suo antidoto e le
  due vanno pianificate insieme.
- **2.4** Leggere i **reporter strutturati** (junit-xml, JSON) per ricostruire l'esito per unità. Non
  è un extra: senza, il consolidamento fa regredire `--resume` e il riepilogo.

### Tappa 3 — Bonificare lo stato condiviso *(prerequisito, non rifinitura)*

- **3.1** Rendere verde `pytest test_services/` in un solo processo: i 3 fallimenti da `fx_rates`.
- **3.2** Rendere verdi gli spec frontend **consolidati per categoria**, a partire dal rosso di
  `tx-delete` visto in §4.
- **3.3** Scegliere e **scrivere la regola**: o ogni test ripulisce ciò che scrive, o si passa a una
  fixture transazionale con rollback. La seconda è più robusta ma tocca 56 file: da decidere, non da
  dare per scontata.

> Questa tappa non produce nessun guadagno di velocità. Produce il **diritto** di parallelizzare — e
> va fatta comunque, perché §4 mostra che quei rossi esistono già oggi al primo consolidamento.

### Tappa 4 — Scheduler ed esecutore

- **4.1** Lo scheduler: inventario + `--workers N` → piano d'esecuzione che rispetta le classi.
- **4.2** Il broker di risorse: `COVERAGE_FILE` per worker (sostituendo la copia dentro/fuori di
  `.coverage`), e i lotti DB/porta/utente.
- **4.3** Politica di fallimento e run cache secondo il contratto §6.
- **4.4** **Attivare PURE + READ**: `test_utilities`, `test_schemas`, `test_external` sul backend;
  gli spec di sola lettura sul frontend con `--fully-parallel`. Sono i due insiemi già provati verdi.
- **4.5** Verifica: stesso numero di test, stessi esiti, **coverage combinata identica** alla
  sequenziale. Il confronto va fatto sui numeri, non sul «verde».

### Tappa 5 — Isolamento per worker: sbloccare le scritture

- **5.1** **Un DB per worker** per la classe WRITE-GLOBAL: `get_async_engine()` legge già
  `DATABASE_URL`; il worker N riceve `app_wN.db`, popolato una volta e poi **copiato per file**
  (copiare uno SQLite già popolato costa una frazione del ripopolarlo).
- **5.2** **Una porta per worker**: `test_server_helper.py` avvia uvicorn in un **thread dentro il
  processo pytest** — deliberatamente, perché `pytest-cov` veda gli endpoint
  (`concurrency = thread,gevent`). La porta è fissa, quindi due worker collidono; `TEST_PORT` è già
  una variabile d'ambiente, il gancio esiste.
- **5.3** **Un utente per worker** per la classe WRITE-SCOPED sul frontend: gli 8 utenti E2E esistono
  già. Va verificato caso per caso che gli spec candidati non assumano `e2e_test_user`.
- **5.4** Verificare `pytest_unconfigure`, che oggi forza `os._exit()` perché i thread di uvicorn non
  terminano mai: in un pool il codice di uscita deve arrivare al padre **dopo** il flush della
  coverage. È il difetto che in P7 perdeva dati in silenzio.

### Tappa 6 — Bilanciamento, flag, documentazione

- **6.1** Persistere le durate per unità (il junit-xml della tappa 2 le contiene già) e distribuire
  con *longest-processing-time first*: il round-robin ha perso metà del guadagno teorico.
- **6.2** Le rinomine dei flag di §1, con alias deprecato, e `--cov-clean-js`.
- **6.3** Aggiornare le skill `testing-backend` / `testing-frontend` e
  `runner_architecture.md` — quest'ultima va **riscritta**, non ritoccata: descrive un'architettura
  che non esisterà più.
- **6.4** Verifica finale: `--fresh-run --coverage all all` con `--workers 1` e con `--workers N`,
  confrontando numero di test, esiti e **percentuali di coverage**.

---

## 8. Rischi

| Rischio | Perché è reale | Mitigazione |
|---|---|---|
| **I 37 test E2E mai eseguiti potrebbero essere rossi** | `fx-csv-import.spec.ts` copre l'import CSV, e il wizard d'import è stato **riscritto** durante P1 e P3 senza che quel file girasse mai. È il candidato più probabile a essere marcito | Tappa 0.3 li esegue **prima** di inserirli in `all`; se sono rossi, la correzione diventa «bug + aggiornamento test», non «bug» soltanto. Non ho potuto verificarlo ora (richiede `db populate`, vietato in modalità piano) — **è la prima cosa da fare ad approvazione** |
| **La tappa 2 accende rossi che oggi non si vedono** | Misurato: consolidare 4 spec di scrittura produce 1 rosso a **1 worker** | Tappe 2 e 3 pianificate insieme; la 0.2 dice cosa era già rosso |
| **Coverage silenziosamente parziale** | Già capitato **due volte** in P7: merge a due passi e `gracefulShutdown` perdevano dati **senza fallire** | 4.5 e 6.4 confrontano le percentuali. Uno strumento di misura che non fallisce quando perde metà dei dati è peggio di uno che si rompe |
| **Classificazione READ/WRITE sbagliata** | L'euristica testuale sbaglia già su `fx-csv-import` | Metadato **dichiarato**, non dedotto; e un controllo che segnala le unità non classificate |
| **Rossi intermittenti sul backend** | Nella prova a 4 vie l'insieme dei falliti **è cambiato**, con un `database is locked` | Tappa 3 prima della 4; WRITE-GLOBAL seriale per definizione; `--workers 1` sempre verificato |
| **Migrazione lasciata a metà** | È il rischio tipico dei piani strutturali | Ogni tappa lascia il sistema coerente; la 1 non cambia comportamento, la 2 e la 3 danno valore anche senza parallelismo |
| **La macchina non è dedicata** | N worker su macchina carica peggiorano le race di timing — P7 ha mostrato quanto i test siano sensibili alla lentezza | `--workers auto` = `cpu_count/2`, non `cpu_count` |
| **`os._exit()` in `pytest_unconfigure`** | Salta i gestori d'uscita; con la coverage in mezzo è perdita di dati invisibile | 5.4 lo verifica esplicitamente |

---

## 9. Le due decisioni aperte

1. **La classificazione READ / WRITE-SCOPED va dichiarata a mano su ~60 spec.** È il costo vero della
   tappa 1: non è difficile, è noioso, e va fatto con attenzione perché una classificazione sbagliata
   produce rossi intermittenti — il tipo di guasto più costoso da diagnosticare. L'alternativa
   (dedurla) l'ho provata e non è affidabile. Terza via possibile: classificare **solo le unità che
   vogliamo parallelizzare** e lasciare tutto il resto in WRITE-GLOBAL (seriale) come default
   prudente, allargando l'insieme un pezzo per volta. **Propendo per questa.**

2. **`pytest-xdist` o esecutore artigianale?**
   xdist **non è installato** (ci sono pytest 9.1.1, pytest-asyncio 1.4.0, pytest-cov 7.1.0,
   coverage 7.14.3). È meno codice, ma il raggruppamento va espresso nelle sue strategie `--dist` e
   il controllo su `COVERAGE_FILE`, DB e porta diventa indiretto — e quelle tre cose sono
   esattamente ciò che qui va governato. In più xdist copre **solo pytest**, mentre Playwright e
   vitest hanno già i loro pool interni: servirebbe comunque uno scheduler sopra.
   **Propendo per l'esecutore artigianale**, che tratta i tre motori allo stesso modo.

---

## 10. Nota di metodo

Questo piano nasce da una domanda su come parallelizzare, e ha trovato per strada **259 test che
credevamo di eseguire e non eseguiamo** — invisibili a un controllo che esiste apposta per trovarli,
perché verifica la stringa e non la raggiungibilità. È un bug in senso stretto, e per questo la
tappa 0.3 lo corregge **subito**, senza aspettare il resto: vale da sola, anche se il piano si
fermasse lì.

Non è un caso isolato: è la stessa causa di tutto il resto. Quando l'inventario non esiste come
oggetto, ogni cosa che dovrebbe derivarne — le liste `all`, i controlli, lo scheduler — viene scritta
a mano, e ciò che è scritto a mano diverge in silenzio.

C'è anche una simmetria che vale la pena notare: **correggere il bug rende `all` più lento**, perché
aggiunge 259 test a ogni corsa. Le due metà del piano si sostengono a vicenda — la tappa 0 aggiunge
copertura, le tappe 4–6 pagano il conto.

Per questo il piano è di migrazione e non di ottimizzazione: il guadagno di velocità è una
conseguenza, non l'obiettivo.

A piano approvato, il documento è stato depositato nel journal come
`plan-phase00TestRunnerMigration.prompt.md`, con cross-link a P7 (da cui eredita la macchina di
coverage). L'aggiornamento passo-per-passo avviene qui, tappa per tappa.
