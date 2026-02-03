# Plan: Settings Mobile Layout & Gallery Improvements

**Data creazione**: 2 Febbraio 2026  
**Ultimo aggiornamento**: 3 Febbraio 2026  
**Status**: ✅ COMPLETED  
**Priorità**: P1  
**Dipendenze**: E2E test infrastructure (completata)

---

## 🎯 Obiettivo

1. **Settings Page Mobile Layout** - Redesign per schermi piccoli
2. **Gallery Theme Support** - Screenshot light/dark con auto-switch
3. **Gallery Coverage** - Aggiungere screenshot mancanti
4. **MkDocs Gallery Pages** - Walkthrough completo con tutti gli screenshot

---

## 📊 Problemi Identificati

### 1. Settings Mobile Layout (CRITICO) - BUG-021

**Problema**: Su mobile (viewport < 640px), il layout a 2 colonne (tabs + content) comprime troppo il contenuto. I controlli non sono visibili/usabili.

**Screenshot problemi**:

- Category dropdown nativo (`<select>`) ha rendering brutto su mobile
- Header "Preferenze Utente" con pulsanti va a capo in modo confuso
- Campi setting (label + controllo) si sovrappongono

**Soluzione proposta**:

- Dropdown custom per mobile (come DataTable rows selector)
- Layout verticale: titolo → pulsanti → contenuto
- Ogni setting su più righe se necessario

**File da modificare**:

- `frontend/src/routes/(app)/settings/+page.svelte`
- `frontend/src/lib/components/settings/SettingsLayout.svelte`
- `frontend/src/lib/components/settings/SettingSelect.svelte` (verifica)
- `frontend/src/lib/components/settings/SettingCurrency.svelte` (verifica)
- `frontend/src/lib/components/settings/SettingTheme.svelte` (verifica)
- `frontend/src/lib/components/settings/GlobalSettingsTab.svelte`

**Mockup comportamento**:

```
DESKTOP (>640px):           MOBILE (<640px):
┌─────┬────────────┐        ┌────────────────┐
│ Tab │  Content   │        │ [▼ Profile   ] │ <- Dropdown
│ Tab │            │        ├────────────────┤
│ Tab │            │        │    Content     │
│ Tab │            │        │    (100%)      │
└─────┴────────────┘        └────────────────┘
```

### 2. Gallery Theme Support

**Problema**: Screenshots solo in light mode, ma la docs supporta dark mode.

**Soluzione proposta**:

- Generare screenshot per ENTRAMBI i temi (light + dark)
- Salvare in struttura: `gallery/{viewport}/{lang}/{theme}/...`
- JavaScript nella gallery page che detecta tema e mostra immagini corrette

### 3. Gallery Coverage Gaps

**Screenshot mancanti**:

- Settings → Preferences tab (User Settings)
- Settings → About tab
- Password Change modal
- Error/Warning modals

### 4. MkDocs Gallery Walkthrough Incompleto

**Problema**: Le pagine `desktop.md` e `mobile.md` usano solo un sottoinsieme degli screenshot generati.

**Da aggiungere**:

- Tutti i screenshot auth (register empty, register filled)
- Tutti i tab settings
- Files (entrambi i tab)
- Brokers (list, detail, import modal)

---

## ✅ Completato in Sessioni Precedenti

### Infrastruttura Test

- [x] `freezeAnimations()` helper per screenshot consistenti (animazioni al 10%)
- [x] `db populate --force` automatico prima di gallery
- [x] Build check automatico prima di test E2E (`_ensure_frontend_build()`)
- [x] Viewport ridotto a 1280x720 per screenshot più leggibili
- [x] WebKit installato per test mobile

### Componenti Settings

- [x] `ProfileTab.svelte` - Righe responsive con `flex-col sm:flex-row`
- [x] `SettingsLayout.svelte` - Dropdown custom per mobile (sostituito select nativo)
- [x] `SettingSelect.svelte` - Layout 3 righe su mobile con allineamento a destra + CustomSelect
- [x] `SettingCurrency.svelte` - Layout 3 righe su mobile con allineamento a destra
- [x] `SettingTheme.svelte` - Layout 3 righe su mobile con allineamento a destra
- [x] `GlobalSettingsTab.svelte` - Layout 3 righe + dropdown custom mobile + CustomSelect per lingua
- [x] Traduzione `settings.category` aggiunta
- [x] `min-h-[28px]` e `min-h-[36px]` per evitare shift quando icone appaiono
- [x] Titolo e icone su stessa riga, sottotitolo sotto (evita shift)

### Gallery Structure

- [x] `mkdocs_src/docs/gallery/index.md` - Overview con cards Desktop/Mobile
- [x] `mkdocs_src/docs/gallery/desktop.md` - Walkthrough con language switcher
- [x] `mkdocs_src/docs/gallery/mobile.md` - Walkthrough mobile
- [x] Language switcher con layout 2x2 (responsive a 4x1)
- [x] Aggiunto a mkdocs.yml navigation
- [x] Card Gallery nella home page

### DB Populate ✅ COMPLETATO

- [x] Aggiunto `BrokerUserAccess` per associare broker a utenti
- [x] Aggiunto `brim_plugin_key` a tutti i broker
- [x] Aggiunto 3 nuovi broker: Directa SIM, eToro, Coinbase
- [x] Aggiunto 3 nuovi asset: Bitcoin, Ethereum, Tesla
- [x] Aggiunto transazioni per nuovi broker
- [x] Aggiunto price history per crypto (24/7, no weekend skip)
- [x] Gallery usa `TEST_ADMIN` invece di `TEST_USER`

### UI Components

- [x] `CustomSelect.svelte` - Select semplice senza ricerca per liste corte
- [x] Fix warning a11y: `<label>` → `<span>` per category selector
- [x] Bottone "Add Broker" nasconde testo su mobile, mostra solo +

---

## 📋 Piano di Implementazione

### Fase 1: Settings Mobile Layout (2h) ✅ COMPLETATA

#### 1.1 Creare dropdown custom per category selector ✅

Implementato in `SettingsLayout.svelte` e `GlobalSettingsTab.svelte`:
- Dropdown custom con click outside handling
- Icone category + chevron animato
- Background highlight per item selezionato
- Dark mode support

#### 1.2 Sistemare header layout mobile ✅

Implementato: Titolo e pulsanti separati verticalmente su mobile:
- Titolo + descrizione in div con `mb-3`
- Pulsanti in riga separata con `flex-wrap gap-2`

#### 1.3 Applicare stesse modifiche a GlobalSettingsTab ✅

- ✅ Aggiunto dropdown custom per category selector mobile
- ✅ Layout responsive per header (titolo + pulsanti in linea)
- ✅ Dark mode classes aggiunte a tutti gli elementi
- ✅ Lucchetto edit sempre visibile per admin
- ✅ Setting rows su 3 righe per mobile (`flex-col sm:flex-row`)

#### 1.4 Verificare e sistemare setting controls ✅

- ✅ `SettingSelect.svelte` - Layout 3 righe + allineamento destra (`self-end`)
- ✅ `SettingCurrency.svelte` - Layout 3 righe + allineamento destra
- ✅ `SettingTheme.svelte` - Layout 3 righe + allineamento destra
- ✅ `GlobalSettingsTab.svelte` - Layout 3 righe per tutti i tipi

### Fase 2: Gallery Theme Support (1.5h) ✅ COMPLETATA

#### 2.1 Modificare gallery.spec.ts per loop temi ✅

Implementato loop su `THEMES = ['light', 'dark']` per generare screenshot in entrambi i temi.

#### 2.2 Aggiornare screenshot() function ✅

Path aggiornato a: `{viewport}/{lang}/{theme}/{category}/{name}.png`

#### 2.3 Gallery pages usano tema MkDocs ✅

- Rimossi selettori tema inline dalle pagine
- Le immagini seguono il tema MkDocs (toggle ☀️/🌙 nell'header)
- MutationObserver per reagire ai cambi tema

### Fase 3: Gallery Coverage (1h) ✅ COMPLETATA

#### 3.1 Aggiungere test per screenshot mancanti ✅

Aggiunti test per:
- About tab (settings)
- Password change modal (settings)

#### 3.2 Aggiornare desktop.md e mobile.md ✅

- Aggiunte sezioni About e Password Change
- Aggiunte sezioni Files (static + brim)
- Aggiunte sezioni Brokers (detail + import modal)
- Language selector spostato nell'header MkDocs
- Creato `gallery-lang-selector.js` per dropdown lingua nell'header

### Fase 4: Fix Mobile Menu Screenshot ✅ COMPLETATA

Problema risolto navigando fresh alla pagina per ogni lingua invece di cercare di chiudere la sidebar.

Soluzione implementata:
- Ogni iterazione fa `page.goto('/dashboard')` fresco
- Questo garantisce che la sidebar sia chiusa prima di cambiare lingua
- Screenshot generati correttamente per tutte le 4 lingue

---

## ⏱️ Stima Tempi Aggiornata

| Fase       | Task                      | Tempo   | Status |
|------------|---------------------------|---------|--------|
| 1.1        | Dropdown custom mobile    | 45min   | ✅      |
| 1.2        | Header responsive         | 30min   | ✅      |
| 1.3        | GlobalSettingsTab         | 15min   | ✅      |
| 1.4        | Verifica setting controls | 15min   | ✅      |
| 2.1        | Gallery theme loop        | 30min   | ✅      |
| 2.2        | Screenshot path update    | 15min   | ✅      |
| 2.3        | Gallery pages theme JS    | 30min   | ✅      |
| 3.1        | New screenshot tests      | 30min   | ✅      |
| 3.2        | Update gallery pages      | 30min   | ✅      |
| 4          | Mobile menu fix           | 15min   | ✅      |
| **TOTALE** |                           | **~4h** | ✅      |

**Completato**: 4h (tutte le fasi)

---

## 🎯 Criteri di Successo

1. ✅ Settings page usabile su mobile (dropdown custom, layout verticale)
2. ✅ Gallery genera screenshot light + dark
3. ✅ Gallery pages mostrano tema corretto automaticamente (via MkDocs theme toggle)
4. ✅ Tutti i tab settings hanno screenshot (user-preferences, global-settings, about, password-modal)
5. ✅ `./dev.py test front all` passa (51/51)
6. ✅ `./dev.py mkdocs gallery` genera tutti gli screenshot senza errori (14 test desktop + 14 mobile = 28 test, ~224 screenshots)

---

## 📝 Note Tecniche

- Il tema MkDocs Material si controlla via `data-md-color-scheme` (`default` o `slate`)
- I PNG in gallery sono in `.gitignore`, verranno generati durante `mkdocs deploy`
- Per test mobile, WebKit è cross-platform (macOS/Linux/Windows)
- Dropdown custom deve gestire click outside per chiusura

---

## 🔗 File Correlati

- `frontend/src/lib/components/settings/SettingsLayout.svelte`
- `frontend/src/lib/components/settings/ProfileTab.svelte`
- `frontend/src/lib/components/settings/PreferencesTab.svelte`
- `frontend/src/lib/components/settings/GlobalSettingsTab.svelte`
- `frontend/src/lib/components/settings/AboutTab.svelte`
- `frontend/e2e/gallery.spec.ts`
- `mkdocs_src/docs/gallery/index.md`
- `mkdocs_src/docs/gallery/desktop.md`
- `mkdocs_src/docs/gallery/mobile.md`
- `mkdocs_src/docs/javascripts/gallery-lang-selector.js` (NEW)
