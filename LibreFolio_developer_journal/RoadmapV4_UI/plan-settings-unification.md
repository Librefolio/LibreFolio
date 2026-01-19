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

## Differenze Chiave tra i Due Tab

| Aspetto | PreferencesTab | GlobalSettingsTab |
|---------|---------------|-------------------|
| Sorgente dati | API `/settings/user` | API `/settings/global` |
| Struttura dati | Oggetto fisso (3 campi) | Array dinamico da DB |
| Lock/Unlock | No | Sì (admin only) |
| Tipi campo | select, currency, radio | toggle, number, select, currency |
| Chi può modificare | Utente corrente | Solo admin |
| Persistenza | API + localStorage (tema) | Solo API |

---

## Piano di Implementazione

### Fase 1: Creare Componenti Base (1 giorno)
1. [ ] Creare `SettingField.svelte` con tutte le prop necessarie
2. [ ] Creare `SettingsLayout.svelte` con sidebar e header
3. [ ] Testare con un esempio isolato

### Fase 2: Refactor GlobalSettingsTab (0.5 giorni)
1. [ ] Usare `SettingsLayout` per struttura
2. [ ] Usare `SettingField` per ogni impostazione
3. [ ] Mantenere logica lock/unlock esistente
4. [ ] Verificare funzionamento completo

### Fase 3: Refactor PreferencesTab (0.5 giorni)
1. [ ] Usare `SettingsLayout` per struttura (senza lock)
2. [ ] Usare `SettingField` per ogni impostazione
3. [ ] Gestire caso speciale tema (localStorage)
4. [ ] Verificare funzionamento completo

### Fase 4: Polish e Test (0.5 giorni)
1. [ ] Verificare dark mode in entrambi
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

## File da Creare

| File | Descrizione |
|------|-------------|
| `src/lib/components/settings/SettingField.svelte` | Campo singolo |
| `src/lib/components/settings/SettingsLayout.svelte` | Layout 2 colonne |
| `src/lib/components/settings/SettingToggle.svelte` | Toggle boolean |
| `src/lib/components/settings/SettingNumber.svelte` | Input numerico |

---

## Domande per Review

1. **Granularità componenti**: Creare anche i componenti input specializzati (Toggle, Number, etc.) o usare direttamente HTML nei tab?

2. **Gestione stato**: Centralizzare in un store Svelte o mantenere stato locale nei tab?

3. **Validazione**: Aggiungere validazione a livello di `SettingField` o mantenerla nei tab parent?

4. **Animazioni**: Aggiungere transizioni per le azioni (save success, error)?

---

## Stima Tempo Totale

- **Ottimistico**: 2 giorni
- **Realistico**: 3 giorni
- **Con imprevisti**: 4 giorni

---

**Attendo review prima di procedere.**
