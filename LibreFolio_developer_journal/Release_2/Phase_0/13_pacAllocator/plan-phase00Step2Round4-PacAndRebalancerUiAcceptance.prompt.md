# Round 4 — PAC + Ribilanciamento P1 multi-servizio

**Stato:** IN CORSO — autorizzato dal developer il 2026-09-14

← Previous: [Round 3 — PAC UI acceptance](plan-phase00Step2Round3-PacAllocatorUiAcceptance.prompt.md)

→ Follow-up solver: [PAC + Ribilanciamento operativo](plan-phase00Step3-PacRebalancingSolver.prompt.md)

## 1. Obiettivo

La review Round 3 ha confermato il progresso funzionale ma respinto la UI.
Round 4 separa due servizi pubblici, entrambi P1:

1. **Allocatore PAC**: distribuzione teorica della liquidità investibile;
2. **Ribilanciamento portafoglio**: confronto fra peso corrente e target finale.

Un solo plugin backend pubblica i due servizi. Ogni servizio ha card, route,
metadati, schema e UI propri. Le UI riusano componenti Svelte coesi; non esiste
un selettore modalità globale.

Restano fuori Round 4: solver, ordini, quantità operative, routing Broker,
vendite, fee, fattibilità per cassa nativa, FX di esecuzione, ottimalità,
short/leva, FIFO/WAC/fisco e Riskfolio.

## 2. Baseline e ownership

| Campo | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-friendly-dollop` |
| Branch | `e-alfy-allocatore-pac` |
| Rollback Round 3 | `afca689dd81cdcfc28664c6328fc74ec51c806da` |
| Target contenuto | `e1f3fe177861d2b9b953b218f66ea7d4714ab405` |
| Stato iniziale | clean; index e untracked vuoti |
| Lane | porta `6153`, data `/tmp/librefolio-r2-d` |
| Venv | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| Coordinatore | `c8328a01-f208-4ade-a352-0486d1f14de2` |

Writer:

- D: piattaforma Tool multi-servizio, plugin/domain PAC + Rebalancer, UI
  dedicate/componenti condivisi, piani.
- J: `ToolsHub.svelte`, quattro cataloghi i18n, onboarding.
- Coordinatore: API sync, i18n, CHANGELOG, runner/registrazioni condivise,
  integrazione additiva J/D.
- `test-author`: tutti i test nuovi/modificati.
- `docs-writer`: tutta la documentazione MkDocs EN.

Vietati: staging, commit, merge, cherry-pick, rebase, push, install, `--force`,
porte condivise/produzione e review server prima dei gate completi.

## 3. Decisioni chiuse

### 3.1 Plugin → più servizi

- `ToolPlugin` dichiara una tupla non vuota di servizi.
- Ogni servizio espone il proprio `tool_code`, metadati, UI, documentazione,
  operazioni, input e output.
- Il wire esterno continua a usare `tool_code`: nessun secondo ID pubblico.
- Registry espande una classe plugin in più definizioni.
- Collisioni sono valutate sul codice servizio.
- Catalogo, diagnostica, worker e compute risolvono la stessa definizione.
- Il plugin conserva versioni backend condivise:
  `contract_version="1.0.0"` e `implementation_version="1.0.0"`.
- Ogni UI usa SemVer indipendente nel descriptor:
  `ui.version="1.0.0"`.
- PAC `1.0.0` evolve in place perché non ancora rilasciato.
- Rebalancer nasce `1.0.0`.
- `catalog_version` cambia perché cambia il descriptor UI.
- Fingerprint resta derivato da schema/operazioni del singolo servizio; la
  versione UI non cambia il fingerprint finanziario.

### 3.2 PAC P1

- Target = distribuzione desiderata della liquidità investibile.
- Budget = cassa esistente + contributi, valorizzati in valuta report.
- Cash e contributi restano vettori separati, nativi e aggregati per valuta.
- Output: quota monetaria ideale del budget per strumento.
- Nessuna quantità acquistabile, fee, quantum operativo, compatibilità cassa
  nativa, conversione FX, fattibilità od ottimalità.

### 3.3 Ribilanciamento P1

- Target = allocazione finale desiderata del portafoglio investito.
- Contesti Broker dello stesso strumento sono aggregati per `instrument_key`,
  mai per nome.
- Output: valore, peso corrente, target e gap per strumento.
- Cassa/contributi sono contesto informativo separato.
- Missing cash buy-only, buy/sell e quantità restano nel solver futuro.

### 3.4 Invarianti comuni

- Target per strumento canonico; custodie Broker restano fatti sorgente.
- Nessun dato altrui privato, Broker altrui o restrizione silenziosa.
- Fatti mancanti non vengono omessi né convertiti in zero/uno.
- Quote base: intero positivo arbitrario.
- `quantity_step` e `monetary_step` sono distinti.
- Inventario esistente non viene arrotondato alla griglia acquisti.
- FX serve solo alla valorizzazione esplicita.
- Tutti i calcoli economici restano backend Decimal.

## 4. Contratto UI

### 4.1 Feedback Round 3

| Gap | Correzione Round 4 |
|---|---|
| Fallback inglesi in IT | review bloccata finché cataloghi J integrati e audit/parità verdi |
| Prezzo ambiguo | pill `Prezzo attuale` + bandiera/valuta/importo; fonte/data secondarie |
| Flicker errore cassa | stato pending atomico; errore precedente nascosto durante retry |
| Contributi incoerenti | amount-first + valuta, virgola/frecce Add Transaction |
| `0.01` oscuro | `Passo monetario` sempre visibile con helper |
| Totali separati | riepilogo unico sotto contributi, per valuta nativa |
| Scope verde/rosso | palette non semantica stabile da `colors.ts` |
| Input/pulsanti grandi | densità DataTable/Add Transaction, touch accessibile |
| Card Asset rumorosa | fatti correnti essenziali compatti; sorgente/lock secondari |
| Badge custodia oscuro | label chiara + tooltip quantità non scalata |
| Deselect rosso | `ConfirmModal warning`, copy perdita personalizzazioni |
| Target sparsi | Step dedicato DataTable, una riga per strumento |
| Target accetta lettere | buffer Decimal filtrato, exact string, niente JS number |
| FX fuori contesto | solo valute estere attive + motivo concreto |
| Tabella risultati locale | `DataTable.svelte` |
| `input_missing` visibile | messaggi tradotti/raggruppati; raw sotto `<details>` |
| `Draft revision` visibile | solo stato interno/data attribute |
| PAC vs Rebalancer | due servizi/route/UI distinti |

### 4.2 Target

- DataTable compatta.
- Colonne: strumento, target exact Decimal, barra.
- Totale e restante sempre visibili.
- Celle custom string; vietato `editable-number`.
- Target rimosso dalle card di custodia.
- Vincoli/griglia restano nei dettagli Asset.

### 4.3 Diagnostica

- Mapper esaustivo per issue e fact reason.
- Copy tradotta con sezione/campo/azione.
- Duplicati raggruppati.
- Codici, path e params safe solo in `Dettagli tecnici`.
- Nessun `— (input_missing)` nella vista primaria.

## 5. ASCII

### PAC desktop

```text
+------------------------------------------------------------------+
| Allocatore PAC · Analisi P1                       Documentazione  |
| Ripartizione teorica della liquidità. Nessun ordine.              |
+------------------------------------------------------------------+

Impostazioni: [Valuta report EUR] [Data]

1. Liquidità da distribuire
[Broker OWNER...]                         [Inserisci manualmente]

Nuovi contributi
[Importo 500,00] [EUR] [Passo monetario 0,01 (?)] [trash]
[+ Aggiungi contributo]

Disponibilità per valuta
🇪🇺 EUR  esistente 1.000 + contributi 500 = disponibile 1.500

2. Asset
[Posseduti] [Altri utenti] [Osservati] [Cerca] [+ Manuale]
[Asset · Prezzo attuale 🇪🇺 EUR 121,34]

3. Distribuzione liquidità
| Asset | Target % | Barra |
| VWCE  | 60,00    | ████████████ |
| Bond  | 40,00    | ████████     |
Totale 100,00% · Restante 0,00%

4. Tassi di valorizzazione (solo se necessari)

[Analizza ripartizione P1]

Risultato: budget disponibile + quota ideale per Asset + avvertenze
```

### Rebalancer desktop

```text
+------------------------------------------------------------------+
| Ribilanciamento · Analisi P1                      Documentazione  |
| Confronta corrente e target. Nessun acquisto/vendita.             |
+------------------------------------------------------------------+

1. Portafoglio corrente
[Asset/custodie selezionati]

2. Allocazione target finale
| Asset | Target % | Barra |

3. Contesto liquidità
[Broker cash] [contributi] [riepilogo nativo]

4. Tassi di valorizzazione (solo se necessari)

[Analizza scostamenti P1]

Risultato: valore/peso corrente aggregato + target + gap
```

### Mobile

```text
[Titolo servizio P1]
[Valuta report] [Data]
[sezioni verticali]
[card Broker/Asset full-width]
[target DataTable scrollabile]
[totale/restante]
[CTA]
[result DataTable]
[Dettagli tecnici chiusi]
```

## 6. Architettura

### Backend piattaforma

- Nuovo `ToolService` immutabile nel confine plugin.
- Versioni backend sulla classe plugin.
- `services: tuple[ToolService, ...]`.
- Compute riceve `tool_code` + modello validato.
- Registry:
  - valida struttura comune plugin;
  - espande servizi;
  - genera adapter e descriptor per servizio;
  - quarantena collisioni/codici/descriptor in modo fail-closed;
  - pubblica mapping immutabile per codice servizio.
- Worker costruisce plugin una volta e passa il codice servizio.
- Executor, auth, deadline, process-tree, cleanup e wire restano invariati.

### Backend dominio

- Primitive Decimal/quote/money/FX condivise.
- Input/output distinti PAC e Rebalancer.
- Target vector separato dalle righe custodia.
- Normalizer verifica target canonici, totale 100, orfani, limiti e dipendenze.
- PAC evaluator: budget report × target / 100.
- Rebalancer evaluator: aggregazione contesti → valore/peso/gap strumento.
- Reporter conserva partial facts e classificazione tipizzata.

### Frontend

- Due renderer compilati.
- Wrapper distinti PAC/Rebalancer.
- Componenti allocation condivisi, non mega-componente con branch.
- Guardie account/request/date/revision preservate.
- Nessun calcolo economico frontend.
- API/generated client innestati dal coordinatore dopo sync.

## 7. Passi

1. [x] **2026-09-14 — Gate 0 rollback-safe**
   > **Nota implementazione**: developer ha creato checkpoint Round 3
   > `afca689dd81cdcfc28664c6328fc74ec51c806da`. Verificati status clean,
   > target `e1f3fe177861d2b9b953b218f66ea7d4714ab405` contenuto e porta 6153
   > libera. Writer lease e ordine integrazione ricevuti dal coordinatore.
   > **Evidenza**: `git rev-parse HEAD`, `git rev-parse dev_release2`,
   > `git merge-base --is-ancestor dev_release2 HEAD`, `git status --short`,
   > `lsof -nP -iTCP:6153 -sTCP:LISTEN`.
2. [x] **2026-09-14 — Piani durevoli**
   > **Nota implementazione**: creati piano Round 4 e piano solver separato;
   > Round 3/4/solver cross-linkati. Decisioni developer riportate senza
   > riaprire scope chiusi.
   > **Evidenza**: path in testa a questo file e link reciproci.
3. [x] **2026-09-14 — Piattaforma Tool multi-servizio**
   > **Nota implementazione**: introdotto `ToolService` immutabile e spostata
   > l'identità pubblica dal plugin al servizio; il registry espande una
   > classe in N definizioni, rileva collisioni anche fra sibling e isola un
   > descriptor/schema sibling malformato senza nascondere quelli sani. Il
   > worker passa il `tool_code` risolto a `compute`; auth, executor, wire,
   > deadline e cleanup restano invariati. Migrati descriptor UI da intero a
   > SemVer (`ui.version`), catalogo/manifest a v2 e sorgenti frontend di
   > compatibilità a `uiVersion`. Il plugin PAC esistente è stato adattato al
   > nuovo confine; il secondo servizio viene aggiunto al passo 5.
   > **Evidenza**: test-author ha aggiornato sei file test backend. Selettori:
   > `schemas tools` 217 passed; `services tools-registry` 91 passed su due
   > run; tre test lifecycle/worker mirati 4 passed su due run; `api tools`
   > 5 passed; `api pac-tool` 1 passed. Totale distinto 318, zero failure.
   > Black/Ruff mirati e `git diff --check` verdi.
   > **⚠️ Fuori pista**: generated API/Tool client sono intenzionalmente
   > ancora stale; l'API sync e l'innesto generated restano lease esclusivo
   > del coordinatore al passo 6.
   > **⚠️ Fuori pista**: al freeze contrattuale sono stati migrati anche i
   > due riferimenti legacy D-owned da `ui_contract_version=1` a
   > `ui.version="1.0.0"`. I match residui sono test negativi intenzionali o
   > superfici shared C/J, segnalate al coordinatore senza modificarle.
   > **Nota implementazione shared — 2026-09-14**: su lease coordinatore,
   > docs-writer ha riallineato la guida developer Tool a `ToolService`
   > multi-servizio, versioni backend condivise, UI SemVer indipendenti e
   > boundary executor/worker/process-tree/resource/auth/schema/renderer.
   > **Evidenza**: `mkdocs build` exit 0; link 12/12; diff-check mirato
   > verde; nessun `ui_contract_version` residuo nella pagina.
4. [x] **2026-09-14 — Contratti/evaluator P1 PAC e Rebalancer**
   > **Nota implementazione**: sostituito il contratto initial-state Round 3
   > con due root strict distinti. PAC riceve Asset canonici, target separati
   > e vettori cash/contributi/FX e restituisce budget report + quote
   > monetarie teoriche. Rebalancer riceve custodie, aggrega per
   > `instrument_key` e restituisce valori/pesi/target/gap firmati. Custodia
   > ripetuta dello stesso strumento è ammessa; nome uguale non aggrega.
   > Cash/contributi non entrano nel denominatore investito. Tutta
   > l'aritmetica usa Decimal backend; zero PAC è no-op ready, zero investito
   > conserva facts con ratio `zero_invested_value`. Nessun output ordine,
   > quantità operativa, feasibility o solver.
   > **Evidenza**: test-author: `schemas pac-analyze` 105 passed;
   > `services pac-analyze` 84 passed; Ruff/Black mirati verdi. Copertura
   > comprende multicurrency/FX, budget basso/zero, quote base arbitrarie,
   > target mancanti/orfani/duplicati, identità, permutation, nonfinite,
   > short unsupported, grid e inventory off-grid non arrotondato.
   > **⚠️ Fuori pista**: il feedback developer richiede più contributi nella
   > stessa valuta. La normalizzazione contributi ora somma le righe omonime
   > con Decimal esatto, mentre cash esistente e tassi restano vettori chiusi
   > a una riga per valuta. Copertura test-author e rerun mirati sono
   > esplicitamente rinviati al passo 12.
   > **⚠️ Fuori pista**: la review finale del percorso numerico ha rilevato
   > che un valore finale non terminante rispetto a
   > `quote_base_quantity` poteva attivare il trap Decimal `Inexact` e uscire
   > dal contratto tipizzato. La normalizzazione ora prova la stessa formula
   > `quantità × prezzo ÷ base` dell'evaluator: moltiplica prima per non
   > rifiutare falsamente casi esatti come `1 × 3 ÷ 3`, e classifica solo i
   > risultati realmente non terminanti come
   > `numeric_domain_exceeded`/unsupported, senza arrotondamenti nascosti né
   > errore worker. Test mirati richiesti al test-author al passo 12.
   > Il `quote_base_quantity` positivo è inoltre limitato esplicitamente a
   > 12 cifre: basi maggiori diventano unsupported tipizzato prima di poter
   > produrre payload incontrollati; anche un risultato esatto ma più lungo
   > delle 52 cifre/caratteri ammesse dal fatto monetario nativo diventa
   > unsupported tipizzato. L'editor usa la stessa primitive intera esatta e
   > non accetta notazione esponenziale.
   > **⚠️ Fuori pista**: il massimo draft Rebalancer malformato ammesso dai
   > bound può produrre circa 486 issue tipizzate; il precedente cap output
   > 384 poteva trasformare la diagnostica in `invalid_output`. Il cap è
   > stato riallineato a 512, ancora entro il budget risposta 256 KiB; il
   > test-author deve coprire il caso limite e la dimensione serializzata.
   > **⚠️ Fuori pista — freeze contrattuale**: la review test-author ha
   > rilevato che i campi output `optimization="not_run"` e
   > `trade_feasibility="not_evaluated"` rendevano ancora rappresentabili
   > due concetti esplicitamente esclusi dal P1. Rimossi dai due modelli
   > output e dal reporter: solver/fattibilità restano confini dichiarati,
   > non campi wire. La modifica invalida entrambi i fingerprint del primo
   > sync e richiede una sola rigenerazione definitiva del coordinatore.
5. [x] **2026-09-14 — Plugin a due servizi + API backend**
   > **Nota implementazione**: `PacAllocatorTool` pubblica
   > `pac_allocator`/`pac-allocator` e
   > `portfolio_rebalancer`/`portfolio-rebalancer`, con versioni backend
   > comuni `1.0.0`, UI SemVer indipendenti e dispatch typed sul
   > `tool_code`. Policy P1 pura/deterministica condivisa; documentazione e
   > schema sono completi per servizio.
   > **Evidenza**: test-author `api pac-tool` 4 passed: catalogo v2 con due
   > descriptor, batch compute autenticato misto con ID distinti/ordine
   > preservato, auth/isolamento foreign-user e assenza endpoint schema
   > separato. `git diff --check` verde; porta 6153 libera.
6. [x] **2026-09-14 — Handoff coordinator API sync + frontend generic compatibility**
   > **Nota implementazione**: il coordinatore ha eseguito la generazione
   > API/Tool sul contratto multi-servizio e verificato codec, mapping e
   > descriptor v2. Hash generazione
   > `c2a08617e3db1d9e189ae90c83f444222a1c311266c9aa3201c2b760daea734c`;
   > fingerprint PAC
   > `764457e0ac01c49e19058f16b830547c44d79cb01ddf7613dc78db30e0c236d6`;
   > fingerprint Rebalancer
   > `7ecbd74632bb4ef7699e75b74ad5a5422134716dd7683244a739af88701ebf82`.
   > Catalogo literal `"2"` e UI descriptor `{kind, component_key, version}`.
   > Gli artifact generated restano ignorati e non entrano nel checkpoint D.
   > **Evidenza**: handoff coordinatore; generated contract map consumata
   > dalla produzione frontend Round 4.
   > **⚠️ Fuori pista**: il successivo disaccoppiamento del limite righe
   > contributo dal limite valute ha modificato entrambi gli schemi. Hash e
   > fingerprint sopra restano evidenza del primo sync ma sono ora stale;
   > il coordinatore deve rigenerarli dopo il freeze D.
7. [x] **2026-09-14 — Componenti allocation condivisi + due wrapper**
   > **Nota implementazione**: creati wrapper pubblici indipendenti
   > `PacAllocatorTool` e `PortfolioRebalancerTool`, senza mode selector. I
   > due renderer condividono componenti allocation piccoli per funding,
   > tassi FX, target, diagnostica e primitive Decimal, mentre Asset PAC,
   > custodie Rebalancer e risultati restano specifici. Entrambi usano il
   > client Tool generato e rispettano account generation, abort, request
   > sequence e draft revision.
   > **Evidenza**: `PacAllocatorTool.svelte`,
   > `PortfolioRebalancerTool.svelte`, `AllocationFundingSummary.svelte`,
   > `AllocationFxSection.svelte`, `AllocationTargetEditor.svelte`,
   > `AllocationDiagnostics.svelte`; precedente `front check` senza
   > diagnostiche nei file produzione dopo la correzione dei contratti host.
   > **⚠️ Fuori pista**: il primo innesto assumeva prop/runtime helper e alias
   > output nominali non esistenti. Riallineato ai contratti reali
   > `{descriptor, accountGeneration}`, `runTool` e `ToolOutput` generico.
   > **⚠️ Fuori pista — gate componenti**: `structuredClone` riceveva proxy
   > Svelte dagli editor e interrompeva il compute prima di `runTool`.
   > Entrambi i wrapper ora estraggono uno `$state.snapshot` plain prima
   > della copia profonda; anche la duplicazione custodia Rebalancer usa lo
   > stesso confine.
8. [x] **2026-09-14 — Funding/input/flicker/totali**
   > **Nota implementazione**: mantenuti cash esistente e contributi
   > separati nel draft, ma presentati in un unico riepilogo per valuta.
   > L'inserimento è importo-prima con primitive Decimal condivise, virgola
   > locale, stepper e filtro immediato dei caratteri non numerici. Sono
   > ammesse più righe contributo nella stessa valuta. I totali combinati
   > sono mostrati solo dai `cash_pools` autorevoli backend e diventano stale
   > dopo una modifica; il frontend mostra gli addendi senza inventare
   > conversioni. Lo stato pending Broker precede la richiesta e nasconde
   > l'errore sostituito, eliminando il flash durante la selezione.
   > **Evidenza**: `PacMoneySection.svelte`,
   > `AllocationFundingSummary.svelte`, `ExactDecimalInput.svelte`,
   > `CompactCashCell.svelte`, `parseDecimalInput.ts`; `git diff --check`
   > verde.
   > **⚠️ Fuori pista**: dopo aver ammesso contributi ripetuti nella stessa
   > valuta, il precedente limite di quattro righe confondeva il limite del
   > dominio valutario con quello degli addendi. Il contratto e l'editor ora
   > ammettono fino a 32 contributi, mantenendo quattro come massimo delle
   > valute complessive nel dominio P1. Le riserve Broker copiate sono inoltre
   > etichettate esplicitamente come native e non scalate; la quota personale
   > resta metadato separato.
   > **⚠️ Fuori pista**: il cash copiato è ora legato a generazione account,
   > data e selezione Broker esatte. Un refresh fallito non può riusare
   > silenziosamente la cassa della selezione precedente; con selezione non
   > vuota il compute resta bloccato, mentre zero Broker selezionati conserva
   > il vettore vuoto intenzionale.
9. [x] **2026-09-14 — Asset compatti + target DataTable**
   > **Nota implementazione**: separata la selezione degli strumenti dalla
   > distribuzione. Le card PAC/custodia sono compatte, distinguono prezzo
   > attuale, provenienza, scope colorato tramite `colors.ts`, modifiche e
   > stale senza usare verde/rosso come selezione. I target sono raccolti in
   > un terzo step DataTable con input stringa Decimal, barre, totale e
   > residuo esatti via BigInt. Il Rebalancer può copiare i pesi correnti
   > backend: l'ultima quota assorbe solo il residuo decimale necessario a
   > chiudere esattamente a 100.
   > **Evidenza**: `OwnedAssetGallery.svelte`, `PacAssetEditor.svelte`,
   > `RebalanceHoldingEditor.svelte`, `AllocationTargetEditor.svelte`,
   > `AllocationTargetInputCell.svelte`, `AllocationTargetBarCell.svelte`,
   > `draftFactories.ts`.
   > **⚠️ Fuori pista**: i refresh sorgente inizialmente marcavano stale una
   > personalizzazione anche quando cambiava solo la selezione cash. Ora il
   > confronto usa il valore importato originale e preserva il draft solo se
   > il fatto sorgente corrispondente è realmente cambiato.
   > **⚠️ Fuori pista**: la review finale ha reso espliciti quantità di
   > custodia piena, quota personale, data snapshot, data e provider prezzo
   > nelle righe importate, senza rendere editabili i facts. Il warning
   > giallo di rimozione compare solo quando andrebbero persi target o
   > personalizzazioni reali, non su una riga manuale appena aggiunta.
   > **⚠️ Fuori pista — gate componenti**: i facts copiati Rebalancer erano
   > ancora tutti inline e rumorosi. Quantità di custodia, quota personale,
   > prezzo/base e provenienza sono ora raccolti in un disclosure compatto
   > chiuso di default; le righe PAC/Rebalancer espongono inoltre
   > `data-stale` stabile per test semantici. L'ARIA dell'input target viene
   > tradotta dentro la cella, così reagisce al cambio locale senza
   > dipendere dalla cache colonne DataTable.
   > **⚠️ Fuori pista — catalogo**: il primo fix ARIA usava
   > `tools.allocation.target.percent`, chiave non compresa nell'handoff
   > i18n condiviso. Tutti i call site target riusano ora la chiave
   > quadrilingue esistente `tools.pacAllocator.rows.target`; nessuna
   > modifica ai cataloghi J-owned.
10. [x] **2026-09-14 — Result DataTable + diagnostica umana**
    > **Nota implementazione**: sostituiti output raw Round 3 con due
    > DataTable specifiche. PAC mostra budget e allocazioni monetarie
    > teoriche; Rebalancer mostra valore/peso corrente, target, valore target
    > e gap firmato. Stati e problemi hanno testo umano, mentre codice e
    > parametri restano in dettagli tecnici chiusi. La revisione interna non
    > è esposta. Entrambe le viste dichiarano che P1 non produce solver,
    > ordini, routing Broker, trasferimenti FX o fattibilità operativa.
    > **Evidenza**: `PacResultPanel.svelte`,
    > `RebalancerResultPanel.svelte`, `AllocationDiagnostics.svelte`;
    > `git diff --check` verde.
    > **⚠️ Fuori pista**: il no-op Rebalancer con valore investito zero ora
    > espone una spiegazione umana dedicata; i trattini dei ratio non restano
    > più privi di contesto.
    > **⚠️ Fuori pista — type gate**: corretto il mapper diagnostico:
    > `limit` viene ristretto a primitiva i18n-safe e il fallback indicizza
    > `issue.code` invece di una variabile inesistente. Le intestazioni delle
    > DataTable usano callback tradotte; il pulsante aggiunta tasso espone un
    > selettore stabile.
11. [x] **2026-09-14 — Handoff i18n/ToolsHub/CHANGELOG + integrazione shared**
    > **Nota implementazione parziale — 2026-09-14**: consegnati al
    > coordinatore artifact atomici per 136 nuove chiavi EN/IT/FR/ES e 5
    > aggiornamenti semantici esistenti; D non ha modificato i cataloghi.
    > **Evidenza**: batch
    > `/tmp/libreFolio_round4_i18n_batch.json`
    > SHA256 `7a685b173a1f1d869fae88b663c2738464b4f0912727c9699cbf8a4338d267c1`;
    > update `/tmp/libreFolio_round4_i18n_updates.json`
    > SHA256 `6241d547ea321ebf4d1df10578bf1b928c509f4e890300a71672ae4cfa6f3f44`;
    > report `/tmp/libreFolio_round4_i18n_validation.json`
    > SHA256 `627b020db2efd9e6c09819923e1d4e091f0f8baee5cacab6b0c2f93ebe3eaf00`;
    > ordinamento, unicità, valori non vuoti e placeholder parity verdi.
    > Applicazione cataloghi, ToolsHub/host version labels, CHANGELOG e nuovo
    > API sync restano lease J/coordinatore.
    > **Nota shared — 2026-09-14**: il coordinatore conferma applicazione
    > J esatta dei 141 valori richiesti e audit/parità 3167/3167, zero
    > incomplete/backend missing. Il checkpoint J e l'innesto della baseline
    > shared restano prerequisiti dei gate finali D.
    > **Nota integrazione shared — 2026-09-14**: applicati semanticamente
    > ToolsHub/ToolHost, fixture catalogo v2, versioni pubbliche
    > Backend/API + UI, registrazioni runner Rebalancer e namespace `tools.*`
    > quadrilingue senza sovrascrivere lifecycle D. Il catalogo corrente
    > passa audit 2985/2985, zero incomplete e zero chiavi backend mancanti;
    > il ref scan finale trova 109 chiavi Tool senza call site e le consegna
    > al writer shared in
    > `/tmp/libreFolio_r4_unused_tool_keys.txt`, SHA256
    > `19db1af79a03403820c28a02608ffa74764e51efbe35e809ded5b7357170342a`.
    > **⚠️ Fuori pista**: la voce PAC del CHANGELOG integrato conserva la
    > vecchia semantica current-vs-target Round 3. Correzione richiesta al
    > coordinatore prima della preview; D non modifica il file shared.
    > **Nota correzione shared — 2026-09-14**: il coordinatore ha distinto
    > definitivamente PAC (cassa selezionata + contributi → allocazioni
    > monetarie teoriche) da Rebalancer (current-vs-target) nel CHANGELOG.
    > Intersecate le 44 chiavi legacy D-only con il ref scan: 27 realmente
    > inutilizzate rimosse via `dev.py i18n remove -f`, 17 ancora usate
    > conservate; nessuna chiave J/platform rimossa. Audit finale 2958/2958,
    > zero incomplete e zero backend missing; 204 unused shared/preesistenti
    > restano debito non visibile. Prettier cataloghi e diff-check verdi.
12. [x] **2026-09-14 — Test-author backend/frontend/E2E + gate**
    > **Nota implementazione parziale — 2026-09-14**: il primo passaggio
    > specialistico ha portato il nucleo a 97 service test, 103 schema test,
    > 5 API test e 1991 core-unit verdi, più 4/8 E2E desktop/mobile verdi.
    > I fallimenti deterministici residui hanno individuato i quattro
    > blocker produzione descritti sopra: proxy Svelte, concetti wire
    > esclusi, due errori type-check diagnostica e ARIA target non reattiva.
    > Le correzioni produzione sono applicate; rerun specialistico e gate
    > completi restano pendenti, senza server review.
    > **Evidenza post-fix — 2026-09-14**: 594 test backend completi verdi
    > (`schemas pac-analyze` 112, `schemas tools` 217,
    > `services pac-analyze` 97, `services tools-registry` 91,
    > `services tools-lifecycle` 67, `api pac-tool` 5, `api tools` 5).
    > Component-unit registrati: 1816 verdi e un solo rosso ARIA; dopo il
    > riuso della chiave quadrilingue esistente, selector ARIA 1/1 e suite
    > `PacAllocatorTool` 15/15 verdi. PAC E2E desktop/mobile 8/8 verdi.
    > `front check`: 0 errori, 41 warning preesistenti in due file estranei.
    > Ruff/Black/Prettier/diff-check mirati verdi; porta 6153 libera.
    > Restano esattamente due orphan shared-runner:
    > `PortfolioRebalancerTool.test.ts` e
    > `portfolio-rebalancer.spec.ts`; registrazione e loro esecuzione sono
    > lease coordinatore.
    > **⚠️ Fuori pista — gate statici definitivi**: il lint repository-wide
    > ha evidenziato un accesso `getattr` costante e due funzioni
    > intenzionalmente branch-heavy prive di motivazione C901. Tipizzato
    > `_availability` con `AllocationIssue`, usato accesso diretto a
    > `kind` e documentata la complessità piatta del validatore target e del
    > reporter Rebalancer. Il format-check frontend ha inoltre individuato
    > due file D-owned non ancora serializzati da Prettier; riallineati senza
    > modifica semantica.
    > **Evidenza finale sul combined tree**: `check-orphans` verde
    > (206 backend, 79 E2E, 204 unit raggiungibili); backend 594/594;
    > component-unit 1837/1837 su 71 file; core-unit 1991/1991 su 82 file;
    > PAC E2E 8/8 e Rebalancer E2E 6/6 desktop/mobile. Dopo il solo
    > formatting, rerun dei percorsi toccati: 112 schema + 97 service + 5
    > API + 1837 component + 14 E2E, tutti verdi. Porta 6153 libera dopo
    > ogni suite.
    > **Evidenza statica**: Ruff completo verde; Black verde sui 23 file
    > Python modificati D/shared; Prettier completo verde; `front check`
    > zero errori e 41 warning preesistenti in due file estranei; build
    > frontend produzione verde; MkDocs strict verde e link 12/12;
    > `git diff --check` verde.
    > **Evidenza codegen**: due rigenerazioni Tool-only byte-identiche,
    > generation
    > `bbed2f1a11196e64f03bd1c63fe0703935c0da372301c6b64e55a8bc2ee6fde3`;
    > PAC fingerprint
    > `507e106cf2a2a2e3b78cc9f96053346cb785551231d8bbce86cd563e028ed495`;
    > Rebalancer fingerprint
    > `cba2b73e9930c7f42ad92f2d43eb1cba91236ca0d2111d2cb454172243bf40b8`.
    > Artifact ignorati invariati: contract schema
    > `bbed2f1a11196e64f03bd1c63fe0703935c0da372301c6b64e55a8bc2ee6fde3`,
    > codecs `0299ca10000b663d959bd37ef5a93ba6dff2deb464367a20fc88a6de4214cf17`,
    > map `9d988ad3fb85e611b29a9b2a67946e74b4ee913174990df423e205ce67f7f3c3`.
    > **Evidenza post-shared finale**: Prettier completo, `front check`
    > (0 errori, 41 warning baseline) e build produzione ripetuti verdi
    > dopo la correzione CHANGELOG/rimozione chiavi; nessun delta generated
    > tracciato, staging o listener sulla porta 6153.
    > **Evidenza integrazione J→D — Gate 1, 2026-09-14**: merge aperto su
    > `HEAD d66f8e58e74532776445506717bb4bf02aff91fd` e
    > `MERGE_HEAD 580bd504fd1d0d3b7b3ee2a8ac0407ef5187a476`;
    > risolti semanticamente 13 conflitti, con 0 unmerged/unstaged/untracked
    > e 116 path staged. `git diff --cached --check` verde;
    > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
    > test --test-port 6153 --data-dir /tmp/librefolio-r2-d check-orphans`
    > registra e rende raggiungibili 206 file backend, 80 spec E2E e 212
    > file unit frontend. Manifest staged
    > `/tmp/libreFolio_j_into_d_staged_manifest.txt`, SHA256
    > `a639b9395852b424a457cfad039ae54b8b6baccf4d1c12b997fda54acc872d1c`.
    > **Evidenza integrazione J→D — Gate 2, 2026-09-14**: eseguiti in
    > serie sulla lane 6153 e `/tmp/librefolio-r2-d` gli 11 selettori
    > `schemas pac-analyze` (112), `schemas tools` (217),
    > `services pac-analyze` (97), `services tools-registry` (91),
    > `services tools-lifecycle` (67), `services settings` (23),
    > `db validate` (17), `db referential-integrity` (15),
    > `api settings` (39), `api pac-tool` (5) e `api tools` (5):
    > 688/688 test passati. Coperti i 15 flow onboarding e gli step
    > multi-stage, persistenza/isolamento/atomicità settings, upgrade e
    > downgrade della migrazione onboarding, FK/unique constraints, i due
    > servizi Tool PAC/Rebalancer, contributi ripetuti nella stessa valuta,
    > limite di quattro valute native distinte, dispatch worker e confini
    > auth/catalog/compute. Nessuna modifica a test o prodotto.
    > **Evidenza integrazione J→D — Gate 3, 2026-09-14**: due esecuzioni
    > complete consecutive di
    > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
    > api sync` hanno prodotto byte identici. Hash: OpenAPI
    > `a31ab5606d16c390cf59885c5e797463b35e0744fff6d2993f9d96830c7378b9`,
    > client Zodios
    > `e3ff9438292d315e59c18b53401acbff0eea6faab748068e7cc9bafc08be970b`,
    > Tool contracts/generation
    > `bbed2f1a11196e64f03bd1c63fe0703935c0da372301c6b64e55a8bc2ee6fde3`,
    > codecs
    > `0299ca10000b663d959bd37ef5a93ba6dff2deb464367a20fc88a6de4214cf17`
    > e contract map
    > `9d988ad3fb85e611b29a9b2a67946e74b4ee913174990df423e205ce67f7f3c3`.
    > Il client espone `OnboardingStepProgressItem`, gli array `steps` e le
    > route step complete/skip; la map espone PAC fingerprint
    > `507e106cf2a2a2e3b78cc9f96053346cb785551231d8bbce86cd563e028ed495`
    > e Rebalancer fingerprint
    > `cba2b73e9930c7f42ad92f2d43eb1cba91236ca0d2111d2cb454172243bf40b8`,
    > entrambi con `uiVersion: "1.0.0"`. Tutti i cinque artefatti generated
    > risultano ignorati; zero delta tracciato o untracked.
    > **Evidenza integrazione J→D — Gate 4, 2026-09-14**: i selettori
    > seriali `front-utility core-unit`, `front-utility component-unit` e
    > `front-utility onboarding-component-unit` sono verdi rispettivamente
    > con 85 file/2132 test, 71 file/1870 test e 11 file/361 test. Coperti
    > controller/surface onboarding, Welcome e coachmark, asset/broker/import
    > guide anchors, ToolHub/ToolHost preload-cache-reload/version/guide,
    > PAC e Rebalancer. Restano solo warning Svelte deprecation e
    > `localStorage` già noti; nessun failure o modifica di test/prodotto.
    > **Evidenza integrazione J→D — Gate 5, 2026-09-14**:
    > `front format --check` verde su tutti i sorgenti/E2E; `front check`
    > verde con 0 errori e 41 warning baseline in due file; `front build`
    > ha completato il bundle produzione e scritto `frontend/build`.
    > **⚠️ Fuori pista**: il cache manager non ha potuto aggiornare MathJax
    > da jsDelivr per `CERTIFICATE_VERIFY_FAILED`, ma ha mantenuto la copia
    > locale già valida e la build è terminata con exit 0. Nessun package,
    > artefatto generated tracciato o sorgente è stato modificato.
    > **Evidenza integrazione J→D — Gate 6, 2026-09-14**: otto selettori
    > Playwright eseguiti in serie sulla lane 6153: `onboarding-tour` 10/10
    > desktop/mobile, `auth` 24/24, `settings` 45/45,
    > `tx-import-flow` 10/10, `tx-asset-identity` 9/9,
    > `asset-list` 27/27, `pac-tool` 8/8 desktop/mobile e
    > `rebalancer-tool` 6/6 desktop/mobile. Totale 139/139. Coperti Welcome,
    > replay, guide e milestone Import/Bulk, auth/account isolation,
    > impostazioni, seam import-identità-lista Asset e i due renderer Tool.
    > **⚠️ Fuori pista**: dopo 27/27 verdi, il teardown `asset-list` ha
    > segnalato che il backend ignorava SIGTERM da 5 secondi e il runner ha
    > escalato sul proprio process group. L'invocazione è uscita 0; `lsof
    > -nP -iTCP:6153 -sTCP:LISTEN` ha provato subito dopo e a fine gate che
    > la porta era libera. Nessun `--force`, retry o modifica a test/prodotto.
    > **Evidenza integrazione J→D — Gate 7, 2026-09-14**: Ruff e Black
    > check-only sono verdi su tutti i 14 file Python cambiati nel merge.
    > `i18n audit` rileva 3185/3185 chiavi complete per ciascuna delle
    > quattro locale, 0 incomplete e 0 backend missing; lo scan copre 3708
    > riferimenti esatti, 279 chiavi backend-driven e 70 prefissi dinamici.
    > Le 82 chiavi Tool potenzialmente inutilizzate sono byte-identiche come
    > insieme al report D post-cleanup: nessuna nuova chiave Tool unused e
    > nessuna delle 27 chiavi D rimosse è stata reintrodotta. Il debito
    > complessivo segnalato dall'audit è 234 chiavi potenzialmente unused.
    > `mkdocs build` strict verde; `mkdocs check-links` 12/12.
    > **⚠️ Fuori pista**: la prima invocazione Ruff via `xargs` è terminata
    > 127 prima del lint perché l'assegnazione ambiente era stata passata
    > come nome eseguibile; nessun file, DB o server toccato. L'invocazione
    > corretta ha poi rilevato due `PLC0415` preesistenti in entrambi i
    > parent in `_frontend_utility.py`. Il coordinatore ha preso la lease
    > shared, spostato i tre nomi già importabili nell'import top-level e
    > rimosso i due import locali, senza modifica comportamentale; Ruff
    > scoped, Black apply/check, AST e diff-check coordinatore verdi. Il
    > rerun D di Ruff e Black su tutti i 14 file è verde.
    > **⚠️ Fuori pista — Gate 8 review indipendente, 2026-09-14**: la review
    > read-only del merge ha trovato un rischio medium in
    > `frontend/src/routes/(app)/+layout.svelte:139`: le dichiarazioni
    > legacy `$:` osservano l'identità stabile del singleton
    > `appBootstrap`, non il getter rune `appBootstrap.ready`; un load
    > autenticato diretto o un retry riuscito potrebbe quindi non
    > ricalcolare il redirect a `/welcome`. Il ramo post-load avvia l'intro
    > solo quando la destinazione coincide già con la route corrente e non
    > naviga quando Welcome diventa dovuto. Nessuna modifica eseguita:
    > finding inviato al coordinatore per lease shared e test di regressione
    > obbligatorio via test-author.
    > **Nota implementazione — Gate 8 correction, 2026-09-15**: estratto
    > `onboardingRouteSettlement.ts`, helper async puro con dipendenze
    > iniettate. Il layout lo invoca subito dopo entrambi gli
    > `appBootstrap.load()` riusciti, iniziale e retry, campionando solo
    > allora pathname+search e route Welcome. Stati non-ready non agiscono;
    > una destinazione diversa viene navigata una sola volta con
    > `replaceState` e termina prima dell'intro; una route invariata
    > non-Welcome può avviare l'intro. I successivi blocchi reattivi,
    > redirect auth, preload, update probe e stati blocked/degraded restano
    > invariati.
    > **Evidenza test-author**: aggiunto il test puro
    > `onboardingRouteSettlement.test.ts` con 8 casi per idle/loading/blocked,
    > redirect Welcome codificato e awaited, retry blocked→ready, degraded
    > invariato+intro, assenza di doppia navigazione/intro vecchia e Welcome
    > invariato. Il coordinatore ha sostituito entrambe le registrazioni
    > runner; `check-orphans` verde (206 backend, 80 E2E, 213 unit). Test
    > focalizzato 8/8 e `onboarding-component-unit` 369/369 su 12 file.
    > Prettier completo verde; `front check` 0 errori/41 warning baseline;
    > build produzione verde.
    > **⚠️ Fuori pista — harness abbandonato**: tre tentativi del primo
    > seam che compilava il layout reale sono falliti prima dell'esecuzione
    > prodotto: alias `$app/stores` non risolto (0 test), invariant
    > esbuild `TextEncoder`/`Uint8Array` (0 test), poi TDZ `$` nel linker
    > CommonJS (4 test raccolti ma skipped). Il coordinatore li ha
    > classificati environment/harness e ha vietato altri workaround.
    > Eliminati il test layout e i due helper esclusivi
    > `AppLayoutSidebarProbe.svelte`/`compileSvelteComponent.ts`; ref scan
    > senza consumatori residui. Nessun timing hack o polyfill globale.
    > **⚠️ Fuori pista — formato**: il primo Prettier check post-helper ha
    > segnalato solo `onboardingRouteSettlement.ts`; applicato Prettier sul
    > singolo file e rerun completo verde, senza cambi semantici.
    > **⚠️ Fuori pista — probe listing coordinatore**: il comando
    > `front-utility all --list` ha posizionato `--list` dopo l'action;
    > argparse lo ha interpretato come filtro test e ha avviato la suite
    > completa. Il coordinatore ha fermato l'esatto albero processi dopo
    > circa quattro minuti. Il run ha popolato solo
    > `backend/data/test/sqlite/app.db`, non la lane assegnata
    > `/tmp/librefolio-r2-d`; nessun suo output vale come evidenza e nessun
    > file prodotto/sorgente/staged è stato intenzionalmente modificato.
    > Sintassi corretta: `front-utility --list all`.
    > **⚠️ Fuori pista — secondo probe listing coordinatore**: anche la
    > sintassi corretta `front-utility --list all` è entrata nei pre-pass di
    > `_run_passes` prima che il dispatch leggesse `list_tests`; il probe ha
    > quindi ripopolato `/tmp/librefolio-r2-d` e iniziato Playwright. Il
    > coordinatore ha fermato l'esatto albero processi e gli orphan PID,
    > verificando libere le porte 6041/6153. Tutti gli output/red E2E dei due
    > probe sono invalidi e non entrano nelle evidenze; nessun sorgente o
    > file staged è stato modificato dal run. Correzione centralizzata e
    > regressione `_run_passes(list_tests=True)` restano lease coordinatore
    > + test-author.
    > **Nota implementazione — runner listing chiuso, 2026-09-15**:
    > `_list_front_tests` normalizza metadata `tests` scalari/sequenziali e
    > considera ogni `.spec.ts`; `_run_passes(list_tests=True)` ritorna dal
    > dispatch prima di setup esclusivi, backend condiviso, parallelismo e
    > consolidamento. Le tre regressioni focalizzate sono verdi 3/3; il
    > comando reale `front-utility --list all` termina 0 in 0 s senza
    > cambiare SHA/mtime DB né aprire la porta 6153. Ruff e Black-check sono
    > verdi sui 17 file Python staged.
    > **Evidenza post-fix D**:
    > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
    > test --test-port 6153 --data-dir /tmp/librefolio-r2-d check-orphans`
    > verde (206 backend, 80 E2E, 213 unit); filtro
    > `onboarding route settlement` verde 8/8 e intero
    > `front-utility onboarding-component-unit` verde 369/369 su 12 file.
    > **⚠️ Fuori pista — seconda review indipendente Gate 8,
    > 2026-09-15**: trovato un rischio medium residuo in
    > `frontend/src/routes/(app)/+layout.svelte:146`. `load()` aggiorna lo
    > stato ready/degraded prima di risolvere; il blocco reattivo può quindi
    > chiamare `goto()` prima che il caller awaited entri nel settlement
    > esplicito, che campiona ancora la route vecchia e può ripetere la
    > stessa navigazione. Il test puro non modella i due owner concorrenti.
    > Finding inviato al coordinatore; nessuna correzione eseguita in attesa
    > di lease e regressione test-author.
    > **Nota implementazione — Gate 8 race correction, 2026-09-15**:
    > aggiunto un coordinatore puro non reattivo che acquisisce ownership
    > prima di ogni `appBootstrap.load*`, registra la firma esatta dello
    > snapshot prima di redirect/intro e la mantiene dopo il rilascio. Il
    > percorso reattivo può reclamare atomicamente solo snapshot nuovi:
    > durante l'ownership non agisce, il rilascio non ripete lo snapshot
    > esplicito, mentre una successiva route/stato/destinazione distinta
    > resta gestibile. Initial load e retry condividono ora lo stesso helper
    > `loadAndSettleOnboardingRoute`; nessun timer o compiler dinamico.
    > **Evidenza**: test-author ha aggiunto
    > `keeps bootstrap ownership through the ready reactive race`; Prettier
    > mirato verde, selettore settlement 9/9 e intero
    > `front-utility onboarding-component-unit` 370/370 su 12 file.
    > **⚠️ Fuori pista — terza review indipendente Gate 8,
    > 2026-09-15**: la review della prima correzione ownership ha trovato
    > due rischi medium. Un `/welcome?returnTo=...` terminale poteva ancora
    > essere navigato sia dal settlement layout sia dalla pagina Welcome;
    > inoltre il test simulava manualmente `acquire()` e non avrebbe rilevato
    > uno spostamento errato dell'acquisizione dopo `load()`.
    > **Nota implementazione — Gate 8 ownership finale, 2026-09-15**:
    > ogni snapshot Welcome è ora inerte prima persino di risolvere la
    > destinazione, lasciando la navigazione terminale alla pagina Welcome.
    > L'orchestrazione reale è stata estratta in
    > `runOwnedOnboardingRouteSettlement`: acquisisce prima di invocare il
    > load, attende, campiona route/path solo dopo, esegue il settlement e
    > rilascia sempre in `finally`. Layout initial e retry chiamano entrambi
    > questa funzione; il test-author usa lo stesso seam con load deferred,
    > mutazione del path, tentativo reattivo concorrente, mancato replay e
    > snapshot successivo distinto.
    > **Evidenza finale correzione**: Prettier mirato verde; settlement
    > 10/10 e `front-utility onboarding-component-unit` 371/371 su 12 file.
    > `front check` verde con 0 errori e i 41 warning baseline nei due file
    > estranei già noti. La review indipendente fresca non ha trovato
    > finding azionabili: verificati ownership prima del load, sampling
    > post-await, rilascio `finally`, soppressione dello snapshot tardivo,
    > gestione di uno snapshot successivo distinto e ownership esclusiva
    > della pagina Welcome sulla navigazione terminale.
13. [ ] **Docs-writer EN + review manuale PAC/Rebalancer**
    > **Nota implementazione parziale — 2026-09-14**: docs-writer ha
    > riscritto la guida PAC P1, aggiunto la guida Rebalancer P1 e aggiornato
    > indice/nav EN. Le pagine distinguono target liquidità vs target
    > portafoglio investito, custodia/cassa complete non scalate, quota
    > personale solo informativa, provenienza/date, stale/errori e confini
    > no-solver/no-order.
    > **Evidenza**: `mkdocs build` exit 0; `mkdocs check-links` 12/12;
    > `git diff --check -- mkdocs_src` verde. `mkdocs translate-validate`
    > resta rosso solo sul debito repository-wide già noto (549 file,
    > 393 OK, 12 missing, 105 errors, 110 warning), senza errori/warning
    > strutturali sotto `user/tools/`. Review manuale ancora pendente.
    > **Nota implementazione follow-up — 2026-09-14**: dopo la rimozione dei
    > concetti wire esclusi, docs-writer ha corretto entrambe le guide: P1
    > non emette campi `not_run`/`not_evaluated`, perché solver,
    > ottimizzazione e fattibilità operativa non sono rappresentabili.
    > `mkdocs build` exit 0, link 12/12 e diff-check mirato verde.

Ogni passo viene aggiornato immediatamente con data, nota, comandi/evidenza e
ogni deviazione.

## 8. Prove pianificate

### Platform

- un plugin → due servizi ordinati;
- collisione codice servizio fail-closed;
- descriptor sibling sano preservato quando possibile;
- versione backend comune + UI SemVer indipendenti;
- fingerprint per schema/operazioni;
- catalogo/diagnostica/worker/compute coerenti;
- batch misto PAC + Rebalancer conserva ordine/correlazione;
- renderer incompatibile non monta.

### P1

- evaluator Decimal indipendenti;
- cash/contributi contati una volta;
- pool per valuta e FX esplicito;
- target per strumento esattamente 100;
- stesso strumento multi-Broker aggregato;
- PAC quota ideale budget;
- Rebalancer current/target/gap;
- zero/missing/invalid/unsupported distinti;
- nessuna quantità/ordine/solver implicito.

### Frontend/E2E

- due card, route e renderer;
- IT senza fallback EN;
- Broker selection senza error flash;
- amount-first, virgola/frecce, lettere bloccate;
- summary funding unico;
- scope non semanticamente verde/rosso;
- prezzo attuale esplicito;
- target DataTable exact + barre;
- warning amber;
- FX condizionale;
- result DataTable;
- issue umane + dettagli tecnici chiusi;
- revisione invisibile;
- stale/account/late response preservano draft;
- desktop/mobile PAC e Rebalancer.

## 9. Gate

Comando canonico sequenziale:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
pipenv run python dev.py test \
--test-port 6153 \
--data-dir /tmp/librefolio-r2-d \
<categoria> <azione>
```

Gate finali:

- backend schema/service/platform/API mirati;
- component/unit e client/registry/host;
- PAC + Rebalancer E2E desktop/mobile;
- lint/format mirati;
- API sync freshness dopo handoff coordinatore;
- `front check`, `front build`;
- i18n parity/audit dopo shared;
- MkDocs strict/check-links;
- `git diff --check`;
- porta libera prima/dopo review.

## 10. Definition of done

1. Un plugin pubblica due servizi completi.
2. Versione backend comune e UI SemVer indipendenti validate end-to-end.
3. PAC P1 produce quote teoriche budget, mai ordini.
4. Rebalancer P1 aggrega per identità canonica e mostra current/target/gap.
5. Tutti i feedback Round 3 chiusi.
6. Nessun fallback EN nella review IT.
7. Test/gate shared/docs verdi.
8. Review developer separata PAC/Rebalancer approvata.
9. Solver resta escluso e tracciato nel piano collegato.
10. Nessun artifact privato/runtime/generated non autorizzato, staging o history
    mutation.
