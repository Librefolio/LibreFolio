# Phase 6 Step 3 — Bugfix Plan v2 (AssetModal & Search)

> Post-checklist review + code review — 27 Mar 2026
> **Stato: 🔧 IN PROGRESS — attesa review utente**

---

## 1️⃣ Riepilogo Round 1 (completato)

| Bug | Fix applicato | Risultato |
|-----|---------------|-----------|
| BUG-1 i18n keys | `common.name`, `common.currency` aggiunte | ✅ 683 keys complete |
| BUG-2 EQUITY→422 | `mapProviderAssetType()` in AssetModal | ⚠️ Parziale — vedi round 2 |
| BUG-3 a11y labels | `id`/`for` su tutti i form control | ✅ 0 warnings |
| BUG-4 button nesting | `div[role=button]` per identifiers header | ✅ 0 warnings |
| BUG-5 stale search | Monotonic `searchId` | ✅ Funziona |
| BUG-6 system selects | SimpleSelect per type/provider/idType | ⚠️ Dropdown troncato |
| BUG-7 Ask Provider | match=✔, diverso=⚠ cliccabile | ✅ |
| BUG-8 InfoBanner doppio | Rimossa icona manuale | ✅ |
| BUG-9 Discard confirm | Dirty tracking + ConfirmModal | ✅ |
| BUG-10 Badge toggle | Sfondo colorato/trasparente | ⚠️ Manca provider nei risultati |

---

## 2️⃣ Code Review — Refactoring Architetturali

### R-1: `ASSET_TYPE_PNG_MAP` duplicato in 3 posti → utility centralizzata

**Stato attuale**: la stessa mappa è copia-incollata in:
- `AssetIcon.svelte` (riga 33)
- `AssetModal.svelte` (riga 84)
- `AssetTable.svelte` (riga 67)

**Fix**: Creare `frontend/src/lib/utils/assetTypes.ts` con:

```ts
// ── Constants ────────────────────────────
export const ASSET_TYPES = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND_LOAN', 'OTHER'] as const;
export type AssetTypeCode = typeof ASSET_TYPES[number];

const PNG_MAP: Record<string, string> = {
    STOCK: 'stock', ETF: 'etf', BOND: 'bond', CRYPTO: 'crypto',
    FUND: 'fund', HOLD: 'hold', CROWDFUND_LOAN: 'crowdfunding', OTHER: 'other',
};

// ── Functions ────────────────────────────
export function getAssetTypeIconUrl(type: string | null | undefined): string {
    const filename = PNG_MAP[(type ?? '').toUpperCase()] ?? 'other';
    return `/icons/asset-types/${filename}.png`;
}

export function buildAssetTypeOptions(t: (key: string) => string): SelectOption[] {
    return ASSET_TYPES.map(at => ({
        value: at,
        label: t(`assets.types.${at}`) || at,
        icon: getAssetTypeIconUrl(at),
    }));
}
```

Poi: `AssetIcon.svelte`, `AssetModal.svelte`, `AssetTable.svelte` importano da qui.

---

### R-2: `PROVIDER_TYPE_MAP` non ha senso nel frontend — spostare la mappatura nel backend

**Analisi**: Il backend `yahoo_finance.py` **già** fa il mapping in `fetch_asset_metadata()` (riga 430-439):
```python
asset_type_map = {
    "equity": "STOCK", "etf": "ETF", "mutualfund": "FUND",
    "cryptocurrency": "CRYPTO", "currency": "OTHER", "future": "OTHER", "option": "OTHER",
}
```

MA: l'endpoint **search** (riga 355) restituisce il `quoteType` RAW di yfinance (es. `"EQUITY"`) senza mappare!

**Fix backend**: Nell'`AssetSearchService.search()` (riga 2607-2627 di `asset_source.py`), dopo aver preso `item.get("type")`, applicare lo STESSO mapping del provider prima di inserirlo in `FAProviderSearchResultItem.asset_type`.

Così il frontend non ha bisogno di nessun `PROVIDER_TYPE_MAP` — riceve dati già normalizzati.

**Domanda: ha senso aggiungere FUTURE, COMMODITY, OPTION, INDEX come AssetType?**

| Tipo yfinance | Oggi → | Considerazione |
|---------------|--------|----------------|
| EQUITY | STOCK | ✅ Mapping corretto |
| ETF | ETF | ✅ Diretto |
| MUTUALFUND | FUND | ✅ Mapping corretto |
| CRYPTOCURRENCY | CRYPTO | ✅ Diretto |
| FUTURE | OTHER | 🔶 Futures su commodities (oro, petrolio) sono usati. Ma hanno pricing diverso (scadenza, rollover). Per ora OTHER va bene. |
| COMMODITY | — | 🔶 Non esiste come quoteType in yfinance. I commodities sono quotati come FUTURE. |
| OPTION | OTHER | ❌ Pricing complesso (Black-Scholes, greeks). Non ha senso per un portfolio tracker. |
| INDEX | OTHER | 🔶 Non sono asset acquistibili, sono benchmark (S&P 500, MSCI World). Utili come confronto, non come posizioni. Futuro: feature "benchmark overlay" nei grafici. |
| CURRENCY | OTHER | 🔶 Coppie FX tipo EUR/USD. Non sono asset, sono cambi. → Espandere yfinance come **FX provider** è un'idea valida per il futuro. |

**Raccomandazione**: Per ora NESSUN nuovo tipo. EQUITY→STOCK, MUTUALFUND→FUND, tutto il resto→`OTHER`. Se in futuro serviranno COMMODITY o FUTURES, si aggiungeranno insieme alla logica di pricing specifica.

---

### R-3: `ID_TYPES` hardcoded — deve venire dal backend

**Stato attuale**: `const ID_TYPES = ['TICKER', 'ISIN', 'CUSIP', 'SEDOL', 'FIGI', 'UUID', 'OTHER']` è duplicata in `ProviderAssignmentSection.svelte`.

Il backend ha `IdentifierType` enum in `models.py` (riga 109-115), e la espone già tramite OpenAPI → i tipi generati Zodios la conoscono.

**Fix**: 
- L'API `/assets/provider` restituisce `FAProviderInfo.params_schema` ma NON l'elenco dei IdentifierType supportati.
- **Opzione A** (semplice): Importare i valori dall'enum generato nel client TypeScript Zodios (se esposta come Zod enum).
- **Opzione B** (pragmatica): Aggiungere `identifier_types: list[str]` alla risposta di `GET /assets/provider` list endpoint.
- **Opzione C** (minima): Estrarre la const in `assetTypes.ts` utility, almeno centralizzata.

**Raccomandazione**: Opzione A se possibile (zero lavoro backend), altrimenti Opzione C come step intermedio.

---

## 3️⃣ Bug Round 2 — Nuovi dal test utente

### BUG-11: Create asset 201 ma modale non si chiude ⭐ CRITICO

**Sintomo**: Backend risponde 201, ma frontend:
- Modale resta aperta
- Nessun toast
- Nessun errore in console
- Secondo tentativo: nessun errore visibile (probabile 409 nascosto)

**Analisi probabile**: 
Il flusso è: `saveCreate()` → create 201 → assign provider → ???
- Se `create` va a buon fine ma `assign_providers_bulk` fallisce, l'errore finisce nel catch generico di `doSave()` che setta `formError`.
- Ma `formError` è in fondo al body scrollabile — potrebbe non essere visibile!
- Oppure: Zod runtime validation del response potrebbe fallire silenziosamente se il response shape non corrisponde allo schema generato.

**Fix**:
1. Aggiungere `console.error('Save failed:', e)` nel catch di `doSave`
2. Scrollare `formError` in vista quando appare (o metterlo in un toast error)
3. Verificare se l'assign provider step fallisce e perché (log il response)
4. Considerare di wrappare il provider assign in un try/catch separato, così l'asset è comunque creato

---

### BUG-12: SimpleSelect dropdown troncato dentro panel collapsible 🔧 UX

**Sintomo**: Il dropdown di Provider e Identifier Type si apre MA è tagliato dal `overflow: hidden` del container `.rounded-lg.overflow-hidden`.

**Fix**: 
- Opzione A: Rimuovere `overflow-hidden` dal container collapsible e usare `rounded-lg` solo su header/content separati
- Opzione B: Il SimpleSelect deve usare un portal (`<div>` appeso a `<body>`) per il dropdown, come fa `BaseDropdown.svelte`
- **Raccomandazione**: Opzione A è più semplice — il `overflow-hidden` serve solo per il border-radius degli angoli, bastano classi separate

---

### BUG-13: "No Provider" checkbox posizionamento 🔧 UX

**Stato attuale**: Checkbox "Nessun Provider" in cima al pannello Provider Assignment, come primo elemento del content.

**Richiesta utente**: 
- Spostare nel titolo della sezione collapsible, a sinistra
- Se spuntato: panel fisso chiuso (non apribile)
- Se non spuntato: panel apribile e chiudibile normalmente

**Fix**: Trasformare l'header del collapsible Provider Assignment in:
```
[▶/▼] Provider Assignment    [☐ No Provider]    [✅/❌ test status]
```
Quando "No Provider" è checked, il chevron scompare e il panel resta chiuso.

---

### BUG-14: Provider icon + name nei risultati di ricerca 🔧 UX

**Stato attuale**: I risultati della search mostrano `via yfinance` come testo puro.

**Richiesta**: Mostrare icona del provider + nome formattato come badge, coerente con i badge toggle.

**Fix**: In `AssetSearchAutocomplete.svelte`, nella riga dei risultati, sostituire:
```svelte
<span class="text-gray-400">via {result.provider_code}</span>
```
con un badge con icona del provider (serve far arrivare `icon_url` nei risultati, o lookup dalla lista providers caricata).

---

### BUG-15: Icona custom asset — feature mancante 🆕 FEATURE

**Richiesta**: L'utente deve poter scegliere un'icona custom per l'asset, con lo stesso meccanismo usato per:
- Avatar utente (ProfileTab → `ImagePickerWrapper preset="avatar"`)
- Icona broker (BrokerForm → `ImagePickerWrapper preset="broker-icon"`)

Il campo `icon_url` esiste già nel modello `Asset` (DB riga 449).

**Fix**: Aggiungere `ImagePickerWrapper` nella sezione Asset Details della modale.

---

## 4️⃣ Proposta Design — Sezione "Asset Details" nella modale

### Campi del modello Asset editabili

| Campo DB | Attualmente in modale | Deve esserci |
|----------|-----------------------|-------------|
| `display_name` | ✅ | ✅ |
| `currency` | ✅ | ✅ |
| `asset_type` | ✅ | ✅ |
| `icon_url` | ❌ | ✅ — ImagePickerWrapper |
| `active` | ❌ | 🔶 Solo in edit mode, toggle nel header |
| `classification_params` | ❌ | 📋 Fase futura (sector, description, geographic area) — non in questo step |
| `identifier_*` | ✅ (sezione separata) | ✅ |

### Proposta A: "Compact Profile Card" ⭐ RACCOMANDATA

L'icona è integrata a sinistra dei campi, come una mini-card profilo:

```
┌─ Asset Details ──────────────────────────────────────┐
│                                                       │
│  ┌──────────┐   Name *    [Apple Inc.              ] │
│  │          │                                        │
│  │   ICON   │   Type *    [📈 Stock           ▾]    │
│  │  (click  │                                        │
│  │ to edit) │   Currency *[🇺🇸 USD             ▾]    │
│  │          │                                        │
│  └──────────┘                                        │
│                                                       │
└──────────────────────────────────────────────────────┘
```

- **Icona**: Riquadro ~64×64px, bordo tratteggiato se vuota, mostra `AssetIcon` se presente
- **Click sull'icona** → apre `ImagePickerWrapper preset="asset-icon"`
- **Hover** → overlay con icona fotocamera/matita
- Layout: `grid grid-cols-[80px_1fr]` o flex con icona fissa a sinistra
- In create mode senza icon_url → mostra l'icona PNG del tipo asset selezionato come placeholder
- **Responsive mobile**: icona sopra, campi sotto (stack verticale)

### Proposta B: "Header Preview + Form Below"

```
┌──────────────────────────────────────────────────────┐
│  ┌────┐                                              │
│  │ 🍎 │  Apple Inc.                                  │
│  └────┘  Stock · USD                    [Edit Icon]  │
├──────────────────────────────────────────────────────┤
│  Name *     [Apple Inc.                            ] │
│  Type *     [📈 Stock                          ▾]    │
│  Currency * [🇺🇸 USD                            ▾]    │
└──────────────────────────────────────────────────────┘
```

- Parte alta: anteprima dell'asset come card (read-only summary)
- Parte bassa: form editabile
- **Pro**: feedback visivo immediato di come apparirà l'asset
- **Contro**: occupa più spazio verticale

### Proposta C: "Inline Icon Button"

```
┌─ Asset Details ──────────────────────────────────────┐
│  Name *     [Apple Inc.                   ] [🖼 Icon] │
│  Type *     [📈 Stock                          ▾]     │
│  Currency * [🇺🇸 USD                            ▾]     │
└───────────────────────────────────────────────────────┘
```

- Bottone icon a destra del campo nome
- **Pro**: Minimale, zero overhead
- **Contro**: Non mostra l'anteprima dell'icona

**La mia raccomandazione è Proposta A**: 
- Coerente con BrokerForm (stessa UX per l'icona)
- Mostra sempre un'anteprima
- Compatta ma informativa
- Il placeholder cambia in base al tipo selezionato (feedback visivo)

---

## 5️⃣ Piano di Implementazione Round 2

### Priorità 1 — Critici
| # | Task | Stima |
|---|------|-------|
| R-2 | Backend: mapping asset_type nella search (non solo metadata) | 15 min |
| BUG-11 | Debug create: logging, error handling, scroll formError in vista | 30 min |

### Priorità 2 — Refactoring
| # | Task | Stima |
|---|------|-------|
| R-1 | Creare `assetTypes.ts` utility, eliminare duplicazioni in 3 file | 20 min |
| R-2 fe | Rimuovere `PROVIDER_TYPE_MAP` dal frontend (dopo fix backend) | 5 min |
| R-3 | Centralizzare/importare `ID_TYPES` (opzione A o C) | 10 min |

### Priorità 3 — UX Fixes
| # | Task | Stima |
|---|------|-------|
| BUG-12 | Dropdown troncato: rimuovere overflow-hidden dal collapsible | 10 min |
| BUG-13 | Spostare "No Provider" nel titolo collapsible | 20 min |
| BUG-14 | Badge provider nei risultati di ricerca | 15 min |

### Priorità 4 — Feature
| # | Task | Stima |
|---|------|-------|
| BUG-15 | ImagePickerWrapper per icona asset + layout "Compact Profile Card" | 40 min |

### Priorità 5 — Futuro (fuori scope)
- Streaming search (WebSocket o SSE per risultati progressivi per provider)
- Classification params editabili (sector, geographic area)
- Active toggle in edit mode
- yfinance come FX provider
- Nuovi AssetType (COMMODITY, FUTURE) se necessario

---

queste le tue domande:

📋 Decisioni da confermare
1. Nuovi AssetType? → La mia raccomandazione è NO per ora. FUTURE/COMMODITY/OPTION/INDEX hanno logiche di pricing complesse. Mapping: tutto ciò che non è STOCK/ETF/FUND/CRYPTO/BOND → OTHER. Ok?
2. Mapping asset_type nel backend (R-2): yfinance.search() restituisce "EQUITY" raw → il fix corretto è nel backend (AssetSearchService.search()), così il frontend riceve dati già normalizzati e il PROVIDER_TYPE_MAP nel frontend si elimina. Ogni provider è responsabile di restituire i nostri tipi standard.
3. ID_TYPES (R-3): La mia raccomandazione è Opzione A — verificare se Zodios genera l'enum IdentifierType dal OpenAPI e importarla, oppure Opzione C (centralizzare in assetTypes.ts). Il backend definisce già l'enum, dobbiamo solo propagarla.
4. Design icona asset: Proposta A "Compact Profile Card" — icona 64×64 a sinistra dei campi, click per ImagePickerWrapper, placeholder dal tipo asset. Confermi?
5. BUG-11 (create non chiude modale): Prima di tutto debuggare. Probabile che il provider assign step fallisca dopo il create. Fix: separare il try/catch per create vs assign, aggiungere console.error, scrollare formError in vista.
6. BUG-13 (No Provider): Spostato nel titolo del collapsible, se checked il panel resta chiuso fisso. Ok?
Attendo la tua review prima di procedere con l'implementazione. 🫡

---
queste le mie risposte:

tra le cose da rivedere metterei come nuovo tipo di asset INDEX, ma metterei anche che un asset di tipo index non può avere transazioni ad esso collegato, proprio perchè p un segnale virtuale.
lo streaming search è da approfondire ora, prima di andare oltre
I classificication params, che sono entrambi dati con distribuzioni vanno pensare sin da subito, con una base comune di estetica che si adatta alle peculiarità tra i 2 dati, perchè la sua configurazione serve per calcolare in futuro le dashboard e gli xray! Dovrebbero essere auto popolati da fetch_metadati.
questa la tabella attuale nel DB degli asset:
id
display_name
currency
icon_url
classification_params
asset_type
active
identifier_isin
identifier_ticker
identifier_cusip
identifier_sedol
identifier_figi
identifier_uuid
identifier_other
created_at
updated_at

il form di create/edit deve permettere di editare tutti i campi che con le api esponiamo ed ha senso editare, se qualcuno è stato dimenticato, dobbiamo lavorare sul backend per correggere la dimenticanza.


per ora appuntiamoci per il futuro di esplorare yFinance come ulteriore fx provider, per ora siamo sugli asset

Ok per la proposta A del layout che permette di inserire l'icona asset, ma non dobbiamo dimenticare gli altri parametri.
Voglio che suddividiamo meglio I campi da mettere in Asset Detail, identifier e provider assignment
queste sono le colonne attuali nell'asset provider:
id
asset_id
provider_code
identifier
identifier_type
provider_params
last_fetch_at
fetch_interval
user_url
created_at
updated_at
anche qui stesso discorso dell'asset fatto sopra

---

Usiamo tutto questo per pianificare il lavoro.
