# Prompt per Agente: Architettura Prezzi e Modale Asset (Blocco 2)

## Contesto
L'obiettivo di questo blocco è gestire in modo pulito ed elegante le discrepanze di quotazione (es. Obbligazioni/BTP quotati su base 100, azioni UK quotate in pence GBX ma contabilizzate in GBP). Non vogliamo alterare il salvataggio dei prezzi grezzi a database per mantenere i grafici coerenti con il mercato, ma dobbiamo correggere il calcolo del controvalore del portafoglio (Asset Valuation).

## Obiettivi e Task Dettagliati

### 1. Migrazione Database (`quote_base_quantity`)
Aggiungeremo un nuovo campo al modello `Asset`.
- **Azione:** Aggiungi la colonna `quote_base_quantity` (intero, nullable, default = `1`) al modello SQLAlchemy `Asset` (e al relativo schema Pydantic).
- **Azione:** Genera e applica la migration Alembic associata.

### 2. Architettura DRY (Backend)
Vogliamo una singola source of truth per la matematica di conversione.
- **Azione:** Crea una funzione di utilità globale (es. in un modulo shared o come metodo helper) chiamata `compute_holding_value(qty: Decimal, raw_price: Decimal, quote_base_quantity: int) -> Decimal`.
  - La formula deve essere: `(qty / quote_base_quantity) * raw_price`. Se `quote_base_quantity` è nullo o <= 0, assumi 1.
- **Azione:** Trova tutti i punti nel backend dove si calcola il valore di mercato, tipicamente `market_value += qty * price` (es. in `portfolio_service.py` e `transaction_service.py` per i WAC). Sostituiscili con l'invocazione di questa nuova funzione. 
  - *Nota sulle prestazioni:* Per il portfolio service, è consigliato caricare una mappa `quote_base_map = {asset_id: base}` a inizio esecuzione per evitare query N+1 durante il loop sullo storico.

### 3. Restyling `AssetModal.svelte` (Frontend)
L'aggiunta del campo `quote_base_quantity` e il recupero del campo `active` (Stato Asset) richiedono un aggiornamento dell'interfaccia utente.

**Azione:** Aggiorna la modale Asset rispettando **esattamente** questa architettura UI (Layout a griglia, senza fieldset invasivi, stile pulito):

```text
┌────────────────────────────────────────────────────────────────┐
│ Aggiungi Asset                                           [ X ] │
│ ────────────────────────────────────────────────────────────── │
│ 🔍 CERCA ONLINE                                                │
│ Suggerimenti: [ 🏷️ AASI ]  [ 🆔 LU1681044480 ]                 │
│ [ Cerca per nome, ticker, ISIN...                            ] │
│ Provider: ( Borsa Italiana ) ( JustETF ) ( Yahoo Finance )     │
│                                                                │
│ 📝 DETTAGLI ASSET                         [ Chiedi al Provider]│
│        Nome *                              Tipo *              │
│ ┌─┐    [ BTP Valore 2033                 ] [ Obbligazione ▼  ] │
│ │🖼️│    Prezzo riferito a N asset (ℹ️)      Valuta Base *       │
│ └─┘    [ 100                             ] [ EUR ▼           ] │
│                                                                │
│ URL Utente                                                     │
│ [ https://...                                                ] │
│                                                                │
│ Descrizione                                                    │
│ [ Brief description of the asset...                          ] │
│                                                                │
│ ▼ ULTERIORI INFO                                               │
│   (Identificatori)                                             │
│                                                                │
│ ► ASSEGNAZIONE PROVIDER                    [ ] Nessun Provider │
│ ────────────────────────────────────────────────────────────── │
│ Stato: [=O] Attivo (ℹ️)               [ Annulla ] [ Crea Asset ]│
└────────────────────────────────────────────────────────────────┘
```

**Dettagli Tecnici UI:**
1. **Prezzo riferito a N asset:** È un campo di tipo `number` posizionato appena sotto `Nome` (a sinistra della Valuta Base).
   - **Tooltip (ℹ️):** Inserisci esattamente questo testo nel tooltip vicino alla label: *"Specifica a quanti titoli o quote fa riferimento il prezzo di mercato. Per Azioni ed ETF è generalmente 1. Per le Obbligazioni (come i BTP) il prezzo è spesso quotato su base 100, in questo caso inserisci 100."*
   - Deve essere collegato al nuovo campo API `quote_base_quantity`.
2. **URL Utente e Descrizione:** Devono essere collocati sotto la griglia 2x2 principale, restando sempre visibili.
3. **Stato (Attivo):** Da posizionare nel footer a sinistra (in basso).
   - Deve usare un componente **Slider Orizzontale (Switch/Toggle)** e non una banale checkbox.
   - **Tooltip (ℹ️):** Inserisci esattamente questo testo: *"Se attivo, l'asset sarà aggiornato automaticamente dallo scheduler e visibile nelle selezioni. Disabilitalo per nasconderlo se non lo possiedi più e non vuoi continuare a scaricarne i prezzi."*

## File di riferimento probabili
- `backend/app/models/asset.py` e `backend/app/schemas/asset.py`
- `backend/app/services/portfolio_service.py`
- `frontend/src/lib/components/assets/AssetModal.svelte`
