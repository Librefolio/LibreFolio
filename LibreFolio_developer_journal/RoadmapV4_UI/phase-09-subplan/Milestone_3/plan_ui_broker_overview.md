# Piano UI v2: Pagina Brokers & Tab Panoramica (Milestone_3 — Fase 1)

> **Supersede**: [`../plan_ui_broker_overview.md`](../plan_ui_broker_overview.md) (disegno originale, pre Portfolio Engine unificato).
> **Riferimento architetturale**: [`../Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md`](../Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md),
> [`LibreFolio_devWiki/wiki/concepts/portfolio-report-unified.md`](../../../../LibreFolio_devWiki/wiki/concepts/portfolio-report-unified.md).
> **Fasi correlate**: → [`plan_ui_broker_holdings.md`](./plan_ui_broker_holdings.md) (Fase 2) · [`plan_ui_broker_transactions.md`](./plan_ui_broker_transactions.md) (Fase 3).
> **Piano implementativo**: → [`impl_plan_broker_overview.md`](./impl_plan_broker_overview.md) (step concreti, file e riuso).

## Perché un v2

Il disegno originale immaginava per il tab Panoramica dei componenti "da costruire da zero" (grafico a 3
linee, KPI card, mappa del mondo). Nel frattempo la **Dashboard Home** ha già costruito tutti questi widget
in forma generica e parametrizzabile per `broker_ids`, alimentati dall'endpoint unificato
`POST /portfolio/report`. Questo documento ridisegna le stesse due schermate (Lista Globale + Tab Panoramica)
aggiornando i contenuti a ciò che esiste oggi, e introduce la **shell a tab** del Broker Detail (Panoramica /
Posizioni / Transazioni) che oggi non esiste — il dettaglio broker è ancora una singola pagina piatta
(`frontend/src/routes/(app)/brokers/[id]/+page.svelte`, 451 righe: header + colonna sinistra
Cassa+Posizioni + colonna destra Info+Import+Transazioni recenti, tutto senza tab).

---

## 1. Wireframe Pagina Globale Brokers (`/brokers`)

```text
+-------------------------------------------------------------------------------------------------+
|  I TUOI BROKER                                          Valuta: [EUR v]             [+ Nuovo]   |
|                                                                                                 |
|  +--------------------------+  +--------------------------+  +--------------------------+       |
|  | [Icon] DIRECTA      (♛)  |  | [Icon] INTERACTIVE B.(✎) |  | [Icon] TRADE REPUBLIC (♛)|       |
|  |            Quota: 100%   |  |             Quota: 50%   |  |             Quota: 100%  |       |
|  |--------------------------|  |--------------------------|  |--------------------------|       |
|  | NAV:   EUR 48.200,00     |  | NAV:   EUR 12.450,00     |  | NAV:   EUR 5.000,00      |       |
|  | Gain: +EUR 3.120 (+6.9%) |  | Gain:  -EUR 120 (-0.9%)  |  | Gain: +EUR 500 (+11.1%)  |       |
|  |--------------------------|  |--------------------------|  |--------------------------|       |
|  | Cassa: EUR 1.200,00      |  | Cassa: USD 2.500,00      |  | Cassa: EUR 500,00        |       |
|  |        USD   500,00      |  |        EUR   100,00      |  |                          |       |
|  |--------------------------|  |--------------------------|  |--------------------------|       |
|  | 12 asset · 2 valute      |  | 5 asset · 2 valute       |  | 3 asset · 1 valuta        |       |
|  +--------------------------+  +--------------------------+  +--------------------------+       |
|   ↳ click sulla card apre /brokers/{id}. Icone [✎ Modifica] [👥 Condividi] [🗑 Elimina] in alto   |
|     a dx sulla card. "Condividi" apre BrokerSharingModal: editabile se sei OWNER, sola-lettura    |
|     (elenco membri+ruolo, nessun controllo di modifica) se sei EDITOR/VIEWER.                    |
|   ↳ NAV/Gain mostrati nella valuta scelta sopra (Valuta), pre-popolata a `default_currency`       |
|     dell'utente. Cassa resta nelle valute native (nessuna conversione) — vedi note sotto.        |
|                                                                                                 |
|  ────────────────────────────────────────────────────────────────────────────────────────────   |
|  ALTRI BROKER ESISTENTI (non tuoi)                                     [NUOVO — richiede backend] |
|                                                                                                 |
|  +--------------------------+  +--------------------------+                                     |
|  | [Icon] DEGIRO       [👥] |  | [Icon] FINECO       [👥] |                                     |
|  | Nessun tuo accesso       |  | Nessun tuo accesso       |                                     |
|  | (nessun importo/asset/NAV mostrato — solo nome + icona)                                      |
|  +--------------------------+  +--------------------------+                                     |
|   ↳ [👥] apre la STESSA BrokerSharingModal in sola-lettura: elenco di chi ha accesso (username +  |
|     ruolo) — così l'utente sa a chi chiedere. Nessun bottone "Richiedi Accesso"/flusso di         |
|     notifica in questa fase (confermato fuori scope, non solo rimandato).                        |
+-------------------------------------------------------------------------------------------------+
```

Note sul disegno:
- Il layout card, il badge di ruolo (♛ Owner / ✎ Editor / 👁 Viewer) e le azioni Modifica/Elimina esistono
  già identici in `BrokerCard.svelte` — si aggiungono la riga Quota, l'icona Condividi e il selettore Valuta
  di pagina.
- **Cassa resta multi-valuta nativa** (non un unico importo convertito): la card mostra ogni valuta di cassa
  del broker come fa oggi. Solo NAV/Gain-Loss vengono mostrati nella valuta target scelta in alto (perché
  derivano da un calcolo di portfolio che richiede necessariamente una valuta comune — non ha senso sommare
  ETF in USD e azioni in EUR senza convertire). Implicazione backend: la fonte dati per NAV/Gain
  (`by_broker`, vedi sotto) deve esporre ANCHE `cash_balances: List[Currency]` nativo, non solo un
  `cash_total` aggregato.
- **Icona Condividi**: nuova su ogni card (propria o "Altri Broker"), apre sempre `BrokerSharingModal`.
  La modale già distingue chi può modificare (oggi: solo OWNER, lato server il PUT è già OWNER-gated) da chi
  può solo consultare — va però estesa una sola-lettura anche a EDITOR/VIEWER (oggi il bottone Condividi
  nella pagina flat è visibile SOLO all'OWNER, vedi §2) e ai non-membri (oggi impossibile: l'endpoint dietro
  la modale nega l'accesso a chi non è membro, vedi "Manca" sotto).
- La sezione "Altri Broker Esistenti" resta una feature voluta e confermata, ma **semplificata** rispetto al
  disegno precedente: la card mostra solo nome/icona (nessun elenco owner incorporato nel testo), perché
  l'icona Condividi in sola-lettura sull'elenco esistente basta a rispondere "chi ha accesso" senza
  duplicare quella logica in un componente nuovo. **Confermato con l'utente**: nessun flusso "Richiedi
  Accesso"/notifica in questa fase — non è un rinvio, è deliberatamente fuori scope per ora.

---

## 2. Wireframe Dettaglio Broker — Shell con Tab (nuovo)

```text
+-------------------------------------------------------------------------------------------------+
|  <- Torna ai Broker                                                                             |
|  [Icon] DIRECTA  (♛ Owner · Quota: 100%)                                    [Share] [↻ Refresh] |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   [* PANORAMICA *]   [ POSIZIONI ]   [ TRANSAZIONI ]                                            |
|                                                                                                 |
|   ... contenuto specifico del tab attivo (vedi §3 per Panoramica, Fase 2/3 per gli altri) ...   |
+-------------------------------------------------------------------------------------------------+
```

- Header, back-button, Share e Refresh **esistono già** nella pagina piatta attuale — vanno solo
  riposizionati sopra la nuova barra tab. Il badge quota (`♛ Owner · Quota: 100%`) è nuovo nell'header ma il
  dato (`user_share_percentage`) è già disponibile in `BRSummary` da `GET /brokers/{id}/summary`.
- **Cambio di comportamento sul bottone Share**: oggi è visibile **solo** se `user_role === 'OWNER'`
  (`frontend/src/routes/(app)/brokers/[id]/+page.svelte`, condizione `{#if safeString(broker.user_role) ===
  'OWNER'}`) — EDITOR/VIEWER oggi non possono nemmeno aprire la modale. Nel nuovo disegno il bottone è
  **sempre visibile** (coerente con l'icona Condividi introdotta sulle card in §1): apre
  `BrokerSharingModal` in modalità editabile per OWNER, sola-lettura per chiunque altro. Vedi "Manca" per il
  lavoro di backend/frontend che questo richiede.
- La barra tab è puro stato locale di pagina (`activeTab: 'overview' | 'positions' | 'transactions'`,
  eventualmente sincronizzato in query string per permettere link diretti a un tab). Nessun componente di
  tab generico esiste ancora nel design system (i settings usano tab hand-rolled per pagina in
  `frontend/src/lib/components/settings/tabs/`) — si può copiare lo stesso pattern hand-rolled, oppure
  estrarre un piccolo componente `<TabBar>` condiviso se si preferisce (nice-to-have, non bloccante).
- Il contenuto oggi presente nella pagina piatta (Cassa, Posizioni, Info Broker, Import File, Transazioni
  recenti) viene **ridistribuito** nei 3 tab: Cassa + Info Broker restano nel tab Panoramica (§3), Posizioni
  diventa il tab dedicato (Fase 2), Import File + Transazioni recenti diventano il tab Transazioni (Fase 3).

---

## 3. Wireframe Tab Panoramica (Overview)

```text
+-------------------------------------------------------------------------------------------------+
|  Range: [1W][1M][3M][6M][1Y][2Y][Custom]     Valuta: [EUR v]                                    |
+-------------------------------------------------------------------------------------------------+
|  +----------------------+  +----------------------+  +----------------------+                    |
|  | P&L PERIODO          |  | RENDIMENTI            |  | PATRIMONIO NETTO      |                    |
|  | +EUR 3.120,00 (+2.1%)|  | ROI      +7,45%       |  | EUR 48.200,00        |                    |
|  | ▸ Plus/minus non real.|  | TWRR cum +6,90%       |  | ▸ Valore di mercato   |                    |
|  | ▸ Realizzato vendite  |  | MWRR cum +7,10%       |  | ▸ Valore contabile    |                    |
|  | ▸ Dividendi/Interessi |  | MWRR ann +8,30%       |  | ▸ Liquidità          |                    |
|  | ▸ Commissioni/Tasse   |  |                       |  | ▸ Capitale netto vers.|                    |
|  +----------------------+  +----------------------+  +----------------------+                    |
|                                                                                                 |
|  +--------------------------------------------------------+  +---------------------------------+ |
|  | GRAFICO DI CRESCITA (3/5)                              |  | ALLOCAZIONE (2/5)  [Ora|Storico] | |
|  |                                                          |  | [Tipo][Settore][Geografia]      | |
|  |  EUR                                                    |  |                                  | |
|  |  60k +                                     ..*******    |  |     ETF  ████████████ 80%       | |
|  |      |                                 ..*******         |  |     Az.  ████ 20%               | |
|  |  40k |                            ..******* - - -        |  |                                  | |
|  |      |                        ..*******                  |  |  (oppure mappa del mondo se      | |
|  |  20k |                    ..*******                      |  |   tab = Geografia)               | |
|  |      |...........*****************.................      |  |                                  | |
|  |    0 +---*---*---*---*---*---*---*---*---*---*---*-->    |  |                                  | |
|  |         Gen  Feb  Mar  Apr  May  Jun  Jul  Aug          |  |                                  | |
|  |         [■] NAV   [- -] Book Value   [....] Cash        |  |                                  | |
|  +--------------------------------------------------------+  +---------------------------------+ |
|                                                                                                 |
|  +----------------------------------+  +-------------------------------------------------------+ |
|  | METADATI / INFO BROKER            |  | CASSA                                 [NUOVO layout]  | |
|  | Stato: Attivo                     |  |---------------------------------------------------------| |
|  | Data Apertura: 2025-01-10         |  |                                      1.200,00 € 🇪🇺 EUR  | |
|  | Leva Finanziaria: No               |  |                                        500,00 $ 🇺🇸 USD  | |
|  | Shorting Attivo: No                |  |                                                          | |
|  | Plugin Import: directa_csv         |  | (sola lettura — niente Deposito/Prelievo qui: sono       | |
|  +----------------------------------+  |  transazioni, si creano da lì — vedi nota sotto)         | |
|                                          +---------------------------------------------------------+ |
|                                                                                                 |
|  +-----------------------------------------------------------------------------------------+   |
|  | TRANSAZIONI RECENTI (opzionale, per coerenza con Dashboard Home)                         |   |
|  | (stessa RecentTransactionsPanel della Dashboard, scoped a questo broker)                 |   |
|  +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

Note sul disegno:
- Il **Range/Valuta è locale a questa pagina**, indipendente dal filtro globale della Dashboard Home E dal
  selettore Valuta della Lista Globale (§1) — sono due preselezioni indipendenti, entrambe pre-popolate da
  `globalSettings.default_currency` ma modificabili separatamente. Broker è fisso (`broker_ids: [id]`),
  quindi non serve un selettore broker qui.
- Le 3 KPI card, il grafico di crescita e il pannello allocazione sono **esattamente** i widget della
  Dashboard Home, montati con lo stesso componente e la stessa chiamata dati — cambia solo il parametro
  `broker_ids`. Le proporzioni di griglia (grafico 3/5, allocazione 2/5) rispecchiano il layout dashboard
  reale.
- **Cassa ridisegnata da zero** (feedback utente: il box attuale, `CashBalanceCard.svelte`, è "estremamente
  embrionale" — icona colorata generica, `Intl.NumberFormat` locale senza bandiera). Il nuovo disegno è un
  **elenco semplice, sola lettura**: una riga per valuta, resa con l'helper condiviso
  `formatCurrencyAmountHtml`/`formatCurrencyAmountPlain`
  (`frontend/src/lib/utils/currency/currencyFormat.ts`) — stesso output "`1.200,00 € 🇪🇺 EUR`" già usato in
  `AssetTable`/`ExposureTable`/`TransactionsTable`, così la resa delle valute è coerente in tutta l'app
  invece di reinventarla qui. Nessun box/icona/bottone per valuta: solo righe allineate a destra, ordinate
  come oggi restituito da `/summary` (nessun ordinamento nuovo da introdurre).
- **Nessun Deposito/Prelievo qui**: sono transazioni (`TransactionType.DEPOSIT`/`WITHDRAWAL`,
  `backend/app/db/models.py:272-273`) e vanno create dal flusso standard "+ Nuova Transazione"
  (`TransactionFormModal`, già usato da Dashboard e dalla pagina `/transactions` con lo stesso bottone
  `transactions.addTransaction`) — lo stesso bottone comparirà nel Tab Transazioni (Fase 3).
  `CashBalanceCard.svelte` **non viene riusato**: è montato solo qui (nessun altro utilizzo nel codebase) e
  viene ritirato, non modificato.
- Metadati/Info Broker resta il blocco **già esistente** nella pagina piatta odierna (nessuna modifica di
  contenuto, solo di posizione: finisce sotto il tab Panoramica).
- Il pannello "Transazioni Recenti" è opzionale: `RecentTransactionsPanel` supporta già una prop `brokerIds`,
  quindi il riuso è immediato se si vuole offrire lo stesso colpo d'occhio della Dashboard Home; altrimenti
  si rimanda tutto al tab Transazioni (Fase 3) che avrà comunque la vista completa.
- Non è previsto un preview delle Posizioni in questo tab (evita duplicazione con il tab dedicato di Fase 2),
  coerente con il disegno originale che non lo includeva.

---

## Requisiti Dati Frontend

### Funzionalità Esistenti (da riutilizzare così come sono)

* **`POST /portfolio/report`** (`backend/app/api/v1/portfolio_api.py`) — unico endpoint per KPI, storico NAV,
  allocazioni; già accetta `broker_ids: [id]`, `date_range`, `target_currency`,
  `include_summary/history/allocation_history`. Nessuna modifica richiesta per il tab Panoramica.
* **`portfolioStore.svelte.ts`** (`frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`) —
  `fetchReport(brokerIds, dateFrom, dateTo, targetCurrency)` con cache lato client, da chiamare passando
  `[brokerId]`.
* **Componenti Dashboard riusabili as-is**: `KpiCard`/`KpiMetricBar`/`KpiDivergingFlowBar`, `GrowthChart`,
  `AllocationPieChart`, `AllocationHistoryChart`, `GeographyMap`, `RecentTransactionsPanel` (già supporta
  `brokerIds`) — tutti in `frontend/src/lib/components/dashboard/`.
* **`CurrencySearchSelect.svelte`** (`frontend/src/lib/components/ui/select/`) — stesso componente del
  selettore valuta della Dashboard, pre-popolato da `globalSettings.default_currency`
  (`frontend/src/lib/stores/app/globalSettings.ts`). Riusato identico sia in Lista Globale (§1) sia in Tab
  Panoramica (§3), come due istanze indipendenti.
* **`GET /brokers/{id}/summary`**: già restituisce `user_role` + `user_share_percentage` per il badge quota
  nell'header del dettaglio broker, e `cash_balances: List[Currency]` nativo per-valuta per il nuovo elenco
  Cassa (§3) — nessuna modifica di schema necessaria qui, solo di rendering frontend.
* **`formatCurrencyAmountHtml`/`formatCurrencyAmountPlain`** (`frontend/src/lib/utils/currency/
  currencyFormat.ts`) — helper condiviso già usato da `AssetTable`/`ExposureTable`/`TransactionsTable` per
  rendere "importo simbolo bandiera codice"; da riusare identico per il nuovo elenco Cassa invece di
  inventare una formattazione locale.
* **`TransactionFormModal`** (già usato da Dashboard e da `/transactions`, bottone
  `transactions.addTransaction`) — flusso standard di creazione DEPOSIT/WITHDRAWAL; assorbe l'azione che
  oggi vive nei bottoni dedicati di `CashBalanceCard`.
* Box Metadati: esistente e funzionante, si sposta di posizione senza modifiche di logica.
* **`BrokerCard.svelte`**: struttura card, badge ruolo, azioni Modifica/Elimina, click-to-detail — invariati.
* **`brokerStore.ts`** (`frontend/src/lib/stores/reference/brokerStore.ts`) — cache di sessione già esistente
  (`refreshAllBrokers()`/`getAllBrokers()`/`invalidateBroker()`), è il pattern da estendere (non reinventare)
  per non ri-richiedere ad ogni mount i dati aggiuntivi introdotti da questa fase (quota, NAV/gain,
  discovery) — stesso principio già applicato da `portfolioStore`.

### Funzionalità da Sviluppare (Backend & API)

* **Quota % nella lista globale senza N+1**: `GET /brokers` (`BrokerService.get_all()`,
  `backend/app/services/broker_service.py:261-305`) fa già un LEFT JOIN con `BrokerUserAccess` per risolvere
  `user_role` per broker, ma scarta `share_percentage` — aggiungere `user_share_percentage` a `BRReadItem` è
  un'estensione minima (il dato è già nella riga joinata, riga 304), **sempre inclusa di default** (nessun
  costo aggiuntivo, nessun flag necessario: non tocca il Portfolio Engine).
* **NAV/Gain/Cash per-card senza N+1 — usa il Portfolio Engine**: sì, questa parte sfrutta l'engine. Oggi la
  pagina lista fa una chiamata `/brokers/{id}/summary` per ciascun broker. `PortfolioReportQuery
  (include_breakdown=true)` restituisce già `by_broker: List[BrokerBreakdown]` (net_worth, gain_loss,
  gain_loss_percent, cash_total) calcolato in un'unica run di engine — sostituirebbe le N chiamate con 1
  sola. **Estensione necessaria** (confermata dall'utente): `BrokerBreakdown` deve esporre anche
  `cash_balances: List[Currency]` nativo per-valuta (non solo `cash_total` convertito), per non perdere il
  dettaglio multi-valuta che la card mostra oggi. Questa chiamata resta **separata** da `GET /brokers`
  (usato da `brokerStore`/selettori broker in tutta l'app): non va fusa nello stesso endpoint, va invocata
  solo dalla pagina Lista Globale e cachata allo stesso modo di `portfolioStore` (invalidata sugli stessi
  trigger: CRUD transazioni, sync prezzi).
* **Broker Discovery ("Altri Broker Esistenti") — NON usa il Portfolio Engine, deve essere opt-in**: nessuna
  route oggi elenca broker non accessibili. Proposta concreta: un parametro query opzionale su `GET /brokers`,
  es. `include_inaccessible: bool = False` (default `False`), che quando `True` aggiunge alla risposta i
  broker esistenti non posseduti/condivisi con l'utente, **solo** `{id, name, icon_url}` — niente owner list
  incorporata (la si ottiene tramite l'icona Condividi, vedi punto successivo). Il default `False` non è solo
  una questione di performance: è anche di correttezza, perché `GET /brokers` alimenta `brokerStore` e da lì
  ogni selettore broker dell'app (es. creazione transazione) — se includesse di default broker inaccessibili,
  un selettore potrebbe proporre di "scegliere" un broker su cui l'utente non può operare.
* **`GET /brokers/{id}/access` va aperto ai non-membri, ma con payload ridotto** — gap concreto scoperto
  leggendo il codice: oggi (`backend/app/api/v1/brokers.py:367-391`) l'endpoint risponde 404 "not found or
  access denied" se il chiamante non ha alcun ruolo sul broker (`BrokerService.list_accesses()`, riga
  719-723: `if not role: return []`, poi la route trasforma la lista vuota in 404). Per abilitare la
  sola-lettura anche ai non-membri va aggiunta una modalità che, quando il chiamante non ha accesso,
  restituisca comunque la lista **ma senza i campi sensibili** che oggi `list_accesses()` include per i
  membri: **`email` e `share_percentage`** (righe 736-738 di `broker_service.py`) non dovrebbero essere
  visibili a chi non ha alcun accesso — solo `username` + `role`. Per i membri (EDITOR/VIEWER) che oggi
  ricevono già la lista completa via questo stesso endpoint, nessun cambiamento: il payload completo resta
  quello attuale. Decisione aperta da confermare in implementazione: se anche `share_percentage` debba
  restare nascosto ai non-membri o sia accettabile mostrarlo.
* **Il PUT `/brokers/{id}/access` (modifica) resta invariato**: è già correttamente ristretto ai soli OWNER
  lato server (`bulk_update_broker_access`, righe 394-430) — nessuna modifica richiesta qui, la richiesta
  dell'utente ("editabile se hai i diritti") è già soddisfatta.

### Funzionalità da Sviluppare (Frontend)

* **Tab bar del Broker Detail**: nuovo stato locale di pagina (`activeTab`), redistribuzione dei blocchi
  esistenti (Cassa, Info, Import File, Transazioni) nei tab corretti. Nessun componente `<Tabs>` generico
  esiste ancora — copiare il pattern hand-rolled di `settings/tabs/` o estrarne uno condiviso (opzionale).
* **`BrokerSharingModal.svelte` — nuova modalità sola-lettura**: oggi la modale assume sempre pieni poteri di
  modifica (nessuna prop `readOnly`/`canEdit` trovata nel componente). Va aggiunta una variante di rendering
  che nasconda i controlli di aggiunta/rimozione/modifica ruolo e mostri solo l'elenco membri+ruolo, attivata
  quando l'apertura avviene da un non-OWNER (membro EDITOR/VIEWER o non-membro). Per i non-membri, il
  componente deve anche gestire l'assenza dei campi `email`/`share_percentage` nella risposta (vedi sopra).
* **Icona Condividi su `BrokerCard.svelte`**: nuova, accanto a Modifica/Elimina, apre `BrokerSharingModal`
  nella modalità corretta in base al ruolo dell'utente sul broker.
* **Bottone Share sull'header Broker Detail**: rimuovere il gate `{#if user_role === 'OWNER'}` — va sempre
  mostrato, aprendo la modale in sola-lettura per i non-OWNER.
* **Card "Altri Broker Esistenti"**: nuovo componente leggero (variante ridotta di `BrokerCard`: solo
  icona+nome+icona Condividi, nessun'altra sezione) — **semplificato** rispetto all'iterazione precedente di
  questo piano, niente più owner-list testuale incorporata né bottone "Richiedi Accesso".
* **Quota % nel badge card/header**: piccola aggiunta di markup su `BrokerCard.svelte` e sull'header del
  dettaglio, una volta disponibile il dato lato API.
* **Selettore Valuta in Lista Globale**: nuovo stato locale di pagina, pre-popolato da
  `globalSettings.default_currency`, passato come `target_currency` alla chiamata `by_broker`.
* **Nuovo elenco Cassa (sola lettura)**: piccolo componente nuovo — un `<div>`/lista, una riga per valuta di
  `cash_balances`, ciascuna resa con `formatCurrencyAmountHtml`, allineate a destra, senza icona/box/bottoni
  per valuta. Sostituisce `CashBalanceCard.svelte` in questo contesto (che va ritirato: non ha altri utilizzi
  nel codebase). Le azioni Deposito/Prelievo **non** vengono ricreate qui: restano disponibili solo tramite
  il flusso standard "+ Nuova Transazione" (già esistente, Fase 3).
