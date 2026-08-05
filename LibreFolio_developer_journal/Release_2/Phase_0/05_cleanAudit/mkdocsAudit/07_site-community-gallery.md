# 07 — Sito, community, gallery

> **Release 2 · Phase 0 · 05_cleanAudit · mkdocsAudit**
>
> Modalità: sola verifica. Nessuna correzione di codice, documentazione, traduzioni o
> configurazione fa parte di questo audit — solo reperti con prova e classificazione.

## Ambito

Pagine in audit (7, tutte in `mkdocs_src/docs/`, nessuna esclusa):

- `index.en.md` (landing page)
- `community/contribute.en.md`, `community/credits-legal.en.md`, `community/faq.en.md`
- `gallery/index.en.md`, `gallery/desktop.en.md`, `gallery/mobile.en.md`

Escluse esplicitamente da questo report (come da tutte le altre): guida developer, user
manual, admin, financial-theory, AI Export, FX. Rientrano invece nell'ambito — perché
citate direttamente dalle 7 pagine sopra — le destinazioni di link/nav (anche se in
sezioni escluse), `mkdocs_src/mkdocs.yml`, gli asset statici e lo script di generazione
screenshot (`frontend/e2e/gallery.spec.ts`), licenza/metadati di progetto, e le capacità
osservabili di backend/frontend citate come claim.

## Baseline

| Campo | Valore |
|---|---|
| Snapshot | [00_BASELINE](00_BASELINE.md) |
| Impronta snapshot (sha256) | `ea01e8f86bd36a9b36f68e83336ee0e174ff35e6d67336922420d8471f235107` — verificata, coincide con `00_INDEX.md` |
| Commit HEAD | `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103` |
| Branch | `dev_release2` |
| Stato worktree | Dirty (32 path modificate, nessuna delle 7 pagine in audit); **nessun drift** rispetto allo snapshot verificato con `git status --short` al momento della stesura |

## Copertura

| # | Pagina | Righe | Reperti | Esito |
|---|---|---:|---:|---|
| 1 | `index.en.md` | 639 | 2 (R1, R2 — claim), 1 rif. incrociato (R3) | Reperti aperti |
| 2 | `community/contribute.en.md` | 99 | 1 (R5, non verificabile) | Nessun difetto, 1 nota |
| 3 | `community/credits-legal.en.md` | 74 | 0 | Verificata, nessun reperto |
| 4 | `community/faq.en.md` | 96 | 1 (R2 — claim gemella di index) | Reperto aperto |
| 5 | `gallery/index.en.md` | 90 | 0 | Verificata, nessun reperto |
| 6 | `gallery/desktop.en.md` | 617 | 0 (contribuisce ai campioni immagine di R3/R4) | Verificata, nessun reperto |
| 7 | `gallery/mobile.en.md` | 627 | 0 (idem) | Verificata, nessun reperto |

5 reperti totali (R1–R5): 3 con classificazione Contraddizione/Dettaglio obsoleto e prova
diretta, 1 Dettaglio obsoleto a impatto nullo oggi, 1 Non verificabile/informativo.

## Metodo di verifica

Oltre alla lettura riga per riga delle 7 pagine, per i riferimenti a screenshot (114
coppie `data-category`/`data-name` tra `index.en.md`, `gallery/desktop.en.md` e
`gallery/mobile.en.md`) è stato scritto uno script Python che estrae ogni coppia dai tag
`<img>` e la confronta con tutte le chiamate `screenshot(...)` — letterali e generate
dinamicamente da array (`TX_FORM_VARIANT_TYPES`, `POSITIONS_SCREENSHOT_VARIANTS`,
`LOTS_SCREENSHOT_VARIANTS`, ecc.) — in `frontend/e2e/gallery.spec.ts`. Le 114 coppie
risultano **tutte** riconducibili a una chiamata dello script di generazione: **nessun
riferimento a categoria/nome di screenshot rotto**. Per i link Markdown/nav sono stati
verificati con `ls`/`grep` i file di destinazione citati (relativi e assoluti) e la loro
presenza in `mkdocs.yml` → `nav:`. Per le claim funzionali (crypto, provider, licenze,
dipendenze) è stata verificata la presenza di codice di produzione con `grep`/`git log`,
non solo la dichiarazione in `Pipfile`/`pyproject.toml`. Per due URL esterni è stata
eseguita una fetch live per distinguere 200 da 404.

---

## Reperti

### 🟡 R1 — Badge "SELF-HOSTED OR CLOUD" presenta come attuale una funzione non ancora esistente

**Dove**: `index.en.md:47`

```html
<span class="badge badge-self-hosted">SELF-HOSTED OR CLOUD</span>
```

Questo badge compare nell'hero della landing page, accanto a "100% OPEN SOURCE" e
"HIGHLY EXPANDABLE" — tutte presentate come caratteristiche **attuali** del prodotto.

**Controprova**: sia `community/contribute.en.md:89-93` sia `community/faq.en.md:15`
descrivono "LibreFolio Cloud" come una funzione **futura**, non disponibile:

> `contribute.en.md:91`: *"For those who want to use LibreFolio but don't have the time,
> skills, or infrastructure to self-host, **we're planning** a hosted platform —
> LibreFolio Cloud."*
>
> `faq.en.md:15`: *"!!! info "**Coming soon**: hosted platform ☁️" — We're working on an
> online platform [...]"*

Non esiste alcuna funzione di sign-up, pricing o istanza hosted raggiungibile oggi (il
prezzo stesso è descritto come "da determinare" in `contribute.en.md:93`). Il badge
hero, letto isolatamente, comunica una scelta di deployment disponibile ora
("self-hosted" **o** "cloud"), mentre le due pagine più dettagliate della stessa sezione
del sito la presentano correttamente come roadmap.

- **Classificazione**: Contraddizione (tra pagine dello stesso sito)
- **Gravità**: major — un visitatore può cercare invano un'opzione cloud attiva
- **Confidenza**: alta — riscontro testuale diretto su tre pagine
- **Correzione suggerita** (non applicata in questo audit): allineare il badge a
  "SELF-HOSTED" oppure qualificarlo esplicitamente come "SELF-HOSTED · CLOUD IN ARRIVO",
  coerente con la formulazione già usata nelle altre due pagine.

---

### 🟡 R2 — FAQ dichiara "Cryptocurrencies — Coming soon" mentre il tipo CRYPTO è già implementato end-to-end

**Dove**: `community/faq.en.md:31`

```markdown
- **Cryptocurrencies** — Coming soon
```

**Controprova** — il tipo asset `CRYPTO` esiste ed è cablato in produzione, non solo
nello schema:

- `backend/app/db/models.py:174` — `CRYPTO = "CRYPTO"` nell'enum `AssetType` (con
  commento esplicativo a riga 154: *"Cryptocurrencies (e.g., Bitcoin, Ethereum)"*)
- `backend/app/services/asset_source_providers/yahoo_finance.py:534,642` — il provider
  Yahoo Finance mappa esplicitamente `"cryptocurrency": "CRYPTO"` per il fetch prezzi
  automatico (import `yfinance` a riga 23)
- `backend/app/services/brim_providers/broker_delta.py:190,218` e
  `broker_revolut.py:94,476` — i broker BRIM Delta Exchange e Revolut riconoscono e
  importano transazioni `CRYPTO` di produzione, non test
- `frontend/src/lib/utils/assetTypes.ts:24` — `CRYPTO` è un'opzione selezionabile
  nell'interfaccia di creazione/modifica asset (icona dedicata, tabelle, card,
  allocation chart)
- Nessuna restrizione o feature flag trovata in `backend/app/api/v1/assets.py` che limiti
  la creazione di asset `CRYPTO`

**Il conflitto è interno allo stesso set di pagine audite**: `index.en.md:332` afferma
già *"Automatically update the values of stocks, ETFs, **and crypto** by connecting to
real-time data providers"* — in diretto contrasto con "Coming soon" della FAQ.

- **Classificazione**: Contraddizione (claim smentita da codice di produzione, e
  contraddetta anche da un'altra pagina in ambito)
- **Gravità**: major — descrive come assente una capacità funzionante, rischiando di far
  scartare il progetto a chi cerca esplicitamente tracking crypto
- **Confidenza**: alta — catena di prova end-to-end (DB enum → provider prezzi → BRIM →
  frontend)
- **Correzione suggerita**: spostare "Cryptocurrencies" fuori da "Coming soon" nella FAQ;
  verificare se l'intento originario era invece riferito a un limite reale (es. copertura
  provider prezzi solo per un sottoinsieme di exchange) e, se sì, riformulare la claim con
  quel limite specifico invece di negare la funzione.

---

### 🟡 R3 — Fallback screenshot GitHub Pages punta a un organization/utente diverso da quello reale, e restituisce 404

**Dove**: `mkdocs_src/docs/javascripts/gallery-img-loader.js:18`

```javascript
var GITHUB_PAGES_BASE = 'https://alfystar.github.io/LibreFolio';
```

Questo script è referenziato in `extra_javascript` di `mkdocs.yml:613` e carica **ogni**
screenshot delle 3 pagine in ambito (`index.en.md`, `gallery/desktop.en.md`,
`gallery/mobile.en.md` — tutte le 114 coppie `data-category`/`data-name` verificate).
Quando uno screenshot manca in locale sia nella lingua richiesta sia nel fallback
`en`, lo script tenta di recuperarlo da questo URL GitHub Pages come ultima risorsa.

**Controprova**:

- `mkdocs.yml:2-4` — `site_url: https://librefolio.github.io/LibreFolio/`,
  `repo_url: https://github.com/Librefolio/LibreFolio`
- `mkdocs_src/hooks/jsonld.py:13-14` — stessa coppia `librefolio.github.io` /
  `github.com/Librefolio` usata per i meta JSON-LD
- `git remote -v` del repository conferma `git@github.com:Librefolio/LibreFolio.git`
- Nessun'altra occorrenza di `alfystar` in tutto `mkdocs_src/docs/`, `scripts/`, `.github/`
- Fetch live eseguita in audit:
  - `https://alfystar.github.io/LibreFolio/gallery/desktop/en/light/dashboard/main.png`
    → **404**
  - `https://librefolio.github.io/LibreFolio/gallery/desktop/en/light/dashboard/main.png`
    → **200**, PNG valido

Il fallback punta quindi a un dominio che non è (più) quello del progetto e che non
serve gli screenshot: per qualunque immagine mancante sia nella lingua richiesta sia in
`en` in locale, la catena di fallback termina con un'immagine rotta invece di recuperare
lo screenshot dal sito ufficiale pubblicato.

- **Classificazione**: Dettaglio obsoleto (riferimento a org/utente GitHub non più
  valido — verosimilmente residuo di un fork personale precedente al trasferimento nella
  organization `Librefolio`)
- **Gravità**: major — rompe silenziosamente un meccanismo di resilienza pensato per la
  produzione; non emette errori visibili se non un'icona di immagine rotta
- **Confidenza**: alta — verificata con fetch live (404 vs 200) e assenza di qualunque
  altro riferimento coerente al vecchio dominio
- **Correzione suggerita**: allineare `GITHUB_PAGES_BASE` a
  `https://librefolio.github.io/LibreFolio`.

---

### 🟢 R4 — URL di fallback della dashboard non corrisponde più alla struttura nav corrente (codice morto oggi)

**Dove**: `mkdocs_src/docs/javascripts/dashboard-check.js:15,78`

```javascript
var fallbackUrl = 'getting-started/installation/';
// ...
dashboardBtn.href = fallbackUrl;
```

Il commento originale nella cronologia Git (`getting-started/installation/"; //
Relative to index.md`) indica che questo percorso era valido prima della ristrutturazione
della documentazione (commit `83e2b3cb`, *"docs: restructure documentation architecture"*).

**Controprova**: la nav corrente in `mkdocs.yml:621-622` espone le due pagine come
`user/getting-started.md` e `user/installation.md` (percorsi pubblicati:
`user/getting-started/` e `user/installation/`) — non più unificate sotto
`getting-started/installation/`.

**Impatto attuale nullo, ma latente**: `dashboardBtn` viene risolto tramite
`document.getElementById('dashboard-link')`, e **nessuna pagina** in `mkdocs_src/docs/`
(verificato con grep ricorsivo, tutte le lingue) contiene oggi un elemento con
`id="dashboard-link"`. Il ramo di codice che assegna l'URL rotto non viene quindi mai
eseguito su una pagina realmente pubblicata. Se in futuro un pulsante "Go to Dashboard"
con quell'id venisse reintrodotto in `index.en.md` (il commento del file suggerisce che
un tempo esisteva), l'URL di fallback sarebbe silenziosamente errato.

- **Classificazione**: Dettaglio obsoleto / Navigazione-link (percorso non aggiornato
  dopo un refactor di nav)
- **Gravità**: minor — nessun effetto osservabile sulle pagine pubblicate oggi
- **Confidenza**: alta sul disallineamento del percorso; nessun impatto utente misurabile
  al momento dell'audit
- **Correzione suggerita**: aggiornare `fallbackUrl` a `user/installation/` (o
  `user/getting-started/`) quando/se il pulsante `#dashboard-link` viene ripristinato in
  `index.en.md`, oppure rimuovere il ramo di codice se il pulsante non è più previsto.

---

### ⚪ R5 — "Community-driven parsers/plugins": claim di framing, non verificabile come fatto storico

**Dove**: `index.en.md:230,240` (hub "Broker Imports": *"smart community-driven
parsers"*) e testo introduttivo del blocco "A Modular Ecosystem" (*"extending its
capabilities through a growing ecosystem of **community-driven plugins**"*)

**Osservazione**: `git log --format='%an' -- backend/app/services/brim_providers/` e
lo stesso comando su `asset_source_providers/` restituiscono un solo autore
(`Alfystar`) per l'intera cronologia. `community/credits-legal.en.md:7-10` elenca due
persone nel "Core Team" (sviluppo + design), nessun collaboratore esterno.

Questo **non è una contraddizione netta**: `community/contribute.en.md:19-35` descrive
un'architettura a plugin con registry pattern esplicitamente pensata per contributi
esterni (guide dedicate BRIM/Asset/FX/Signal, modulo di richiesta plugin per i
non-sviluppatori) — quindi "community-driven" è difendibile come descrizione
dell'**architettura di estensione**, non necessariamente come affermazione che i plugin
attuali siano già stati scritti dalla community. La formulazione sulla home resta però
ambigua: un lettore letterale potrebbe intendere che i parser esistenti siano già
contributi esterni, il che non risulta dalla cronologia Git.

- **Classificazione**: Non verificabile (dipende dall'interpretazione del claim, non da
  un fatto univoco nel repository)
- **Gravità**: info
- **Confidenza**: media — l'assenza di contributor esterni è un fatto verificato, ma non
  implica automaticamente che la frase sia "falsa", solo potenzialmente fuorviante

---

## Campioni verificati senza reperti

Elenco non esaustivo delle claim controllate positivamente (nessuna azione richiesta):

- **Licenza**: `LICENSE` (AGPL-3.0 v3, testo completo) e `THIRD_PARTY_LICENSES.md`
  esistono entrambi in root, come citato da `community/credits-legal.en.md:41,72`.
- **Dipendenze di terze parti citate in `credits-legal.en.md`**: QuantLib, Riskfolio-Lib,
  TA-Lib, pandas-ta-classic, NumPy, SciPy, pandas sono tutte dichiarate in `Pipfile` **e**
  effettivamente importate in produzione (`services/risk/quant/quantlib_worker.py`,
  `services/risk/quant/riskfolio_worker.py`, `services/risk_plugins/portfolio_optimization.py`,
  `services/signal_plugins/*.py` per `talib`/`pandas_ta`) — non solo dichiarate e mai
  usate.
- **Link GitHub**: tutti i link a `github.com/Librefolio/LibreFolio` (issue, PR, star,
  discussions, subscription) nelle 4 pagine che li citano corrispondono al remote reale
  del repository e a `repo_url`/`repo_name` in `mkdocs.yml`.
- **Issue template**: `plugin_request.yml`, `idea.yml`, `bug_report.yml`,
  `feature_request.yml` citati da `contribute.en.md` esistono tutti in
  `.github/ISSUE_TEMPLATE/`.
- **Link a guide plugin developer** (`registry_pattern.md`, `brim_plugin_guide.md`,
  `asset_plugin_guide.md`, `fx_plugin_guide.md`, `signal_plugin_guide.md`, e
  `developer/index.md`): tutti presenti come file e tutti presenti in `nav:` di
  `mkdocs.yml:838-849`.
- **Riferimenti a pagine escluse citate dalle 7 pagine in ambito** (FAQ →
  `admin/host_installation.md`, `user/installation.md`, `user/fx/detail/provider.md`,
  `user/fx/sync.md`, `user/pwa.md`): tutti risolvono a file esistenti.
- **114 coppie `data-category`/`data-name`** di screenshot su `index.en.md` +
  `gallery/desktop.en.md` + `gallery/mobile.en.md`: tutte riconducibili a una chiamata
  (letterale o dinamica) di `frontend/e2e/gallery.spec.ts` — nessuna categoria o nome
  orfano.
- **4 lingue documentate** (`gallery/index.en.md`: EN/IT/FR/ES "Complete"): tutte e
  quattro configurate con `build: true` nel plugin `i18n` di `mkdocs.yml` (righe 69, 73,
  248, 423), con `nav_translations` coerenti per le voci Gallery/Community nelle tre
  lingue non inglesi.
- **Asset statici**: `static/logo.png`, `static/favicon.png`,
  tutti gli 8 file in `extra_javascript` (incl. `gallery-img-loader.js`,
  `dashboard-check.js`, `site-lang-selector.js`, `bmc-widget.js`) e i 2 hook Python
  (`absolute_hreflang.py`, `jsonld.py`) referenziati in `mkdocs.yml` esistono tutti.
- **Comando reset password** (`faq.en.md`): `./dev.py user reset <username>
  <new_password>` corrisponde esattamente a `scripts/user_cli.py:307,335`, cablato in
  `dev.py:2145`.
- **PWA** (`faq.en.md`): `frontend/static/manifest.json` esiste, a supporto della claim
  di installabilità come app.
- **Asset types citati in FAQ** (Bonds manuale, P2P/scheduled-yield, Cash & Deposits):
  coerenti con l'enum `AssetType` (`db/models.py`) e con
  `asset_source_providers/scheduled_investment.py` (nessun provider di prezzo automatico
  per BOND, a conferma della claim "manual entry supported").
- **Link "Buy Me a Coffee"** (`contribute.en.md`, `bmc-widget.js`): stesso username
  `librefolio` in entrambi i punti; URL risolve con 200.

## Claim non risolvibili ulteriormente in questo audit

- **`contribute.en.md:75-77`** — *"A PR will be merged only if all existing tests
  continue to pass."* È una policy di revisione umana, non contraddetta da nulla nel
  repository, ma **non verificabile come garanzia automatica**: gli unici workflow in
  `.github/workflows/` sono `manual-test-run.yml` (`on: workflow_dispatch`, nessun
  trigger `pull_request`) e `release.yml`. La pagina non dichiara che sia un gate CI
  automatico, quindi non è una contraddizione — resta un impegno manuale del
  maintainer, non enforceable dal solo repository. Nessuna azione: solo annotazione per
  chi valutasse in futuro di aggiungere un workflow `pull_request`.
- **R5** (sopra) resta parzialmente soggettivo: dipende da come si legge
  "community-driven" — descrizione dell'architettura vs. affermazione storica sui
  contributori.

## Sintesi

| Gravità | Conteggio | Reperti |
|---|---:|---|
| 🔴 Critical | 0 | — |
| 🟡 Major | 3 | R1, R2, R3 |
| 🟢 Minor | 1 | R4 |
| ⚪ Info/Non verificabile | 1 | R5 |

Nessun reperto di questo report riguarda rischio dati o sicurezza. I tre reperti major
condividono lo stesso pattern: **un claim isolato (badge, FAQ, costante JS) non è stato
aggiornato in sincrono con un'altra pagina o con un refactor già avvenuto altrove nello
stesso sito** — non difetti di funzionalità del prodotto, ma disallineamenti testuali/di
configurazione tra pagine e script che condividono la stessa fonte di verità implicita
(stato del roadmap Cloud, stato del tipo asset CRYPTO, nome della organization GitHub).
La verifica sistematica delle 114 coppie di screenshot referenziate dalle 3 pagine con
immagini (index, gallery/desktop, gallery/mobile) non ha prodotto alcun riferimento
rotto: la generazione screenshot (`frontend/e2e/gallery.spec.ts`) e le pagine di
consumo sono coerenti al 100% sul piano categoria/nome.
