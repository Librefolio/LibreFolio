# Piano: Unificazione PreferencesTab e GlobalSettingsTab

**Data**: 20 Gennaio 2026  
**Ultimo aggiornamento**: 29 Gennaio 2026  
**Status**: ✅ QUASI COMPLETATO (manca solo Fase 5 Polish)

---

## Problema Attuale

I due componenti `PreferencesTab.svelte` e `GlobalSettingsTab.svelte` hanno:

- Logica simile ma duplicata
- Stili leggermente diversi (ora uniformati a bg-gray-50)
- Gestione azioni (Save/Undo/Reset) implementata due volte
- Nessun componente riutilizzabile condiviso

---

## Proposta: Creare Componenti Condivisi

### 1. `SettingField.svelte` - Componente Base per Singola Impostazione

```
Props:
- label: string
- hint?: string
- icon?: Component (lucide icon)
- isModified: boolean
- isLocked?: boolean (solo per GlobalSettings)
- onSave: () => void
- onUndo: () => void
- onReset: () => void

Slot:
- default: contenuto del campo (input, select, toggle, etc.)

Layout:
┌─────────────────────────────────────────────────────────┐
│ [icon] Label                           [Save][Undo][Reset]│
│ Hint text                                                │
│ ┌───────────────────────────────────────────────────────┐│
│ │ <slot /> - Campo personalizzato                       ││
│ └───────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2. `SettingsLayout.svelte` - Layout a Due Colonne

```
Props:
- categories: Array<{id, icon, labelKey}>
- selectedCategory: string
- hasChanges: boolean
- hasNonDefaults: boolean
- isLocked?: boolean
- onSaveAll: () => void
- onUndoAll: () => void
- onResetAll: () => void
- onToggleLock?: () => void

Layout:
┌──────────┬──────────────────────────────────────────────┐
│ All      │ Header con titolo e azioni bulk             │
│ Cat 1    │ [SaveAll] [UndoAll] [ResetAll] [Lock?]      │
│ Cat 2    │─────────────────────────────────────────────│
│ Cat 3    │ <slot /> - Lista di SettingField           │
└──────────┴──────────────────────────────────────────────┘
```

### 3. Componenti Input Specializzati (opzionali)

- `SettingToggle.svelte` - Toggle switch per boolean
- `SettingNumber.svelte` - Input numerico con unità
- `SettingSelect.svelte` - Dropdown select
- `SettingCurrency.svelte` - FuzzySelect per valuta
- `SettingLanguage.svelte` - Select per lingua
- `SettingTheme.svelte` - Radio buttons per tema

---

## Differenze Chiave tra i Tre Componenti

| Aspetto            | PreferencesTab            | GlobalSettingsTab                | Profile (NEW)                                     |
|--------------------|---------------------------|----------------------------------|---------------------------------------------------|
| Sorgente dati      | API `/settings/user`      | API `/settings/global`           | API `/users/me`                                   |
| Struttura dati     | Oggetto fisso (3 campi)   | Array dinamico da DB             | User object                                       |
| Lock/Unlock        | No                        | Sì (admin only)                  | No                                                |
| Tipi campo         | select, currency, radio   | toggle, number, select, currency | text, email, password modal, avatar upload        |
| Chi può modificare | Utente corrente           | Solo admin                       | Utente corrente                                   |
| Persistenza DB     | Sì (API write)            | Sì (API write)                   | Sì (API write)                                    |
| Persistenza client | Sì (tema in localStorage) | No                               | No                                                |
| Campi speciali     | Tema (client+server)      | Lock toggle                      | Password (modal), Avatar (upload), Delete Account |

---

## Piano di Implementazione

### Fase 1: Creare Componenti Base (1.5 giorni) ✅ COMPLETATA

1. [x] Creare `SettingField.svelte` con tutte le prop necessarie (base wrapper)
2. [x] Creare `SettingsLayout.svelte` con sidebar e header (layout 2 colonne)
3. [x] Creare `SettingText.svelte` per username/email con inline edit ✅
4. [x] **Creare `SettingSelect.svelte`** per dropdown con azioni inline ✅ NUOVO
5. [x] **Creare `SettingCurrency.svelte`** per FuzzySelect con azioni inline ✅ NUOVO
6. [x] **Creare `SettingTheme.svelte`** per radio buttons con azioni inline ✅ NUOVO
7. [ ] **SettingImageUpload.svelte**: ⏳ RIMANDATO a Image Crop Plan (plan-image-crop.md)
8. [x] Testare (0 errors, 0 warnings ✅)

**Componenti creati in `frontend/src/lib/components/settings/`**:

- `SettingsLayout.svelte` - Layout 2 colonne (sidebar + content)
- `SettingField.svelte` - Base wrapper con slot
- `SettingText.svelte` - Inline text edit
- `SettingSelect.svelte` - Dropdown con azioni
- `SettingCurrency.svelte` - FuzzySelect con azioni
- `SettingTheme.svelte` - Radio buttons con azioni

### Fase 2: Refactor PreferencesTab (1 giorno) ✅ COMPLETATA

1. [x] Usare `SettingsLayout` per struttura
2. [x] Usare `SettingSelect` per lingua
3. [x] Usare `SettingCurrency` per valuta
4. [x] Usare `SettingTheme` per tema
5. [x] Gestire caso speciale tema (localStorage + API)
6. [x] Verificare funzionamento completo (0 errors, 0 warnings)
7. [x] **Stile allineato a GlobalSettingsTab** (azioni inline con icone)

**Risultato**: UI identica a GlobalSettingsTab, componenti riutilizzabili

### Fase 3: Refactor GlobalSettingsTab (0.5 giorni) ⏭️ SALTATA

**Decisione**: GlobalSettingsTab è già ben strutturato (688 righe) e lo abbiamo usato come riferimento per creare i componenti unificati. Refactorarlo non porterebbe benefici
significativi dato che:

- Ha settings dinamiche dal DB (tipi diversi: bool, int, str)
- Gestisce lock/unlock complesso
- Funziona correttamente

**Azione**: Skip to Fase 4, eventuale refactor in futuro se necessario.

### Fase 4: Creare Profile Page (1.5 giorni) ✅ COMPLETATA

1. [x] **Fix API PreferencesTab**: PUT invece di PATCH, campi corretti (language, base_currency)
2. [x] **PasswordChangeModal**: Modale per cambio password (dark mode supportato)
3. [x] **ProfileTab dark mode**: Supporto tema scuro
4. [x] **Backend API update_profile**: PUT /auth/profile per username/email
    - Schema: `UpdateProfileRequest`, `UpdateProfileResponse`
    - Service: `user_service.update_profile()` con validazione uniqueness
    - Tests: `test_services/test_user_profile.py`, `test_api/test_profile_api.py`
5. [x] **Account Section Frontend**:
    - [x] Username - Input con Save/Undo icons a sinistra quando modificato
    - [x] Email - Input con Save/Undo icons a sinistra quando modificato
    - [ ] Avatar - `SettingImageUpload` con crop 1:1 (⏳ rimandato a plan-image-crop.md)
    - [x] Account created - readonly, formatted date
6. [x] **Security Section**:
    - [x] Change Password - Bottone che apre modale
    - [x] Delete Account - Bottone danger con conferma (digita username)
        - Backend DELETE `/auth/users/me` + test API + test service
        - Valida che non si può eliminare l'unico superuser
7. [x] **Layout uniformato**:
    - Header con Save All / Undo All (stile GlobalSettingsTab)
    - Campi evidenziati in amber quando modificati
    - Save/Undo icons a sinistra del campo (non s/n a destra)
    - Debug logging aggiunto

### Fase 5: Polish e Test (0.5 giorni) 📋 DA FARE

1. [ ] Verificare dark mode in tutti e tre (Settings, GlobalSettings, Profile)
2. [ ] Verificare responsive su mobile
3. [ ] Verificare accessibilità (tab navigation, aria labels)
4. [ ] Cleanup codice duplicato residuo
5. [ ] **Dark mode mkdocs**: Allineare colori documentazione con frontend (vedi bug list)

**Nota**: La Fase 5 è rimasta in sospeso, ma le funzionalità core sono complete.

---

## Alternative Considerate

### A) Mantenere Separati (Status Quo)

- Pro: Nessun refactoring necessario
- Contro: Codice duplicato, difficile mantenere consistenza

### B) Un Solo Componente Parametrizzato

- Pro: Massima riusabilità
- Contro: Troppo complesso, troppe condizioni

### C) Componenti Condivisi (Proposta) ✅

- Pro: Bilanciato tra riuso e semplicità
- Pro: Flessibile per future estensioni
- Contro: Richiede lavoro iniziale

---

## File da Creare/Modificare

| File                                                    | Descrizione                  |
|---------------------------------------------------------|------------------------------|
| `src/lib/components/settings/SettingField.svelte`       | Campo singolo con azioni     |
| `src/lib/components/settings/SettingsLayout.svelte`     | Layout 2 colonne             |
| `src/lib/components/settings/SettingToggle.svelte`      | Toggle boolean               |
| `src/lib/components/settings/SettingNumber.svelte`      | Input numerico               |
| `src/lib/components/settings/SettingText.svelte`        | Text/email con edit inline   |
| `src/lib/components/settings/SettingImageUpload.svelte` | Upload con crop/resize       |
| `src/routes/(app)/profile/+page.svelte`                 | Nuova pagina profilo         |
| `src/lib/components/profile/PasswordChangeModal.svelte` | Modale cambio password       |
| `src/lib/components/profile/DeleteAccountModal.svelte`  | Modale cancellazione account |

---

## Domande per Review

1. **Granularità componenti**: ✅ **RISOLTO** - Creare componenti condivisi e montarli secondo necessità

2. **Persistenza**: ✅ **CHIARITO** - Entrambe le pagine scrivono su DB via API. PreferencesTab scrive ANCHE il tema su localStorage per applicazione immediata

3. **Gestione stato**: ✅ **DECISO** - Stato locale nei componenti, massima flessibilità per riutilizzo futuro

4. **Validazione**: ✅ **DECISO** - Validazione a livello componente quando possibile, parent override dove necessario (approccio flessibile)

5. **Animazioni transizioni**: ✅ **DECISO** - Nessuna animazione eccetto il click del pulsante e la sua comparsa/scomparsa in base a se serve/non serve.

6. **Image Crop**: ✅ **DECISO** - Implementare crop avanzato (libreria), massima estensibilità per futuro (vedi plan-image-crop.md)

---

## Stima Tempo Totale

- **Ottimistico**: 4 giorni (componenti base + refactor + profile + crop)
- **Realistico**: 6 giorni
- **Con imprevisti**: 8 giorni

---

**Status**: 📋 IN PROGRESS - Decisioni chiave prese, implementazione da iniziare
**Blockers**: Nessuno - Piano pronto per esecuzione
