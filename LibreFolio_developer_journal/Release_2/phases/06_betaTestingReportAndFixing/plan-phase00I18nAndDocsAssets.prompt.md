# P6 — i18n, font e risorse della documentazione

> **Priorità**: 🟡 Bassa in urgenza, **alta in visibilità**: sono i primi difetti che un nuovo
> utente incontra su un'installazione Docker pulita.
> **Ambito**: `scripts/update_js_cache.py`, `Dockerfile`, `dev.py`,
> `mkdocs_src/docs/javascripts/gallery-img-loader.js`,
> `backend/app/services/asset_source_providers/`
> **Rilievi coperti**: I1, I2, I3
> **Riferimenti**: [`01_tassonomia_findings.md`](01_tassonomia_findings.md) §2

---

## 0. Il filo conduttore di I1 e I2

Entrambi i difetti **non si manifestano in sviluppo** e **non sono stati intercettati dalla CI**,
perché in entrambi gli ambienti la risorsa mancante è già presente per altre vie.

> **Sono difetti che colpiscono solo chi installa da zero** — cioè esattamente il beta tester,
> e ogni futuro utente self-hosted. La build fallisce parzialmente e **dichiara comunque successo**.

Il tema comune: **una build che degrada in silenzio**. La correzione più preziosa non è la singola
risorsa mancante, ma **rendere rumoroso il fallimento**.

---

## 🟠 I1 — Le bandiere diventano lettere su Windows nella build Docker

> *"su windows nella docker version le bandiere nel sito per la selezione lingue non compaiono,
> al loro posto hanno ripreso ad esserci le lettere della nazione"*

### La catena del guasto

| # | Fatto | Riferimento |
|---|---|---|
| 1 | Il font è applicato via classe CSS | `app.css:87-89` → `.emoji-flag { font-family: 'Apple Color Emoji', 'Noto Color Emoji', 'Segoe UI Emoji', sans-serif; }` |
| 2 | Le regole `@font-face` sono in un CSS autonomo | `app.html:12` → `<link href="/fonts/noto-color-emoji/noto-color-emoji.css">` |
| 3 | **Il font non è in git** | `.gitignore:83` → `frontend/static/fonts/` |
| 4 | È scaricato da Google Fonts a build time | `update_js_cache.py:44-50` |
| 5 | **Il fallimento è silenzioso** | `:188-192` → `print("❌ CSS download failed…"); return False` — nessuna eccezione, exit code **0** |
| 6 | La build prosegue comunque | `dev.py:509` (`cmd_fe_build`), `dev.py:1353` (`_docker_ensure_assets_built`) |
| 7 | L'immagine copia una build incompleta | `Dockerfile:52-53` → `COPY frontend/build/ ./frontend/build/`, senza verifica |

**Risultato**: il `<link>` va in 404 → la catena di fallback CSS scende fino a `Segoe UI Emoji` →
su Windows le coppie di *regional indicator* si rendono come **due lettere**, non come bandiera.

**Perché in locale funziona**: la macchina dello sviluppatore ha il font già in cache da un
download riuscito in passato, e Vite serve `static/` direttamente. Il difetto è **invisibile a chi
sviluppa** e visibile solo a chi installa.

### Fix

> 🔄 **Riscopato il 02/09/2026 (utente)**: il font **non** va versionato in git (potrebbe
> cambiare nel tempo). Il lavoro richiesto è:
>
> | # | Intervento | Priorità |
> |---|---|---|
> | **A** | **Fallire rumorosamente**: `update_js_cache.py` esce con codice ≠ 0 se una risorsa manca **e** non esiste versione cached (cached presente → warning e prosegui: è il caso offline legittimo); `dev.py` propaga l'errore nei path di build Docker (`:539`, `:1385`) invece di declassarlo a warning (`:2068`) | 🔴 Sempre |
> | ~~B~~ | ~~Versionare il font in git~~ | ❌ **Ritirata 02/09** |
> | **C** | Il fallback CSS resta come rete ultima: la catena `'Noto Color Emoji' → 'Segoe UI Emoji' → sans-serif` in `app.css:87-89` non si tocca — serve se il font è irraggiungibile a runtime | ✅ Solo verifica |

> ⚠️ **Correzione rispetto all'INDEX pre-02/09**: I1 non è mai stato iniziato — il font non è
> in git (`.gitignore:84` invariato, `git ls-files` vuoto), lo script esce 0 anche se il
> download fallisce, e `dev.py` declassa persino un exit≠0 a warning "will use CDN fallback".
> La build fallisce parzialmente e dichiara successo: esattamente il difetto originario.

**Complessità**: Piccola (A) / Media (B) · Solo build tooling

---

## 🟠 I2 — Le immagini della documentazione non si caricano

> *"nella documentazione non sono caricate le immagini, né quelle del server … né da GitHub
> (e questo è strano perché il fallback esiste apposta)"*

L'osservazione del tester è acuta: il fallback **esiste**. Il punto è che **è rotto anch'esso** —
due guasti indipendenti che si sommano.

### Guasto 1 — l'URL di fallback punta al posto sbagliato

```js
// mkdocs_src/docs/javascripts/gallery-img-loader.js:18
var GITHUB_PAGES_BASE = 'https://alfystar.github.io/LibreFolio';
```

Ma il sito reale è un altro:

```yaml
# mkdocs_src/mkdocs.yml:2-4
site_url: https://librefolio.github.io/LibreFolio/
repo_name: Librefolio/LibreFolio
```

Residuo del periodo in cui il progetto stava su un account personale, prima del passaggio
all'organizzazione. **Il fallback 404 sistematicamente.**

### Guasto 2 — le immagini locali non vengono mai generate

- Gli screenshot sono artefatti gitignorati: `.gitignore:75` → `/mkdocs_src/docs/gallery/**/*.png`
- Si generano con `./dev.py mkdocs gallery` (`dev.py:776`, Playwright su `gallery.spec.ts`)
- **Ma `_docker_ensure_assets_built()` (`dev.py:1367-1390`) non lo invoca mai**, e le istruzioni
  in testa al `Dockerfile` (righe 5-6) citano solo `front build` e `mkdocs build`

La pipeline ufficiale di release lo fa correttamente (`.github/workflows/release.yml:130`), quindi
**il sito pubblico è a posto**: a rompersi è solo il percorso self-hosted/Docker. Ed è proprio lì
che il fallback avrebbe dovuto salvare la situazione — se non fosse rotto anche lui.

### Fix

1. **Correggere `GITHUB_PAGES_BASE`** → `https://librefolio.github.io/LibreFolio`.
   Meglio ancora: **derivarlo da `site_url` di `mkdocs.yml`** a build time, così non può più
   divergere.
2. **Aggiungere `mkdocs gallery`** a `_docker_ensure_assets_built()`, o renderlo un passo
   obbligatorio documentato come `front build`.
3. Cercare altri riferimenti residui a `alfystar` nel repository.

**Complessità**: Banale (1) + Piccola (2) · Solo docs/build tooling

---

### ✅ Risolto e verificato sul campo (12/08/2026)

Diagnosi confermata **empiricamente** sulla nightly self-hosted, non più per sola lettura del
codice:

| Prova | Esito |
|---|---|
| `alfystar.github.io/…/import-modal.png` | **404** |
| `librefolio.github.io/…/import-modal.png` | **200** |
| Le 22 immagini referenziate da `/mkdocs/it/`, in `en` **e** `it` | **200 tutte** |
| JS servito dal container | conteneva ancora `alfystar` |
| PNG locale sul server | 404 |
| CSP che blocchi immagini di terze parti | **nessuna** (né header, né backend) |

L'assenza di CSP è ciò che rende il guasto 1 *sufficiente*: corretto l'hostname, non serve
altro.

#### Correzione alla diagnosi del guasto 2

Il piano attribuiva le immagini mancanti a `_docker_ensure_assets_built()`, che non chiama
`mkdocs gallery`. È vero per un `./dev.py docker build` locale, **ma la nightly non nasce da
lì**: la costruisce `release.yml` su push a `dev`, e quel workflow la gallery la invoca
(riga 130). Il vero meccanismo è un altro:

```yaml
- name: Generate Screenshots with Playwright
  continue-on-error: ${{ github.ref_name == 'dev' }}
```

Su `dev` la generazione screenshot **può fallire e la pipeline prosegue**, pubblicando `nightly`
lo stesso. Non è un difetto: è la scelta deliberata di non far cadere la nightly per un
Playwright ballerino — ed è **esattamente lo scenario per cui il fallback esiste**. Il fallback
era l'unica rete, e aveva il buco.

> **Il fix 2 proposto dal piano va quindi scartato.** Aggiungere `mkdocs gallery` a
> `_docker_ensure_assets_built()` imporrebbe a ogni `docker build` locale una suite Playwright
> da `timeout-minutes: 120`. Con il fallback funzionante non serve: le immagini arrivano da
> Pages, che è precisamente il compito che gli era stato assegnato.

#### Cosa è stato fatto

Applicata la variante robusta indicata dal piano stesso — **derivare l'URL da `site_url`**, non
riscriverlo a mano:

- **`mkdocs_src/overrides/main.html`** (nuovo, la `custom_dir` era già configurata e vuota):
  pubblica `window.LF_GALLERY_FALLBACK_BASE` da `config.site_url` nel blocco `extrahead`.
- **`gallery-img-loader.js:18`**: legge il valore iniettato e normalizza lo slash finale. La
  costante letterale resta **solo** come rete per una pagina resa senza il template.

Verificato prima che `site_url` non sia mai sovrascritto per ambiente (`dev.py`, `Dockerfile`,
workflow): il sito servito dal container porta già `<link rel="canonical">` su Pages. Derivarlo
è quindi corretto in ogni deploy, e i due valori non possono più divergere.

#### Verifica end-to-end

Riprodotta la nightly in locale — sito costruito servito da un server che restituisce **404 per
ogni PNG della gallery** — e caricata la home in Chromium via Playwright:

```
prima dello scroll:  8 / 11 caricate
dopo lo scroll:     11 / 11 caricate
src finale: https://librefolio.github.io/LibreFolio/gallery/desktop/it/light/dashboard/main.png
```

Le 3 iniziali non erano rotte: sono `loading="lazy"` sotto la piega, non ancora richieste. Il
`onerror` scatta alla prima richiesta reale e la catena di fallback le recupera.

> **Limite residuo, da conoscere**: `gh-deploy` gira solo da `main` o da una release, quindi
> Pages contiene gli screenshot dell'ultimo rilascio. Il fallback copre le immagini esistenti,
> **non quelle nuove**: le schermate dei nuovi step del wizard non compariranno finché non si
> rilascia. Non è un difetto del fallback, è il suo perimetro.

---

## 🟡 I3 — I messaggi del backend sono sempre in inglese

> *"il warning sul prezzo corrente nel fondo di borsa italiana è in inglese sempre, dovrebbe
> dipendere dalla lingua usata, quindi se scegliamo italiano, anche i warning dovrebbero esserlo"*

### Il caso specifico

```python
# backend/app/services/asset_source_providers/borsa_italiana.py:495-507
raise AssetSourceError(
    f"Fund {codice_fondo} NAV is dated {dati.data_nav}, not today",
    "NO_DATA",
    {"codice_fondo": codice_fondo, "nav_date": str(dati.data_nav)},
)
```

Ironia: il provider **supporta già** un'opzione lingua (`SUPPORTED_LANGUAGES` en/it) — ma solo per
il **nome dell'asset**, mai per i messaggi.

### Il problema è architetturale, non testuale

Oggi il backend non ha un meccanismo generale di i18n per i messaggi rivolti all'utente:

| Meccanismo esistente | Copre |
|---|---|
| `translation_utils.py` (Babel) | **solo** nomi di paesi e valute |
| `resolveValidationMessage.ts` | **solo** i codici di validazione delle transazioni |

**Ma gli ingredienti ci sono già**: `AssetSourceError` (`asset_source.py:216-222`) porta
`error_code` (es. `"NO_DATA"`) **e** `details: dict`. È esattamente lo schema
`codice + parametri` che serve. Il problema è che a essere mostrato è `message` — il testo libero.

### Fix — estendere un pattern già collaudato

1. **Backend**: garantire che `error_code` e `details` siano sempre valorizzati e propagati nella
   risposta API. `message` resta come *fallback* in inglese, non come fonte primaria.
2. **Frontend**: un resolver modellato su `resolveValidationMessage.ts` che mappi
   `error_code` + `details` → stringa localizzata.
3. **Adozione incrementale**: partire dai messaggi che l'utente incontra davvero.

**Scala**: 54 punti di `raise AssetSourceError(...)` con testo libero
(`borsa_italiana` 17, `yahoo_finance` 13, `css_scraper` 11, `justetf` 8, `scheduled_investment` 4,
`mockprov` 1).

> ⚠️ **Non tentare la conversione di tutti e 54 in un colpo solo.** Costruire il meccanismo,
> convertire i pochi messaggi effettivamente visibili, e lasciare gli altri al fallback inglese.

> 🔄 **Riscopato e approvato 02/09/2026 (utente)** — "in forma ridotta":
>
> - **BRIM è fuori scope per design**: i warning dei plugin di import seguono la lingua
>   **del file** importato, non quella della UI (documentato in `broker_credit_agricole.py:9-13`).
>   Un report italiano produce warning italiani a prescindere dalla lingua dell'interfaccia.
> - **Resta in scope solo il caso asset-source**: il messaggio inglese grezzo è tuttora
>   mostrato nella superficie "Test Configuration" del modale asset
>   (`ProviderAssignmentSection.svelte:292,298` rendono `cp.error`/`h.error` raw).
> - **Gli ingredienti sono già sul filo**: `error_code` + `details` sono nello schema
>   (`schemas/provider.py:355-356`) e già usati dal frontend per classificare
>   (`providerProbe.ts`). Manca solo il resolver di **testo**.
> - **Deliverable ridotto**: un resolver frontend (modello `resolveValidationMessage.ts` /
>   `translatedCode` di `RiskResultFrame.svelte`) che mappi i 4-5 codici davvero visibili
>   (`NO_DATA` con `nav_date`, `NOT_IMPLEMENTED`, `FETCH_ERROR`, `RATE_LIMIT`…) a stringhe
>   localizzate; tutto il resto cade sul messaggio raw come fallback.

### Sinergia forte con W8 (P2)

`BRIMFieldTodo` usa **già** `reason_code` + `context` "*for i18n*" (`brim.py:400-402`), e **W8** di
P2 sta per introdurre `BRIMWarning` con severità. Questi tre lavori convergono sullo stesso
modello:

> **Il backend emette un codice stabile più parametri; il frontend possiede il testo localizzato.**

Vale la pena definire quel contratto **una volta sola** e applicarlo a tutti e tre — invece di
inventare tre varianti che poi andranno riconciliate.

**Complessità**: Media (meccanismo + primo messaggio) / Grande (tutti e 54) ·
Backend + frontend · Nessun cambio di schema DB

---

## Ordine di esecuzione

```
I1-A (fail-loud in build Docker; I1-B ritirata 02/09; I1-C = solo verifica fallback CSS)
I2 ✅ fatto il 12/08 (URL derivato da site_url; fix 2 scartato — vedi blocco I2)
I3 ridotto [resolver frontend per i codici visibili; dopo W8: contratto codice+parametri già consolidato]
```

I1 e I2 sono indipendenti e parallelizzabili. **I3 va per ultimo**, per riusare il contratto
definito da W8 invece di anticiparlo.

---

## Verifica

```bash
./dev.py front build          # deve FALLIRE se il font non è disponibile (dopo I1-A)
./dev.py docker build
./dev.py mkdocs build
```

**Verifica manuale obbligatoria** — sono difetti che si vedono solo dove si manifestano:

| # | Controllo | Dove |
|---|---|---|
| 1 | Bandiere nel selettore lingue | **Windows**, immagine Docker, build da checkout pulito |
| 2 | Immagini della documentazione | Docker, sia locali sia via fallback |
| 3 | `GITHUB_PAGES_BASE` risponde | `curl` sull'URL corretto |

> Il controllo 1 richiede **un checkout pulito**: su una macchina di sviluppo il font è già in
> cache e il difetto non si riproduce. È precisamente il motivo per cui è sfuggito finora.

---

## Stato

> 🔄 **Riverificato e riscopato il 02/09/2026** (decisioni utente).

| ID | Rilievo | Complessità | Stato |
|---|---|---|---|
| I1 | Font bandiere assente nella build Docker | Piccola | ✅ **Fatto 02/09** — scope utente: no versionamento git. `update_js_cache.py` ora raccoglie gli hard failure (risorsa non scaricabile E senza copia cached; subset font parziali inclusi) ed esce 1; `dev.py update_js_cache(strict=True)` propaga l'errore a `front build` e `_docker_ensure_assets_built` → la build Docker si ferma. Il path `server` resta non bloccante (sviluppo offline con cache calda). Catena fallback CSS invariata |
| I2 | Immagini docs: URL fallback errato + gallery non generata | Banale/Piccola | ✅ **Fatto** (12/08, riverificato 02/09) — `overrides/main.html` inietta `window.LF_GALLERY_FALLBACK_BASE` da `config.site_url`; fix 2 (gallery nel path Docker) scartato per scelta documentata |
| I3 | Messaggi backend non localizzati | Piccola (scope ridotto) | ✅ **Fatto 02/09** (scope ridotto approvato) — `BaseProbeOperationResult.error_details` (JSON-safe) + codice `TIMEOUT` sui probe; nuovo resolver frontend `resolveProviderError.ts` (modello `resolveValidationMessage.ts`) con chiavi `providerErrors.*` ×4 per i codici visibili (NO_DATA + variante stale-NAV con `nav_date`, NOT_FOUND, FETCH_ERROR, NOT_IMPLEMENTED, TIMEOUT, MISSING_PARAMS, PARSE_ERROR, SCRAPE_ERROR); integrato in `ProviderAssignmentSection`; fallback al messaggio raw per i codici non mappati. BRIM fuori scope (lingua del file, by design) |
