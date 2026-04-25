# Manual Walkthrough — Phase 7 Part 4 (`/transactions`)

> Da seguire a mano (non Playwright). L'obiettivo è raccogliere impressioni
> UX/touch-and-fill sulla pagina TX e modali, con focus su: ergonomia degli
> input, leggibilità della tabella, predisposizione al raffinamento.
>
> Per ogni step:
> - ✅ se "ok come è"
> - ⚠️ se "funziona ma migliorabile" → annota
> - ❌ se "rotto/inaccettabile" → annota e passa oltre
>
> Annotazioni libere alla fine di ogni sezione (campo `Note`).

---

## 0. Setup

Avvia backend (test mode con dati mock già popolati) + frontend dev:

```bash
./dev.py db create-clean              # solo se vuoi DB pulito (rigenera mock)
./dev.py server start --port 8000     # backend
./dev.py front dev                    # frontend Vite (http://localhost:5173)
```

Login con `e2e_test_user` / `E2eTestPass123!` (utente normale) — ti serve
almeno **2 broker** con qualche transazione, idealmente con **almeno una
linked pair** (TRANSFER o FX_CONVERSION) e **almeno un DIVIDEND con
asset_event_id**. Se mancano, vedi "Mock data gaps" in fondo.

Apri http://localhost:5173/transactions

---

## 1. Header + first impression

| | Check | Esito |
|--|--|--|
| 1.1 | La pagina si apre senza errori in console? | |
| 1.2 | I bottoni `Import` e `Add Transaction` sono visibili e ben allineati? | |
| 1.3 | L'icona del titolo / sottotitolo sono coerenti col resto dell'app (`/assets`, `/fx`)? | |
| 1.4 | Cliccando `Import` cosa succede? (atteso: console warning — è un TODO Step 10 noto) | |

**Note**: _________

---

## 2. Tabella — first read

| | Check | Esito |
|--|--|--|
| 2.1 | Le righe caricano? `data-testid="tx-table"` deve essere presente. | |
| 2.2 | La **color band** a sinistra (4px) cambia colore per broker diversi? Le tinte sono distinguibili? | |
| 2.3 | Il **broker badge** in coda riga ha la stessa tinta della band? Leggibile in light + dark? | |
| 2.4 | I **type badge** (BUY, SELL, DIVIDEND, …) hanno l'icona PNG + label localizzata corretta? | |
| 2.5 | Cambia lingua (settings → IT/FR/ES): i type badge si traducono? | |
| 2.6 | Il **display name** dell'asset è popolato (non `#42`)? | |
| 2.7 | Quantity: i segni sono leggibili? (`+10.00`, `-5.00`, `0`) | |
| 2.8 | Cash: il formato `+€1,050.00 EUR` / `-$50.00 USD` è coerente? Currency code accanto leggibile? | |
| 2.9 | Tags column è popolata e separa con virgola in caso di multi-tag? | |

**Note**: _________

---

## 3. Always-pair-adjacent + ghost rows

Prerequisito: avere almeno una **linked pair** (TRANSFER o FX_CONVERSION).

| | Check | Esito |
|--|--|--|
| 3.1 | Le 2 righe della pair sono **sempre adiacenti** in ogni ordering? Prova a cambiare sort (date asc/desc, quantity asc/desc). | |
| 3.2 | La row "giver" (out) è **sopra** la "receiver" (in)? La receiver mostra `↳` come prefisso quantity? | |
| 3.3 | Filtra per un solo broker tale che il partner esca dal filtro: appare la **ghost row viola tenue** con chip "ghost"? | |
| 3.4 | Toggle dark mode: la ghost row resta distinguibile? | |
| 3.5 | La ghost row è **selezionabile** (checkbox cliccabile)? | |

**Note**: _________

---

## 4. GoTo (link icon 🔗)

| | Check | Esito |
|--|--|--|
| 4.1 | Le righe linked mostrano l'icona 🔗 in colonna `links`? | |
| 4.2 | Click sull'icona: il partner scrolla in vista (smooth) e ha un **pulse violetto** per ~1.4s? | |
| 4.3 | Dopo il pulse l'URL **non** mostra `?highlight_id=…` persistente (auto-clear dopo 1.6s)? | |
| 4.4 | Funziona anche quando il partner è una **ghost row**? | |
| 4.5 | Apri direttamente l'URL `/transactions?highlight_id=NN`: la riga NN viene messa in evidenza al primo render? | |

**Note**: _________

---

## 5. Event badge (●evt) — DIVIDEND linked

Prerequisito: almeno una transazione con `asset_event_id` valorizzato (es. DIVIDEND).

| | Check | Esito |
|--|--|--|
| 5.1 | Il badge `●evt` è visibile in colonna `links`? Colore violetto, font piccolo? | |
| 5.2 | Hover: appare il `title` con `[type · date · value currency · auto/manual]`? | |
| 5.3 | Click: NON apre niente (è un TODO Step 6 — popover deferito). Annota se ti aspetti di più. | |

**Note**: _________

---

## 6. Filtri URL + sync bidirezionale

| | Check | Esito |
|--|--|--|
| 6.1 | Apri `/transactions?broker_id=1&types=BUY,SELL` — i filtri sono applicati? | |
| 6.2 | Cambia un filtro nella tabella (header column popover): l'URL si aggiorna **senza** scroll-jump? | |
| 6.3 | Backward/forward del browser preserva lo stato dei filtri? | |
| 6.4 | Reload pagina: filtri preservati? | |

**Note**: _________

---

## 7. Add Transaction (StagingModal create-many)

| | Check | Esito |
|--|--|--|
| 7.1 | Click `+ Add Transaction`: la modale apre con 1 riga vuota (BUY default, today, broker primo)? | |
| 7.2 | Click `+ Add row`: si aggiunge una nuova riga? | |
| 7.3 | Tab/click tra i campi è naturale? Date input nativo si comporta? | |
| 7.4 | Cambia type su DIVIDEND: il banner issues compare con "asset_id required"? Quanto velocemente (≈500ms debounce)? | |
| 7.5 | AssetSelect: ricerca per ticker/ISIN funziona? Le option mostrano `[icon] name [CURRENCY]`? | |
| 7.6 | Quantity / Cash amount: input text accetta segni e decimali? Cash currency 3 chars uppercase? | |
| 7.7 | Color band a sinistra riga cambia se cambi broker? | |
| 7.8 | Click `Commit N`: payload corretto? La modale si chiude e la lista si ricarica con la nuova riga? | |
| 7.9 | Forza un errore (es. data futura impossibile o currency mismatch): banner rosso "Commit rolled back" appare con dettagli? La modale resta aperta? | |

**Note**: _________

---

## 8. Edit single row (StagingModal edit-many con N=1)

| | Check | Esito |
|--|--|--|
| 8.1 | Click sull'icona `✎` in colonna actions di una riga: la modale apre con quella riga in mode `edit-many`? | |
| 8.2 | Type e Broker sono **disabled** (immutable)? | |
| 8.3 | Modifica la quantity: la riga passa a status `edited` (sfondo amber tenue)? | |
| 8.4 | `Reset row` (↺) ripristina i valori originali? | |
| 8.5 | `Reset all` ripristina tutto? | |
| 8.6 | Commit: la modale chiude e la lista mostra il valore aggiornato? | |
| 8.7 | Senza modifiche: il bottone `Commit 0` è disabled? | |

**Note**: _________

---

## 9. Bulk: Edit / Clone / Delete / Promote

Seleziona 2-3 righe via checkbox → la **SelectionBar** verde appare in fondo.

| | Check | Esito |
|--|--|--|
| 9.1 | Counter "N selected" è corretto e include eventuali ghost rows selezionate? | |
| 9.2 | `✎ Edit bulk`: apre modale edit-many con N righe? Show only modified utile? | |
| 9.3 | `📋 Clone`: apre modale create-many con N righe pre-popolate, id strippati, date=today, related_transaction_id=null? | |
| 9.4 | `🗑 Delete` su righe **clean** (senza link): la modale apre come confirm; commit elimina e ricarica? | |
| 9.5 | `🗑 Delete` con almeno 1 linked pair (selezioni solo 1 dei 2): appare la modale **extender** con toggle globale `Remove`/`Extend` + radio per riga? | |
| 9.6 | Toggle globale sincronizza tutti i radio? La summary "Final batch: N transactions" è corretta? | |
| 9.7 | Commit: una sola DELETE va al backend con tutti gli id? Atomicità rispettata in caso di errore? | |
| 9.8 | Seleziona esattamente 1 DEPOSIT + 1 WITHDRAWAL **non linked**: appare il bottone `⚡ Promote pair`? | |
| 9.9 | Selezioni miste (es. BUY+SELL): il Promote NON appare? | |

**Note**: _________

---

## 10. Promote pair (TRANSFER + FX_CONVERSION)

### TRANSFER (broker diversi, currency uguale)

| | Check | Esito |
|--|--|--|
| 10.1 | Apre Step 1 modale: il pair summary ("From... / To...") è leggibile? | |
| 10.2 | Radio `TRANSFER` selezionabile? `FX_CONVERSION` greyed con motivo? | |
| 10.3 | `Next ▸` → Step 2: AssetSelect + Quantity sono richiesti (asterisco rosso)? | |
| 10.4 | `Promote` con campi vuoti è disabled? | |
| 10.5 | Compila e commit: la lista si ricarica + nuova pair pulsata via highlight_id? | |
| 10.6 | Forza errore (asset wrong currency): banner rosso, modale resta aperta? | |

### FX_CONVERSION (stesso broker, currency diverse)

| | Check | Esito |
|--|--|--|
| 10.7 | Step 1: `FX_CONVERSION` selezionabile, `TRANSFER` greyed con motivo? | |
| 10.8 | Step 2: mostra "Implied rate: 1 USD = 0.9215 EUR" calcolato dai cash amounts? | |
| 10.9 | `Promote` immediatamente abilitato (no extra fields)? | |
| 10.10 | Commit chiude modale e ricarica? | |

**Note**: _________

---

## 11. Performance / responsive

| | Check | Esito |
|--|--|--|
| 11.1 | Carico iniziale: tempo di first-paint accettabile (<1s su dataset 30-100 TX)? | |
| 11.2 | Scroll su tabella lunga (~100 righe): smooth, niente jank? | |
| 11.3 | Apertura modali: animazione fade+scale fluida? | |
| 11.4 | Responsive layout (riduci viewport a ~1024px): la tabella resta leggibile? | |
| 11.5 | Mobile (~600px): orizzontale scrollable? Disastro? | |

**Note**: _________

---

## 12. Dark mode + i18n

| | Check | Esito |
|--|--|--|
| 12.1 | Toggle dark mode: tutti i contrasti sono ok in tabella e modali? | |
| 12.2 | Cambia in IT: tutte le label tradotte? Type badge tradotti? | |
| 12.3 | Cambia in FR: idem? | |
| 12.4 | Cambia in ES: idem? | |
| 12.5 | Banner issues / rollback / ghost chip — sono tradotti? (Alcune stringhe sono ancora hardcoded — annota quali) | |

**Note**: _________

---

## 13. Edge cases / smell test

| | Check | Esito |
|--|--|--|
| 13.1 | Dataset vuoto: la tabella mostra empty state leggibile (`No transactions yet`)? | |
| 13.2 | Errore di rete (fai il backend giù): banner rosso comparare? Recovery quando torna su? | |
| 13.3 | Modal aperta + click backdrop: si chiude con safety (no chiusura accidentale durante drag)? | |
| 13.4 | Modal aperta + Escape: chiude correttamente? Le modali stacked (es. confirm dentro staging) gestiscono bene Escape? | |
| 13.5 | Selezioni > 50 righe: la SelectionBar resta usable? Performance staging modal con 50 drafts? | |

**Note**: _________

---

## Mock data gaps (se mancano scenari)

Se ti accorgi che mancano TX per testare alcuni scenari, le opzioni sono:

1. **Aggiungerle a mano** dalla `+ Add Transaction` UI stessa (è un buon test
   indiretto: stai creando dati di test usando il flow che vuoi testare).
2. **Estendere `populate_mock_data.py`** (è uno dei follow-ups deferiti del
   plan Step 6/10): aggiungere ≥1 DIVIDEND con `asset_event_id`, ≥1 TRANSFER
   cross-broker, ≥30 TX su 2-3 broker.

---

## Output finale del walkthrough

Quando hai finito, raccogli:

1. **Lista priorità raffinamento** — i punti ⚠️ ordinati per impatto UX.
2. **Bug trovati** — i punti ❌ con repro steps.
3. **Idee emerse** — cose non in checklist che ti son venute in mente
   (es. "vorrei un keyboard shortcut per +Add row", "il color band
   potrebbe essere più sottile", ecc.).

Da lì creiamo il piano di **Round 1 di refinement** per Part 4 (sotto
`phases/phase-07-subplan/Parte4/Round1-XYZ/` quando la archivieremo).

