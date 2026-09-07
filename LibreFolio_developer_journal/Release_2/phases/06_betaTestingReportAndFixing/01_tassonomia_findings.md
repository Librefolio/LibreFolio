# Tassonomia dei rilievi — Beta Testing 05/08/2026

> Classificazione completa dei **34 rilievi** emersi dalla sessione con Marco.
> Ogni voce riporta: evidenza `file:riga`, causa radice, verdetto di verifica, e il piano di destinazione.
> Fonte: [`00_20260805_betaTester_report.md`](00_20260805_betaTester_report.md).

**Metodo di verifica**: ogni rilievo è stato tracciato staticamente nel codice sorgente.
Il verdetto è **CONFERMATO** solo se esiste un'evidenza `file:riga` che spiega il sintomo.
I rilievi contraddetti dal codice sono isolati in §5 e **non** sono stati pianificati.

| Verdetto | Conteggio |
|---|---:|
| ✅ CONFERMATO | 30 |
| ⚠️ PARZIALE (sintomo reale, causa diversa dall'ipotesi) | 2 |
| ❌ SMENTITO (codice contraddice il report) | 2 |
| ➕ Scoperti in analisi (non nel report) | 3 |

---

## 1. 🔧 Problemi del plugin (BRIM Crédit Agricole) → **P1**

> Tutti i rilievi di questa sezione, tranne B4/B8, discendono da **una sola causa radice**.

### 🔴 B1 — La causale `COMPRAVENDITA TITOLI/FONDI/OPZIONI` non è gestita

**Verdetto**: ✅ CONFERMATO — **causa radice primaria dell'intera sessione**.

`_classify_account_row` (`broker_credit_agricole.py:591-629`) mappa esplicitamente solo
commissioni/imposte, redditi e canoni. Tutto il resto cade nel ramo finale:

```python
# Everything else (incl. the cash side of trades) -> deposit/withdrawal by sign.
if amount > 0:
    return TransactionType.DEPOSIT, Currency(code=currency, amount=abs_amt)
return TransactionType.WITHDRAWAL, Currency(code=currency, amount=-abs_amt)
```

Il commento `(incl. the cash side of trades)` rivela l'assunzione errata: si presuppone che il
lato titoli dell'operazione arrivi **sempre** dal file *Deposito Titoli*. Quando l'utente importa
solo estratti conto — o estratti conto che coprono periodi non coperti dal Deposito Titoli — la
compravendita **sparisce**: la posizione non viene mai aperta e la cassa viene decurtata come se
fosse un prelievo verso l'esterno.

Osservazione del tester che centra il punto: *"ad ora ho verificato che se non presenti li prende
come deposito e prelievo, ed ecco perché andava in negativo!!!"*

**Impatto misurato — 4 righe su 4 perse:**

| Riga | Data | Descrizione | Importo | Ctv carico (Excel) |
|---:|---|---|---:|---:|
| 211 | 05/11/2025 | `SOTTOSC SICAV ORD.:2025/003955841 AMUNDI PIO GLOB EQ G` | −20.129,44 | 20.129,41 |
| 282 | 28/07/2025 | `NOTA INF. ACQ. TIT:BTP 1/3/32 1,65%` | −46.603,73 | 46.177,79 |
| 283 | 28/07/2025 | `NOTA INF. ACQ. TIT:BTP 01/03/35 3,35%` | −50.683,13 | 50.018,11 |
| 392 | 25/02/2025 | `NOTA INF. ACQ. TIT:BTP PIU 25-2-33 CU` | −15.000,00 | 15.000,00 |

Il tester ne aveva corrette 3 a mano. La quarta (**BTP 01/03/35**) no → è il buco da ~50k.

→ **P1 / B1**

---

### ➕ B5 — Il nominale è recuperabile *in-file* (abilitatore, scoperto in analisi)

**Verdetto**: ➕ SCOPERTO IN ANALISI — cambia radicalmente la qualità della fix di B1.

Il nome nella riga d'acquisto **combacia in prefisso** con quello delle cedole dello stesso
titolo, e le cedole portano **ISIN + `NOMINALE`**:

| Acquisto (troncato dall'export) | Cedola | ISIN | Nominale |
|---|---|---|---:|
| `BTP 1/3/32 1,65%` | `BTP 1/3/32 1,65%` | IT0005094088 | 50.000 |
| `BTP 01/03/35 3,35%` | `BTP 01/03/35 3,35%` | IT0005358806 | 50.000 |
| `BTP PIU 25-2-33 CU` | `BTP PIU 25-2-33 CUM` | IT0005634792 | 15.000 |

Quindi per le obbligazioni il plugin può risolvere **quantità e ISIN in automatico**, senza
chiedere nulla all'utente.

**Il pattern esiste già nel file**: `_parse_account_movements` costruisce `income_identity_by_date`
(`broker_credit_agricole.py:695-720`) proprio per recuperare ISIN + nominale dalle cedole, e lo usa
per le scadenze. È coperto da test (`test_brim_providers.py:886`, *"identifiable maturity closes WAC
cost basis"*). La fix consiste nel **generalizzare quell'indice da per-data a per-nome**, non nel
progettare un meccanismo nuovo → rischio basso, coerenza architetturale alta.

→ **P1 / B5** *(prerequisito di B1 e B3)*

---

### 🟠 B2 — Rateo e commissioni incorporati nel prezzo d'acquisto

**Verdetto**: ✅ CONFERMATO.

L'estratto conto espone **un solo importo** che accorpa prezzo secco, rateo d'interesse e
commissioni. Confronto con l'Excel della banca:

| Titolo | Cassa uscita | Ctv carico | Differenza (rateo + comm.) |
|---|---:|---:|---:|
| BTP 1/3/32 1,65% | 46.603,73 | 46.177,79 | **425,94** |
| BTP 01/03/35 3,35% | 50.683,13 | 50.018,11 | **665,02** |
| BTP PIU 25-2-33 | 15.000,00 | 15.000,00 | 0,00 *(emissione alla pari)* |

Il tester lo aveva colto: *"purtroppo accorpano commissione e acquisto, bisogna flaggare anche
questo per farlo correggere all'utente; come fallback va bene mettere tutto nell'acquisto, ma da
segnalare"* — e ha dovuto creare a mano la transazione di commissione per il fondo Amundi.

**Conseguenza contabile**: registrando tutto nell'acquisto, il nostro costo di carico risulterà
**superiore** a quello della banca dell'importo del rateo. È accettabile come fallback, ma va
dichiarato — altrimenti la prossima riconciliazione fallirà di nuovo, per un motivo diverso.

→ **P1 / B2**

---

### 🟠 B3 — Quantità non estraibile per fondi/SICAV

**Verdetto**: ✅ CONFERMATO.

Per `SOTTOSC SICAV ... AMUNDI PIO GLOB EQ G` non esiste alcuna cedola da cui dedurre una quantità
(i fondi non staccano cedole con `NOMINALE`), e la descrizione non riporta né quote né NAV.
B5 quindi **non** si applica: la quantità è genuinamente assente dal dato.

Tester: *"per amundi pio dai movimenti conto non sembra si possa estrarre la quantità associata,
solo l'ammontare economico, bisogna far flaggare e chiedere all'utente di inserire la quantità
giusta"*.

**Il meccanismo esiste già**: `BRIMFieldTodo` (`backend/app/schemas/brim.py:382-402`) ha
`severity: Literal["blocker","warning"]`, `reason_code`, `message` e `context` per l'i18n, con
semantica documentata *"blocker means Step 4 cannot proceed without resolution"*. Serve solo
emetterlo — **nessuna modifica di schema**.

→ **P1 / B3**

---

### 🟡 B4 — Le ritenute sulle cedole non vengono mai registrate

**Verdetto**: ➕ SCOPERTO IN ANALISI (il tester lo aveva intuito: *"credo mancano anche le varie tasse"*).

Le cedole sono importate **al netto**. La descrizione contiene però tutti gli addendi:

```
CEDOLA:BTP PIU 25-2-33 CUM IT0005634792 ... NOMINALE: 15.000,00 TASSO: 2,85 ALIQ: 12,50 RITENUTA: 13,36
```

Verifica: `15.000 × 2,85% ÷ 4 = 106,88` lordo − `13,36` ritenuta = **93,52** = l'importo importato. ✅

Il plugin ha regex per `NOMINALE` (`_ACCOUNT_NOMINALE_RE`) ma **nessuna** per `RITENUTA`.

**Impatto misurato**: **56 righe cedola/dividendo su 56** espongono `RITENUTA`, per un totale di
**2.203,42 €** di imposte oggi invisibili. Sono dati fiscalmente rilevanti già presenti nel file.

→ **P1 / B4**

---

### 🟡 B6 / B7 — Warning: livello INFO mancante e righe non citate

**Verdetto**: ✅ CONFERMATO.

Il warning sulla successione (`broker_credit_agricole.py:550-553`) è puramente aggregato:

```python
f"{succession_count} righe di successione (GIRO ALTRO DOSSIER / VERS.TITOLI) importate come RETTIFICA senza cassa ..."
"Ogni gamba conserva il proprio prezzo tramite cost_basis_override; ..."
```

Due problemi distinti:

1. **Non cita le righe** — eppure `offset` è in scope nello stesso ciclo, e i warning fratelli
   nello stesso file usano già `f"Riga {offset}: ..."` (righe 446, 725, 747). Il pattern è già la
   prassi del file: manca solo qui, perché `succession_count` è un intero invece di una lista di righe.
2. **La parola "gamba"** non comunica che si tratta di un trasferimento titoli di cui tracciamo
   solo metà. Va riscritta in linguaggio d'utente.

→ **P1 / B6, B7** *(il livello INFO lato schema è W8, in P2)*

---

### ➕ B8 — Buco di copertura: il caso è nel fixture, ma nessun test lo asserisce

**Verdetto**: ➕ SCOPERTO IN ANALISI.

Il fixture `sample_reports/credit_agricole-conti.csv` **contiene già** una riga con la causale
incriminata:

```
21/05/2026;...;COMPRAVENDITA TITOLI/FONDI/OPZIONI;NOTA INF. ACQ. TIT:BTP SAMPLE DOSS:...;'-15.000,00;EUR
```

Nessun test la asserisce: `test_credit_agricole_account_deposits_withdrawals_by_sign`
(`test_brim_providers.py:878`) verifica solo `PENSIONE` (deposito) e `UTILITY` (prelievo).
Il bug è quindi passato attraverso una suite verde per costruzione: **il dato c'era, l'asserzione no**.

> Stessa famiglia dei difetti censiti in `05_cleanAudit/17_stabilizzazione_suite_completa.md`:
> *un controllo che non può fallire non è un controllo*.

→ **P1 / B8**

---

## 2. 🐛 Anomalie UI (difetti)

| ID | Rilievo | Evidenza | Verdetto | Piano |
|---|---|---|---|---|
| **W1** | Conteggio asset non deduplicato: `14 (37)` | `ImportWizardModal.svelte:199-216`; `uniqueAssetIds` deduplica i `fake_asset_id`, che però **collidono** tra file perché ogni parse riparte da `FAKE_ASSET_ID_BASE`; il secondo numero è un `.filter().length` piatto | ✅ | P2 |
| **W2** | Stesso asset duplicato nello step 4, con e senza ISIN | `mergeAllTransactions()` `:698-816` — la chiave di merge **non** è ISIN né nome: ogni coppia `(file, fake_id)` è rimappata su un contatore nuovo (`:706`, `:766`). I due layout CA producono lo stesso titolo una volta senza ISIN (`_parse_securities`) e una con (`_parse_account_movements`) | ✅ | P2 |
| **W3** | Il riepilogo non sottrae le transazioni rimosse | `parseAggregateStats` è `$derived` solo da `parseResults` (grezzo); la risoluzione duplicati scrive su `duplicateResolverSelections`/`mergedTransactions` — **due alberi di stato disgiunti**, mai collegati | ✅ | P2 |
| **W4** | Tipi transazione in inglese nel riepilogo analisi | `ParseDetailModal.svelte:181` — `<span>{type}</span>` senza `$t()`. Altrove (`TransactionTypeBadge`) la chiave `transactions.types.*` è usata correttamente: è un singolo punto sfuggito | ✅ | P2 |
| **W6** | "Annulla" non riporta l'asset a neutro | `resolveAssetManual` `:896-899` assegna **prima** di aprire la modale; il tasto Annulla `:3833-3839` fa solo `identifierPromptOpen = false` e non chiama `clearResolution()` (che esiste, `:823-825`) | ✅ | P2 |
| **W7** | Dopo l'assegnazione, non tutte le transazioni si auto-selezionano | `selected` è impostato **una volta sola** al merge (`:793`), mai rivalutato. La logica corretta esiste già in `recheckOpenings()` `:1466-1469` ma è invocata solo dal ricalcolo data di apertura, mai da `resolveAsset`/`resolveAssetManual`/`clearResolution` | ✅ | P2 |
| **A1** 🔴 | **Impossibile selezionare un asset disattivato** | `AssetSelect.svelte:66,73` → `disabled: a.active === false`; `SearchSelect.svelte:241` → `if (option.disabled) return;`. L'asset è visibile ma non cliccabile | ✅ | P3 |
| **A2** | Modale ISIN spuria se l'ISIN è già tra gli identificativi alternativi | `checkAndPromptIdentifier` `:905-934` legge solo `identifier_isin` e `identifier_ticker`, mai `identifier_other` — che esiste (`models.py:519`) ed è esposto al frontend (`assetStore.ts:58`) | ✅ | P3 |
| **A3** | Messaggio ISIN non corrispondente alla condizione | ⚠️ **PARZIALE**: la condizione `:916` è corretta e il testo IT/EN/FR/ES dice *"ha già {existing} come {type}"* — non *"l'asset esiste già"*. Trovato però un difetto vicino reale: `identifierPromptIsConflict = existingValue !== null` `:929` → con `identifier_isin === ""` mostra il testo di conflitto senza conflitto | ⚠️ | P3 |
| **T1** | Decimali `,` e `.` cancellati in "aggiungi transazione" | Ciclo controllato: `CompactCashCell.emit()` `:80-89` → `setCash` `TransactionFormModal.svelte:1179-1181` crea **un nuovo oggetto a ogni tasto** → torna giù come `value` → l'`$effect` `:71-78` applica `formatDecimalForDisplay("12.")` → `"12"`, sovrascrivendo il separatore. La docstring di `formatDecimal.ts:20-22` avverte *"don't reformat mid-typing"* | ✅ | P5 |
| **I1** | Bandiere → lettere su Windows nella build Docker | Il font **non è in git** (`.gitignore:83 frontend/static/fonts/`): è scaricato da Google Fonts a build time da `update_js_cache.py:44-50`, che in caso di errore *stampa e prosegue* (`:188-192`, nessuna eccezione, exit 0). `Dockerfile:52-53` copia la build senza verificare → il `<link>` in `app.html:12` va in 404 → fallback su `Segoe UI Emoji` → coppie di lettere | ✅ | P6 |
| **I2** | Immagini della documentazione non caricate | Doppio guasto: (a) `gallery-img-loader.js:18` → `GITHUB_PAGES_BASE = 'https://alfystar.github.io/LibreFolio'` mentre il sito reale è `https://librefolio.github.io/LibreFolio/` (`mkdocs.yml:2`) → il fallback 404; (b) gli screenshot sono gitignorati (`.gitignore:75`) e `_docker_ensure_assets_built()` `dev.py:1367-1390` **non** invoca mai `mkdocs gallery` | ✅ | P6 |
| **I3** | Warning prezzo Borsa Italiana sempre in inglese | `borsa_italiana.py:495-507` — f-string inglese hardcoded. `AssetSourceError` porta già `error_code` + `details`, ma è `message` (testo libero) a essere mostrato. 54 punti di `raise` analoghi nei provider | ✅ | P6 |

---

## 3. ✨ Richieste UI (nuove funzionalità / riformulazioni)

| ID | Richiesta | Nota tecnica | Piano |
|---|---|---|---|
| **W5** | `N TX` poco chiaro in italiano nello step 4 → emoji o parola per esteso | Solo copy + i18n | P2 |
| **W8** | Livello **INFO** nei messaggi di import (il warning non basta) | ⚠️ Richiede **cambio di contratto API**: `warnings: List[str]` (`brim.py:429,455`) → `List[BRIMWarning] {message, severity}`. Il pattern esiste già in `BRIMFieldTodo.severity` `:399`. Non è una migrazione DB (è un DTO di preview) | P2 |
| **B7** | Warning successione: elencare le righe / gli intervalli coinvolti e riscrivere "gamba" | Vedi §1 B6/B7 | P1 |
| **A4** | Opzione per salvare l'identificativo del report come **identificativo alternativo** | Caso d'uso reale del tester: i BTP *CUM* all'emissione hanno un codice diverso da quello del provider (che espone il liberamente scambiabile). `identifier_other` esiste già | P3 |
| **A5** | Pulsante "modifica asset" su ogni card dello step 4 dopo l'assegnazione | — | P3 |
| **T2** | Il tooltip custom non deve comparire subito: ritardo o click, **ovunque** | Punto di intervento **unico**: `Tooltip.svelte` — la docstring `:5` dichiara *"0ms delay on hover"*; esistono solo ritardi in uscita (`:76-77`), nessun `delay` in ingresso. Usato in 38 file / 85 occorrenze, ma la fix è centrale | P5 |
| **T3** | "Duplica transazione" deve copiare anche la data | Scelta **deliberata** e documentata (`TransactionFormModal.svelte:8`, `resetDate: true` a `:424`). È un cambio di requisito, non un difetto: *"so che avevamo pensato fosse corretto fare così, ma la realtà sta dimostrando che è meglio di no"* | P5 |
| **T4** | Delete singolo → aprire la bulk modal con la riga già marcata | L'infrastruttura **c'è già**: `WorkspaceIntent` `:76` supporta `{action:'delete', txIds}` e apre le righe già marcate (`:346-347`). `edit` e `clone` a riga singola passano già di lì (`+page.svelte:625,630`): solo `delete` è rimasto l'eccezione | P5 |

---

## 4. ⚡ Miglioramenti

| ID | Miglioramento | Nota tecnica | Piano |
|---|---|---|---|
| **W9** | Upload e parsing dei file in parallelo | `uploadAllPendingFiles()` `:2129-2158` e `doParseAll()` `:2560-2581` sono cicli `for` con `await` per file | P2 |
| **W10** | Parse sincrono dentro `async def` → blocca l'event loop | `brokers.py:721` `async def parse_file` chiama `brim_provider.parse_file` (un `def` puro, `brim_provider.py:1022`) **senza** `asyncio.to_thread`. Viola la regola di progetto sull'I/O asincrono; lo stesso file la rispetta altrove (`brokers.py:384`) | P2 |
| **E1** | Drawdown calcolato sul massimo della finestra visibile | La formula **è** un massimo espandente corretto (`risk/metrics.py:193-204`), ma il plugin dichiara `warmup_requirement(minimum_points=2, total_points=2)` (`drawdown.py:85-95`) → `asset_source.py:2099-2110` carica solo ~4 giorni prima del range visibile, quindi `values[0]` parte dentro la finestra. **Bug nell'input, non nella matematica** | P4 |
| **B4** | Registrare le ritenute delle cedole | Vedi §1 B4 — 2.203,42 € | P1 |

---

## 5. ⛔ Rilievi contraddetti dal codice — da riprodurre insieme

> **Non pianificati.** Il codice attuale contraddice il sintomo descritto: pianificare una fix
> alla cieca rischierebbe di "correggere" qualcosa che funziona, o di mancare la causa vera.

### ❌ X1 — "Non posso riportare attivo un asset disattivato dal modifica"

Il toggle **esiste ed è sempre renderizzato**: `AssetModal.svelte:1860-1873`
(`data-testid="asset-active-toggle"`, `role="switch"`), **non** condizionato a `editMode`, e
incluso sia in `saveCreate()` (`:1142`) sia in `saveEdit()` (`:1236`). Il backend accetta
l'aggiornamento (`FAAssetPatchItem.active`).

*Da chiarire*: il toggle era invisibile, disabilitato, o presente ma senza effetto al salvataggio?
Serve l'asset specifico.

### ❌ X2 — "Anche export AI è disattivo"

Nessun filtro su `Asset.active` esiste nell'AI export: `runtime_service.py:586` fa
`select(Asset).where(Asset.id.in_(...))` senza condizioni, e `asset_core.py:138` /
`asset_resources.py:112` propagano `active` come **semplice metadato di output**.

*Ipotesi alternativa*: l'asset non compariva perché a **posizione zero** (universo guidato dalle
posizioni), non perché disattivato — meccanismo diverso, fix diversa. Serve l'export specifico.

---

## 6. 📐 Riconciliazione contabile — chiusa in analisi

| ID | Rilievo | Esito |
|---|---|---|
| **E2** | *"Patrimonio netto 544k vs 530k: credo sommiamo due volte dividendi e interessi"* | ❌ **Ipotesi smentita.** `nav = market_value + cash + in_transit` (`portfolio_engine.py:1002-1004`); `total_pnl = nav − capital_baseline` è **derivato e mai risommato**. Invariante già coperta da test (`test_portfolio_service.py:411-430`). I dividendi entrano in cassa **una volta sola** |
| — | *Carico 530k (Excel) vs 480k (dashboard)* | ✅ **Spiegato**: stesso BTP 01/03/35 di B1 |

Dettaglio numerico completo e metodo per la verifica congiunta:
[`02_riconciliazione_credit_agricole.md`](02_riconciliazione_credit_agricole.md).

---

## 7. Mappa rilievo → piano

| Piano | Rilievi | Priorità |
|---|---|---|
| **P1** — Plugin Crédit Agricole | B1 🔴, B2, B3, B4, B5, B6, B7, B8 | 🔴 Bloccante |
| **P2** — Wizard di import | W1, W2, W3, W4, W5, W6, W7, W8, W9, W10 | 🟠 Alta |
| **P3** — Ciclo di vita asset | A1 🔴, A2, A3, A4, A5 | 🔴 Alta |
| **P4** — Motore e segnali | E1, E2 | 🟠 Media |
| **P5** — UX transazioni | T1, T2, T3, T4 | 🟠 Media |
| **P6** — i18n, font, docs | I1, I2, I3 | 🟡 Bassa |
| **—** — Da riprodurre col tester | X1, X2 | ⏸️ Sospeso |
