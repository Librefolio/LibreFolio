# PAC allocator UI refinement - Round 2

**Stato:** approvato dal developer; Phase A numerica committata a `a6960ef04`;
slice Asset global committata a `7a02517e6`; WIP Round 2 preservato a
`8273335ff`; merge H chiuso dal developer a `d7d40c0ec`. Ripresa Round 2
completa autorizzata dopo il gap audit: slice A-D concluse, produzione E-F
implementata e in validazione; superfici condivise, cataloghi e documentazione
restano ai writer coordinati. Nessuna integrazione dichiarata prima della nuova
review developer.

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
3. [x] 2026-09-11 - Espandere Portfolio allocation source: catalogo, icone, cash source/aggregate.
   > **Nota implementazione 2026-09-11**: `/portfolio/report` espone ora, solo
   > su richiesta esplicita, il catalogo globale privacy-safe: tutti gli Asset
   > attivi e gli inattivi con custodia OWNER corrente, tassonomia
   > `owned|other_users|observed`, chiavi candidate stabili, prezzi salvati
   > alla data richiesta e soli contesti OWNER in full custody (inclusi
   > OWNER0). I contesti includono metadati icona/portale/plugin Broker; nessun
   > contesto, broker o saldo di altri utenti viene serializzato.
   > **Nota implementazione 2026-09-11 - cassa**: aggiunta selezione stretta e
   > senza duplicati di Broker OWNER. Il backend restituisce ogni fonte cassa
   > OWNER per valuta nativa e aggrega una sola volta i Broker selezionati,
   > senza conversione, share scaling o clamp; saldi zero/negativi e
   > inclusivita `as_of_date` sono preservati. ID non OWNER/inaccessibili
   > producono `403 allocation_source_cash_broker_forbidden`.
   > **Nota implementazione 2026-09-11 - cache/privacy**: identita L2 estesa a
   > selezione cassa, catalogo/active/metadati Asset, quote salvate,
   > metadati Broker OWNER, transazioni OWNER e conteggi globali necessari alla
   > sola categoria coarse. Il filtro report non restringe il source editor.
   > Conservati i contratti H FIFO/YOC/report e nessuna chiamata provider.
   > **Evidenza**: `test-author` ha aggiunto le regressioni service/API.
   > Con prefisso lane canonico: `services roi-fifo-utils
   > TestPortfolioAllocationSource` -> `12 passed`; `api portfolio` sui
   > quattro selettori allocation-source -> `10 passed`; suite condivise
   > allargate `services roi-fifo-utils` -> `396 passed` e `api portfolio`
   > -> `34 passed`. Dopo il refactor di lint, ripetuti i selettori mirati con
   > gli stessi `12/12` e `10/10`. Ruff sui sei file, Black mirato e
   > `git diff --check` verdi; porta 6153 libera.
   > **Fuori pista**: il primo gate statico ha rilevato solo
   > `C901 build_portfolio_allocation_source (20 > 10)`. Separati caricamenti,
   > proiezioni e aggregazione cassa in helper focalizzati, senza cambiare I/O;
   > formattati i due file service e ripetuti lint e test mirati con esito
   > verde. Nessun API sync ancora eseguito: il passo 4 resta bloccato sul
   > writer coordinatore.
4. [x] 2026-09-11 - Sincronizzare client e adapter dopo stabilizzazione schema.
   > **Nota implementazione 2026-09-11**: dopo sync coordinatore verde, il
   > normalizer frontend tratta come obbligatori `candidate_key`, lifecycle e
   > `usage_scope`, conserva metadata Broker dei contesti, normalizza
   > `cash_sources` e `selected_cash_balances` senza sommare o convertire, e
   > invia sempre `selected_cash_broker_ids`. Estesi i tipi editor con origini
   > `manual|portfolio_context|catalog_candidate|manual_duplicate`, metadata
   > sorgente completi e stato cassa broker/manuale/stale. Artifact
   > OpenAPI/Zodios/Tool restano ignorati e non modificati dal workstream.
   > **Evidenza**: Prettier mirato verde; `front check` -> `0 errors`, 41
   > warning deprecation preesistenti; gate registrato completo
   > `front-utility component-unit` -> `70 files / 1833 tests passed`.
   > **Fuori pista**: il primo type-check ha trovato quattro fixture
   > `PacAllocatorTool.test.ts` prive dei nuovi default metadata/cash; corrette
   > esclusivamente da `test-author`, poi type-check verde. Due tentativi
   > mirati tramite filtro nome hanno raccolto zero test adapter (uno ha
   > eseguito solo un test PAC non correlato): non sono stati contati come
   > evidenza. Eseguito quindi il gate component-unit registrato completo, che
   > ha incluso realmente tutti i 70 file.
5. [x] 2026-09-11 - Implementare controlli/layout PAC.
   > **Nota implementazione parziale 2026-09-11 - contributi**: aggiunto il
   > tipo editor distinto per contributi, default visibile ed editabile
   > `monetary_step="0.01"` per ogni nuova riga e serializzazione esatta del
   > valore nel contratto pubblico PAC `1.0.0`. `PacMoneySection` mostra il
   > controllo Decimal soltanto per i contributi, con layout a riga su desktop
   > e stack compatto su mobile. Cassa, quote base, fatti importati/manuali e
   > altre semantiche restano invariati. Nessun catalogo i18n, client generato
   > o file condiviso modificato in questa slice.
   > **Fuori pista 2026-09-11 - editor**: il primo `front check` della slice E
   > ha trovato due soli errori nel nuovo formatter read-only, che accettava
   > `string|null` mentre i campi wire possono essere anche `undefined`.
   > Allargato il tipo dell'helper a `string|null|undefined`, senza fallback
   > economici o modifica dei valori; gate da ripetere dopo il completamento
   > della slice.
   > **Nota implementazione parziale 2026-09-11 - editor**: il form usa ora
   > due pannelli responsive `Stato iniziale`/`Target`; su mobile restano
   > verticali. Le nuove righe manuali/importate mostrano il default acquisti
   > `whole + 1`; lo switch fra intere e frazionarie applica `0.001`/`1` solo
   > quando il passo precedente era ancora il default, preservando un valore
   > custom. La quote base manuale e un input numerico `min=1 step=1`, quindi
   > non e piu limitata al select `1/100`. Aggiunti Tooltip distinti per base
   > quotazione, griglia e passo quantita.
   > **Evidenza parziale**: Prettier mirato sui due file produzione verde;
   > secondo `front check` -> `0 errors`, 41 warning deprecation preesistenti.
   > **Nota implementazione 2026-09-11 - shell/FX/risultati P1**: `Scenario`
   > diventa `Valuation settings`, con spiegazione del ruolo matematico,
   > Currency selector compatto e una sola label per `SingleDatePicker`. La
   > sezione FX appare solo quando esistono valute estere o un draft FX gia
   > configurato; ogni riga rende esplicita l'equazione
   > `1 valuta nativa = tasso valuta report` e ribadisce che non scambia,
   > trasferisce o unisce casse. Il risultato apre nella vista formattata,
   > spiega il denominatore P1 basato sui soli Asset investiti e mantiene le
   > casse native separate per valuta. Nessun dato after/order/solver e stato
   > simulato.
   > **Evidenza**: Prettier mirato sui tre file produzione PAC verde;
   > `front check` -> `0 errors`, 41 warning deprecation preesistenti.
6. [x] 2026-09-11 - Implementare funding-first e gallery catalogo.
   > **Nota implementazione parziale 2026-09-11 - funding-first**: il blocco
   > Fondi precede ora gli Asset. La cassa espone quattro stati distinti
   > `not_supplied|none|broker_copy|manual`; in modalita broker mostra solo
   > fonti OWNER con `BrokerIcon`, quota personale informativa e saldi nativi,
   > ma usa nel payload esclusivamente `selected_cash_balances` restituito dal
   > backend. Nessuna somma/conversione economica frontend. Selezione, data,
   > account generation e refresh sono protetti da sequence/AbortSignal; una
   > risposta vecchia viene ignorata e lo stato stale/pending disabilita
   > Analizza. Il fallback manuale conserva righe e contributi.
   > **Evidenza**: Prettier mirato verde; `front check` -> `0 errors`, 41
   > warning preesistenti; sette test component mirati -> `7 passed`, inclusi
   > quattro mode, aggregate backend esatto, late responses, errore+fallback,
   > separazione contributi e ordine funding prima della gallery.
   > **Fuori pista**: il primo run mirato ha chiuso `6 passed / 1 failed`.
   > Triage: assumption test, non difetto prodotto. Il test aggiungeva una
   > seconda riga manuale senza compilare il nome `required`, quindi la
   > constraint validation nativa impediva `submit`. `test-author` ha
   > compilato soltanto quel prerequisito; rerun congiunto `7/7` verde.
   > **Nota implementazione 2026-09-11 - gallery catalogo**: la gallery usa
   > tre filtri multi-select in unione `owned|other_users|observed`, con
   > default solo `owned`, conteggi espliciti e ricerca esclusivamente per nome
   > Asset. L'ordine e stabile active-first/inactive-last; le card inattive
   > espongono lifecycle semantico e superficie ambra. La selezione resta nel
   > draft quando filtri o ricerca nascondono una card. Un Asset senza contesti
   > crea una sola riga `catalog_candidate` a quantita iniziale zero, senza
   > inventare Broker o altri dati privati; un Asset corrente conserva invece
   > atomicamente tutti i contesti OWNER.
   > **Evidenza**: `test-author` ha portato il file PAC a 29 test con una nuova
   > regressione e tre casi estesi. Con prefisso lane canonico,
   > `front-utility component-unit` sui quattro selettori gallery -> `4 passed`
   > (`1 file`, `69 skipped`, catalogo complessivo `1834`); `front format
   > --check` verde; `front check` -> `0 errors`, 41 warning deprecation
   > preesistenti in due file.
7. [x] 2026-09-11 - Separare card importate/manuali e azioni responsive.
   > **Nota implementazione 2026-09-11**: i fatti sorgente importati
   > (Asset/Broker, quantita, prezzo/valuta, base, data e provider) sono
   > renderizzati read-only; solo target e griglia restano controlli. Header
   > con `AssetIcon`, `BrokerIcon` e icona provider canonica; custodia intera e
   > quota economica personale sono distinte. `instrument_key` e `row_key`
   > restano interni e non vengono mostrati. `Duplica` crea ora una
   > `manual_duplicate` source-free con nuova `row_key`, fatti editabili e
   > stessa identita canonica nascosta. Il refresh aggiorna i soli fatti
   > sorgente e conserva target/griglia correnti. Azioni con testo da `sm` e
   > icon-only sotto `sm`. La copertura resta tracciata separatamente nel passo
   > 9.
   > **Evidenza 2026-09-12**: `test-author` ha aggiornato 11 test esistenti
   > senza cambiare il totale (`29`). Gate `front-utility component-unit` sui
   > selettori E -> `11 passed`, `1 file`, `69 skipped`, catalogo complessivo
   > `1834`.
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
9. [x] 2026-09-12 - Aggiungere test tramite `test-author`.
   > **Nota implementazione parziale 2026-09-11**: `test-author` ha aggiunto
   > regressioni component/unit ed E2E deterministiche per truth table,
   > ordinamento per ogni pannello e marker visuali card/riga. Il passo resta
   > aperto per i test delle slice Portfolio/PAC ancora congelate.
   > **Nota implementazione parziale 2026-09-11 - monetary step**:
   > `test-author` ha completato i tre file PAC gia preservati. Il test API
   > mantiene fingerprint `884ce254...` e input/output normalizzato con step;
   > il component test verifica default `0.01`, assenza del controllo sulla
   > cassa, precisione a 12 decimali e persistenza attraverso i mode toggle;
   > l'E2E riusa i 14 scenari su desktop/mobile e verifica default, assenza
   > cash-control e serializzazione esatta. Nessun test duplicato o count
   > aumentato; `git diff --check` mirato verde.
   > **Nota implementazione parziale 2026-09-11 - allocation source**:
   > `test-author` ha esteso esclusivamente i test Portfolio service/API per
   > catalogo active/inactive, tre usage scope, OWNER0/full custody, metadata
   > Broker, saldi nativi e aggregazione selezionata, as-of, privacy/403,
   > validazione stretta e invalidazione cache. Nessun file runner, produzione
   > o generated e stato modificato dal writer test.
   > **Nota implementazione parziale 2026-09-11 - adapter frontend**:
   > `test-author` ha esteso `allocationSource.test.ts` per nuova shape,
   > cash/broker metadata, selezione esplicita, default array e fail-closed
   > protocol; ha aggiornato solo le fixture tipate di
   > `PacAllocatorTool.test.ts`. Il gate component-unit completo ha chiuso
   > `1833/1833`.
   > **Nota implementazione parziale 2026-09-11 - funding**:
   > `PacAllocatorTool.test.ts` copre ordine DOM, quattro mode cassa, cards
   > OWNER, ID selezionati, aggregate backend senza somma frontend,
   > pending/disabled, risposte vecchie per selezione/data/account, errore e
   > fallback manuale. Gate finale mirato `7/7`.
   > **Nota implementazione parziale 2026-09-11 - gallery catalogo**:
   > `PacAllocatorTool.test.ts` copre default e unione dei tre scope, conteggi,
   > ricerca per nome, selezioni nascoste persistenti, ordine lifecycle,
   > privacy delle card globali, import atomico multi-contesto, candidato zero,
   > deselection collegata e cap 32 all-or-nothing. Gate mirato `4/4`; totale
   > file PAC `29` test. Il passo resta aperto per editor, risultati ed E2E.
   > **Nota implementazione parziale 2026-09-12 - editor**: 11 test esistenti
   > coprono fatti importati bloccati, ID tecnici assenti dalla UI, icone
   > Asset/Broker/provider, custodia intera vs quota personale, candidato senza
   > Broker inventato, duplica source-free, quote base manuale arbitraria,
   > default/switch quantum, refresh che preserva target/griglia e warning
   > 28/32. Gate mirato `11/11`. Il passo resta aperto per shell FX/risultati ed
   > E2E desktop/mobile.
   > **Nota implementazione parziale 2026-09-12 - contratto backend finale**:
   > sulla lane 6153, `schemas pac-analyze` -> `848 passed`, `services
   > pac-analyze` -> `221 passed`, `api pac-tool` -> `1 passed`. Contratto
   > pubblico invariato a `1.0.0`; nessun solver, ordine, routing o FX di
   > esecuzione introdotto.
   > **Nota implementazione parziale 2026-09-12 - controlli condivisi**:
   > gate `front-utility component-unit ExactDecimalInput
   > CurrencySearchSelect SingleDatePicker` -> `51 passed` in tre file. Nessun
   > test fuori filtro contato come evidenza.
   > **Fuori pista 2026-09-12 - E2E finale A-F**: il comando lane
   > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
   > --test-port 6153 --data-dir /tmp/librefolio-r2-d front-utility pac-tool`
   > ha chiuso `26/28`. I due rossi sono lo stesso scenario su desktop/mobile:
   > il test pretende il valore wire `40.000000%`, mentre la UI formattata
   > mostra correttamente `40%`; Broker, data, provider e resto dei fatti sono
   > presenti. Verdetto `test-triage`: **assumption**, non difetto, stato
   > condiviso, ambiente, lentezza o flaky. Riparazione semantica affidata allo
   > stesso `test-author`; nessuna modifica produzione.
   > **Fuori pista 2026-09-12 - secondo E2E finale A-F**: dopo la prima
   > canonicalizzazione il rerun completo e rimasto `26/28`; lo stesso scenario
   > desktop/mobile ha superato la quota personale e rivelato l'identica
   > assunzione successiva, quantita wire `1.500000` contro resa intenzionale
   > `1.5 units`. Verdetto ancora **assumption**. Richiesto al writer test un
   > audit circoscritto di tutti i Decimal wire confrontati con fatti
   > formattati nello scenario, per evitare correzioni assertion-per-assertion;
   > nessun difetto o cambio produzione.
   > **Evidenza 2026-09-12 - regressione component completa**: durante la
   > riparazione E2E, il gate indipendente e sequenziale
   > `front-utility component-unit` ha chiuso `70/70` file e `1834/1834` test.
   > Restano soltanto avvisi Svelte deprecation gia preesistenti nei componenti
   > Broker/settings fuori scope.
   > **Nota implementazione finale 2026-09-12 - E2E A-F**: il `test-author`
   > ha canonicalizzato esclusivamente le asserzioni di resa Decimal dei fatti
   > importati, mantenendo intatte le stringhe esatte nei payload e tutti i
   > controlli Broker/data/provider/valuta/quote basis. Il terzo run completo
   > `front-utility pac-tool` ha chiuso verde `28/28`: 14 scenari su desktop e
   > gli stessi 14 su mobile.
10. [ ] Aggiornare i18n, docs EN tramite `docs-writer`, CHANGELOG.
    > **Nota implementazione parziale 2026-09-12 - handoff i18n**: confronto
    > deterministico tra call site PAC correnti, baseline `HEAD` e quattro
    > cataloghi. Inviato al coordinatore il set atomico con valori finali
    > EN/IT/FR/ES e riferimenti produzione: `45 ADD`, `10 UPDATE`, `14 REMOVE`.
    > Per le rimozioni verificati zero riferimenti correnti in `frontend/src`;
    > nessun catalogo modificato in D. Applicazione/audit/parita restano di
    > proprieta del coordinatore. Documentazione EN delegata al `docs-writer`;
    > CHANGELOG resta fuori scope D.
    > **Evidenza coordinatore 2026-09-12**: il writer unico J ha applicato i 45
    > ADD e i 10 UPDATE; audit/parita verdi `3043/3043`, zero incomplete e zero
    > chiavi backend mancanti. Dodici REMOVE erano gia assenti su J.
    > `tools.pacAllocator.scenario` e `tools.pacAllocator.rates.title` restano
    > temporaneamente per call site P1 ancora vivi su J e saranno rimossi via
    > CLI soltanto dopo l'integrazione della produzione D. Cataloghi D invariati.
    > **Nota implementazione parziale 2026-09-12 - docs EN**: il
    > `docs-writer` ha riallineato soltanto
    > `mkdocs_src/docs/user/tools/pac-allocator/index.en.md` al comportamento
    > stabile A-F: facts/cash backend-owned, funding-first, scope/privacy,
    > import bloccato e copia manuale, quote base/quantum distinti, FX/casse
    > native, workflow/risultati e confine P1 senza solver. Gate con venv
    > condiviso: `mkdocs build` exit 0, `mkdocs check-links` `12/12`, diff-check
    > verde. Nessun sibling tradotto esiste, quindi `translate-validate` non
    > applicabile; nessun translate/stamp/nav eseguito. Debito Aphra
    > sostanziale esplicitamente preservato. Step resta aperto per
    > CHANGELOG/cataloghi/integrazione condivisa del coordinatore.
11. [ ] Gate combinati e nuova review manuale desktop/mobile su lane 6153.
   > **Nota implementazione 2026-09-11 - ripresa post-merge**: verificato
   > `HEAD=d7d40c0ec4773bc1b81ecefe8b6d8c5e2389ba00`, merge chiuso, index vuoto e
   > set preservato esattamente limitato a piano + test PAC API + E2E + unit.
   > Graph wiki non disponibile nel worktree; ricerca mirata sulle pagine
   > committate senza risultati PAC pertinenti. Riletti contratto Round 2,
   > istruzioni frontend/testing e wiring corrente prima di modificare la
   > produzione.
   > **Nota implementazione parziale 2026-09-11 - merge H**: verificati
   > `HEAD=8273335ff` e `MERGE_HEAD=f092a194b`; risolti additivamente e staged
   > soltanto `CHANGELOG.md`, `backend/app/schemas/portfolio.py`,
   > `backend/app/services/portfolio_service.py` e
   > `backend/test_scripts/test_api/test_portfolio_api.py`. Conservati i
   > contratti H YOC/FIFO/cache/report e i contratti D allocation source.
   > Revisionati anche l'auto-merge del test service Portfolio, i quattro
   > cataloghi i18n e il renderer H.
   > **Evidenza backend**: schema completi `1889 passed`; suite
   > Portfolio/FIFO/YOC, PAC, Tool, Signals, AI Export e Risk service/API verdi;
   > il Risk API e passato `10/10` dopo il popolamento fixture della lane. Il
   > PAC API e verde dopo tre riparazioni test-only via `test-author`: hash
   > schema `1.0.0`, `monetary_step` nel contributo nominale e relativo output
   > normalizzato.
   > **Evidenza frontend**: unit/component condivisi verdi; AI Export+Signals
   > `22 file / 188 test`; Asset lifecycle E2E `25/25`; Dashboard/Exposure
   > `6/6`; Risk E2E `6/6`; Prettier verde; Svelte check `0 error` e 41 warning
   > deprecation preesistenti; build produzione verde. API/Tool client
   > rigenerati come artifact ignorati e non staged.
   > **Evidenza i18n/docs**: quattro cataloghi da 2802 chiavi, zero traduzioni
   > mancanti; MkDocs strict verde; `12/12` link cross-boundary validi.
   > **Fuori pista - PAC E2E**: il primo run ha prodotto `24 passed / 4
   > failed`, tutti `needs_input` con
   > `contributions.0.monetary_step` mancante. Dopo l'aggiornamento del
   > contratto test via `test-author`, il run ha prodotto `22 passed / 6
   > failed`, tutti timeout sul controllo di produzione inesistente
   > `pac-contributions-monetary-step-0`. Verdetto: gap prodotto Round 2 gia
   > noto; non e merge regression e non e flaky. Per ordine del coordinatore,
   > nessuna modifica alla UI finche il merge resta aperto; le riparazioni test
   > restano unstaged.
   > **Fuori pista - format baseline**: Ruff verde; `black --check backend`
   > segnala nove file fuori scope/preesistenti, inclusi
   > `pac_allocator/normalize.py` e `pac_allocator/report.py`; nessun file della
   > risoluzione merge. Nessuna riformattazione applicata durante il freeze.
   > **Review manuale**: non avviata; nessun server persistente. La nuova review
   > desktop/mobile resta subordinata al commit merge e al completamento della
   > UI `monetary_step`.
   > **Fuori pista 2026-09-11 - primo gate post-merge**: PAC API verde e
   > component unit `PacAllocatorTool` verde. PAC E2E ha chiuso `26/28`: lo
   > scenario reale e tornato `ready` su desktop/mobile, ma una expectation
   > test-only pretendeva una seconda contribuzione USD zero mai inviata.
   > Output reale e contratto API normalizzano correttamente la sola riga EUR
   > fornita. Nessun errore produzione; riparazione rinviata allo stesso
   > `test-author`, senza indebolire il controllo sullo step EUR.
   > **Nota implementazione 2026-09-11 - gate PAC monetary step**: lo stesso
   > `test-author` ha rimosso soltanto la contribuzione USD zero inventata
   > dall'expectation. Con prefisso
   > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
   > -q --test-port 6153 --data-dir /tmp/librefolio-r2-d`: `api pac-tool`
   > verde; `front-utility component-unit PacAllocatorTool` verde;
   > `front-utility pac-tool` verde `28/28` su desktop+mobile. Confermati
   > default `0.01`, precisione 12 decimali, request reale `ready`, guardie
   > stale/account e assenza del controllo sulla cassa.
   > **Fuori pista 2026-09-11 - format**: il primo
   > `front format --check` post-implementazione si e fermato su due soli file:
   > `PacMoneySection.svelte` e il test E2E PAC. Type-check/build non sono
   > partiti per il chain `&&`. Formattazione produzione mirata; formattazione
   > test affidata a `test-author`, poi gate statici completi da ripetere.
   > **Nota implementazione 2026-09-11 - gate condivisi/statici**: con la
   > stessa lane, `front-utility component-unit ExactDecimalInput
   > CurrencySearchSelect` verde; `front format --check` verde; `front check`
   > verde con `0 error` e 41 warning deprecation preesistenti in due file;
   > `front build` verde. Nessun API sync, audit i18n, MkDocs, CHANGELOG o
   > runner eseguito/modificato, come richiesto dal coordinatore.
   > **Evidenza 2026-09-12 - gate statici finali PAC-owned**: ripetuti in
   > sequenza `pipenv run python dev.py front check` e `front build`.
   > Type-check verde con `0 error` e gli stessi 41 warning deprecation
   > preesistenti in due file fuori scope; build produzione verde.
   > **Evidenza 2026-09-12 - formato finale**: dopo le riparazioni test-only,
   > `pipenv run python dev.py front format --check` ha confermato tutti i file
   > frontend/E2E conformi a Prettier.
   > **Fuori pista 2026-09-12 - sync implicito del build**: `front build`
   > esegue internamente la sincronizzazione API prima della build. Nessun sync
   > separato e stato richiesto o lanciato; gli artifact generati restano
   > ignorati e devono essere esclusi dal checkpoint.
   > **Evidenza 2026-09-12 - chiusura checkpoint PAC-owned**: `git diff
   > --check` verde; index vuoto; 18 path tracked tutti unstaged; porta lane
   > `6153` libera (`lsof` senza listener). Step 11 resta aperto: mancano writer
   > coordinatore per cataloghi/i18n, docs/CHANGELOG e integrazione additiva
   > `ToolsHub`, quindi nuova review manuale desktop/mobile non ancora
   > autorizzata.
   > **Nota implementazione 2026-09-11 - ambiente review developer**:
   > ripopolata da zero `/tmp/librefolio-r2-d` con fixture statiche/report e
   > ricostruito il frontend; server test D attivo su
   > `http://127.0.0.1:6153`, PID 74159, risposta root HTTP 200.
   > **Fuori pista**: `dev.py server --rebuild` rigenera automaticamente anche
   > OpenAPI/Zodios/Tool client prima del build, nonostante nessun `api sync`
   > esplicito fosse richiesto. I cinque artifact sono tutti ignorati da Git,
   > non compaiono nel manifest tracked e non verranno staged. Nessun file
   > i18n/docs/CHANGELOG/runner modificato.
   > **Nota implementazione 2026-09-12 - preview estetica richiesta dal
   > developer**: su autorizzazione diretta avviato senza `--force` il server
   > test D con venv condiviso, porta `6153` e data dir
   > `/tmp/librefolio-r2-d`; listener PID `35419`, root HTTP `200`, canvas
   > aperto su `/tools/pac-allocator`. Preview esplicitamente
   > pre-integrazione J: fallback EN, card `ToolsHub` e CHANGELOG condivisi non
   > sono criteri di review; nessuna modifica produzione, merge o staging.

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
