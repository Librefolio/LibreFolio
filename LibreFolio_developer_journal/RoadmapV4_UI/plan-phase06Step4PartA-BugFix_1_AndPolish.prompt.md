# Plan: Bug Fix + UI Polish — Asset Detail Page (Part A)

Piano consolidato: 10 step per risolvere i bug critici, fix IDE, e miglioramenti UI inclusi i grafici di classificazione. Niente migrazioni Alembic — solo modifica `001_initial.py` + `db create-clean`.

---

## 🔴 Step 1 — Fix `effect_update_depth_exceeded` (modale bloccata)

**Root cause**: in `+page.svelte` riga 873, `editData={buildEditData()}` è inline nel template → ogni render crea un nuovo oggetto → ri-triggera l'`$effect` a riga 313 di `AssetModal.svelte` → loop infinito.

**Fix** in `frontend/src/routes/(app)/assets/[id]/+page.svelte`:
1. Aggiungere un `$derived` nella sezione state: `let editData = $derived(buildEditData())`
2. Nel template usare `editData={editData}` (riferimento stabile)
3. Opzionalmente, nell'`$effect` di `AssetModal.svelte` riga 313, aggiungere guard `untrack(() => editData)` per evitare che cambi di `editData` scatenino il re-populate

---

## 🔴 Step 2 — Fix errori di tipo IDE in `+page.svelte`

**Root cause**: `AssetInfo` da `z.infer<typeof FAinfoResponse>` ha campi con tipo union `(string | null) | Array<string | null>` — artefatto del generatore openapi-zod-client. Al runtime sono sempre stringhe.

**Fix** — interfaccia locale (pattern della lista asset in `assets/+page.svelte`):
1. Rimuovere `import type {AssetInfo, ProviderAssignment} from '$lib/types/asset'` a riga 43
2. Definire due interfacce locali con i tipi reali (no `Array<>`):
   - `AssetDetailInfo`: `id, display_name, currency, asset_type?: string|null, icon_url?: string|null, provider_code?: string|null, has_metadata, active, identifier_*?: string|null, identifier?: string|null, identifier_type?: string|null, user_url?: string|null`
   - `ProviderAssignmentLocal`: `asset_id, provider_code, identifier, identifier_type, provider_params?: Record<string,any>|null, fetch_interval?: number|null, last_fetch_at?: string|null, user_url?: string|null, provider_url?: string|null`
3. Usare queste interfacce per `assetInfo` e `providerAssignment` nello state
4. In `loadAssetInfo()` e `loadProviderAssignment()`, castare con `as AssetDetailInfo` / `as ProviderAssignmentLocal`

Questo risolve tutti e 5 gli errori di compilazione.

---

## 🟡 Step 3 — Spostare `user_url` da `AssetProviderAssignment` a `Asset`

L'utente vuole che l'URL esterno sia un campo dell'asset, non del provider, così anche gli asset senza provider possono avere un link.

**Backend** — 3 file:
1. **`backend/app/db/models.py`**: aggiungere `user_url: Optional[str] = Field(default=None)` al modello `Asset` (dopo `active`, riga ~501). Rimuovere `user_url` da `AssetProviderAssignment` (riga 937)
2. **`backend/alembic/versions/001_initial.py`**: spostare la colonna `user_url` dalla tabella `asset_provider_assignments` (riga 249) alla tabella `assets`
3. **`backend/app/schemas/assets.py`**: aggiungere `user_url: Optional[str]` a `FAinfoResponse` (riga 828) e a `FAAssetPatchItem` (riga 872+). Rimuoverlo da `FAProviderAssignmentReadItem` se presente

**Frontend** — 3 file:
1. Rigenerare il client Zodios: `./dev.py api sync`
2. **`AssetModal.svelte`**: spostare il campo `providerUserUrl` nella sezione base del form (vicino a `display_name`/`currency`), non nella sezione provider
3. **`+page.svelte`**: leggere `assetInfo.user_url` anziché `providerAssignment.user_url`

**Ricreare DB**: `./dev.py db create-clean` + `./dev.py test db populate --force`

---

## 🟡 Step 4 — README link Node.js

In `README.md` riga 37, aggiungere il link:
```
- [Node.js](https://nodejs.org/en/download) 20.19+ (includes npm)
```

---

## 🟡 Step 5 — Refresh button spin su tutte le pagine

Aggiungere `animate-spin` durante il loading ai bottoni refresh delle **pagine lista**:

1. **`frontend/src/routes/(app)/assets/+page.svelte`** riga 954: aggiungere un booleano `refreshing` che viene settato a `true` in `fetchAllPriceData()` e `false` nel finally. Usare `class={refreshing ? 'animate-spin' : ''}` su `<RefreshCw>`
2. **`frontend/src/routes/(app)/fx/+page.svelte`** riga 831: stesso pattern con `handleRefreshAll()`

Le detail page hanno già la logica (`loading ? 'animate-spin'`), verificare che il booleano cambi effettivamente durante la fetch.

---

## 🟡 Step 6 — Header polish

In `frontend/src/routes/(app)/assets/[id]/+page.svelte` sezione header (righe 451-491):

1. **Provider badge con icona**: usare `getAssetProviderIconUrl()` e `ensureAssetProvidersCached()` da `$lib/utils/providerHelpers.ts`. Caricare icons in `onMount`. Nel badge (riga 482-486), mostrare icona + nome provider (pattern di `assetProviderBadgeHtml` ma come Svelte markup, non HTML string)
2. **Bottone link esterno**: aggiungere icona `ExternalLink` da lucide-svelte. Mostrare se `assetInfo.user_url` (dallo Step 3) è presente, o fallback su `providerAssignment?.provider_url`. Se nessuno dei due esiste, non mostrare il bottone
3. **Rimuovere `primaryIdentifier`**: eliminare il blocco righe 476-480 e il `$derived` `primaryIdentifier` a riga 151
4. **Mobile layout**: cambiare il div riga 462 da `flex items-center gap-3 flex-wrap` a layout a 2 righe su mobile: nome (h2) sulla prima riga, badge + currency + provider sulla seconda riga come gruppo compatto. Usare `flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3`

---

## 🟡 Step 7 — Currency select label + warning conversione

In `+page.svelte` sezione filter bar (righe 522-530):

1. **Label**: aggiungere `<label class="text-[10px] ...">` sopra `CurrencySearchSelect` con testo `$t('assetDetail.displayCurrency')` che spieghi la funzione
2. **Invertire posizione**: spostare il Price Summary (righe 532-550) prima di CurrencySearchSelect
3. **Warning valuta non convertibile**: aggiungere un `$derived` che controlla se `displayCurrency !== assetInfo.currency` e la coppia FX non esiste in `allConfiguredFxSlugs`. Se manca, mostrare un info-banner con link per aprire la modale add FX pair

---

## 🟡 Step 8 — Scheduled Investment sync fix

In `+page.svelte`:
1. Il `$derived` `isScheduledInvestment` (riga 121) verrà risolto dallo Step 2 (fix tipo `never`)
2. Verificare che `handleSync()` funzioni per `scheduled_investment` — il backend dovrebbe ricalcolare i punti
3. Se il provider è `scheduled_investment`, la label del bottone sync deve mostrare `$t('assetDetail.recalculate')` — già implementato a riga 587, serve solo che `isScheduledInvestment` valuti correttamente

---

## 🟢 Step 9 — Grafici classificazione (Pie + Mappa)

Creare due componenti chart riutilizzabili in `frontend/src/lib/components/charts/`:

### 9a — `SectorPieChart.svelte`

Pie chart ECharts per distribuzione settori:
- **Props**: `data: Record<string, number>` (chiave = settore, valore = peso 0-1), `height?: number`, `locale?: string`
- **Design**: pie chart standard con legenda laterale, colori differenziati per settore, tooltip con `%`
- **i18n**: usare `$t(\`assets.sectors.${sectorKey}\`)` per tradurre i nomi settori
- **Dark mode**: auto-detect `html.dark` per colori testo/sfondo (pattern da `SemiDonutChart.svelte`)
- **Pattern**: seguire la struttura di `SemiDonutChart.svelte` — init ECharts, ResizeObserver, cleanup in `onMount`

### 9b — `GeographyMap.svelte`

Mappa del mondo ECharts con intensità colore per paese:
- **Props**: `data: Record<string, number>` (chiave = codice ISO-3166 A3, valore = peso 0-1), `height?: number`
- **Design**: mappa cloropleta (choropleth) — paesi presenti colorati con gradiente di intensità (verde chiaro → verde scuro), paesi assenti in grigio chiaro
- **Dipendenza**: installare `world-atlas` da npm. ECharts 6 richiede registrazione manuale della mappa GeoJSON. Usare il pacchetto npm `world-atlas` con il file `countries-110m.json` e convertirlo con `topojson-client` per registrarlo con `echarts.registerMap('world', geoJson)`
- **ISO mapping**: i codici nel DB sono ISO-3166 A3 (USA, ITA, DEU), il GeoJSON usa nomi per paese — serve una tabella di mapping A3 → nome paese (o usare un GeoJSON che ha già i codici A3 nelle properties)
- **Tooltip**: nome paese + percentuale
- **Dark mode**: sfondo mappa trasparente, bordi paesi grigi chiari/scuri

### 9c — Integrazione nella sezione Metadata

In `+page.svelte`, sezione metadata (righe 832-838):
1. Caricare i dati di classificazione tramite `GET /api/v1/assets?asset_ids={id}` (endpoint `read_assets_bulk` che ritorna `FAAssetMetadataResponse` con `classification_params`)
2. Se `has_metadata`, aggiungere una chiamata in `onMount` per caricare i dati completi
3. Sostituire il placeholder "Classification data available" con i due grafici:
   - Se `sector_area` presente: `<SectorPieChart data={sectorDistribution} />`
   - Se `geographic_area` presente: `<GeographyMap data={geographicDistribution} />`
4. Riordinare la sezione: URLs in alto → grafici → identifiers in basso

---

## 🟡 Step 10 — Mock data con `scheduled_investment` e `css_scraper`

Aggiornare lo script di populate test DB per creare:
1. Un asset con provider `scheduled_investment` (es. "BTP Italia 2028" con schedule di interessi)
2. Un asset con provider `css_scraper` (es. "Oro prezzo spot" con URL e selector)

---

## Ordine di Esecuzione

1. Step 1 → Step 2 (sbloccano tutti gli errori IDE e il bug modale)
2. Step 3 (cambio DB + schema — richiede `db create-clean`)
3. Step 4 (README — veloce)
4. Step 5 (Refresh spin — veloce)
5. Step 6 (Header polish — usa dati dallo Step 3)
6. Step 7 (Currency warning)
7. Step 8 (verificato automaticamente dallo Step 2)
8. Step 9 (Grafici — step più pesante, indipendente)
9. Step 10 (Mock data — ultimo, dopo tutte le modifiche schema)

Dopo tutti gli step:
- `./dev.py db create-clean`
- `rm -rf backend/data/test/`
- `./dev.py test db populate --force`

