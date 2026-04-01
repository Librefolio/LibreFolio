# Checklist Test — F9 ScheduledInvestmentEditor: Merge, Split & CRUD

Data: 2026-03-31  
Stato: PARZIALMENTE COMPLETATO (Round 9 fix applicati)

---

## Setup Prerequisiti
- [x] Navigare alla pagina asset con provider `Scheduled Investment`
- [x] Verificare che l'editor tabellare appaia correttamente

---

## 1. Add Period

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 1.1 | Click "Add Period" da stato vuoto | Prima riga creata, start=oggi, end=+1 mese. Empty state scompare. |  |
| 1.2 | Click "Add Period" con righe esistenti | Nuova riga con start = ultimo end_date + 1 giorno |  |
| 1.3 | Verificare che la nuova riga copi config dall'ultima (rate, compounding, day_count) | Stessi valori dell'ultima riga |  |
| 1.4 | Click "Add Period" su mobile (< sm) | Bottone mostra solo icona "+" senza label |  |

---

## 2. Delete (singola riga)

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 2.1 | Delete prima riga (2+ righe) | La seconda riga espande il suo start_date al start della riga cancellata | ✅ |
| 2.2 | Delete ultima riga (2+ righe) | La penultima riga espande il suo end_date all'end della riga cancellata | ✅ |
| 2.3 | Delete riga centrale (3+ righe) | **Modale BoundaryDate** appare con min=start e max=end della riga da eliminare | ✅ |
| 2.4 | Modale delete: conferma con data di confine | La riga precedente prende end=boundary, la successiva prende start=boundary+1 | ✅ |
| 2.5 | Modale delete: cancel | Nessuna modifica |  |
| 2.6 | Delete unica riga rimasta | Empty state riappare |  |

---

## 3. Split (row action)

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 3.1 | Click ✂️ Split su riga con ≥2 giorni | **Modale BoundaryDate** in modalità "split" appare | ✅ |
| 3.2 | Modale split: conferma con data midpoint | 2 righe identiche: riga1.end=boundary, riga2.start=boundary+1, stessa config | ✅ |
| 3.3 | Modale split: conferma con data = min | Prima riga ha 1 solo giorno (min_date), seconda il resto |  |
| 3.4 | Modale split: conferma con data = max | Prima riga ha tutto tranne ultimo giorno, seconda ha 1 giorno |  |
| 3.5 | Modale split: cancel | Nessuna modifica |  |
| 3.6 | Split su riga con esattamente 1 giorno | Bottone Split disabilitato |  |

---

## 4. Merge (bulk action)

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 4.1 | Selezionare 2 righe contigue → click Merge | Una riga unica con start=prima.start, end=ultima.end, config=prima riga | ✅ |
| 4.2 | Selezionare 3+ righe contigue → Merge | Una riga unica che copre l'intero range | ✅ |
| 4.3 | Selezionare 2 righe NON contigue | Bottone Merge disabilitato (grigio) |  |
| 4.4 | Selezionare 1 sola riga | Merge non appare / disabilitato (serve almeno 2) |  |
| 4.5 | Dopo merge, verificare contiguità con righe adiacenti | Nessun gap o overlap |  |

---

## 5. Bulk Delete

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 5.1 | Selezionare tutte le righe → Bulk Delete | Empty state. Nessuna modale. |  |
| 5.2 | Selezionare prima riga + seconda → Bulk Delete | Terza riga espande start_date indietro |  |
| 5.3 | Selezionare ultime 2 righe → Bulk Delete | Riga precedente espande end_date in avanti |  |
| 5.4 | Selezionare righe centrali (blocco nel mezzo) → Bulk Delete | **Modale BoundaryDate** appare per blocco nel mezzo |  |
| 5.5 | Modale bulk delete: conferma | Riga prima del blocco.end=boundary, riga dopo.start=boundary+1 |  |
| 5.6 | Selezione non contigua (es. 2°, 5°, 8°) → Bulk Delete | **Modale multi-gap** con N sezioni, conferma unica | 🔲 da testare |

---

## 6. Contiguità Automatica (DateRangePicker)

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 6.1 | Allargare end_date di una riga verso destra | La riga successiva riduce il suo start_date a end+1 | ✅ |
| 6.2 | Ridurre start_date di una riga verso sinistra | La riga precedente espande il suo end_date a start-1 | ✅ |
| 6.3 | Espandere una riga così tanto da "mangiare" la successiva | La riga successiva viene eliminata automaticamente | ✅ |
| 6.4 | Modificare date della prima riga verso sinistra | Nessun effetto sulle altre righe (solo la prima si estende) |  |
| 6.5 | Modificare date dell'ultima riga verso destra | Nessun effetto sulle altre righe |  |

---

## 7. Late Interest

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 7.1 | Toggle late interest ON | Riga speciale appare in fondo con stile "⚡ Late" |  |
| 7.2 | Toggle late interest OFF | Riga si opacizza (grayed out) |  |
| 7.3 | Modificare grace days nel popover | Valore aggiornato nel display "(+Nd grace → ∞)" | ✅ (fix Round 9) |
| 7.4 | Late interest row NON selezionabile | Checkbox non presente o non funzionante |  |

---

## 8. Validazione & Status Banner

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 8.1 | Stato vuoto (0 periodi) | Banner "📅 No interest periods defined" |  |
| 8.2 | 1+ periodi, tutti validi | Banner "✅ N periods, contiguous — date → date (X days)" |  |
| 8.3 | Rate negativo | Form invalid (se c'è validazione visuale) |  |
| 8.4 | Compounding=COMPOUND ma frequency vuota | Form invalid |  |

---

## 9. UI/UX

| # | Test | Atteso | ✅/❌ |
|---|------|--------|------|
| 9.1 | DateRangePicker si chiude cliccando fuori | ✅ (fix backdrop overlay) | ✅ |
| 9.2 | DateRangePicker si chiude scrollando la pagina | ✅ (fix scroll listener) | ✅ |
| 9.3 | Info icons sugli header delle colonne cliccabili | Si apre la pagina doc in nuovo tab |  |
| 9.4 | Toolbar bulk appare a destra accanto a "Add Period" | Stessa riga, allineata a destra | ✅ (fix Round 9) |
| 9.5 | Su mobile, bottoni toolbar/add mostrano solo icone | Label nascosta sotto sm breakpoint |  |
| 9.6 | Serializzazione JSON corretta dopo ogni operazione | Verificare con console.log o network tab |  |
| 9.7 | Tooltip colonne: testo normale, multi-riga, non uppercase | Leggibile e informativo | ✅ (fix Round 9) |
| 9.8 | SimpleSelect day_count: dropdown sopra azioni riga | z-index corretto | ✅ (fix Round 9) |
| 9.9 | DateRangePicker: zero errori IDE | Nessun warning/error | ✅ (fix Round 9) |

---

## Note
- Per testare merge/split servono almeno 3 periodi
- Ordine consigliato: Add 3 periodi → test Split → test Merge → test Delete → test Bulk Delete
- Verificare sempre la contiguità dei range dopo ogni operazione
- **Round 9**: fix bulk delete multi-gap (test 5.6), grace period click, z-index, tooltip, toolbar alignment
