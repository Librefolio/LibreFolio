# Piano Implementativo: Broker Overview (Milestone_3 — Fase 1)

> **Deriva da**: [`plan_ui_broker_overview.md`](./plan_ui_broker_overview.md) (disegno UI + requisiti dati, approvato).
> **Fasi correlate (non ancora implementate)**: [`plan_ui_broker_holdings.md`](./plan_ui_broker_holdings.md) (Fase 2) ·
> [`plan_ui_broker_transactions.md`](./plan_ui_broker_transactions.md) (Fase 3) — avranno ciascuna un proprio
> `impl_plan_*.md` con lo stesso pattern, dopo questa fase.
> **Ambito**: SOLO Fase 1 (Lista Globale `/brokers` + shell a tab + Tab Panoramica). Posizioni e Transazioni
> vengono solo "traslocate" as-is negli altri due tab (nessun redesign, quello è Fase 2/3).

## Principio guida

> Riusare ovunque i componenti già scritti (custom o Dashboard), evitare funzionalità standard/browser
> quando esiste già un componente/helper custom equivalente (`currencyFormat.ts` invece di
> `Intl.NumberFormat`, `portfolioStore`/`brokerStore` invece di nuove fetch ad-hoc, `TransactionFormModal`
> invece di modali dedicate, `BrokerSharingModal` invece di una nuova modale sharing).

Ogni step sotto dichiara esplicitamente cosa **riusa** (invariato) vs cosa è **nuovo** (minimo indispensabile).

## Decisioni prese (non più aperte)

| Decisione | Scelta |
|---|---|
| Forma risposta `GET /brokers` per Discovery | Wrappata in `{items, inaccessible}` (1 sola chiamata, 2 call-site diretti da aggiornare — uno dei quali un bug preesistente da correggere, vedi 1.3) |
| `email`/`share_percentage` ai non-membri (`/access`) | **Entrambi visibili**, nessuna redazione — aggiornato dopo feedback: chi è registrato nel sistema non è un perfetto sconosciuto |
| `<TabBar>` condiviso | Unifica le **3** implementazioni hand-rolled già esistenti (non solo il nuovo broker detail) |
| Ambito di questo documento | Solo Fase 1; Fase 2/3 seguiranno con lo stesso pattern |

## Ordine di implementazione

```
STEP 1 (Backend, indipendenti tra loro)
 ├─ 1.1 Quota % su GET /brokers
 ├─ 1.2 Cash multi-valuta su BrokerBreakdown (/report)
 ├─ 1.3 Broker Discovery (GET /brokers?include_inaccessible=true)
 └─ 1.4 Apertura GET /brokers/{id}/access ai non-membri
        │
STEP 2 (Frontend, infra condivisa — nessuna dipendenza da Step 1)
 ├─ 2.1 <TabBar> condiviso (nuovo, minimo)
 └─ 2.2 Pulizia formattazione valuta (currencyFormat.ts ovunque)
        │
        ▼
STEP 3 (Lista Globale — dipende da 1.1, 1.2, 1.3)
        │
        ▼
STEP 4 (Shell Dettaglio Broker — dipende da 1.4, 2.1)
        │
        ▼
STEP 5 (Tab Panoramica — dipende da 4, 2.2)
        │
        ▼
STEP 6 (Ritiro componenti) → STEP 7 (i18n)
```

---

## STEP 1 — Backend

### 1.1 Quota % in `GET /brokers` (nessun uso del Portfolio Engine)

- **File**: `backend/app/schemas/brokers.py` — `BRReadItem` (righe 96-124). Aggiungere:
  ```
  user_share_percentage: Optional[SafeDecimal] = Field(default=None, ...)
  ```
  (stesso nome/tipo già presente su `BRSummary`, riga ~che ridefinisce lo stesso campo — una volta
  spostato sul genitore, **rimuovere la ridichiarazione ridondante da `BRSummary`**, che eredita il campo
  invariato: piccolo cleanup a costo zero.)
- **File**: `backend/app/services/broker_service.py` — `get_all()` (righe 261-306). Il LEFT JOIN a riga
  285-297 seleziona oggi solo `Broker, BrokerUserAccess.role`: aggiungere `BrokerUserAccess.share_percentage`
  alla `select(...)` e popolare `user_share_percentage` nel risultato (righe 302-305), analogo a come
  `user_role` è già popolato da `role.value if role else None`.
- **Nessun flag/opzione**: campo sempre incluso, dato già nella riga joinata, nessun costo aggiuntivo, non
  tocca il Portfolio Engine.
- Dopo la modifica: `./dev.py api sync` per rigenerare il client TypeScript.

### 1.2 Cassa multi-valuta nativa in `BrokerBreakdown` (USA il Portfolio Engine) ✅ completed (2026-07-06)

> **Note implementazione**: aggiunto `cash_balances` a `BrokerBreakdown` con `ConfigDict(extra="forbid")` e popolato in `PortfolioService` proiettando `broker_cash` in `List[Currency]` senza nuova logica di aggregazione. Eseguiti `./dev.py api sync`, test backend mirati su breakdown/report, e lint/format sui file backend toccati.

- **File**: `backend/app/schemas/portfolio.py` — `BrokerBreakdown` (righe 327-336). Aggiungere:
  ```
  cash_balances: List[Currency] = Field(default_factory=list, description="Cash balance per currency, native (unconverted)")
  ```
  (stesso nome/tipo già usato in `PortfolioSummary.cash_balances`, righe 338-390 — pattern esistente,
  non nuovo.)
- **File**: `backend/app/services/portfolio_service.py` — dentro il loop per-broker, blocco
  `if include_breakdown:` (righe 905-917). Il dizionario nativo per-valuta **esiste già in scope** come
  `broker_cash` (popolato righe 891-901, usato per calcolare `broker_cash_base` convertito) — non richiede
  nuovo calcolo, solo proiettarlo:
  ```python
  cash_balances=[Currency(code=ccy, amount=amt) for ccy, amt in broker_cash.items()],
  ```
  aggiunto al costruttore `BrokerBreakdown(...)` (riga 908-917), **esattamente lo stesso pattern** già usato
  per il totale globale a riga 993 (`cash_balances_list = [Currency(code=ccy, amount=amt) for ccy, amt in
  all_cash_balances.items()]`). Nessuna nuova logica di aggregazione da scrivere.
- Questa chiamata (`POST /portfolio/report` con `include_breakdown=true`) resta **separata** da `GET
  /brokers`: va invocata solo dalla pagina Lista Globale via `portfolioStore.fetchReport(...)` (riuso, non
  nuova fetch), non fusa nello store broker.
- Dopo la modifica: `./dev.py api sync`.

### 1.3 Broker Discovery — `GET /brokers?include_inaccessible=true`

- **Nuovo schema** `backend/app/schemas/brokers.py`: `BRDiscoveryItem {id: int, name: str, icon_url:
  Optional[str]}` — deliberatamente minimo (mai dati finanziari), coerente con `ConfigDict(extra="forbid")`.
- **Nuovo schema wrapper**: `BRListResponse {items: List[BRReadItem], inaccessible: List[BRDiscoveryItem] =
  []}` — sostituisce la risposta oggi piatta `List[BRReadItem]` di `GET /brokers`
  (`backend/app/api/v1/brokers.py`, righe 154-177).
- **Servizio** `broker_service.py`: nuovo parametro `include_inaccessible: bool = False` su `get_all()` (o
  wrapper chiamante); quando `True`, query aggiuntiva per i `Broker` **senza** riga corrispondente in
  `BrokerUserAccess` per `filter_user_id` (stessa join di righe 285-297, invertita — `LEFT JOIN ... WHERE
  BrokerUserAccess.user_id IS NULL`), proiettata solo su `id, name, icon_url`.
- **Default `False`**: non solo per performance — per correttezza, dato che `GET /brokers` alimenta
  `brokerStore` e da lì ogni selettore broker dell'app (es. creazione transazione); un default `True`
  rischierebbe di proporre broker non operabili in quei selettori.
- **Blast radius del cambio di forma risposta** — 2 call-site diretti da aggiornare, nessun altro trovato
  via grep:
  1. `frontend/src/lib/stores/reference/brokerStore.ts` — `loader: async () => (await
     zodiosApi.list_brokers_api_v1_brokers_get())` (riga 88) → `(await
     zodiosApi.list_brokers_api_v1_brokers_get()).items`.
  2. **`frontend/src/routes/(app)/dashboard/+page.svelte:597` — bug confermato, si corregge qui (non solo
     `.items`)**: questa riga fa una chiamata diretta e ridondante allo stesso endpoint appena dopo
     `ensureBrokersLoaded()` (riga 596, che già popola `brokerStore`) — doppia richiesta di rete per lo
     stesso dato. Si **rimuove** la chiamata diretta e si sostituisce con `getAllBrokers()` dello store
     (stessa forma dati: `BrokerInfo` soddisfa l'interfaccia `BrokerLike` richiesta da
     `PositionsPanel`/`brokerColors.ts`, che ha solo `id` obbligatorio e il resto opzionale — verificato in
     `frontend/src/lib/utils/broker/brokerColors.ts:17-26`). Nessuna perdita di dati: `allBrokers` era già
     popolato dallo stesso identico endpoint, solo richiesto due volte invece di una.
- Dopo la modifica: `./dev.py api sync`.

### 1.4 Apertura `GET /brokers/{id}/access` ai non-membri (nessun dato nascosto)

- **Aggiornato dopo feedback**: nessuna redazione di campi. Chi è registrato nel sistema non è un perfetto
  sconosciuto: **`email` e `share_percentage` restano entrambi visibili** anche ai non-membri — l'unica cosa
  che cambia davvero è che il 404 "nessun accesso" viene rimosso.
- **File**: `backend/app/api/v1/brokers.py` — endpoint righe 367-391. Oggi: `service.list_accesses(...)`
  vuoto → 404 "not found or access denied" (nessuna distinzione tra "broker inesistente" e "broker esistente
  ma nessun accesso"). Serve **distinguere** i due casi: riusare lo stesso controllo di esistenza broker già
  presente in `GET /brokers/{broker_id}` (righe 179-213, quello che oggi già dà 404 sul broker realmente
  inesistente) — solo quello resta un vero 404 qui.
- **File**: `backend/app/services/broker_service.py` — `list_accesses()` (righe 707-743). **Rimuovere** il
  ramo `if not is_superuser and not role: return []` (righe 719-724): la query (righe 728-741) viene
  eseguita e restituita **senza filtri** per qualunque chiamante autenticato che confermi l'esistenza del
  broker — stesso payload completo già visto oggi dai membri (`email`, `share_percentage`, `role`,
  `username`, `avatar_url`).
- **Nessuna modifica di schema**: `BRAccessItem` (righe 345-360) resta invariato, nessun campo da rendere
  Optional — semplificazione rispetto alla versione precedente di questo piano.
- **Il PUT `/brokers/{id}/access` resta invariato** (righe 394-444, già OWNER-only lato server) — solo la
  lettura si apre, la scrittura resta ristretta.
- Dopo la modifica: `./dev.py api sync`.

---

## STEP 2 — Frontend: infrastruttura condivisa

### 2.1 `<TabBar>` condiviso — unifica 3 implementazioni esistenti (non solo "nuovo per il broker")

- **Corretto dopo feedback**: cercando in tutto il codebase (non solo `settings/`, come l'audit iniziale
  aveva limitato la ricerca) risultano **3** implementazioni hand-rolled quasi identiche dello stesso
  pattern (stato `activeTab` + riga di bottoni `role="tablist"`/`role="tab"`/`aria-selected` + contenuto
  condizionale), tutte con lo **stesso indicatore visivo** (bordo inferiore 2px colore `libre-green` sul tab
  attivo):
  1. `frontend/src/routes/(app)/settings/+page.svelte` (righe 10-63) — 4 tab con icona, classi Tailwind
     interpolate.
  2. `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` (righe 105, 496-538) — 2 tab
     (Prezzi/Eventi), classi Tailwind interpolate, **badge conteggio modifiche** per tab + contenuto extra
     allineato a destra (etichetta valuta) nella stessa riga.
  3. `frontend/src/routes/(app)/files/+page.svelte` (righe 100, 718-725) — 2 tab (Static/BRIM), **CSS
     scoped locale** (`.tabs`/`.tab`/`.tab.active`, righe 97-141 del blocco `<style>`, stessi colori hex
     `#1a4031`/`#10b981` = libre-green invece di classi Tailwind), stato persistito in **localStorage +
     query string** (`?tab=`), riga con contenuto extra (SelectionBar/ColumnVisibilityToggle) come elemento
     fratello esterno al tablist.
  Costruire un 4° hand-rolled per il broker detail sarebbe esattamente l'errore da evitare — si unificano
  tutti e 4 (i 3 esistenti + il nuovo) sullo stesso componente.
- **Nuovo file**: `frontend/src/lib/components/ui/tabs/TabBar.svelte` — componente puramente
  presentazionale (nessuna logica di persistenza al suo interno: locale/localStorage/query-string restano
  scelte del consumer, non del componente). Props: `tabs: {id: string; label: string; icon?: ComponentType;
  badge?: number}[]`, `activeTab: string` (bindable). Stile Tailwind (coerente con 2 dei 3 esistenti e con
  la convenzione di progetto, non CSS scoped), indicatore bordo-inferiore-2px `libre-green` identico a
  tutti e 3 gli esistenti — nessuna regressione visiva attesa, cambia solo il meccanismo di implementazione.
- **Migrazione dei 3 consumer esistenti (in scope in questo stesso step)**:
  - `settings/+page.svelte`: sostituire il blocco tab (righe 32-50) con `<TabBar>`, passando l'array `tabs`
    già esistente (righe 18-23, ha già icona) — nessuna perdita di funzionalità.
  - `AssetDataEditorSection.svelte`: sostituire righe 496-538 con `<TabBar>` passando `badge` per il
    conteggio modifiche; l'etichetta valuta a destra resta un elemento fratello esterno (come già oggi), non
    entra nel componente condiviso.
  - `files/+page.svelte`: sostituire righe 718-725 con `<TabBar>`; la persistenza localStorage/query-string
    (righe 59, 182-193, 217, 228) **resta nella pagina** (il componente resta agnostico), si limita a
    cablare `activeTab` bindable sullo stesso stato già gestito da `setActiveTab()`. Rimuovere il CSS scoped
    `.tabs`/`.tab`/`.tab.active` (righe 97-141) ora ridondante.
  - **Broker Detail** (nuovo, STEP 4.2): quarto consumer, stesso componente.

### 2.2 Pulizia formattazione valuta — `currencyFormat.ts` ovunque

Estende alla intera Fase 1 il principio già applicato al box Cassa (round 3): **nessuna formattazione
valuta ad-hoc** dove esiste già l'helper condiviso.

- `frontend/src/lib/components/brokers/BrokerCard.svelte` — rimuovere `formatAmount()` (righe 34-41,
  `Intl.NumberFormat` locale) → `formatCurrencyAmountHtml`.
- `frontend/src/routes/(app)/brokers/[id]/+page.svelte` — rimuovere `formatCurrency()` (righe 100-108) →
  `formatCurrencyAmountHtml`/`Plain`, usato oggi per Holdings table, box Info Broker (`total_value_base_currency`),
  Transazioni Recenti (`tx.cash`).
- `CashBalanceCard.svelte` — non applicabile, componente ritirato (STEP 6).

---

## STEP 3 — Frontend: Lista Globale (`/brokers`)

### 3.1 Selettore Valuta di pagina

- Riuso `CurrencySearchSelect.svelte` (`frontend/src/lib/components/ui/select/`) — stessa istanza-pattern
  già usata in Dashboard (`dashboard/+page.svelte` righe 621-630), nuovo stato locale pre-popolato da
  `globalSettings.default_currency` (nessun binding diretto esistente da riusare, va cablato come fa
  Dashboard: `baseCurrency = $globalSettings.default_currency || 'EUR'`, righe 109-111/143-145).

### 3.2 Card: Quota, NAV/Gain, Cassa nativa — 1 sola chiamata aggiuntiva

- Sostituire l'attuale `Promise.all(basicBrokers.map(b => .../summary))` (N+1, `+page.svelte` righe 44-45)
  con **una sola** chiamata `portfolioStore.fetchReport(accessibleBrokerIds, undefined, undefined,
  targetCurrency, {includeBreakdown: true})` (riuso store esistente, già supporta `brokerIds` — qui
  passando TUTTI gli id accessibili invece di uno solo) → mappare `by_broker` per `broker_id` sulle card.
- `BrokerCard.svelte`: aggiungere riga Quota (`user_share_percentage`, da `brokerStore`/`GET /brokers`,
  STEP 1.1) e riga NAV/Gain-Loss (da `by_broker`, STEP 1.2) sopra la sezione Cassa esistente.
- Sezione Cassa della card: sostituire la griglia attuale (righe 130-146, box colorati) con un elenco
  righe-per-valuta via `formatCurrencyAmountHtml` (coerente con STEP 2.2), alimentato da
  `BrokerBreakdown.cash_balances` (nativo, STEP 1.2) — non più da `/summary`.

### 3.3 Icona Condividi + `BrokerSharingModal` sola-lettura

- `BrokerCard.svelte`: nuova icona `Share2` (lucide-svelte, stessa icona già importata in
  `/brokers/[id]/+page.svelte` riga 9) accanto a `Pencil`/`Trash2` esistenti (righe 104-111). Dispatch nuovo
  evento `share` gestito dalla pagina, che apre `BrokerSharingModal` (riuso, non nuova modale) passando
  `readOnly={broker.user_role !== 'OWNER'}` (nuova prop, vedi 3.3.1).
- **`BrokerSharingModal.svelte` — nuova prop `readOnly: boolean = false`** (nessuna prop di questo tipo
  oggi, verificato). Quando `true`: nasconde bottoni Aggiungi/Rimuovi/Salva/reset (`showAddModal`,
  `confirmRemoveOpen`, azioni su righe con edit-ruolo), mostra solo l'elenco `accesses` (username, ruolo,
  `share_percentage`, `email` — tutti sempre visibili, nessuna redazione lato backend) + il `SemiDonutChart`
  esistente (resta invariato, è già solo visivo). Riuso totale di `ModalBase`, `SemiDonutChart`,
  `InfoBanner`, `LazyImage` — nessun nuovo sotto-componente.

### 3.4 Sezione "Altri Broker Esistenti"

- Nuova chiamata locale (solo in questa pagina, **non** in `brokerStore`) a `GET
  /brokers?include_inaccessible=true`, letto `.inaccessible` (STEP 1.3).
- Nuovo componente leggero `BrokerDiscoveryCard.svelte` (variante minima di `BrokerCard`: icona + nome +
  icona Condividi soltanto, nessuna altra sezione) — riuso di `BrokerIcon.svelte` esistente per l'icona.
  Condividi apre `BrokerSharingModal` con `readOnly={true}` forzato (il caller non ha alcun ruolo).

---

## STEP 4 — Frontend: Shell Dettaglio Broker (`/brokers/[id]`)

### 4.1 Header

- Quota badge: dato già presente in `BRSummary.user_share_percentage` (confermato via grep — **nessuna
  modifica backend richiesta qui**), solo markup aggiuntivo accanto al badge ruolo esistente (righe 152-164).
- Bottone Share: rimuovere il gate `{#if safeString(broker.user_role) === 'OWNER'}` (riga 178) — sempre
  visibile, passa `readOnly={safeString(broker.user_role) !== 'OWNER'}` a `BrokerSharingModal` (riuso, STEP
  3.3.1 già copre la prop).

### 4.2 Redistribuzione nei 3 tab

- Monta `<TabBar>` (STEP 2.1) con 3 tab: Panoramica (attivo di default) · Posizioni · Transazioni.
- **Posizioni** e **Transazioni**: in questa fase, **solo trasloco as-is** dei blocchi esistenti (tabella
  Holdings righe 255-314 → tab Posizioni; Import Files righe 366-380 + Transazioni Recenti righe 382-416 →
  tab Transazioni), **nessun redesign** — quello è Fase 2/3 (`impl_plan_broker_holdings.md`/
  `impl_plan_broker_transactions.md`, da scrivere dopo).
- **Panoramica**: contenuto interamente nuovo, vedi STEP 5.

---

## STEP 5 — Frontend: Tab Panoramica

### 5.1 KPI + Grafico + Allocazione — mount widget Dashboard, scope `broker_ids: [id]`

- **Riuso esatto del pattern Dashboard**, non `KpiCard.svelte`: l'audit conferma che `KpiCard.svelte`
  esiste (`frontend/src/lib/components/dashboard/KpiCard.svelte`) ma **non è usato** dalla Dashboard Home,
  che compone le 3 KPI con wrapper hand-rolled + `KpiMetricBar`/`KpiDivergingFlowBar` (`dashboard/+page.svelte`
  righe 751-908). Per coerenza si copia **questo** pattern (stesso markup, stessi due sotto-componenti), non
  si introduce `KpiCard` (adottarlo ovunque sarebbe un refactor più ampio, fuori scope qui).
- `GrowthChart` (`frontend/src/lib/components/dashboard/GrowthChart.svelte`, props `history`, `baseCurrency`,
  righe 32-39) e `AllocationHistoryChart` (stesso folder, props `data`, `dimension`, righe 36-44): montati
  identici a Dashboard (righe 914-916, 963-965), alimentati da `portfolioStore.fetchReport([brokerId], ...)`.
- Range temporale: **da identificare in implementazione** l'esatto componente di selezione range già usato
  da Dashboard per i bottoni `[1W][1M][3M][6M][1Y][2Y][Custom]` (non ancora auditato puntualmente) — riuso
  di quello, nessun nuovo date-picker.
- Valuta: 3ª istanza indipendente di `CurrencySearchSelect` (dopo Dashboard e Lista Globale), locale a
  questa pagina, pre-popolata da `globalSettings.default_currency`.

### 5.2 Cassa ridisegnata (sola lettura)

- Nuovo elemento minimo (non un nuovo componente pesante): lista righe-per-valuta con
  `formatCurrencyAmountHtml`/`Plain`, allineate a destra, ordine invariato rispetto a oggi. Alimentata da
  `BRSummary.cash_balances` (già nativo multi-valuta, nessuna modifica backend). Nessun box/icona/bottone
  per valuta.

### 5.3 "+ Nuova Transazione" — nuovo punto di ingresso, riuso totale

- Le azioni Deposito/Prelievo **non vengono ricreate**: un solo bottone generico "+ Nuova Transazione"
  (stessa label/chiave i18n `transactions.addTransaction` già usata da Dashboard e `/transactions`) apre
  `TransactionFormModal` (`frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte`)
  con **`forcedBroker={broker.id}`** (prop già esistente, righe 103/164/254/504-505: preseleziona e blocca
  il broker, `brokerImmutable` righe 737). L'utente sceglie il tipo (`DEPOSIT`/`WITHDRAWAL`/altro) dal
  `TransactionTypeSearchSelect` interno alla modale (nessuna prop di pre-selezione tipo trovata — accettabile,
  non blocca il flusso). Questo preserva la possibilità di operare senza ricreare `CashTransactionModal`.

### 5.4 Metadati (trasloco) + Transazioni Recenti (opzionale)

- Box Metadati/Info Broker: markup esistente (righe 319-364 dell'attuale pagina flat), spostato senza
  modifiche di logica.
- `RecentTransactionsPanel` (`frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte`, prop
  `brokerIds` righe 34-45): riuso diretto con `brokerIds={[broker.id]}`.
- Nessuna preview Posizioni in questo tab (evita duplicazione col tab dedicato di Fase 2).

---

## STEP 6 — Ritiro componenti

- `frontend/src/lib/components/brokers/CashBalanceCard.svelte` — eliminare (confermato: nessun altro
  utilizzo nel codebase oltre alla pagina flat che viene sostituita).
- `frontend/src/lib/components/brokers/CashTransactionModal.svelte` — eliminare (confermato via grep:
  unico utilizzo era `/brokers/[id]/+page.svelte`, sostituito da `TransactionFormModal` in STEP 5.3).

---

## STEP 7 — i18n

- `./dev.py i18n audit` dopo l'implementazione per individuare chiavi mancanti (quota %, sezione "Altri
  Broker Esistenti", stati vuoti Discovery, eventuali nuovi tooltip Condividi) in EN/IT/FR/ES. Chiave
  `transactions.addTransaction` già esistente, riusata as-is in 5.3.

---

## Riepilogo componenti riusati (invariati)

`BrokerCard` (struttura base) · `BrokerIcon` · `BrokerModal` · `DeleteBrokerDialog` · `BrokerSharingModal`
(+ nuova prop `readOnly`) · `BrokerImportFilesModal` · `CurrencySearchSelect` · `TransactionFormModal` ·
`GrowthChart` · `AllocationHistoryChart` · `RecentTransactionsPanel` · `KpiMetricBar` ·
`KpiDivergingFlowBar` · `portfolioStore.fetchReport` · `brokerStore` (`refreshAllBrokers`/`getAllBrokers`/
`invalidateBroker`) · `formatCurrencyAmountHtml`/`Plain` · `ModalBase` · `SemiDonutChart` · `InfoBanner` ·
`LazyImage` · `POST /portfolio/report` (esteso, non sostituito).

## Componenti nuovi (minimi, motivati)

`TabBar.svelte` (unifica le 3 implementazioni hand-rolled già esistenti + il nuovo broker detail — 4
consumer totali, nessuna regressione visiva) · `BrokerDiscoveryCard.svelte` (variante ridottissima di
`BrokerCard`) · `BRDiscoveryItem`/`BRListResponse` (schemi backend).

## Componenti ritirati

`CashBalanceCard.svelte` · `CashTransactionModal.svelte`.

## Rischi / note aperte

- Range-selector esatto della Dashboard (5.1) da identificare puntualmente in implementazione (nome
  file/props).
- Migrare `files/+page.svelte` su `<TabBar>` tocca una pagina con logica di persistenza (localStorage +
  query string) più ricca degli altri consumer: verificare in implementazione che il binding `activeTab`
  non rompa il round-trip già esistente (deep-link `?tab=`, righe 182-193/217).
- Dopo ogni modifica di schema/endpoint backend: `./dev.py api sync` (rigenera client TS) prima di toccare
  il frontend che li consuma.
- Dopo modifiche a modelli DB (nessuna prevista in questa fase — solo schemi Pydantic): eventuale
  `./dev.py db create-clean` non necessario qui.
