# Plan: Settings Mobile Layout + Gallery Improvements

**Data creazione**: 2 Febbraio 2026  
**Ultimo aggiornamento**: 2 Febbraio 2026  
**Status**: 🔄 IN PROGRESS  
**Priorità**: P1  
**Dipendenze**: E2E test infrastructure (completata)

---

## 🎯 Obiettivi

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

## ✅ Lavoro Già Completato

### Infrastruttura

- [x] `freezeAnimations()` helper per screenshot consistenti (animazioni al 10%)
- [x] `db populate --force` automatico prima di gallery
- [x] Build check automatico prima di test E2E (`_ensure_frontend_build()`)
- [x] Viewport ridotto a 1280x720 per screenshot più leggibili
- [x] WebKit installato per test mobile

### Componenti Settings

- [x] `ProfileTab.svelte` - Righe responsive con `flex-col sm:flex-row`
- [x] `SettingsLayout.svelte` - Dropdown category su mobile (select nativo - da migliorare)
- [x] Traduzione `settings.category` aggiunta

### Gallery Structure

- [x] `mkdocs_src/docs/gallery/index.md` - Overview con cards Desktop/Mobile
- [x] `mkdocs_src/docs/gallery/desktop.md` - Walkthrough con language switcher
- [x] `mkdocs_src/docs/gallery/mobile.md` - Walkthrough mobile
- [x] Language switcher con layout 2x2 (responsive a 4x1)
- [x] Aggiunto a mkdocs.yml navigation
- [x] Card Gallery nella home page

---

## 📋 Piano di Implementazione

### Fase 1: Settings Mobile Layout (2h) 🔄 IN CORSO

#### 1.1 Creare dropdown custom per category selector ⏳

Riferimento: DataTable rows selector (`DataTablePagination.svelte`)

```svelte
<!-- In SettingsLayout.svelte -->
<!-- Sostituire <select> nativo con dropdown custom -->
<div class="sm:hidden mb-4 relative">
    <button on:click={toggleDropdown} class="...">
        {selectedCategoryLabel}
        <ChevronDown />
    </button>
    {#if isDropdownOpen}
        <div class="absolute z-50 bg-white shadow-lg rounded-lg ...">
            {#each categories as cat}
                <button on:click={() => selectCategory(cat.id)}>
                    <svelte:component this={cat.icon} />
                    {$_(cat.labelKey)}
                </button>
            {/each}
        </div>
    {/if}
</div>
```

#### 1.2 Sistemare header layout mobile ⏳

Problema: Titolo e pulsanti sulla stessa riga causano wrap confuso.

Soluzione:

```svelte
<!-- Mobile: stack verticalmente -->
<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
    <div>
        <h3>{title}</h3>
        <p>{description}</p>
    </div>
    <!-- Pulsanti su riga separata su mobile -->
    <div class="flex items-center space-x-1 justify-end">
        <!-- Save, Undo, Reset, Lock buttons -->
    </div>
</div>
```

#### 1.3 Applicare stesse modifiche a GlobalSettingsTab ⏳

- Verificare che usi SettingsLayout (sì, lo usa)
- Verificare che lucchetto edit sia visibile
- Testare visivamente

#### 1.4 Verificare setting controls ⏳

- `SettingSelect.svelte` - dropdown lingua
- `SettingCurrency.svelte` - FuzzySelect valuta
- `SettingTheme.svelte` - toggle tema

### Fase 2: Gallery Theme Support (1.5h) ⏳

#### 2.1 Modificare gallery.spec.ts per loop temi

```typescript
const THEMES = ['light', 'dark'] as const;

async function setTheme(page: Page, theme: 'light' | 'dark') {
    await page.getByTestId('theme-toggle').click();
    // Verificare che il tema sia cambiato
}

// Struttura path: {viewport}/{lang}/{theme}/{category}/{name}.png
```

#### 2.2 Aggiornare screenshot() function

```typescript
function getGalleryPath(
    viewport: 'desktop' | 'mobile',
    lang: Language,
    theme: 'light' | 'dark',
    category: string
): string {
    return path.join(GALLERY_ROOT, viewport, lang, theme, category);
}
```

#### 2.3 Aggiornare gallery pages per theme detection

```javascript
// Detect MkDocs Material theme
const isDark = document.documentElement.getAttribute('data-md-color-scheme') === 'slate';
const theme = isDark ? 'dark' : 'light';
// Update image src based on theme + language
```

### Fase 3: Gallery Coverage (1h) ⏳

#### 3.1 Aggiungere test per screenshot mancanti

```typescript
// Settings - tutti i tab
test('preferences tab - all languages', ...);
test('about tab - all languages', ...);

// Password change modal
test('password change modal - all languages', ...);
```

#### 3.2 Aggiornare desktop.md e mobile.md

Aggiungere sezioni per:

- Register empty + filled (già generati)
- All settings tabs
- Password change modal
- Files tabs
- Brokers (list, detail, import)

### Fase 4: Fix Mobile Menu Screenshot ⏳

Problema: Sidebar overlay intercetta click su language selector.

Opzioni:

1. Skip test (non critico per documentazione)
2. Chiudere sidebar prima di cambiare lingua (già provato, non funziona sempre)
3. Usare diversa strategia (screenshot solo in EN per mobile menu)

---

## ⏱️ Stima Tempi Aggiornata

| Fase       | Task                      | Tempo   | Status |
|------------|---------------------------|---------|--------|
| 1.1        | Dropdown custom mobile    | 45min   | ⏳      |
| 1.2        | Header responsive         | 30min   | ⏳      |
| 1.3        | GlobalSettingsTab         | 15min   | ⏳      |
| 1.4        | Verifica setting controls | 15min   | ⏳      |
| 2.1        | Gallery theme loop        | 30min   | ⏳      |
| 2.2        | Screenshot path update    | 15min   | ⏳      |
| 2.3        | Gallery pages theme JS    | 30min   | ⏳      |
| 3.1        | New screenshot tests      | 30min   | ⏳      |
| 3.2        | Update gallery pages      | 30min   | ⏳      |
| 4          | Mobile menu fix           | 15min   | ⏳      |
| **TOTALE** |                           | **~4h** |        |

---

## 🎯 Criteri di Successo

1. ✅ Settings page usabile su mobile (dropdown custom, layout verticale)
2. ⏳ Gallery genera screenshot light + dark
3. ⏳ Gallery pages mostrano tema corretto automaticamente
4. ⏳ Tutti i tab settings hanno screenshot
5. ✅ `./dev.py test front all` passa (51/51)
6. ⏳ `./dev.py mkdocs gallery` genera tutti gli screenshot senza errori

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
