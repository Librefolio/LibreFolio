# PAC allocator UI refinement - Round 2

**Stato:** approvato dal developer; Phase A numerica committata a `a6960ef04`;
slice indipendente Asset global completata, resto congelato in attesa
dell'integrazione H.

← Piano precedente: [PAC allocator P1](plan-phase00PacAllocator.prompt.md)

**Baseline:** `570beb386a7e72085a4ae8f84fb7c966e734c9b1`, oltre al redesign
PAC non ancora committato ma gia validato prima della review manuale.

## 1. Obiettivo

Rendere il PAC coerente con i pattern visuali di LibreFolio senza perdere il
contratto numerico rigoroso, il fallback manuale, le copie snapshot e le guardie
account/request/revision gia consegnate.

Round 2:

1. descrizione Tool su riga card a tutta larghezza;
2. impostazioni di valorizzazione compatte, senza label data duplicata;
3. fondi disponibili prima degli asset;
4. cassa OWNER selezionabile per broker e aggregata dal backend per valuta;
5. contributi separati con passo monetario esatto;
6. gallery Asset con filtro multiplo Posseduti/Altri utenti/Osservati;
7. candidati senza posizione a quantita iniziale zero e senza broker inventato;
8. card importate read-only per i fatti sorgente, target/griglia editabili;
9. card manuali complete ma prive di ID tecnici;
10. layout desktop stato iniziale/target e layout mobile verticale;
11. quote base intera positiva, non piu limitata a 1/100;
12. fix Asset global per Attivi+Inattivi, evidenza ambra e inattivi in fondo.

Restano fuori scope: solver, raccomandazioni, buy/sell, routing broker, ordini,
conversioni FX automatiche, FIFO/WAC/fisco e optimizer Riskfolio.

## 2. Decisioni chiuse

### 2.1 Righe importate

- Asset, broker, quantita iniziale, prezzo, valuta, quote base, data e provider
  sono fatti sorgente bloccati.
- Target e griglia acquisto sono decisioni modificabili.
- Duplica crea una riga manuale indipendente: nuova `row_key`, source link rimosso,
  fatti sbloccati, stessa identita canonica dello strumento.
- `instrument_key` e `row_key` non vengono mostrati.

### 2.2 Cassa

- Gallery dei soli broker OWNER, incluso OWNER 0%.
- Quantita/cassa a custodia intera, mai scalate per quota personale.
- Il backend aggrega i broker selezionati per valuta nativa.
- Il frontend non somma e non converte valori.
- Cassa manuale resta disponibile.
- Contributi nuovi restano per valuta e senza broker: nessun routing.

### 2.3 Due quantum distinti

- `quantity_step`: incremento minimo della quantita acquistabile di un asset.
  Intere normalmente `1`; frazionarie, per esempio, `0.001`.
- `monetary_step`: incremento minimo di un nuovo contributo/soglia operativa
  nella sua valuta. Con step `1 EUR`, `555.55 EUR` non e ammesso.
- La cassa esistente e un fatto osservato e non deve rispettare un passo monetario.
- L'inventario iniziale frazionario non viene mai arrotondato alla griglia acquisti.

### 2.4 Quote base

Il form manuale e il backend PAC accettano qualsiasi intero positivo, come il
dominio Asset. Il valore importato resta read-only.

### 2.5 Categorie Asset

Riusa la tassonomia Asset global:

- Posseduti: `tx_count_own > 0`;
- Altri utenti: nessuna transazione propria e `tx_count > 0`;
- Osservati: nessuna transazione.

Default: solo Posseduti. I chip sono multi-select con unione. La ricerca opera
sul nome.

Un asset storico proprio con quantita corrente zero genera un candidato a zero.
Asset di altri utenti e osservati generano un candidato importato con quantita
zero, nessun broker e nessun dato privato. Contesti correnti non-zero non vengono
omessi se l'Asset e inattivo; candidati aggiuntivi senza posizione sono solo attivi.

### 2.6 Asset global

- Attivi+Inattivi mostra entrambi.
- Attivi solo e Inattivi solo filtrano correttamente.
- Nessuno selezionato conserva il contratto corrente: nessun filtro lifecycle.
- Dentro ogni pannello Posseduti/Altri/Osservati: attivi prima, inattivi in fondo.
- Card e righe inattive hanno sfondo ambra chiaro in light/dark mode; il dot resta
  indicatore secondario.

## 3. Semantica da spiegare nella UI

### 3.1 Impostazioni di valorizzazione

"Scenario" non e una variabile matematica autonoma.

- Valuta report: unita comune per valorizzare asset, cassa e contributi.
- Data di riferimento: cutoff inclusivo per custodia, prezzi e tassi salvati.

Il blocco diventa **Impostazioni di valorizzazione**.

### 3.2 Denominatore P1

I pesi correnti usano solo il valore degli asset investiti. Cassa e contributi
sono riportati separatamente e non modificano pesi/gap: P1 non esegue il solver.

### 3.3 Cambio di valorizzazione

`1 USD = 0.90 EUR` significa che una unita USD vale 0.90 EUR nel report. Non
scambia, trasferisce o fonde casse. Un tasso mancante non diventa mai `1`.

## 4. Contratti

### 4.1 Tool PAC `1.0.0` evoluto in place

Unica versione pubblica per backend e renderer. Il contratto non e ancora stato
pubblicato: Round 2 evolve `1.0.0` in place senza introdurre `1.1.0`.

```text
cash_balances[]:
  currency
  amount

contributions[]:
  currency
  amount
  monetary_step

rows[].quote.quote_base_quantity:
  integer > 0

rows[].buy_grid:
  mode = whole | fractional
  quantity_step = exact decimal > 0
```

Gate:

- `monetary_step > 0`;
- contributo non negativo e multiplo esatto del passo;
- cassa esclusa dal vincolo monetario;
- quote base intera positiva;
- whole step intero positivo;
- fractional step positivo;
- duplicate currency/nonfinite/scientific restano invalidi;
- output normalizzato conserva stringhe Decimal e `monetary_step`;
- `optimization="not_run"` e stati P1 restano invariati.

Default UI visibili, non policy nascoste:

- whole `1`;
- fractional `0.001`, modificabile;
- nuovo contributo `0.01`, modificabile.

### 4.2 Portfolio allocation source

Nessun `/tools/prefill`. Estensione del dominio Portfolio:

```text
request:
  as_of_date
  selected_cash_broker_ids[]

response:
  assets[]
  cash_sources[]
  selected_cash_balances[]
```

Ogni Asset espone metadata globali, `active`, `usage_scope`, chiave candidato,
ultimo prezzo salvato <= data, contesti OWNER correnti. Ogni contesto include i
campi necessari a `BrokerIcon`. Ogni cash source include broker, icone, quota
personale informativa e saldi nativi alla data.

Regole:

1. classificazione con contatori transazioni esistenti;
2. contesti OWNER non-zero a custodia intera;
3. candidato a zero se non esiste un contesto corrente;
4. nessun broker/quantita/cassa altrui;
5. nessuna chiamata provider e nessun `/assets/prices/current`;
6. prezzo mancante mantenuto;
7. cassa da somma `Transaction.amount` inclusiva della data;
8. ID selezionati devono essere accessibili OWNER, altrimenti errore esplicito;
9. aggregazione per valuta, una volta per broker/valuta;
10. zero/negativi preservati, mai clamp;
11. cache/fingerprint include metadata Asset/Broker, quote, cash transaction e data.

### 4.3 Stato editor

Origini:

```text
manual
portfolio_context
catalog_candidate
manual_duplicate
```

Cash:

```text
not_supplied | none | broker_copy | manual
selectedBrokerIds
sourceAsOfDate
sourceFingerprint
backendAggregatedBalances
manualBalances
stale
```

Solo i campi matematici entrano nel payload Tool.

## 5. ASCII approvata

### 5.1 Tool card

```text
+------------------------------------------------------------------+
| [calculator] PAC allocator                         [book] Docs    |
|                                                                  |
| Analyze the exact initial allocation state.                      |
| Version 1.0.0                                         [arrow ->] |
+------------------------------------------------------------------+
```

Mobile:

```text
+----------------------------------+
| [calc] PAC allocator      [book] |
| Analyze the exact initial        |
| allocation state.                |
| Version 1.0.0               [->] |
+----------------------------------+
```

Descrizione sibling a tutta card; card intera resta link; Docs resta azione separata.

### 5.2 Ordine pagina

```text
Tool header                         Docs | Refresh
Subtitle a tutta larghezza

Impostazioni di valorizzazione
1. Fondi disponibili
2. Asset e target
3. Tassi di valorizzazione (solo se servono)
Analizza stato
Risultati
```

### 5.3 Valorizzazione

```text
Impostazioni di valorizzazione                              [i]
+------------------------------+ +------------------------------+
| Valuta report                | | Data di riferimento          |
| [EUR Euro                 v] | | [calendar] 2026-09-11       |
+------------------------------+ +------------------------------+
```

Mobile: due controlli verticali. Una sola label per campo, stessa altezza/bordo/focus.

### 5.4 Fondi desktop

```text
1. Fondi disponibili
[Non indicata] [Nessuna] [Dai broker] [Manuale]

+--------------------------+ +--------------------------+
| [Broker] Directa     [x] | | [Broker] IBKR       [ ] |
| EUR 1,250.35             | | EUR 200.00               |
| USD    40.00             | | USD 900.00               |
+--------------------------+ +--------------------------+

Aggregato backend read-only: EUR 1,250.35 | USD 40

Nuovi contributi
+----------------+ +-----------+ +-------------------+       [+]
| Importo        | | Valuta    | | Passo monetario i |
| 555            | | EUR    v  | | 1 EUR             |
+----------------+ +-----------+ +-------------------+
```

Mobile:

```text
[Non indicata] [Nessuna]
[Dai broker]   [Manuale]

+------------------------------+
| [Directa] EUR 1,250.35  [x] |
|           USD    40.00      |
+------------------------------+

Nuovo contributo              [+]
[Importo 555                  ]
[EUR                       v  ]
[Passo 1 EUR                i ]
```

### 5.5 Gallery Asset

```text
2. Asset e target
[x Posseduti 8] [ Altri 5] [ Osservati 4]       [cerca nome...]
                                                  [refresh] [+ Nuovo]

+----------------------+ +----------------------+ +----------------------+
| [Asset] Microsoft[x]| | [Asset] BTP      [ ]| | [Asset] VWCE     [ ]|
| MSFT · 2 contesti    | | 101.20 EUR           | | quantita iniziale 0 |
| 410.25 USD           | |                      | | prezzo mancante      |
+----------------------+ +----------------------+ +----------------------+
```

Mobile: chip, cerca, refresh e `+` verde icon-only; card a colonna singola.

### 5.6 Riga importata corrente

```text
+--------------------------------------------------------------------------+
| [Asset] Microsoft Corporation        [Broker] Interactive Brokers        |
| MSFT · snapshot importato                         [copy] [trash red]      |
| Snapshot 2026-09-11 · prezzo 2026-09-11 · [provider icon] · read-only  |
+-----------------------------------+--------------------------------------+
| STATO INIZIALE                    | TARGET                               |
| Custodia broker       2 quote     | Peso target          [30.00] %       |
| Quota economica       30% [i]     | Griglia       [# Intere][.1 Frac] i |
| Prezzo nativo         410.25 USD  | Passo quantita       [1] quote i     |
| Base quotazione       1 unita     |                                      |
+-----------------------------------+--------------------------------------+
```

### 5.7 Candidato catalogo a zero

```text
+--------------------------------------------------------------------------+
| [Asset] Vanguard FTSE All-World                    [Osservato]            |
| Nessuna custodia corrente                       [copy] [trash red]        |
| prezzo 2026-09-10 · [provider icon] · read-only                        |
+-----------------------------------+--------------------------------------+
| STATO INIZIALE                    | TARGET                               |
| Quantita iniziale     0           | Peso target          [20.00] %       |
| Prezzo nativo         121.34 EUR  | Griglia       [# Intere][.1 Frac] i |
| Base quotazione       1           | Passo quantita       [1] quote i     |
+-----------------------------------+--------------------------------------+
```

### 5.8 Riga manuale

```text
+--------------------------------------------------------------------------+
| Nuovo asset manuale                                [copy] [trash red]    |
+-----------------------------------+--------------------------------------+
| STATO INIZIALE                    | TARGET                               |
| Nome asset        [............]  | Peso target          [......] %      |
| Quantita          [......] quote  | Griglia       [# Intere][.1 Frac] i |
| Prezzo nativo     [....][EUR v]   | Passo quantita       [1......] i     |
| Base quotazione   [1.........] i  |                                      |
| Data prezzo       [calendar ....] |                                      |
+-----------------------------------+--------------------------------------+
```

Mobile: header Asset/Broker/source, azioni icon-only, stato iniziale sopra target.
Remove resta rosso discreto. Numeri senza zero finali inutili.

### 5.9 FX e azione

```text
3. Tassi di valorizzazione [i]
Solo confronto valori; nessuna cassa viene scambiata.

1 [USD] = [0.900000] [EUR]  data [calendar 2026-09-11] [trash]

                                             [Analizza stato]
```

`2/32` diventa `2 contesti selezionati`; limite in Tooltip/avviso da 28.

### 5.10 Asset global

```text
[x Attivi] [  Inattivi] -> attivi
[  Attivi] [x Inattivi] -> inattivi
[x Attivi] [x Inattivi] -> entrambi
[  Attivi] [  Inattivi] -> entrambi

Pannello:
  card/riga attiva
  card/riga attiva
  card/riga inattiva  <- sfondo ambra chiaro
  card/riga inattiva  <- sfondo ambra chiaro
```

## 6. Guardie

1. Fetch catalogo/cassa keyed per account generation + data.
2. Filtri gallery non rimuovono righe gia selezionate.
3. Copia asset multi-contesto atomica.
4. Data nuova marca asset/cassa stale, non sovrascrive.
5. Selezione broker avvia aggregazione backend protetta; risposta vecchia ignorata.
6. Dati mancanti restano mancanti.
7. Import con dato mancante si completa duplicando in manuale.
8. Conferme rimozione/refresh import restano.
9. Protezione risultato stale/busy/timeout resta.

## 7. Superfici

| Area | File principali |
|---|---|
| Tool PAC | `backend/app/schemas/pac_allocator.py`, `backend/app/services/pac_allocator/*`, plugin PAC |
| Portfolio source | `backend/app/schemas/portfolio.py`, `backend/app/services/portfolio_allocation_source.py`, `portfolio_service.py` |
| Tool shell | `frontend/src/lib/features/tools/ToolsHub.svelte`, registry/client |
| PAC UI | `frontend/src/lib/features/tools/pac-allocator/*` |
| Shared controls | `ExactDecimalInput`, `CurrencySearchSelect`, `SingleDatePicker`, `Tooltip` |
| Asset global | Assets `+page.svelte`, `AssetCard.svelte`, `AssetTable.svelte` |
| Shared outputs | generated client, i18n, runner, CHANGELOG |
| Docs | Tool/PAC e Asset English docs |

## 8. Passi

1. [x] 2026-09-11 - Piano Round 2 approvato e cross-linkato.
   > **Nota implementazione**: decisioni chiuse, ASCII desktop/mobile, contratti,
   > privacy, test e DoD persistiti.
2. [x] 2026-09-11 - Evolvere il contratto PAC non pubblicato `1.0.0` in place: passo
   monetario e quote base positive.
   > **Nota implementazione 2026-09-11**: il coordinatore ha autorizzato una
   > ripresa stretta dei soli schema/modello/normalizer/evaluator/report/plugin
   > PAC e relativi test schema/service via `test-author`. Override developer:
   > la versione pubblica resta `1.0.0`; nessun bump `1.1.0`.
   > **Fuori pista**: Round 2 e stato congelato prima dell'implementazione per
   > sovrapposizione con H su `schemas/portfolio.py`, `portfolio_service.py` e
   > relativi test. Nessun workstream Fleet aveva modificato file produzione.
   > Restano congelati Portfolio/allocation source, frontend, Asset global,
   > generated client, i18n, docs, runner e CHANGELOG fino al merge H.
   > **Nota implementazione 2026-09-11**: introdotti input contributo con
   > `monetary_step` positivo e divisibilita Decimal esatta, cash invariato,
   > quote base intera positiva arbitraria, normalized contribution con
   > amount+step esatti; rimossi `quote_basis_unsupported` e
   > `allowed_quote_bases`. Versione plugin/renderer/documentazione confermata
   > `1.0.0`; `optimization="not_run"` e stati P1 invariati.
   > **Evidenza**:
   > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
   > --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas pac-analyze`
   > -> 848 passed; stesso prefisso con `services pac-analyze` -> 221 passed;
   > `git diff --check` verde; porta 6153 libera.
   > **Fuori pista**: primo gate service si e fermato prima del setup per il
   > server di review D ancora attivo su 6153; DB lasciato intatto. Verificati
   > PID `5951/5988` come server D
   > `dev.py server --test --port 6153 --data-dir /tmp/librefolio-r2-d`,
   > arrestati per PID esplicito, poi gate rieseguito una sola volta con esito
   > verde.
3. [ ] Espandere Portfolio allocation source: catalogo, icone, cash source/aggregate.
4. [ ] Sincronizzare client e adapter dopo stabilizzazione schema.
5. [ ] Implementare controlli/layout PAC.
6. [ ] Implementare funding-first e gallery catalogo.
7. [ ] Separare card importate/manuali e azioni responsive.
8. [x] 2026-09-11 - Correggere Asset global lifecycle/ordine/sfondo.
   > **Nota implementazione 2026-09-11**: estratta una regola lifecycle unica:
   > Attivi+Inattivi e nessuno selezionato mantengono l'unione, mentre le
   > selezioni singole filtrano il rispettivo stato. Ogni pannello
   > Posseduti/Altri utenti/Osservati conserva l'ordine ricevuto dentro il
   > gruppo ma sposta stabilmente gli inattivi in fondo. Card e righe inattive
   > espongono stato semantico e superficie ambra light/dark; dot, focus e
   > selezione restano distinguibili.
   > **Evidenza**:
   > `npx prettier --check` sui sei file della slice -> verde;
   > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
   > test --test-port 6153 --data-dir /tmp/librefolio-r2-d front-utility
   > component-unit 'asset lifecycle'` -> 7 passed;
   > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
   > front check` -> verde;
   > stesso prefisso lane con `front-asset asset-list` e i due selettori
   > lifecycle mirati -> 2 passed desktop; `git diff --check` verde e porta
   > 6153 libera dopo il teardown del runner.
   > **Fuori pista**: il primo check Prettier ha segnalato soltanto
   > `AssetCard.svelte`; applicato Prettier al file e ripetuto il check con
   > esito verde. Il graph cache wiki era assente nel worktree, quindi sono
   > state lette le pagine committate `F-032` e `dual-view-pattern`.
9. [ ] Aggiungere test tramite `test-author`.
   > **Nota implementazione parziale 2026-09-11**: `test-author` ha aggiunto
   > regressioni component/unit ed E2E deterministiche per truth table,
   > ordinamento per ogni pannello e marker visuali card/riga. Il passo resta
   > aperto per i test delle slice Portfolio/PAC ancora congelate.
10. [ ] Aggiornare i18n, docs EN tramite `docs-writer`, CHANGELOG.
11. [ ] Gate combinati e nuova review manuale desktop/mobile su lane 6153.

Ogni passo completato riceve immediatamente data, `Nota implementazione`, comando
ed evidenza. Ogni deviazione riceve `Fuori pista`.

## 9. Test

Backend:

- quote base positiva arbitraria e valore Decimal;
- monetary step positivo, multiplo/non multiplo esatto;
- cassa non quantizzata;
- whole/fractional quantity step;
- schema/descriptor/normalized output coerenti con `1.0.0` evoluto in place;
- categorie Asset esatte;
- own storico a zero, current inattivo, altri/osservati;
- nessun dato privato altrui;
- quote <= as-of e prezzo mancante;
- cash OWNER/OWNER0, full custody, as-of, aggregato per valuta;
- broker ID non autorizzato rifiutato;
- cache invalidation su Asset/Broker/price/cash.

Frontend:

- unione chip categorie e ricerca nome;
- selezione non persa se nascosta dal filtro;
- current context vs zero candidate;
- source import bloccata, target editabile, duplica manuale;
- ID tecnici assenti;
- icone/fallback;
- quote base intera e formatter exact;
- altezze campi e label data unica;
- responsive labels/azioni;
- cash aggregate solo backend e late-response guard;
- contribution monetary step;
- FX condizionale;
- cap 28/32;
- Tool card description.

Asset global:

- API senza `active` restituisce entrambi;
- truth table quattro stati;
- inattivi in fondo per pannello;
- classi ambra card/riga;
- focus/hover/dark mode.

E2E desktop/mobile:

- Tool card/first open;
- cassa broker e contributo valido/invalido;
- tre categorie e search;
- multi-context, zero-own, other/observed privacy;
- duplicate/manual;
- grid quantity;
- missing quote/FX, invalid, stale;
- Asset global both-toggle e inactive styling/order.

## 10. Lane e gate

Solo:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc
pipenv run python dev.py ...
port 6153
data /tmp/librefolio-r2-d
```

Mai bare `./dev.py`, 6040/6041, `--force`, install o runtime concorrente nella lane.

Gate:

- PAC schema/service;
- Portfolio source service/API;
- Tool lifecycle/API/PAC API;
- frontend unit/component;
- Asset global regressions;
- PAC desktop+mobile E2E;
- orphan inventory;
- API sync;
- Ruff/Black/Prettier/Svelte check/build;
- i18n audit;
- MkDocs strict/check-links;
- diff-check e port teardown.

Test nuovi/modificati solo via `test-author`; docs EN via `docs-writer`.

## 11. DoD

1. Tool card descrizione full-width senza regressione link/docs.
2. Valuta/data uniformi e label unica.
3. Funding prima degli asset.
4. Cassa broker full-custody aggregata backend per valuta.
5. Contributi con passo monetario separato.
6. Gallery default Posseduti, union Altri/Osservati e cerca nome.
7. Candidati zero senza broker inventato o privacy leak.
8. Import read-only + target/grid editabili + duplicate manuale.
9. Icone canoniche e nessun ID tecnico.
10. Layout manuale/importato desktop/mobile approvato.
11. Quote base positiva e quantum distinti in contract/UI/docs/test.
12. Asset global both-toggle verde, inattivi ambra in fondo.
13. Gate verdi, nessun artifact privato/generato staged.
14. Server review ricostruito e review first-hand chiusa dal developer.
