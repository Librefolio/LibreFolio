# Prompt per Agente: Miglioramenti UX e Parser (Blocco 1)

## Contesto
Stiamo migliorando l'esperienza utente dell'Import Wizard di LibreFolio (Svelte 5) e dei relativi parser CSV. Il tuo obiettivo è implementare una serie di migliorie all'interfaccia utente basate sui feedback dei test utente e correggere alcuni edge-case emersi nei plugin.

## Obiettivi e Task Dettagliati

### 1. Quick Search Badges in `AssetModal.svelte`
Attualmente, quando l'utente crea un nuovo asset dallo Step 4 dell'Import Wizard, i dati estratti dal CSV (Nome, Ticker, ISIN) vengono concatenati brutalmente nella stringa di ricerca.
- **Azione:** Aggiungi una prop `initialSearchBadges: string[]` al componente `AssetModal.svelte`.
- **UI:** Renderizza questi badge appena sopra la barra di input "Cerca Online".
- **Comportamento:** Quando l'utente clicca su uno di questi badge (es. `[ 🏷️ AASI ]` o `[ 🆔 LU1681044480 ]`), il valore testuale del badge deve popolare istantaneamente l'input di ricerca.
- **Integrazione:** Modifica l'Import Wizard (Step 4) in modo che passi l'array di badge.

**Design Target (ASCII Art):**
```text
┌────────────────────────────────────────────────────────────────┐
│ 🔍 Cerca e Aggiungi Asset                                [ X ] │
│ ────────────────────────────────────────────────────────────── │
│ Suggerimenti dall'importazione (Clicca per cercare):           │
│ [ 🏷️ AASI ]   [ 🆔 LU1681044480 ]   [ 📝 AMUNDI MSCI E... ]    │
│                                                                │
│ [ Cerca online tramite provider...                           ] │
│                                                                │
│ Risultati da JustETF / Yahoo:                                  │
│  ... (in attesa di ricerca)                                    │
└────────────────────────────────────────────────────────────────┘
```

### 2. Ridisegno Asset Card (Step 3 e 4)
Le attuali card che mostrano gli asset estratti danno troppa priorità visiva al Ticker (spesso corto) e troncano il nome dell'asset.
- **Azione:** Ridisegna la UI della "Asset Card" usata nello Step 3 (Dettaglio Analisi) e nello Step 4 (Mappatura Asset).
- **Design Target (Badge Style):** 
  - Il Nome per esteso deve essere in cima, in grande e ben leggibile (es. `AMUNDI MSCI EM ASIA UCITS ETF`).
  - Sotto al nome, posiziona gli identificatori (Ticker, ISIN) come badge affiancati (es. `[ Ticker: AASI ] [ ISIN: LU1681044480 ]`).

**Design Target (ASCII Art):**
```text
┌──────────────────────────────────────────────┐
│ AMUNDI MSCI EM ASIA UCITS ETF          10 TX │
│ [ Ticker: AASI ]  [ ISIN: LU1681044480 ]     │
│ 📁 Movimenti_K6245_13-6-2026.csv             │
│                                              │
│ [ Cerca nei tuoi asset...                  ▼]│
└──────────────────────────────────────────────┘
```

### 3. Pulsante File Preview (Step 3)
Nel `ParseDetailModal`, è difficile capire perché una transazione ha generato un warning senza vedere il file sorgente.
- **Azione:** Aggiungi un pulsante "Vedi File / Preview" che apra la modale esistente di File Preview (`FilePreviewModal`), permettendo all'utente di ispezionare il CSV raw.

### 4. Modale di Conferma Warning (Step 3)
Gli utenti spesso ignorano i warning.
- **Azione:** Intercetta il click sul pulsante "Avanti" nello Step 3 se l'array dei `warnings` contiene elementi.
- **Comportamento:** Mostra un `ConfirmModal` (giallo/warning) che obbliga l'utente a confermare di aver preso visione dei warning.

### 5. BugFix `AssetSelect` Disabilitato (Step 4)
Nello Step 4, i bottoni degli asset esistenti appaiono erroneamente grigiati (`disabled=""`).
- **Azione:** Investiga la logica del dropdown in `AssetSelect.svelte` usato per la mappatura. Controlla e rimuovi il blocco di disabled.

### 6. Filtro Testuale Transazioni
Nella pagina Transazioni, il pannello dei filtri che si apre cliccando sull'imbuto della colonna "Asset" non permette ricerche veloci.
- **Azione:** Aggiungi un campo di ricerca testuale libero all'interno del pannello filtri per cercare l'asset per nome o ticker.

### 7. Fix Directa `Bollo` (Parser Backend)
Il parser di Directa attualmente salta la riga "Bollo portafoglio titoli*" etichettandola come tipo sconosciuto.
- **Azione:** Nel file `backend/app/services/brim_providers/broker_directa.py`, mappa la stringa/parola chiave "bollo" al `TransactionType.TAX`.

## File di riferimento probabili
- Frontend: `frontend/src/lib/components/assets/AssetModal.svelte`, `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte`, `frontend/src/lib/components/transactions/modals/ParseDetailModal.svelte`
- Backend: `backend/app/services/brim_providers/broker_directa.py`

Procedi in modo iterativo, testando la UI e il backend dopo ogni step.
