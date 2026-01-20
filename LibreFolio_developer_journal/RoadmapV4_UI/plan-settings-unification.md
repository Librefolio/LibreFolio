# Piano: Unificazione PreferencesTab e GlobalSettingsTab

**Data**: 20 Gennaio 2026  
**Status**: 📋 DA REVIEW

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

| Aspetto | PreferencesTab | GlobalSettingsTab | Profile (NEW) |
|---------|---------------|-------------------|---------------|
| Sorgente dati | API `/settings/user` | API `/settings/global` | API `/users/me` |
| Struttura dati | Oggetto fisso (3 campi) | Array dinamico da DB | User object |
| Lock/Unlock | No | Sì (admin only) | No |
| Tipi campo | select, currency, radio | toggle, number, select, currency | text, email, password modal, avatar upload |
| Chi può modificare | Utente corrente | Solo admin | Utente corrente |
| Persistenza DB | Sì (API write) | Sì (API write) | Sì (API write) |
| Persistenza client | Sì (tema in localStorage) | No | No |
| Campi speciali | Tema (client+server) | Lock toggle | Password (modal), Avatar (upload), Delete Account |

---

## Piano di Implementazione

### Fase 1: Creare Componenti Base (1.5 giorni) ✅ COMPLETATA
1. [x] Creare `SettingField.svelte` con tutte le prop necessarie
2. [x] Creare `SettingsLayout.svelte` con sidebar e header
3. [ ] Creare `SettingImageUpload.svelte` per avatar/icon con crop/resize (dipende da Image Crop plan)
4. [ ] Creare `SettingText.svelte` per username/email con inline edit
5. [x] Testare con un esempio isolato (0 errors, 1 warning)

### Fase 2: Refactor GlobalSettingsTab (0.5 giorni)
1. [ ] Usare `SettingsLayout` per struttura
2. [ ] Usare `SettingField` per ogni impostazione
3. [ ] Mantenere logica lock/unlock esistente
4. [ ] Verificare funzionamento completo

### Fase 3: Refactor PreferencesTab (0.5 giorni)
1. [ ] Usare `SettingsLayout` per struttura (senza lock)
2. [ ] Usare `SettingField` per ogni impostazione
3. [ ] Gestire caso speciale tema (localStorage + API)
4. [ ] Verificare funzionamento completo

### Fase 4: Creare Profile Page (1.5 giorni)
1. [ ] **Account Section**:
   - [ ] Username - `SettingText` con edit inline
   - [ ] Email - `SettingText` con edit inline  
   - [ ] Avatar - `SettingImageUpload` con crop 1:1
   - [ ] Account created - readonly, formatted date
2. [ ] **Security Section**:
   - [ ] Change Password - Bottone che apre modale
     - Modale con: current password, new password, confirm new password
     - Password strength indicator (zxcvbn-ts)
     - Cancel e Save buttons nella modale
     - ⚠️ **IMPORTANTE**: Password change NON attiva Save/Undo globali
   - [ ] Delete Account - Bottone danger sotto Security
     - Modale conferma con input "Type username to confirm"
     - Backend valida che esistano altri utenti (e altri superuser se utente è superuser)
     - API DELETE `/users/me`
     - ⚠️ **IMPORTANTE**: Delete Account NON attiva Save/Undo globali
3. [ ] **Layout**: Save/Undo/Reset globali ATTIVI
   - Username/Email/Avatar modifiche rimangono nel browser
   - Save globale o specifico per campo per salvare
   - Password e Delete Account sono ESCLUSI dal sistema Save globale (hanno modali separate)

### Fase 5: Polish e Test (0.5 giorni)
1. [ ] Verificare dark mode in tutti e tre
2. [ ] Verificare responsive
3. [ ] Verificare accessibilità
4. [ ] Cleanup codice duplicato

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

| File | Descrizione |
|------|-------------|
| `src/lib/components/settings/SettingField.svelte` | Campo singolo con azioni |
| `src/lib/components/settings/SettingsLayout.svelte` | Layout 2 colonne |
| `src/lib/components/settings/SettingToggle.svelte` | Toggle boolean |
| `src/lib/components/settings/SettingNumber.svelte` | Input numerico |
| `src/lib/components/settings/SettingText.svelte` | Text/email con edit inline |
| `src/lib/components/settings/SettingImageUpload.svelte` | Upload con crop/resize |
| `src/routes/(app)/profile/+page.svelte` | Nuova pagina profilo |
| `src/lib/components/profile/PasswordChangeModal.svelte` | Modale cambio password |
| `src/lib/components/profile/DeleteAccountModal.svelte` | Modale cancellazione account |

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
