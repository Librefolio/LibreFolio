# Plan: Phase 6 Step 3 — Round 8: AssetModal Fix + Bulk Delete Rewrite

Post Round 7. Integra le nuove richieste utente:
- Fix cosmetica icona modale add asset
- Duplicate name detection on-demand con Tooltip
- Chiarimento edit-mode ScheduledInvestmentEditor (input JSON)
- Riscrittura bulk delete per selezione non contigua con spartiacque multipli
- Ristrutturazione: `ui_component` dentro `params_schema`, non come campo separato

---

## §0 — Relazione Round 6 / Round 7 (chiarimento)

| Documento | Ruolo | Contenuto |
|-----------|-------|-----------|
| **Round 6** (`plan-phase06Step3Round6-LayoutPolish.prompt.md`) | Piano completo F1–F9 | F1–F8 definitivi + F9 come bozza con scelte aperte (layout α vs β, late interest inline vs separato) |
| **Round 7** (`plan-phase06Step3Round7-F9ScheduledInvestmentEditor.prompt.md`) | **Sostituzione integrale della sezione F9** | Dettaglio aggiornato F9 con le scelte dell'utente: Layout β, late interest permanente, contiguità automatica, CRUD avanzato §9.1–§9.12 |

**Round 7 NON è un piano separato** — è l'aggiornamento autoritativo della sola sezione F9 di Round 6.
Le sezioni F1–F8 di Round 6 restano invariate e autoritative.

**Questo Round 8** parte da Round 7 come base per F9 e aggiunge modifiche puntuali.

---

## Stato esecuzione F1–F8 + Round 8

| # | Item | Stato | Note |
|---|------|-------|------|
| F1 | SimpleSelect dropdown `position:fixed` | ✅ DONE | Dropdown non più troncato da overflow parent |
| F2 | "Other" in fondo alle distribuzioni | ✅ DONE | Sort secondario `key === 'Other'` → always last |
| F3 | Paginazione ∞ nelle distribuzioni | ✅ DONE | `pageSizeOptions={[5, 10, 25, 0]}` |
| F4 | Tooltip history: mostrare valuta | ✅ DONE | Propaga `priceCurrency` dal current_price alla history |
| F6 | Rimuovere bottoni "Remove" esterni | ✅ DONE | BrokerForm + ProfileTab: rimossi bottoni + modale ridondanti |
| F6.1 | Fix IDE error ProviderAssignmentSection | ✅ DONE | `e.target as HTMLInputElement` → `e.currentTarget` |
| §1 | Icona centrata in AssetModal | ✅ DONE | `items-start` → `items-center` |
| §2 | Duplicate name detection | ✅ DONE | $effect debounced + warning con Tooltip + i18n 4 lingue |
| F8 | `accepted_identifier_types` per provider | ✅ DONE | Backend (base+5 provider+schema+endpoint) + Frontend (filtered select + auto-set) |
| F8b | Ristruttura `ui_component` dentro `params_schema` | ✅ DONE | Rimosso da FAProviderInfo, usa tipo speciale in params_schema |
| F7 | Fetch Interval HH:MM | ✅ DONE | |
| F5 | Layout B Two-Panel + wrap | 🔲 TODO | |
| F9 | ScheduledInvestmentEditor | 🔲 TODO | Piano dettagliato in Round 7 |
| §3 | Edit mode chiarimento | 🔲 N/A | Solo specifica, implementato con F9 |
| §5 | Bulk delete multi-gap | 🔲 TODO | Vedi §5 sotto — parte di F9 |

---

## §1 — Fix: Icona centrata verticalmente in AssetModal ✅ DONE

`AssetModal.svelte` L862: `items-start` → `items-center`.

---

## §2 — Feature: Duplicate Name Detection ✅ DONE

- $effect debounced (400ms) su `displayName` → query API per match esatto
- Warning arancione sotto input nome con `Tooltip.svelte`
- i18n chiavi `duplicateNameWarning` + `duplicateNameTooltip` in EN/IT/FR/ES
- Reset in `resetForm()` e `populateFromEditData()`

---

## §3 — ScheduledInvestmentEditor: Edit mode (chiarimento)

Specifica: il componente `ScheduledInvestmentEditor.svelte` accetta `value: Record<string, any> | null`.
- `null` / `{}` → Create mode (tabella vuota)
- `{ schedule: [...], late_interest: {...} }` → Edit mode (deserializza e popola)

Implementato come parte di F9.

---

## §4 — Conferme invarianti da Round 7 ✅

- Merge solo se righe contigue (Round 7 §9.7.4)
- Tabella sempre in ordine temporale (`enableSorting: false`)

---

## §5 — Bulk Delete con spartiacque multipli (aggiornamento Round 7 §9.7.5)

### Problema

Round 7 §9.7.5 tratta la selezione come blocco potenzialmente contiguo.
L'utente vuole supportare **selezione non contigua** con spartiacque multipli.

### Esempio

10 periodi, seleziono il 2°, 4°, 5° e 8°:

```
Periodo:  [1]  [2]  [3]  [4]  [5]  [6]  [7]  [8]  [9]  [10]
Stato:     ·   DEL   ·   DEL  DEL   ·    ·   DEL   ·    ·
Gruppi:         G1        ──G2──              G3
```

3 buchi → 3 spartiacque (ognuno tra il sopravvivente prima e dopo).

### Algoritmo

1. `groupContiguousIndices(indices)` → raggruppa in blocchi contigui
2. Ogni blocco MIDDLE (ha sopravvivente prima E dopo) → modale spartiacque
3. Blocchi HEAD/TAIL → auto-espansione, nessuna modale
4. Tutti eliminati → empty state

### BoundaryDateModal multi-step

Se N > 1 gap da risolvere → modale mostra N sezioni con DatePicker vincolati.
Conferma unica "Confirm Delete" applica tutti gli spartiacque.

Implementato come parte di F9.

---

## §6 — Ristrutturazione: `ui_component` dentro `params_schema` ✅ DONE

### Decisione di design

| Campo | Dove va | Motivazione |
|-------|---------|-------------|
| `accepted_identifier_types` | `FAProviderInfo` (top-level) | È metadata del provider, come `supports_search`. Non c'entra con params. |
| `ui_component` | **Dentro `params_schema`** come campo speciale | Descrive *come renderizzare* i params → stessa responsabilità di `params_schema` |

### Come funziona

`scheduled_investment.py` `params_schema`:
```python
[{"key": "_ui_component", "type": "ui_component", "required": False,
  "description": "Custom editor", "default": "scheduled_investment"}]
```

Frontend: se trovo campo con `type === 'ui_component'` → uso quel componente,
altrimenti genero form generico. I campi `ui_component` sono filtrati dal loop generico.

---

## Ordine di esecuzione rimanente

| # | Item | Effort |
|---|------|--------|
| 1 | F5 — Layout B Two-Panel + wrap | 35 min |
| 2 | F9 — ScheduledInvestmentEditor (incl. §3, §5 bulk delete) | 150 min |

---

## Validation Checklist (Round 8)

- [x] F1: SimpleSelect dropdown non troncato
- [x] F2: Distribution "Other" sempre in fondo
- [x] F3: Paginazione distribution ha opzione ∞
- [x] F4: Tooltip history mostra valuta
- [x] F6: No bottone "Remove" esterno (BrokerForm + ProfileTab)
- [x] F6.1: Fix IDE error ProviderAssignmentSection
- [x] §1: Icona centrata verticalmente
- [x] §2: Duplicate name detection + Tooltip + i18n
- [x] F8: `accepted_identifier_types` backend + frontend filtering + auto-set
- [x] §6: `ui_component` dentro params_schema, rimosso da FAProviderInfo
- [x] F7: Fetch Interval HH:MM
- [ ] F5: Layout B Two-Panel
- [ ] F9: ScheduledInvestmentEditor completo
- [ ] §5: Bulk delete multi-gap (parte di F9)
