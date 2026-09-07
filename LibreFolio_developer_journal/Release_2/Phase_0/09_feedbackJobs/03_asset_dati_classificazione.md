# 03 — Asset, dati & classificazione

Task su modello dati degli asset e classificazione. Approvati dall'utente il 07/09/2026.

---

## 🏷️ Settori per i bond: Corporate e Governativi

**Complessità**: S · **Origine**: nota utente

### Richiesta
Aggiungere tra i settori: **Corporate** (bond di aziende) e **Governativi** (bond statali).

### Note implementative
- Il settore vive nella classificazione dell'asset: verificare dov'è l'enum/lista settori
  (`sector_fin_utils.py` / `FinancialSector` e il selettore nel `DistributionEditor` /
  nella modale asset) e come valida il backend.
- Aggiungere le due voci con label i18n ×4. Verificare che la normalizzazione sector→
  allocazione dashboard le prenda in automatico.
- Decidere se vale anche per l'auto-classificazione da provider (JustETF/Yahoo mappano già
  dei settori: mappare i bond segnalati dai provider su queste due classi).

---

## 📥 Import CSV delle distribuzioni (geografica e settoriale)

**Complessità**: M · **Origine**: nota utente

### Richiesta
Nell'edit asset, per le distribuzioni geografica e settoriale, la possibilità di fare un
**import da CSV** — similmente a quanto già esiste per i prezzi di forex e asset.

### Note implementative
- Pattern di riferimento: l'import CSV dei prezzi (asset data editor) e FX — stessa UX
  (file → preview mappata → applica).
- Target: il `DistributionEditor` (sector/geographic) nella modale asset: un bottone
  "Importa da CSV" che riempie le righe (nome area/settore + peso %), con validazione
  (totale 100% coerente col totale verde già esistente).
- Formato CSV minimo: `name,weight` (peso in % o 0-1 da decidere e documentare).
- Match dei nomi: contro l'enum/settori noti; le righe non riconosciute vanno in errore
  chiaro, non ignorate.
