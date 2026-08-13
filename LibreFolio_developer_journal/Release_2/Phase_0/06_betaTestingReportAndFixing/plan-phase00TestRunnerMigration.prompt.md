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

> ### ✅ Tappa 1 — completata (1.1 → 1.5) e **2.1 anticipata**
>
> **Note implementazione**
>
> - **1.1 / 1.2 — l'inventario esiste.** Nuovo modulo `scripts/test_runner/_inventory.py`:
>   `TestUnit` (percorso, motore, categoria, azione, classe di isolamento) e `collect_launches()`,
>   che invoca ogni azione registrata con i punti di lancio sostituiti da raccoglitori.
>   Risultato: **294 unità, 0 errori di raccolta** — 170 pytest, 63 playwright, 61 vitest.
> - **1.3 — classificazione, con la terza via di §9.1.** PURE è *dimostrato* staticamente, tutto il
>   resto è WRITE-GLOBAL per difetto. Esito: **130 PURE / 164 WRITE-GLOBAL**.
>   La deduzione ingenua per-file non bastava: l'impurità è spesso **transitiva** (un test pulito che
>   importa un helper che punta al DB condiviso), quindi `classify()` segue anche gli helper locali
>   (`test_utils`, `test_db_config`, `test_server_helper`). Sono 2 unità che così passano da PURE a
>   WRITE-GLOBAL — poche, ma sono esattamente quelle che avrebbero prodotto rossi intermittenti.
> - **1.3 — verifica empirica, non solo statica.** I 65 percorsi pytest PURE eseguiti **in un solo
>   processo**: **1881 passati, 21 saltati, 0 falliti in 82,4 s**. È il caso in cui `test_services/`
>   consolidato produceva 3 rossi (§5.2), quindi la classificazione regge proprio dove il problema
>   si manifesta. Poi **su 4 processi concorrenti: 1881 test, tutti verdi, 41,5 s → 1,99×**, con la
>   stessa somma esatta (305+317+716+543). Lo squilibrio fra worker (40,9 s contro 14,1 s) conferma
>   già ora il bisogno di LPT (tappa 6.1).
> - **1.4 — le liste `all` sono derivate.** `_get_category_tests_for_all()` ora accetta i kwargs del
>   frontend e li filtra per firma; tutte e 8 le categorie frontend sono state convertite. Le liste
>   scritte a mano sono sparite: «registrato ma irraggiungibile» **non è più uno stato esprimibile**.
>   La conversione è stata verificata **prima** di applicarla, confrontando per ogni categoria
>   l'insieme dei lanci di oggi con quello derivato: **8 categorie su 8, insiemi identici**.
> - **1.5 — raggiungibilità sull'inventario.** `_reachability.py` è stato **eliminato**: era diventato
>   un duplicato della macchina di raccolta. `_check_unreachable_tests()` consuma ora
>   `reachable_paths()` / `on_disk()` / `is_covered()` dell'inventario, e `_BACKEND_SUITE_DIRS` ha
>   una sola definizione. Verifica: **59 spec + 56 vitest + 175 file backend**, tutti raggiungibili,
>   DB di test intatto.
>
> **⚠️ Fuori pista 3 — la 1.4 non era realizzabile senza la 2.1.**
> Derivare `all` dal registry significa che l'`all` chiama le *azioni*, e ogni azione fa il proprio
> setup: il conto sarebbe stato un `db populate` (8,56 s) e otto sottoprocessi utente (~19 s) **per
> ogni azione** — su `front-transaction`, 26 volte. La 1.4 da sola avrebbe reso `all` drammaticamente
> più lento.
> Rimedio: **anticipare la 2.1** in forma *scope-based*. `_SETUP_DONE` + `reset_setup_scope()` in
> `_frontend_common.py`: l'`all` apre lo scope, il primo `_ensure_*` lavora davvero, gli altri lo
> trovano caldo. Un'azione invocata da sola trova lo scope vuoto e si comporta **esattamente come
> oggi**; `all-frontend` riapre lo scope a ogni categoria, quindi anche lì il conto è quello di oggi.
> Una sola sottigliezza, gestita: `db populate` cancella gli utenti E2E, quindi popolare invalida il
> memo degli utenti.
>
> **Una verifica che ha cambiato il giudizio sul rischio.** Sembrava che memoizzare riducesse la
> freschezza del DB fra sotto-azioni — cioè che aprisse la porta all'inquinamento §5.2. Non è così:
> `globalSetup` di Playwright esegue `populate_mock_data --force --with-reports` **prima di ogni
> invocazione**, quindi la freschezza fra sotto-azioni E2E è garantita da Playwright, non dal lato
> Python. La memoizzazione toglie **solo** lavoro ridondante. È anche il motivo per cui la 2.2 va
> fatta con attenzione: è quel `globalSetup` a reggere oggi l'isolamento.
>
> **Verifiche end-to-end della derivazione**: `front-user` 3/3, `front-broker` 3/3 (22 test
> Playwright), `front-portfolio` 5/5 — e nei log **`Populating test DB` compare una volta sola** a
> fronte di 3–5 azioni.
>
> **Nota di progetto emersa dal `conftest.py` di root**: la fixture `restore_registration_setting` è
> `session`-scoped e `autouse`, e **scrive sul DB condiviso** a ogni sessione pytest. Il suo docstring
> cita già «a parallel Playwright run recreating the DB» come causa nota di guasti. È racchiusa in
> `try/except sqlite3.Error` e salta se il file non esiste, quindi degrada bene, ma va tenuta
> presente nella tappa 5: **anche un worker PURE tocca il file del DB, se esiste.**
>
> **Aggiunta al contratto del registry**: `add_test(..., in_all=False)` marca un'azione i cui test
> sono già eseguiti da un'altra (un alias aggregato, o un «concern» accorpato in un'unica
> invocazione). Serviva per `front-ai-export`, dove `cutover` esegue in un colpo i 4 spec che
> `panel`/`catalog`/`memory`/`contract` eseguono singolarmente: senza il flag, l'`all` derivato li
> avrebbe eseguiti **due volte**. La raggiungibilità non ne risente, perché ragiona sui *percorsi
> lanciati*, non sulle azioni — le due garanzie si compongono.

### Tappa 2 — Estrarre il setup dall'azione

- **2.1** ✅ *(anticipata nella tappa 1 — vedi fuori pista 3)* `_ensure_db_populated` /
  `_ensure_test_users` diventano operazioni del **livello risorse**, eseguite una volta per scope.
  Resta da fare: le 8 creazioni utente in **una** invocazione batch invece di 8 avvii a freddo
  (~19 s → ~2 s, ma ora si pagano una volta per categoria invece che una per azione).
- **2.2** Rendere condizionale la parte duplicata di `globalSetup` (variabile `LF_SETUP_DONE`),
  **conservando** il percorso attuale per chi lancia `npx playwright test` a mano.
  ⚠️ `globalSetup` inizializza anche le impostazioni globali via API, cosa che il lato Python **non**
  fa: quella parte resta sempre.

> ### ✅ Tappa 2.2 — completata
>
> `globalSetup` salta i punti 1 (popolamento) e 2 (utenti) quando trova `LF_SETUP_DONE=1`, che il
> lato Python imposta **solo** dopo che `_ensure_db_populated()` *e* `_ensure_test_users()` sono
> andati a buon fine. Il punto 3 — l'inizializzazione delle impostazioni globali via API — gira
> **sempre**: nessuno lato Python lo fa, e `populate --force` cancella quella tabella che il server
> semina solo all'avvio. Chi lancia `npx playwright test` a mano non ha la variabile e prende il
> percorso completo, invariato.
>
> **⚠️ Fuori pista 10 — il lato Python popolava *meno* del lato JS, e il flag l'avrebbe reso
> visibile.** `globalSetup` chiama `populate_mock_data --force --with-reports`; `_ensure_db_populated()`
> chiamava `db_populate(force=True)` e basta. Finché il JS rifaceva tutto da capo la differenza era
> invisibile — il popolamento buono arrivava comunque, secondo. Con il salto attivo sarebbe sparito
> il seeding dei file BRIM di esempio, e con lui i test di import-history dei broker: un rosso in una
> categoria che non c'entra niente con questa tappa.
> È il difetto tipico della deduplicazione — **si può togliere solo ciò che è davvero duplicato** —
> quindi prima ho reso il lato Python un superset (`with_reports=True`), poi ho tolto il doppione.
> Il valore residuo della tappa è comunque calato molto rispetto a quando è stata scritta: dopo la
> 2.3 `globalSetup` gira 16 volte invece di 120, quindi si risparmiano ~23 s × 16 e non × 120.
- **2.3** Consolidare le invocazioni: una per categoria invece di una per azione (Playwright, pytest
  e vitest). **Attenzione**: è qui che l'inquinamento §5.2 emerge — la tappa 3 è il suo antidoto e le
  due vanno pianificate insieme.
- **2.4** Leggere i **reporter strutturati** (junit-xml, JSON) per ricostruire l'esito per unità. Non
  è un extra: senza, il consolidamento fa regredire `--resume` e il riepilogo.

> ### ✅ Tappa 2.3 e 2.4 — completate (insieme, come previsto)
>
> **Il risultato in una riga: 120 invocazioni frontend diventano 16.**
>
> | Categoria | Playwright | vitest | invocazioni oggi | dopo |
> |---|---:|---:|---:|---:|
> | `front-ai-export` | 4 | 22 | 26 | 2 |
> | `front-asset` | 7 | 15 | 22 | 2 |
> | `front-broker` | 2 | 3 | 5 | 2 |
> | `front-fx` | 8 | 3 | 11 | 2 |
> | `front-portfolio` | 3 | 3 | 6 | 2 |
> | `front-transaction` | 25 | 7 | 32 | 2 |
> | `front-user` | 2 | 2 | 4 | 2 |
> | `front-utility` | 8 | 6 | 14 | 2 |
> | **totale** | **59** | **61** | **120** | **16** |
>
> Il costo fisso per invocazione (popolamento, otto utenti, `globalSetup`, avvio del webServer) si
> paga 16 volte invece di 120.
>
> **Note implementazione**
>
> - Nuovo `scripts/test_runner/_consolidate.py`. `group_frontend_units(scope)` deriva i gruppi
>   dall'inventario; `run_playwright_group()` e `run_vitest_group()` eseguono e **rileggono i
>   reporter JSON** per ricostruire l'esito **per spec**. Le azioni coperte finiscono in
>   `_SKIP_ACTIONS` e la passata seriale non le ripete.
> - **La 2.4 non è un accessorio della 2.3, è la sua condizione.** Senza rileggere il reporter, la
>   CLI direbbe «la categoria è rossa» invece di nominare la spec, e `--resume` ripartirebbe da una
>   categoria intera. Il riepilogo per azione resta identico a prima.
> - Una spec **assente dal report è contata come fallita**. Il silenzio non deve poter leggersi come
>   successo: è esattamente così che in P7 si perdeva metà della coverage senza che niente
>   diventasse rosso.
> - **Il consolidamento non si applica a un'azione singola.** `./dev.py test front-fx fx-list` resta
>   un'invocazione per una spec. Vale solo per `all` di categoria e per `all-frontend`, cioè quando
>   le azioni girerebbero comunque una dietro l'altra. `--no-consolidate`, `--test-names`, `--ui`,
>   `--headed` e `--debug` tornano alla forma 1:1.
> - Le azioni aggregate (che già lanciano più unità) sono lasciate stare: sono già consolidate.
>
> **⚠️ Fuori pista 7 — il consolidamento non rompe per chiavi duplicate, rompe per *inflazione di
> righe*.**
>
> Consolidando **tutte** le 25 spec di `transactions/` in una sola invocazione: **212 verdi, 3
> rossi, 19,8 min**. `tx-delete` era verde — la correzione della 3.2 regge anche con dieci spec
> davanti. I tre nuovi rossi, però, hanno rivelato un meccanismo che non avevo previsto:
>
> | Test | Perché fallisce |
> |---|---|
> | `tx-tooltips` › paired tooltip for hidden broker | scandisce **solo le prime 20 righe** (`Math.min(count, 20)`) cercando `access-test`: non ci arriva più |
> | `tx-split-promote` › Split from Main Table | cerca una riga appaiata nella **prima pagina**: è stata spinta fuori |
>
> Non è un vincolo violato, non è un dato sporco: è che **le fixture non sono più dove il test le
> cerca**. Le spec precedenti hanno creato transazioni senza rimuoverle, e cento righe nuove si
> ordinano davanti a quelle di `populate_mock_data`. Il guasto ha due proprietà sgradevoli: **accusa
> l'innocente** (fallisce chi legge, non chi ha scritto) e **dipende dall'ordine alfabetico dei
> file**.
>
> **Rimedio — la regola resa automatica invece che ripetuta a mano.** Applicare a mano
> `beforeEach`/`afterEach` a 59 spec avrebbe funzionato ed è ciò che la 3.3 prescrive, ma sarebbe
> stato 59 volte dimenticabile. Invece la garanzia sta in una **fixture automatica** in
> `e2e/fixtures/playwright.ts` (`txHygiene`, `auto: true`), accanto a quella della coverage JS.
>
> **⚠️ Fuori pista 8 — la granularità giusta è il *file*, non il test: misurato.**
> La prima versione fotografava gli id prima di **ogni test** e cancellava la differenza dopo. È la
> forma che viene naturale ed è **sbagliata**: le spec sono scritte in sequenza —
> `tx-commit-all-types` committa un BUY e poi ne vende una parte, `tx-delete` crea una coppia in un
> test e la cancella nel successivo. Ripulire fra un test e l'altro spezza quelle catene. Provata
> sull'intera directory `transactions/`: **da 3 rossi a 5**, e i due nuovi erano proprio SELL dopo
> BUY e la coppia di `tx-delete`.
>
> Il punto che mi era sfuggito: il consolidamento non ha tolto un reset *fra test* — quello non c'è
> mai stato. Ha tolto il reset **fra file**, perché prima ogni spec girava in un processo suo contro
> un database appena popolato. Quindi è esattamente quello, e nulla di più, che va ripristinato: lo
> stato si accumula liberamente dentro un file e viene annullato quando il file cambia (più una
> volta a fine worker, per l'ultimo file, che non ha un successore a fargli da innesco).
>
> Contesto API con login a livello di **worker**: un login per processo, due chiamate per file.
> Attiva **solo con `LF_TX_HYGIENE=1`**, che imposta la passata consolidata. La scelta è precisa e
> non è timidezza: l'invariante «il database è quello che `populate_mock_data` ha prodotto» va
> ripristinata **esattamente quando le spec se lo condividono**. Chi lancia una spec da sola prende
> il percorso di sempre, bit per bit.
> Una pulizia che fallisce **non fa diventare rosso il test**: inventare un rosso nell'innocente che
> è capitato di girare per primo è peggio del difetto che si sta curando.
>
> **⚠️ Fuori pista 9 — il consolidamento stava per dimezzare AI Export in silenzio.**
> `front-ai-export` è l'unica categoria che lancia le sue spec con `project=None`, cioè su **desktop
> e mobile**; tutte le altre solo su desktop. Raggruppare per sola categoria le avrebbe fatte girare
> con `--project=desktop`: metà dei test spariti, **e tutto verde**, perché ciò che resta passa. È lo
> stesso difetto di P7 (perdere dati senza fallire) con un altro vestito.
> Rimedio: l'inventario registra il `project` accanto a ogni unità Playwright e il raggruppamento è
> per `(categoria, project)`. Nello stesso passaggio è caduta anche l'euristica «vince la prima
> azione», che serviva a gestire l'alias `cutover`: ora un percorso può appartenere a **più azioni** e
> ognuna riceve il proprio verdetto dalla stessa corsa, invece che una vincere lo spec e l'altra
> essere rieseguita in seriale.
>
> **`--resume` conservato per unità.** La passata consolidata tiene un proprio spazio nella run cache
> (`consolidated:<categoria>`): le suite seriali sono indicizzate per **titolo umano** («Frontend
> User Tests»), scritto a mano dentro ogni `*_all` e non derivabile dal registry — prenderlo in
> prestito avrebbe voluto dire indovinarlo. Le unità già verdi non vengono rieseguite e restano
> comunque marcate come coperte, così nemmeno la passata seriale le ripete.
>
> Verifica: `tx-crud-full` + `tx-split-promote` + `tx-tooltips` consolidate → **15/15 verdi** (erano
> 3 rossi). Verifica finale sull'intera directory `transactions/` — **25 spec in una sola
> invocazione**:
>
> | | Prima della fixture | Con la fixture simmetrica |
> |---|---|---|
> | Esito | 3 falliti / 212 passati / 2 saltati | **1 fallito / 214 passati / 2 saltati** |
> | Tempo | 19,8 min | **18,7 min** |
>
> L'unico rosso rimasto è `tx-wac-mode` W9, **preesistente** e sul codice WAC già committato da
> un'altra linea di lavoro: segnalato, non toccato. Tutti i rossi che il consolidamento aveva acceso
> — `tx-tooltips`, `tx-picker-pagination` ×4, `tx-fx-implied-rate` ×2, `tx-split-promote` ×2,
> `tx-brim-import` T1 — sono spenti.
>
> **⚠️ Fuori pista 13 — un aiutante che falliva in silenzio.**
> `selectFirstAvailableFile()` in `tx-brim-import.spec.ts` aspettava 400 ms fissi e poi sondava la
> visibilità per 3 s **con `.catch(() => false)`**: se la lista dei file del broker non era ancora
> arrivata, non selezionava nulla e proseguiva come se niente fosse. Il rosso appariva una riga dopo,
> con scritto che `Parse (0)` era disabilitato — un messaggio che non nomina la causa. Solo il primo
> test del file pagava il caricamento a freddo, quindi T2–T8 passavano con lo stesso aiutante.
> Sostituito il sonnellino con un'attesa esplicita della riga (`toBeVisible`, 15 s) e un messaggio che
> dice cosa controllare. Un `catch` che ingoia un fallimento in un test è sempre un difetto: sposta il
> guasto lontano dalla sua causa.
>
> **⚠️ Fuori pista 11 — il ripristino andava fatto nei due versi, non in uno solo.**
> È la scoperta più istruttiva del piano, ed è arrivata da una misura, non da un ragionamento.
> La prima fixture cancellava le righe che una spec **aggiungeva**: metà dell'invariante. L'altra metà
> è che `tx-delete` **distrugge** righe del mock — di proposito, è il suo mestiere — e nessuna
> chiamata API può resuscitare una riga con il suo id originale e la sua metà di coppia.
>
> Il guasto che ne segue non nomina mai il colpevole:
>
> | | `tx-picker-pagination` da solo, DB fresco | `tx-picker-pagination` sul DB lasciato dalla suite |
> |---|---|---|
> | Esito | **5 passati** | **4 falliti** |
>
> Con meno righe in tabella, i primi due clic della spec cadono su una **coppia collegata**; la
> BulkModal la tratta come entità unica e apre da sé una FormModal; quattro test scadono cliccando un
> pulsante dietro il fondale di quella modale. Il messaggio d'errore parla di un `tx-form-modal` che
> intercetta i puntatori: nessun riferimento a `tx-delete`, che sta due file più in là in ordine
> alfabetico. Stessa famiglia dell'*inflazione di righe* già vista, ma **al contrario**: deflazione.
>
> Rimedio in `playwright.ts`: al cambio di file si confronta l'insieme degli id con la fotografia di
> partenza. Se ne manca anche uno solo → **ripopolamento completo**, reinizializzazione delle
> impostazioni globali (`initGlobalSetup()` estratta da `global-setup.ts` proprio per poter essere
> richiamata) e nuovo login del contesto API, perché dopo il ripopolo gli utenti hanno id nuovi e il
> cookie di sessione è scaduto. Se non manca nulla → si cancella solo la differenza, come prima.
>
> Due dettagli che non sono dettagli:
> - il ripopolo costa ~20 s e Playwright li addebita **al test in corso**, che gira a 25 s di budget.
>   `testInfo.setTimeout(+25 s)` viene applicato **solo quando il ripopolo è davvero avvenuto**: un
>   aumento indiscriminato nasconderebbe proprio le lentezze che quei timeout esistono per cogliere.
> - `populate_mock_data` ricrea da sé gli utenti E2E, ma **non** le impostazioni globali: quelle sono
>   l'unico pezzo di `globalSetup` che va rieseguito a mano.
>
> **⚠️ Fuori pista 12 — venti minuti di silenzio per un uvicorn mezzo morto.**
> Una corsa interrotta può lasciare uvicorn semi-spento ma ancora **in ascolto** su 6041: accetta le
> connessioni e non risponde a nulla — `/docs` e `/openapi.json` compresi, quindi è l'event loop, non
> un lock del database. `reuseExistingServer` lo riusa volentieri e Playwright resta appeso per sempre
> dentro la `fetch` **senza scadenza** di `globalSetup`, prima che il reporter abbia stampato una riga.
> Segno diagnostico: il processo node non ha **figli** e il log si ferma al banner di dotenv.
> Rimedio: `AbortSignal.timeout(20 s)` su entrambe le `fetch` di `globalSetup`, con un messaggio che
> dice cosa cercare invece di lasciare indovinare.


### Tappa 3 — Bonificare lo stato condiviso *(prerequisito, non rifinitura)*

- **3.1** Rendere verde `pytest test_services/` in un solo processo: i 3 fallimenti da `fx_rates`.
- **3.2** Rendere verdi gli spec frontend **consolidati per categoria**, a partire dal rosso di
  `tx-delete` visto in §4.
- **3.3** Scegliere e **scrivere la regola**: o ogni test ripulisce ciò che scrive, o si passa a una
  fixture transazionale con rollback. La seconda è più robusta ma tocca 56 file: da decidere, non da
  dare per scontata.

> Questa tappa non produce nessun guadagno di velocità. Produce il **diritto** di parallelizzare — e
> va fatta comunque, perché §4 mostra che quei rossi esistono già oggi al primo consolidamento.

> ### ✅ Tappa 3.1 — completata
>
> `pytest test_services/` in un solo processo: **3 falliti / 2669 passati → 0 falliti / 2672
> passati**, in 150 s. I tre rossi erano **due difetti distinti**, e il secondo non era affatto un
> problema di test.
>
> **Note implementazione**
>
> - **I due rossi da `fx_rates`** erano quelli previsti dal piano. La causa esatta: la fixture
>   `fx_asset_ids` di `test_asset_source.py` è **module-scoped** e **committa davvero** tre righe
>   `('2025-02-0{1,2,5}','EUR','USD')` via upsert, senza ripulire. Più tardi
>   `test_lots_analysis_service.py` fa un `session.add()` semplice sulla stessa chiave e sbatte
>   contro `UNIQUE constraint failed`. Corretto con un teardown dopo lo `yield`, che cancella le
>   righe `PriceHistory`, le tre `FxRate` e l'asset. I due file insieme: **80 passati**.
> - **Osservazione che decide la 3.3**: tutte le altre fixture `session` fanno già flush+rollback.
>   Gli unici colpevoli possibili sono quindi le fixture che **committano di proposito** — poche e
>   individuabili. Questo sposta il pendolo verso «chi committa, ripulisce» invece del refactoring
>   transazionale su 56 file.
>
> **⚠️ Fuori pista 6 — il terzo rosso era un bug di produzione in `NamedCache.clear()`.** 🐛
>
> `test_get_report_uses_layer2_cache` falliva **solo dopo** che girava
> `test_ai_export_components_asset_fx_integration.py` (trovato per bisezione su 79 file). Un plugin
> pytest che tracciava la cache L2 ha mostrato una cosa che escludeva ogni ipotesi sui dati: un
> `[L2 SET]` seguito **immediatamente** da un `[L2 GET]` con chiave **identica byte per byte** che
> restituiva `hit=False`. Non erano le impronte a divergere: era la cache a **non trattenere**.
>
> La causa, riprodotta in otto righe fuori da LibreFolio:
>
> ```python
> c = Cache(20)
> for i in range(40): c.set(f'k{i}', i, ttl=ttl)
> c.clear()
> c.set('nuova', 'v', ttl=ttl)
> c.get('nuova')          # -> (None, False)   e len(c) == 0
> ```
>
> `theine.Cache.clear()` (theine 2.0.0) svuota la mappa delle voci ma **non azzera il filtro di
> ammissione W-TinyLFU**, che conserva le frequenze delle chiavi appena buttate via. Da lì in poi
> ogni `set()` viene rifiutato in ammissione contro quei fantasmi e **la cache smette di essere una
> cache** — in modo definitivo e senza sollevare nulla. Soglia esatta misurata: **19 voci prima del
> clear si recupera, 20 (cioè `maxsize`) no**.
>
> Questo **non è un difetto dei test**. `clear_cache()` è esposto in amministrazione: in produzione,
> chiunque svuoti una cache la **disattiva per sempre** per la vita del processo, e l'unico sintomo
> è che le prestazioni peggiorano. È esattamente la classe di guasto che il piano P7 chiamava «una
> misura che perde i dati senza fallire».
>
> **Correzione**: `NamedCache.clear()` **ricostruisce** l'istanza sottostante invece di delegare a
> `theine.clear()`, chiudendo la vecchia perché il suo thread timer-wheel non resti appeso. Più un
> test di regressione, `test_clear_keeps_the_cache_usable_after_it_filled_up`, che riempie oltre
> `maxsize` prima di svuotare — la condizione senza la quale il difetto non si manifesta.
>
> È il secondo caso in questo piano in cui **consolidare non ha creato il guasto: lo ha reso
> visibile**. Un processo per azione lo teneva nascosto da mesi.

> ### ✅ Tappa 3.2 e 3.3 — completate
>
> **Il rosso di `tx-delete`, diagnosticato.** Riprodotto consolidando quattro spec di scrittura in
> una sola invocazione Playwright: **1 fallito / 36 passati**, sempre lo stesso — `A2-confirm:
> paired delete — confirm removes both halves`. Il test cancella la coppia ETH taggata
> `delete-safe` e verifica che non ne resti traccia; ne restava una.
>
> Restringendo a **due sole** spec (`tx-clone` + `tx-delete`) il rosso si è riprodotto identico: il
> colpevole è uno solo. `tx-clone.spec.ts::clone paired commit → pair created in DB with link`
> cerca «la prima coppia giver/receiver su broker modificabili» e ne **committa davvero** il clone.
> Quella prima coppia *è* la TRANSFER ETH `delete-safe` (IB↔Coinbase, entrambi modificabili).
> Risultato: due coppie identiche in tabella, `tx-delete` ne cancella una e trova l'altra.
>
> Nessun test era sbagliato. Sbagliato era il **contratto implicito** — «il database è appena
> popolato» — che reggeva solo perché ogni azione aveva un processo suo e `globalSetup` ripopolava
> prima di ognuna. Il consolidamento non lo viola: lo **smaschera**.
>
> **La regola scelta (3.3): chi committa, ripulisce.** Le alternative erano due e la scelta è stata
> guidata dai dati raccolti nella 3.1, non dal gusto:
>
> | | Fixture transazionale con rollback | Chi committa, ripulisce |
> |---|---|---|
> | File toccati | **56** | quelli che committano davvero — pochi e individuabili |
> | Copre il frontend? | **no**: gli E2E scrivono via HTTP, non c'è una sessione da annullare | **sì**, stessa regola per i due lati |
> | Rischio | riscrive fixture che oggi funzionano | nullo sui test che non scrivono |
>
> La 3.1 ha mostrato che **tutte** le fixture `session` fanno già flush+rollback: gli unici
> colpevoli possibili sono le fixture che committano *di proposito*. E il frontend non può avere un
> rollback, perché scrive attraverso l'API. Una regola sola che vale per entrambi i lati è
> preferibile a una che ne copre metà.
>
> **Note implementazione**
>
> - Nuovo `frontend/e2e/fixtures/db-cleanup.ts`: `snapshotTransactionIds()` e
>   `deleteTransactionsCreatedSince()`. Il meccanismo è **per differenza di id**, non per lettura
>   della risposta: si fotografa prima, si cancella ciò che è comparso dopo.
>   La scelta non è stilistica — coglie anche le righe create **indirettamente** (la seconda metà di
>   una coppia, una promozione, un evento derivato) che la spec non ha mai nominato, e sono proprio
>   quelle che ci si dimentica di ripulire.
> - `page.request` condivide il barattolo dei cookie del contesto browser e l'API autentica con
>   cookie di sessione: la pulizia gira già autenticata, senza doppio login.
> - Applicata a `tx-clone.spec.ts` con `beforeEach` (snapshot) / `afterEach` (pulizia), così la
>   garanzia vale **per ogni test** e non solo per quello che oggi sporca. Costo misurato: due
>   chiamate API per test, sotto la soglia del rumore.
> - Verifica: `tx-clone` + `tx-delete` consolidate → **20/20 verdi** (era 1 rosso / 19 verdi).
>
> **Il documento della regola** sta in `mkdocs_src/docs/developer/test-walkthrough/` (§ *Stato
> condiviso*), perché deve essere leggibile da chi scrive il prossimo test, non sepolto in un piano.

> **⚠️ Fuori pista 14 — la passata seriale ripopolava il DB per non eseguire niente.**
> Provando `run_consolidated()` **attraverso la CLI** per la prima volta (`./dev.py test front-user
> all`: 2 spec Playwright + 2 file vitest) tutto ha funzionato — ramo `LF_SETUP_DONE` incluso, con il
> messaggio «DB and users already prepared by the runner» — ma dopo il verde della passata consolidata
> la suite seriale ricostruiva il frontend, **ripopolava il database** e ricreava gli utenti, per poi
> annunciare `0/0 tests passed`. Dieci secondi per categoria, e in `all` sono otto categorie.
> Peggio dello spreco è la lettura del log: il ripopolamento compare **dopo** i test che usavano quel
> database, come se qualcosa fosse ancora in sospeso.
> Rimedio: `nothing_left_to_run(categoria)` in `_common.py`, chiamata per prima in tutte e otto le
> `*_all`. È volutamente tutto-o-niente: se anche una sola azione resta alla via seriale, si passa dal
> percorso normale con il suo setup completo.
>
> **⚠️ Fuori pista 15 — la guardia stava per riciclare un rosso in verde.**
> La prima versione di `nothing_left_to_run` restituiva `True` e basta: la categoria saltata risultava
> **passata**. Con `--no-fail-fast` la corsa stampava `✘ front-transaction tx-wac-mode` e venti righe
> più sotto **«🎉 ALL FRONTEND TESTS PASSED! 🎉»**. Il codice d'uscita è sempre stato corretto (1), ma
> un riepilogo che contraddice il codice d'uscita è peggio di nessun riepilogo — è il modo di guasto
> che questo piano vieta esplicitamente (§8, «coverage silenziosamente parziale»): *il silenzio non
> deve mai leggersi come successo*.
> Rimedio: `consolidated_verdict(categoria)` riporta ciò che la passata ha davvero trovato, e
> `_SKIP_ACTIONS` / `_FAILED_ACTIONS` restano **due insiemi distinti**, perché rispondono a due
> domande diverse — «è già stato eseguito?» e «è passato?». Confonderle è esattamente il meccanismo
> con cui un rosso diventa verde.
> Verificato nei due versi: con fail-fast si ferma prima della passata seriale; con `--no-fail-fast`
> arriva in fondo, nomina `tx-wac-mode` ed esce con 1.
>
> **Verifica di tutte e otto le categorie sotto consolidamento** (`./dev.py test --no-fail-fast
> all-frontend`), che era l'ultima incognita rimasta:
>
> | Categoria | Playwright | vitest |
> |---|---|---|
> | `front-ai-export` | 34 ✅ *(desktop **+** mobile)* | 185 ✅ |
> | `front-asset` | 85 ✅ | 203 ✅ |
> | `front-broker` | 31 ✅ | 26 ✅ |
> | `front-fx` | 63 ✅ *(include i 21 di `fx-csv-import` recuperati)* | 40 ✅ |
> | `front-portfolio` | 22 ✅ | 32 ✅ |
> | `front-transaction` | 214 ✅ / **1 ✘** | 130 ✅ |
> | `front-user` | 17 ✅ | 5 ✅ |
> | `front-utility` | 163 ✅ | 66 ✅ |
> | **totale** | **629 ✅ / 1 ✘** | **687 ✅** |
>
> Su ~1316 test un solo rosso, `tx-wac-mode` W9, preesistente e su codice non nostro. Le sette
> categorie mai provate sotto consolidamento **non hanno acceso nemmeno un rosso**: la fixture di
> igiene, scritta per le transazioni, si è rivelata sufficiente perché è l'unica superficie che gli
> spec si scambiano davvero. Il consolidamento resta quindi **attivo per tutte e otto** — non
> opt-in.

### Tappa 4 — Scheduler ed esecutore

- **4.1** Lo scheduler: inventario + `--workers N` → piano d'esecuzione che rispetta le classi.
- **4.2** Il broker di risorse: `COVERAGE_FILE` per worker (sostituendo la copia dentro/fuori di
  `.coverage`), e i lotti DB/porta/utente.
- **4.3** Politica di fallimento e run cache secondo il contratto §6.
- **4.4** **Attivare PURE + READ**: `test_utilities`, `test_schemas`, `test_external` sul backend;
  gli spec di sola lettura sul frontend con `--fully-parallel`. Sono i due insiemi già provati verdi.
- **4.5** Verifica: stesso numero di test, stessi esiti, **coverage combinata identica** alla
  sequenziale. Il confronto va fatto sui numeri, non sul «verde».

> ### ✅ Tappa 4 — completata (4.1 → 4.5), con **6.1 e 6.2 anticipate**
>
> **Note implementazione**
>
> - **4.1 — lo scheduler** (`_scheduler.py`). Decide cosa gira con cosa **solo** dalla classe di
>   isolamento, mai dal nome del test o dalla forma della directory. `--workers auto` = metà dei core.
> - **4.2 — il broker di risorse** (`_executor.py`). Oggi il lotto contiene una cosa sola,
>   `COVERAGE_FILE` per worker: è quella che sostituisce la copia dentro/fuori del `.coverage` globale,
>   cioè il punto in cui il disegno vecchio **imponeva** la serializzazione. La forma è già pronta a
>   ricevere DB, porta e utente. Aggiunti anche `-p no:cacheprovider` (i worker non devono contendersi
>   `.pytest_cache`) e `--cov-report=` (senza, ogni worker scriverebbe lo stesso `htmlcov-backend/`).
> - **4.3 — politica di fallimento.** Al primo rosso il padre non assegna altro lavoro ma **non uccide
>   nessuno**: i worker già avviati arrivano in fondo e riportano. `--no-fail-fast` esegue tutto.
> - **4.4 — PURE attivo**: 51 unità pytest su 170 lanci girano in parallelo.
> - **4.5 — verifica numerica, non «verde»**:
>
>   | Misura | `--workers 1` | `--workers 4` |
>   |---|---|---|
>   | `utils all` — test | **258** | **258** (160 paralleli + 98 seriali) |
>   | `utils all` — tempo | 31,8 s | **22,8 s** |
>   | `utils all` — coverage | **14,73 %** | **14,73 %** |
>   | `services all` — passata parallela | — | 44 unità / 1329 test in **41,5 s** |
>
>   La coverage è identica alla seconda cifra decimale: `coverage combine` sui file per worker non
>   perde nulla. Era la verifica che più contava, perché in P7 la coverage si è persa **due volte in
>   silenzio**.
>
> - **6.1 anticipata — bilanciamento LPT su misure vere.** Le durate non sono stimate spalmando il
>   tempo del gruppo sulle sue unità (spalmare cancella proprio le differenze su cui LPT lavora): ogni
>   worker scrive un `--junit-xml`, e da lì si leggono i secondi **per unità**. pytest lascia vuoto
>   l'attributo `file` ma riempie `classname` con il modulo puntato, che rimappa esattamente sul
>   percorso dell'unità. Le misure finiscono in `.coverage_data/unit_durations.json`.
> - **6.2 anticipata — rinomine dei flag.** `--cov-clean-frontend` → `--cov-clean-backend-e2e` con
>   alias deprecato, più `--cov-clean-js` come utilità manuale. Documentate in `index.md` e
>   `coverage-model.md`.
> - **6.3 parziale — `runner_architecture.md` riscritta**: inventario, classi di isolamento,
>   scheduler, esecutore, lotto di risorse, politica di fallimento, `--workers`.
>
> **⚠️ Fuori pista 4 — il primo `services all --workers 4` ha eseguito 350 test di troppo.**
> Verde, ma **3067 test contro 2717**: esattamente il tipo di guasto che il «verde» non vede e che il
> confronto numerico prende. La causa è che la regola «un'azione è coperta se tutti i suoi percorsi
> sono paralleli» è **necessaria ma non sufficiente**: ci sono 10 percorsi PURE che nessuna azione
> coperta lancia da sola e che vengono lanciati **solo** da azioni aggregate rimaste seriali —
> `risk-all` contiene 4 percorsi PURE più uno WRITE-GLOBAL, quindi resta seriale e li rilancia tutti.
> Girando anche in parallelo, quei percorsi giravano due volte.
>
> Serve la regola simmetrica: **un percorso lanciato da un'azione seriale non può girare in
> parallelo**. Le due regole si alimentano a vicenda (escludere un percorso può rendere seriale
> un'altra azione, che a sua volta esclude altri percorsi), quindi si applicano fino a **punto fisso**
> — che converge sempre, perché l'insieme seriale può solo crescere.
> Verificato analiticamente su tutte le categorie: **170 lanci a `--workers 1` = 170 lanci a
> `--workers 4`**, zero divergenze. Poi confermato eseguendo `services all`:
> **2717 test seriali = 1776 seriali + 941 paralleli**, esattamente.
>
> **Nota sul bilanciamento, misurata sulla seconda corsa.** La prima passata parallela di `services`
> ha chiuso in 41,5 s con i worker a 23,5 / 23,5 / 41,5 / 41,5 — le durate erano ignote e LPT
> ripiegava sulla mediana. Alla corsa successiva, con le misure vere in
> `unit_durations.json`, ha chiuso in **10,7 s con tutti e quattro i worker a 10,7 s**: l'unità più
> lenta è finita da sola in un gruppo e le 13-14 rapide negli altri. È il guadagno che il round-robin
> perdeva.
>
> Sul totale di categoria il guadagno resta però modesto — `services all` passa da **5m04s a 3m54s**,
> perché 31 azioni su 61 restano seriali. Non è una delusione: è la misura di quanto valga la
> **tappa 5**. Il parallelismo delle sole unità PURE è arrivato al suo limite.
>
> **⚠️ Fuori pista 5 — un rosso preesistente in `tx-wac-mode`.**
> Durante la verifica di `front-transaction all` (18/26 verdi, poi stop) è emerso
> `W9 — Focus and blur without editing stays in Auto mode`: dopo focus+blur senza modifiche il toggle
> risulta in **manual**, non in **auto**. **Non è causato dalla migrazione** — è deterministico anche
> eseguendo la spec da sola, e `WacPreviewSection.svelte` non è toccato dal working tree. È materia
> WAC/totali, quindi lasciato all'agente che ci sta lavorando: `handleValueChange` ha già la guardia
> «blur senza modifica non cambia modo» (riga 297), quindi il sospetto è che in quello scenario il
> `mode` non parta da `auto`.
> È esattamente la distinzione che la tappa 0.2 doveva permettere: **rotto dalla migrazione** contro
> **già rosso**.

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

> ### ✅ Tappa 5.4 — verificata, nessun intervento necessario
>
> Il rischio era plausibile ma non si materializza, e il motivo sta nell'**ordine dei gancio**, non
> in una precauzione presa da qualcuno.
>
> `pytest-cov` chiama `cov_controller.finish()` — cioè il salvataggio del file di coverage — dentro
> `pytest_runtestloop`, un hook che si chiude molto **prima** di `pytest_sessionfinish` e a maggior
> ragione prima di `pytest_unconfigure`. Quando il nostro `os._exit()` scatta, i dati sono già su
> disco da due fasi.
>
> Prova indipendente dalla lettura del sorgente: la tappa 4.5 ha confrontato la coverage combinata a
> 1 e a 4 worker su `utils` e ha ottenuto **14,73 % in entrambi i casi**. Se `os._exit()` troncasse
> il flush, quattro processi su quattro perderebbero dati e il totale scenderebbe. Non scende.
>
> Nessuna modifica a `conftest.py`: toccarlo per un difetto che non c'è avrebbe solo introdotto il
> rischio di reintrodurre l'attesa infinita sui thread di uvicorn.

> ### ⚠️ Tappa 5.1–5.3 — **non eseguite**, e due premesse del piano si sono rivelate false
>
> Le ho analizzate a lettura sola alla fine della 6.4, per poterle o fare o riprogrammare con
> cognizione. Vanno riprogrammate: due delle tre poggiano su affermazioni che il codice smentisce.
>
> **5.1 — «`get_async_engine()` legge già `DATABASE_URL`». Non è vero, e il gancio non esiste.**
> `get_settings()` **sovrascrive** `DATABASE_URL` a ogni chiamata con `get_database_url()`, che lo
> ricava da `get_data_dir()`. E `get_data_dir()`, in modalità test, ha questa forma:
>
> ```python
> # 1. Test mode → ALWAYS backend/data/test/ (no override)
> if is_test_mode():
>     return DEFAULT_TEST_DATA_DIR
> ```
>
> Il «no override» non è una svista: è la garanzia che una corsa di test non possa **in nessun caso**
> scrivere sui dati di produzione. Dare un DB per worker significa toccare **quella** regola — cioè
> allentare una protezione di produzione per far correre più in fretta i test. Non è una modifica da
> fare di iniziativa.
> Esiste però una forma che non la indebolisce: un override ammesso **solo se risolve dentro**
> `DEFAULT_TEST_DATA_DIR` (per esempio `LIBREFOLIO_TEST_WORKER=3` → `backend/data/test/w3/`).
> L'invariante «in modalità test non si esce mai da `backend/data/test/`» resta vera per costruzione,
> e in più si isolano anche upload e broker report, non solo lo SQLite.
>
> **5.2 — questa invece è quasi gratis.** `TEST_PORT` è un campo di `Settings`, quindi si popola
> dall'ambiente; `test_server_helper.py` fa `TEST_SERVER_PORT = _settings.TEST_PORT` all'import e i
> ~100 file di `test_api/` calcolano `API_BASE` dalla stessa fonte, sempre all'import. Basta metterlo
> nel lotto di risorse del worker in `_worker_env()`. L'unica coda da sistemare è il controllo di porta
> libera, che oggi guarda la sola 6041 e dovrebbe guardare l'intervallo.
>
> **5.3 — la premessa non regge più, perché nel frattempo è cambiata l'architettura.** «Un utente per
> worker per gli spec WRITE-SCOPED» presuppone più worker *sopra* Playwright. Ma il consolidamento ha
> stabilito la regola opposta — **mai due invocazioni Playwright insieme**: la concorrenza frontend
> vive **dentro** Playwright, con `fullyParallel`. Quindi non esiste il worker a cui assegnare
> l'utente. La versione sensata di 5.3 è un'altra cosa — un utente per *worker di Playwright*, dentro
> le fixture — e va ripensata da capo, non eseguita come scritta.
>
> **Quanto varrebbe.** Il grosso: oggi 3160 dei 4654 test backend restano seriali perché
> WRITE-GLOBAL, e la 6.4 mostra che il parallelismo delle sole unità PURE prende 7m49s su 38. Con un
> DB e una porta per worker il tetto si alzerebbe parecchio. È il pezzo di valore più grande rimasto
> nel piano — e anche il più rischioso, l'unico che tocca configurazione di produzione.
>
> **Decisione rimandata a te**, per la ragione detta sopra: il rimedio passa da un allentamento di una
> regola di sicurezza, e va deciso, non dedotto.
>
> ### ⚠️ Ma la tappa 5 non è la mossa giusta: il tempo non sta dove il piano credeva
>
> Prima di proporre l'isolamento per worker ho misurato **dove va davvero il tempo seriale**,
> ricostruendo le 90 invocazioni pytest dal log della corsa di chiusura. Il risultato ribalta la
> priorità:
>
> | | Invocazioni | Tempo | Test | s/test |
> |---|---:|---:|---:|---:|
> | `test_api/` | 47 | **15,0 min** | 564 | **1,59** |
> | tutto il resto seriale | 43 | 8,7 min | 1315 | 0,40 |
> | passata parallela (PURE) | — | 0,6 min | 1494 | **0,022** |
>
> `test_api` è **il 62 % del tempo per il 30 % dei test**, ed è quattro volte più lento per test di
> qualunque altra cosa seriale. Il motivo non è che quei test siano pesanti: è che **ognuna delle 47
> invocazioni avvia e chiude il proprio server uvicorn**. La fixture del server è a livello di modulo
> (`with _TestingServerManager() as server_manager`), e ogni invocazione è un processo nuovo che
> reimporta l'intera app FastAPI — registry dei provider compresi — prima di eseguire una dozzina di
> test. A 12 test per invocazione e 0,4 s/test di lavoro vero, **circa 11 dei 15 minuti sono avvio di
> server**.
>
> Quindi il guadagno maggiore rimasto **non richiede né un DB per worker né una porta per worker**:
> richiede di non avviare 47 server. È esattamente la mossa già fatta sul frontend con il
> `globalSetup` condizionale — consolidare le invocazioni — e costa una frazione del rischio, perché
> non tocca `config.py`, non tocca l'isolamento e non introduce concorrenza in scrittura.
>
> **Prima di provarci, però, c'è una mina da disinnescare.** `start_server()` chiama
> `_force_kill_port(6041)` quando trova la porta occupata, e `_force_kill_port` **non esclude
> `os.getpid()`**. Oggi non fa danni perché ogni invocazione ha un processo tutto suo; ma nel momento
> in cui due moduli `test_api` girassero **nello stesso** processo pytest, il secondo troverebbe la
> porta tenuta dal thread del primo, `lsof` restituirebbe il PID di pytest stesso e il processo si
> manderebbe un `SIGKILL` da solo. È un difetto latente che sta esattamente sul percorso
> dell'ottimizzazione più conveniente, e va corretto **per primo**.
>
> Nota collegata: `stop_server()` non ferma nulla — è documentato («With thread-based server, we can't
> gracefully stop it»), e va bene finché il processo muore subito dopo. Consolidando, quella
> premessa cade.

### Tappa 6 — Bilanciamento, flag, documentazione

- **6.1** Persistere le durate per unità (il junit-xml della tappa 2 le contiene già) e distribuire
  con *longest-processing-time first*: il round-robin ha perso metà del guadagno teorico.
- **6.2** Le rinomine dei flag di §1, con alias deprecato, e `--cov-clean-js`.
- **6.3** Aggiornare le skill `testing-backend` / `testing-frontend` e
  `runner_architecture.md` — quest'ultima va **riscritta**, non ritoccata: descrive un'architettura
  che non esisterà più.
- **6.4** Verifica finale: `--fresh-run --coverage all all` con `--workers 1` e con `--workers N`,
  confrontando numero di test, esiti e **percentuali di coverage**.

> ### ✅ Tappa 6.3 — completata
>
> `runner_architecture.md` era già stata riscritta (nota alla tappa 4); restavano indietro le due
> skill, ed erano indietro in modo asimmetrico: `testing-backend` citava `--workers` sette volte,
> `testing-frontend` una sola, e **nessuna delle due** nominava `--no-fail-fast`, `--no-consolidate`,
> `--cov-clean-js` o la rinomina `--cov-clean-backend-e2e`. Un audit di quattro righe l'ha mostrato
> in un colpo solo — cercare i flag invece di rileggere i documenti.
>
> - **`testing-backend`**: aggiunti i numeri della 6.4 (4654/4654, coverage identica, 38m52s →
>   31m03s, e il perché il guadagno si ferma lì), `--no-fail-fast`, e il riquadro sulla porta 6041.
> - **`testing-frontend`**: nuova sezione «Consolidation is on by default» con `--no-consolidate` e
>   l'avvertenza di non lanciare mai due Playwright insieme; nuova tabella dei tre flag di pulizia,
>   con la spiegazione del perché `--cov-clean-js` è solo un'utilità manuale e perché i vitest non ne
>   hanno uno proprio.
> - **`runner_architecture.md`**: aggiunta la tabella 1-vs-4 worker, il riquadro sulla porta 6041 e —
>   nella guida «come aggiungere un'azione» — un riquadro di pericolo che spiega che una lista `all`
>   scritta a mano non diverge fra un anno: **rilancia subito** ciò che i worker hanno appena
>   eseguito.
> - `test-walkthrough/index.md` era già allineato: tutti e sei i flag presenti, con l'alias
>   deprecato documentato.
>
> **⚠️ Fuori pista 18 — un import morto che indicava un difetto già corretto.**
> Il lint segnalava `from ._backend_external import external_all` inutilizzato in `_suites.py`: era
> il residuo di quando la suite globale trattava `external` come caso speciale. Rimosso. Le uniche
> segnalazioni rimaste in `scripts/test_runner/` sono le ~30 pre-esistenti, tutte F401 e tutte
> anteriori a questa migrazione.

> ### ✅ Tappa 6.4 — completata
>
> `./dev.py test --fresh-run --no-fail-fast --coverage py --workers {1,4} all-backend`, due corse
> complete a confronto:
>
> | | `--workers 1` | `--workers 4` |
> |---|---|---|
> | Test eseguiti | **4654** | **4654** |
> | Falliti | 0 | 0 |
> | Coverage | 37336 istruzioni, 3224 scoperte, **91,36 %** | 37336, 3224, **91,36 %** |
> | Tempo | **38 min 52 s** | **31 min 03 s** |
>
> A 4 worker i 4654 test si scompongono in **1494 nella passata parallela** e 3160 in quella seriale.
> La coverage non è «simile»: confrontata **file per file** su tutti e 241 i moduli, non differisce in
> nessuno. È la sola forma di verifica che valga qualcosa per uno strumento che può perdere dati senza
> fallire (§8) — e infatti è così che è saltato fuori il difetto qui sotto.
>
> **Il guadagno è modesto, e il motivo è istruttivo.** La passata parallela esegue 51 unità PURE —
> 1494 test — in **32,2 s**, con i quattro worker che finiscono a 32,2 / 32,1 / 32,1 / 32,1 s: il
> bilanciamento LPT su durate misurate è praticamente perfetto. Ma quelle 51 unità sono un terzo dei
> test e una frazione molto minore del tempo: il grosso della corsa è WRITE-GLOBAL e resta seriale
> **per costruzione**. 7 min 49 s su 38 è ciò che si può prendere senza toccare l'isolamento; il
> resto richiede la tappa 5.1 (un database per worker), che il piano lascia deliberatamente aperta.
>
> ### La corsa di chiusura: backend **e** frontend insieme
>
> Le due tabelle qui sopra riguardano il solo backend. La verifica vera —
> `--fresh-run --no-fail-fast --coverage all --workers 4 all`, cioè tutto in un comando solo, cosa mai
> fatta prima — ha richiesto due giri, perché il primo ha scoperto l'OOM del *fuori pista* 19.
>
> | | Prima corsa | Corsa di chiusura |
> |---|---|---|
> | Tempo | 83 min 50 s | **83 min 12 s** |
> | Rossi | **4** (`tx-delete`, `tx-fx-implied-rate`, `tx-wac-mode`, `settings`) | **1** (`tx-wac-mode` W9) |
> | OOM / SIGABRT | 2 / 2 | **0 / 0** |
> | Coverage Python | 3220 scoperte, **91,38 %** | 3122 scoperte, **91,64 %** |
> | Test | — | **6031 passati**, 1 fallito, 31 saltati |
>
> **La riga della coverage è la più importante di tutta la tappa, e va letta con attenzione**: la corsa
> di chiusura copre **98 istruzioni Python in più** pur eseguendo esattamente lo stesso lavoro. Non è
> rumore — il rumore misurato al *fuori pista* 17 vale 4 istruzioni, non 98 — ed è di segno opposto a
> quello che ci si aspetterebbe.
> La spiegazione è che i tre spec che morivano di OOM esercitavano il backend attraverso gli E2E, e la
> loro coverage **spariva insieme al processo**. Il difetto non stava solo facendo fallire dei test:
> stava **falsando la misura**, e verso il basso, in silenzio. È la terza volta in due piani (P7 due
> volte, qui una) che un guasto si manifesta come «coverage un po' più bassa» invece che come errore —
> ed è il motivo per cui §8 insiste sul confrontare i numeri e non il colore.
> Il tempo, a parità di risultato, è invariato: i tre `globalSetup` in più dei lotti sono compensati
> dai tre worker che non muoiono più a metà.
>
> **⚠️ Fuori pista 16 — 28 test giravano due volte, e li ha trovati un conteggio che non tornava.**
> Il primo confronto dava 4654 contro **4682**: 28 test in più a 4 worker. Poiché la coverage era
> identica, la spiegazione doveva essere una duplicazione, non un test in più.
> Ricostruendo i conteggi per invocazione, tutte le differenze erano della forma «girato nel
> pre-pass», tranne una: `test_external/test_fx_providers.py` — **28 test** — compariva sia fra le 51
> unità parallele sia nella passata seriale.
> Causa: `external_all()` era **l'unico `*_all` del backend a costruire la lista a mano** invece di
> usare `_get_category_tests_for_all()`, e quindi l'unico che non filtrava `_SKIP_ACTIONS`. È
> esattamente il difetto §5.1 in un'altra veste: ciò che è scritto a mano diverge in silenzio.
> Rimedio: `external_all` deriva la lista dall'helper come le altre quattro categorie. Il
> comportamento è invariato (stesse 4 azioni, stessi nomi, stessi parametri `providers` /
> `exclude_providers` filtrati per firma), ma ora rispetta i salti. Verificato con una terza corsa
> completa a 4 worker: `test_fx_providers.py` compare **solo** nel pre-pass, e il totale è tornato a
> 4654 — 3160 seriali + 1494 paralleli.
> Vale la pena notare *come* si è visto: non da un rosso — non c'era — ma da **due numeri che
> dovevano coincidere e non coincidevano**. Senza il confronto a parità di test della 6.4, questo
> sarebbe rimasto un doppio giro invisibile per sempre.
>
> **⚠️ Fuori pista 17 — la coverage ha un pavimento di rumore, e si sa esattamente dove.**
> La terza corsa ha chiuso a 3220 istruzioni scoperte invece di 3224: **quattro in meno**, cioè
> *più* coperte, pur avendo eliminato un'esecuzione doppia — causalmente impossibile se il numero
> fosse deterministico.
> Il confronto file per file lo localizza senza ambiguità:
>
> | File | w1 | w4 | w4 (terza corsa) |
> |---|---|---|---|
> | `asset_source.py` | 99 scoperte | 99 | **98** |
> | `asset_source_providers/borsa_italiana.py` | 82 | 82 | **79** |
> | *tutti gli altri 239 file* | — | — | **identici** |
>
> Sono i due moduli che **parlano con internet dal vivo**. Il numero di test e di skip è lo stesso in
> tutte e tre le corse (`33 passed, 3 skipped`): non è cambiato *cosa* si esegue, è cambiato *quale
> ramo* ha preso il provider a seconda di come ha risposto il sito. Le prime due corse, lanciate a
> pochi minuti l'una dall'altra, coincidevano cifra per cifra; la terza, ore dopo, no.
> Conseguenza pratica per chi userà questo confronto come test di accettazione: **la coverage è
> deterministica per tutti i 239 file locali, e ha un rumore di ~4 istruzioni (0,01 %) confinato ai
> provider di rete**. Un confronto va fatto per file, non sul totale: sul totale il rumore è
> indistinguibile da una perdita di dati, per file è immediatamente attribuibile.
>
> ### La corsa completa: `--coverage all --workers 4 all`
>
> Il backend e il frontend erano stati verificati **separatamente**. La 6.4 chiede la corsa intera, e
> farla ha avuto senso: **83 min 50 s**, e ha acceso due difetti che nessuna delle due metà aveva mai
> mostrato. Nessuno dei due riguarda il parallelismo; entrambi riguardano la **combinazione**
> consolidamento + coverage JS, che prima non era mai esistita.
>
> Vale la pena notare l'ordine di esecuzione, perché leggendo il log sorprende: le due passate
> anticipate — quella parallela del backend e quella consolidata del frontend — girano **entrambe
> prima** della suite seriale. Quindi si vedono i test frontend prima di quelli backend, e la suite
> seriale che segue è quasi tutta backend, con le 8 categorie frontend che si fanno da parte.
>
> **⚠️ Fuori pista 19 — il consolidamento più la coverage JS esauriva la memoria di Node.**
> Quattro rossi frontend, di cui due segnalati in **0 ms**: non un'asserzione fallita, un processo
> morto. Il log lo dice esattamente:
>
> ```
> FATAL ERROR: Ineffective mark-compacts near heap limit - JavaScript heap out of memory
> Error: worker process exited unexpectedly (code=null, signal=SIGABRT)
> ```
>
> **La prima diagnosi era giusta ma parziale, e la seconda corsa l'ha smentita.** La fixture
> costruiva una nuova istanza monocart **per ogni test** — `MCR(options)` è un costruttore, non un
> singleton, e alla prima `add()` risolve le sourcemap dell'intero build. Finché Playwright partiva
> una volta per spec il processo moriva dopo una dozzina di istanze; con il consolidamento un solo
> worker esegue i 25 file di `transactions/` di fila. Ho reso l'istanza una **fixture di worker** e
> alzato l'heap a 8 GB come rete di sicurezza — e ha **ri-esaurito la memoria lo stesso**, a 8181 MB
> dopo 988 s. Rinviare un guasto non è correggerlo, e la prova l'ha detto subito.
>
> La causa vera sta in quattro righe di `monocart-coverage-reports/lib/index.js`:
>
> ```js
> const { cacheName, cachePath } = Util.getCacheFileInfo('coverage', dataId, this.options.cacheDir);
> this.fileCache.set(cacheName, results);              // ← in memoria, per sempre
> await Util.writeFile(cachePath, JSON.stringify(results));  // ← e anche su disco
> ```
>
> `add()` scrive il payload su disco **e** ne tiene una copia in una `Map` d'istanza, con una chiave
> nuova a ogni chiamata. Non è un difetto di monocart: è un'ottimizzazione per chi chiama `add()` e
> `generate()` **nello stesso processo** — `generate.js` legge da `fileCache` se la chiave c'è, e
> altrimenti rilegge lo stesso file da disco.
> Da noi quei due momenti non condividono mai un processo: la fixture aggiunge soltanto, e il report
> lo produce dopo `scripts/mcr-generate.js`. Quindi ogni voce trattenuta è un payload V8 completo —
> sorgenti e sourcemap incluse — conservato per un lettore che non lo guarderà mai.
> Rimedio: `mcr.fileCache?.clear()` subito dopo `add()`. Le due modifiche curano due metà diverse
> dello stesso sintomo — e **nessuna delle due lo elimina**.
>
> **La misura lo dice chiaramente, e vale la pena leggerla per intero:**
>
> | Configurazione | Tetto raggiunto | Dopo quanto |
> |---|---|---|
> | 25 spec, istanza MCR per test, heap di default (~4 GB) | ~4 GB | ~700 s |
> | 25 spec, istanza per worker, `--max-old-space-size=8192` | 8181 MB | 988 s |
> | 25 spec, + `fileCache.clear()` | 8174 MB | **1214 s** |
> | **8 spec**, stesse due correzioni | — | **nessun OOM**, 163 test verdi in 7,8 min |
>
> Alzare l'heap e liberare la cache **spostano il momento, non lo tolgono**: ogni correzione ha
> comprato quattro-cinque minuti. La riga che chiude la questione è l'ultima: a parità di codice, un
> gruppo da 8 spec arriva in fondo e uno da 25 no. **La grandezza che conta non è cosa fa un singolo
> test, è quanto a lungo vive il processo.**
>
> Rimedio strutturale, quindi, e non l'ennesima caccia dentro monocart: quando la coverage JS è
> attiva, un gruppo viene **spezzato in lotti da 8 spec** (`_JS_COVERAGE_CHUNK` in `_consolidate.py`).
> È una decisione dello *scheduler* — quanto lavoro sta in un processo — non dell'esecutore, e infatti
> vive nel punto di chiamata, non dentro `run_playwright_group()`.
> Il guadagno del consolidamento resta quasi intatto: `front-transaction` passa da **25 invocazioni a
> 4**, non da 25 a 1.
>
> **Verifica**: `front-transaction all --coverage js` in 24m31s — 4 lotti (92 + 65 + 51 + 7 test) più
> 130 vitest, **zero OOM**, 287 file raw di coverage e tutti e tre i report prodotti. Il costo dei tre
> `globalSetup` in più è di circa un minuto e mezzo in tutto, contro una corsa che prima non arrivava
> in fondo.
> Il dettaglio che conferma la diagnosi meglio di qualunque conteggio di memoria: l'unico rosso
> rimasto, `tx-wac-mode` W9, adesso fallisce a **10,5 s** invece che a `0ms`. Non è più un processo che
> muore addosso a un test qualunque — è un'asserzione che non passa, quella già nota sul codice WAC.
>
> È la stessa forma di guasto già vista tre volte in questo piano: **il fallimento nomina la vittima,
> mai la causa**. Il worker muore mentre gira un test qualunque, e il rosso finisce su `tx-delete` o
> su `settings.spec.ts`, che non c'entrano nulla.>
> **⚠️ Fuori pista 20 — un file del Finder fermava l'intera corsa.**
> Al primo rilancio il comando è morto in 2,4 s, prima di eseguire un test, con un traceback:
> `OSError: [Errno 66] Directory not empty: frontend/coverage-js`.
> `shutil.rmtree` elenca la cartella, cancella quello che ha visto, poi fa `rmdir` — e macOS ci
> aveva infilato un `.DS_Store` nuovo nel frattempo, perché il Finder stava guardando quella cartella.
> Finestra di pochi millisecondi, effetto totale.
> Rimedio: tre tentativi a 200 ms di distanza e, se ancora non va, un errore **esplicito** che dice
> cosa fare. Non un `ignore_errors=True`: non pulire la coverage JS deve restare rumoroso, perché
> offset V8 vecchi riproiettati su un bundle ricostruito danno un report sbagliato **senza essere
> rotto** — il difetto che in P7 è costato di più.

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
