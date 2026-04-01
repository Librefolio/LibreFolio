# Checklist — Asset Source Providers: CSS Scraper & Scheduled Investment

Data: 2026-03-31  
Stato: PARZIALMENTE COMPLETATO — Fix residui in Round 10

---

## 0. Provider Static Icons

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 0.1 | File `cssscraper.png` esiste in `asset_source_providers/static/` | File presente | ✅ |
| 0.2 | File `scheduled_investment.png` esiste in `asset_source_providers/static/` | File presente | ✅ |
| 0.3 | `CSSScraperProvider.get_icon` ritorna `/api/v1/uploads/plugin/asset/cssscraper.png` | URL corretto | ✅ |
| 0.4 | `ScheduledInvestmentProvider.get_icon` ritorna `/api/v1/uploads/plugin/asset/scheduled_investment.png` | URL corretto | ✅ |
| 0.5 | API `GET /api/v1/assets/providers` ritorna `icon_url` per CSS Scraper | URL presente nel JSON response |✅ |
| 0.6 | API `GET /api/v1/assets/providers` ritorna `icon_url` per Scheduled Investment | URL presente nel JSON response |✅ |
| 0.7 | Frontend mostra icona CSS Scraper nel provider selector | Immagine visibile | ✅|
| 0.8 | Frontend mostra icona Scheduled Investment nel provider selector | Immagine visibile |✅ |
| 0.9 | `GET /api/v1/uploads/plugin/asset/cssscraper.png` ritorna 200 + PNG | File servito correttamente |✅ |
| 0.10 | `GET /api/v1/uploads/plugin/asset/scheduled_investment.png` ritorna 200 + PNG | File servito correttamente |✅ |

---

## 1. CSS Scraper Provider — Backend

### 1.1 Provider Registration & Info

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 1.1.1 | `provider_code` = `"cssscraper"` | Corretto | ✅ |
| 1.1.2 | `provider_name` = `"CSS Web Scraper"` | Corretto | ✅ |
| 1.1.3 | `accepted_identifier_types` = `[URL]` | Solo URL | ✅ |
| 1.1.4 | `supports_search` = `False` (default) | Non supporta search | ✅|
| 1.1.5 | `supports_history` = `False` | Non supporta storico | ✅ |
| 1.1.6 | Provider registrato nell'AssetProviderRegistry | Presente nella lista provider |✅ |

### 1.2 params_schema

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 1.2.1 | `current_css_selector` — tipo string, required | Schema corretto | ✅ |
| 1.2.2 | `currency` — tipo string, required | Schema corretto | ✅ |
| 1.2.3 | `decimal_format` — tipo select, options: [us, eu], default: "us" | Schema corretto | ✅ |
| 1.2.4 | `timeout` — tipo number, default: 30 | Schema corretto | ✅ |
| 1.2.5 | `user_agent` — tipo string, default: "LibreFolio/1.0" | Schema corretto | ✅ |
| 1.2.6 | Frontend genera form dinamico dai params_schema | Campi visibili e editabili | ✅|
compare tutto, ma dovresti fare in modo che il plugin invii anche i testi di esempio da mettere, ed un eventuale link di approfondimento che spieghi come usare quel plugin.
E a tal proposito prendendo spunto da quanto avevamo scritto nella documentazione: http://localhost:8001/mkdocs/developer/backend/assets/system_providers/#css-scraper-cssscraper
dovresti, creare nella documentazione utente un capitolo per gli asset, e un sotto capitolo per la configurazione di ogni plugin, per ora puoi anche mettere dei placeholder, li raffiniamo in seguito, ma tutti i plugin devono avere il link di info per il proprio plugin
in css scraper devi spiegare come ottenere i css selector e tutti gli altri parametri, usa pure come esempio la banca di italia, e dettaglia come ottenere i dati con chrome, firefox, etc...

### 1.3 get_current_value

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 1.3.1 | Scrape BTP Borsa Italiana (formato US) | Prezzo Decimal valido, currency EUR |✅ |
| 1.3.2 | Scrape BTP Borsa Italiana (formato EU) | Prezzo Decimal valido, currency EUR |✅ |
| 1.3.3 | CSS selector non trovato | AssetSourceError NOT_FOUND | ✅|
| 1.3.4 | URL inesistente | AssetSourceError HTTP_ERROR o REQUEST_ERROR | ✅|
| 1.3.5 | httpx non installato | AssetSourceError NOT_AVAILABLE |✅ |
| 1.3.6 | Parametri mancanti (no css_selector) | AssetSourceError MISSING_PARAMS |✅ |
| 1.3.7 | decimal_format invalido (es. "xyz") | AssetSourceError INVALID_PARAMS |✅ |
nel test la history se non supportata è mostrata rossa, ma sarebbe più corretto mostrarla gialla con un triangolo.
poi in caso di errore mostri lo stesso testo sia nella modale che nel tooltip, mi sta bene che lo mostri nel tooltip, ma nella modale fai un riassunto dicendo cosa non ha funzionato (l'errore), in oltre serve aggiungere il supporto per il tooltip che se si fa doppio clic si salva il contenuto nella clipboard, quando avviene fai comparire una notifica di toast blu che conferma la copia in clipboard, stesso effetto tenendo prolungato con il dito in modalità mobile.

### 1.4 get_history_value

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 1.4.1 | Qualsiasi richiesta storica | AssetSourceError NOT_IMPLEMENTED |✅ |

### 1.5 parse_price

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 1.5.1 | "100.39" formato US | Decimal("100.39") | ✅|
| 1.5.2 | "1,234.56" formato US | Decimal("1234.56") |✅ |
| 1.5.3 | "100,39" formato EU | Decimal("100.39") | ✅|
| 1.5.4 | "1.234,56" formato EU | Decimal("1234.56") |✅ |
| 1.5.5 | "€ 100.39" (con simbolo) | Decimal("100.39") |✅ |
| 1.5.6 | Testo vuoto | AssetSourceError PARSE_ERROR | ✅|

### 1.6 get_asset_url

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 1.6.1 | Identifier con `http` prefix | Ritorna l'identifier stesso | ✅ |
| 1.6.2 | Identifier senza `http` | Ritorna `None` | ✅ |

---

## 2. Scheduled Investment Provider — Backend

### 2.1 Provider Registration & Info

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 2.1.1 | `provider_code` = `"scheduled_investment"` | Corretto | ✅ |
| 2.1.2 | `provider_name` = `"Scheduled Investment Calculator"` | Corretto | ✅ |
| 2.1.3 | `accepted_identifier_types` = `[AUTO_GENERATED]` | Solo AUTO_GENERATED | ✅ |
| 2.1.4 | `supports_search` = `False` | Non supporta search | ✅ |
| 2.1.5 | `supports_history` = `True` | Supporta storico calcolato | ✅ |
| 2.1.6 | Provider registrato nell'AssetProviderRegistry | Presente nella lista provider |✅ |

### 2.2 params_schema & ui_component

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 2.2.1 | `_ui_component` presente con `type: "ui_component"`, default: "scheduled_investment" | Schema corretto | ✅ |
| 2.2.2 | Frontend rileva `type === 'ui_component'` e mostra ScheduledInvestmentEditor | Editor visualizzato |✅ |
| 2.2.3 | Campi `_ui_component` filtrati dal loop generico form | Non genera input field | ✅|

### 2.3 get_current_value — Calcolo Sintetico

in datapickrange se provo ad aprire i menù per scegliere mese o anno, appena scrollo si chiude

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 2.3.1 | Principal da BUY: 10000 EUR, rate 5%, SIMPLE, ACT/365, 1 anno | ~10500 EUR | |
| 2.3.2 | Principal 0 (nessuna transazione) | 0 EUR | |
| 2.3.3 | Multiple BUY + SELL → calcolo principal corretto | Principal ridotto | |
| 2.3.4 | INTEREST con price negativo → riduce principal | Principal aggiornato | |
| 2.3.5 | Date prima della schedule → ritorna solo principal | Nessun interesse | |
| 2.3.6 | COMPOUND interest (MONTHLY) | Interesse composto calcolato | |
| 2.3.7 | ACT/360 day count | Frazione anno diversa da ACT/365 | |
| 2.3.8 | 30/360 day count | Convenzione 30/360 applicata | |
| 2.3.9 | asset_id inesistente | AssetSourceError ASSET_NOT_FOUND | |
| 2.3.10 | provider_params mancanti | AssetSourceError MISSING_PARAMS | |

impossibile fare questi test a frontend, manca il bottone test della connessione.

### 2.4 get_history_value — Serie Storica Calcolata

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 2.4.1 | Range 1 mese, simple interest | N punti prezzo crescenti lineari | |
| 2.4.2 | Range con compound interest | N punti prezzo crescenti esponenziali | |
| 2.4.3 | Range che attraversa 2 periodi diversi | Cambiamento tasso visibile | |
| 2.4.4 | Range parziale (prima dell'inizio schedule) | Punti con solo principal | |

### 2.5 Post-Maturity: Grace Period + Late Interest

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 2.5.1 | target_date > maturity, grace_period_days=30 | Interesse a tasso normale durante grace | |
| 2.5.2 | target_date > maturity + grace | Interesse a tasso late_interest | |
| 2.5.3 | No late_interest config, target_date > maturity | Solo periodi schedulati, nessun extra | |
| 2.5.4 | grace_period_days = 0, target_date > maturity | Late interest immediato (no grace) | |

### 2.6 validate_params

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 2.6.1 | JSON valido con schedule + late_interest | FAScheduledInvestmentSchedule valido | |
| 2.6.2 | JSON con solo schedule (no late_interest) | Valido, late_interest = None | |
| 2.6.3 | JSON vuoto / None | AssetSourceError MISSING_PARAMS | |
| 2.6.4 | Rate negativo | ValidationError (Pydantic) → AssetSourceError | |
| 2.6.5 | `_transaction_override` viene rimosso prima della validazione | Nessun errore | |

### 2.7 _calculate_face_value_from_transactions

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 2.7.1 | Solo BUY (qty=1, price=10000) | 10000 | |
| 2.7.2 | BUY + SELL parziale | Differenza corretta | |
| 2.7.3 | INTEREST con price negativo | Principal ridotto | |
| 2.7.4 | INTEREST con price positivo | Principal invariato | |
| 2.7.5 | Transaction come dict (override mode) | Stesso risultato degli ORM objects | |

---

## 3. Frontend — ScheduledInvestmentEditor (F9)

### 3.1 CRUD Periodi

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 3.1.1 | Add Period da stato vuoto | Prima riga, start=oggi, end=+1 mese | ✅|
| 3.1.2 | Add Period con righe esistenti | Nuova riga start = ultimo end + 1 | ✅|
| 3.1.3 | Delete prima riga (2+) | Seconda espande start indietro | ✅|
| 3.1.4 | Delete ultima riga (2+) | Penultima espande end in avanti |✅ |
| 3.1.5 | Delete riga centrale | Modale BoundaryDate |✅ |
| 3.1.6 | Delete unica riga | Empty state |✅ |

### 3.2 Split & Merge

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 3.2.1 | Split con modale → conferma | 2 righe contigue, stessa config |✅ |
| 3.2.2 | Split su riga con 1 giorno | Bottone disabilitato |✅ |
| 3.2.3 | Merge 2 righe contigue | 1 riga con range unito |✅ |
| 3.2.4 | Merge righe non contigue | Bottone Merge disabilitato |✅ |
non è però chiaro se entrambi gli estremi sono inclusi o no

### 3.3 Bulk Delete (Multi-Gap)

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 3.3.1 | Selezionare tutte → Bulk Delete | Empty state, nessuna modale | ✅|
| 3.3.2 | Selezione HEAD (prime N righe) | Auto-expand survivor successivo | ✅|
| 3.3.3 | Selezione TAIL (ultime N righe) | Auto-expand survivor precedente |✅ |
| 3.3.4 | Selezione MIDDLE (blocco centrale) | Modale con 1 boundary date |✅ |
| 3.3.5 | Selezione non contigua (es. 2°, 5°, 8°) | Modale multi-gap con N sezioni |✅ |
| 3.3.6 | Modale multi-gap: conferma unica | Tutti gli spartiacque applicati | ✅|

### 3.4 Contiguità Automatica

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 3.4.1 | Espandere end_date a destra | Riga successiva riduce start | ✅|
| 3.4.2 | Ridurre start_date a sinistra | Riga precedente espande end |✅ |
| 3.4.3 | Espandere fino a "mangiare" successiva | Riga successiva eliminata |✅ |

### 3.5 Late Interest
| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 3.5.1 | Toggle late interest ON | Riga speciale "⚡ Late" visibile | ✅|
| 3.5.2 | Toggle late interest OFF | Riga grayed out |✅ |
| 3.5.3 | Click grace period → popover | Popover editabile con grace days |✅ |
servirebbe permettere di inserire anno con y, mese con m e giorni con d, e tenere le freccette che muovono in avanti i giorni, la logica dovrebbe essere nella riconversione fare anni + mesi + giorni, anche se si superano le soglio, come ad esempio 40 d invece di 1m e 10m, quando la modale si riapre i giorni devono essere riconvertiti in y m e d logici con anni da 365gg m da 30 e g da 1
| 3.5.4 | Cambiare grace days | Valore aggiornato "(+Nd grace → ∞)" |✅ |
| 3.5.5 | Late row non selezionabile | Checkbox assente | ❌|
il late interest si clicca anche se disattivo

### 3.6 Serializzazione JSON

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 3.6.1 | Serializzare → deserializzare (round-trip) | Dati identici | |
| 3.6.2 | Rate % → decimal (5.00 → 0.0500) | Conversione corretta | |
| 3.6.3 | SIMPLE → compound_frequency null/undefined | Non serializzato | |
| 3.6.4 | late_interest OFF → `null` nel JSON | Nessun campo late | |

i pacchetti inviati sono stati:
[{"display_name":"via silone","currency":"USD","asset_type":"CROWDFUND_LOAN"}]
e
[{"asset_id":14,"provider_code":"scheduled_investment","identifier":"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0s005634800-MOTX.html?lang=it","identifier_type":"AUTO_GENERATED","provider_params":{"schedule":[{"start_date":"2026-03-31","end_date":"2026-12-24","annual_rate":"0.0500","compounding":"SIMPLE","day_count":"ACT/365"},{"start_date":"2026-12-24","end_date":"2027-05-08","annual_rate":"0.0500","compounding":"SIMPLE","day_count":"ACT/365"},{"start_date":"2027-05-08","end_date":"2027-08-14","annual_rate":"0.0500","compounding":"SIMPLE","day_count":"ACT/365"},{"start_date":"2027-08-14","end_date":"2027-09-13","annual_rate":"0.0500","compounding":"SIMPLE","day_count":"ACT/365"}],"late_interest":null},"fetch_interval":1440}]

avevo configurato sia css che schedule, ma vedo che sono rimasti salvati entrambi, questo è evidentemente un bug, al salva deve essere mandato solo il pezzo selezionato in quel momento.

al salvataggio ho avuto un 
{"event": "Error listing assets: 1 validation error for FAinfoResponse\nidentifier_type\n  Input should be 'ISIN', 'TICKER', 'CUSIP', 'SEDOL', 'FIGI', 'UUID' or 'OTHER' [type=enum, input_value=<ProviderInputType.AUTO_G...RATED: 'AUTO_GENERATED'>, input_type=ProviderInputType]\n    For further information visit https://errors.pydantic.dev/2.12/v/enum", "logger": "backend.app.api.v1.assets", "level": "ERROR", "timestamp": "2026-03-31T20:12:04.609656Z"}
INFO:     127.0.0.1:50690 - "GET /api/v1/assets/query HTTP/1.1" 500 Internal Server Error

### 3.7 UI/UX

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 3.7.1 | DateRangePicker: 0 errori IDE | Nessun warning/error | ✅ |
| 3.7.2 | Toolbar bulk: allineata a destra | Accanto a Add Period | ✅ |
| 3.7.3 | Tooltip colonne: testo normale, multi-riga | Leggibile, non uppercase | ✅ |
| 3.7.4 | Tooltip periodo: "end date inclusive" | Chiarimento presente | ✅ |
| 3.7.5 | SimpleSelect dropdown: sopra azioni riga | z-index corretto | ✅ |
| 3.7.6 | Status banner: mostra N periodi + range + days | Info corrette |✅ |
| 3.7.7 | Empty state con bottone "Add First Period" | Funzionante |✅ |

---

## 4. Frontend — CSS Scraper Form

### 4.1 Form Dinamico (da params_schema)

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 4.1.1 | Campo "current_css_selector" — text input, required | Visibile, validato | |
| 4.1.2 | Campo "currency" — text input, required | Visibile, validato | |
| 4.1.3 | Campo "decimal_format" — select [us, eu], default us | Dropdown funzionante | |
| 4.1.4 | Campo "timeout" — number input, default 30 | Pre-compilato | |
| 4.1.5 | Campo "user_agent" — text input, default "LibreFolio/1.0" | Pre-compilato | |
| 4.1.6 | Identifier input: label "URL", placeholder "https://..." | Dinamico da ProviderInputType.URL | |

le note di sopra del backend le ho verificate dal frontend

### 4.2 Integrazione

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 4.2.1 | Creare asset con CSS Scraper provider | Asset creato in DB | |
| 4.2.2 | Probe test su CSS Scraper (con URL + selettore validi) | Current price estratto | |
| 4.2.3 | Probe test fallito (URL invalido) | Error message chiaro | |

le note di sopra del backend le ho verificate dal frontend

---

## 5. Integration Tests (End-to-End)

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 5.1 | `./dev.py test provider asset cssscraper` | Test pass (scrape BTP) | |
| 5.2 | `./dev.py test provider asset scheduled_investment` | Test pass (calcolo interesse) | |
| 5.3 | API probe per CSS Scraper → frontend mostra risultato | Prezzo visibile in Probe tab | |
| 5.4 | API probe per Scheduled Investment → frontend mostra risultato | Valore calcolato visibile | |
| 5.5 | Cambiare provider su un asset → icona aggiornata | Icona corretta nella UI | |
| 5.6 | Dark mode: icone provider visibili | Contrasto sufficiente | |

---

nella modalità dark lo sfondo del datapicker dovrebbe diventare bianco o panna, per permettere di mantenere il contrasto alle icone che hanno la trasparenza.

---

## Note

- I nomi file icona corrispondono ai `provider_code`: `cssscraper.png`, `scheduled_investment.png`
- L'URL statico è generato tramite `generate_static_url()` della base class `AssetSourceProvider`
- Il routing statico è: `GET /api/v1/uploads/plugin/asset/{filename}`
- Per il CSS Scraper, il form è generato dinamicamente da `params_schema`
- Per lo Scheduled Investment, `_ui_component` attiva il ScheduledInvestmentEditor custom

