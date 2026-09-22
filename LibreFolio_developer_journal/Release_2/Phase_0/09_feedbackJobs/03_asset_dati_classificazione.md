# 03 — Asset, dati & classificazione

Task su modello dati degli asset e classificazione. Approvati dall'utente il 07/09/2026.

---

## 🏷️ Settori per i bond: Corporate e Governativi

**Complessità**: S · **Origine**: nota utente

### Richiesta
Aggiungere tra i settori: **Corporate** (bond di aziende) e **Governativi** (bond statali).

### Note implementative
- **Verifica 2026-09-07**: `FinancialSector` in `sector_fin_utils.py:14` non contiene le
  due voci. Aggiornare anche fallback `assetTypes.ts`, API settori, selettore, i18n ×4
  e mappe emoji in utilities/portfolio.
- Borsa Italiana mappa già tipologie corporate/governative esplicite a `Financials`
  (`borsa_italiana.py:223-249`): riallineare questi mapping, non solo l'input manuale.
- JustETF passa le distribuzioni al normalizzatore; Yahoo usa il settore disponibile.
  Non inferire la classe dal solo tipo BOND, non riclassificare in massa vecchi Financials
  o dati manuali; sovranazionali/casi ambigui non vanno assimilati senza una decisione.
- Superfici e DoD nel task A1 di [06_piano_sprint.md](06_piano_sprint.md). S, SP03;
  nessuna migrazione di colonne DB.

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
- **Decisione utente 2026-09-07**: formato minimo `name,weight`, peso in percentuale
  **0-100**. Niente riconoscimento automatico delle frazioni 0-1.
- Match dei nomi: contro l'enum/settori noti; le righe non riconosciute vanno in errore
  chiaro, non ignorate.
- **Verifica 2026-09-07**: `CsvEditor` e `DataImportModal` impongono oggi `date` e
  consentono import delle sole righe valide. **Estendere proprio quei componenti condivisi**,
  già usati per prezzi/eventi Asset e tassi FX: non creare un editor/parser indipendente.
- Rendere configurabili identità primaria e validazione (`date` resta default, `name`
  per le distribuzioni); preservare i tipi dei caller dated, senza date fittizie.
  Una wrapper di dominio configura il motore comune, non lo duplica.
- Modalità distribuzioni strict: niente import delle sole righe valide se restano errori.
  I default degli import prezzi/eventi/FX non cambiano; coprirli tutti con regressioni.
- Errori su nomi sconosciuti, duplicati canonici e numeri invalidi; applicare soltanto
  alla distribuzione del draft scelta, dopo preview valida. Non usare il fallback a Other
  come riconoscimento di un nome CSV.
- Il totale verde frontend e la tolleranza backend non coincidono: `BaseDistribution`
  accetta oggi scarto fino all'1% e rinormalizza, non quanto dice la sua docstring.
  Fissare la policy dell'import coerente col totale verde senza modificare tacitamente
  i contratti legacy. Bilanciamento solo esplicito.

### Confronto UI e parallelismo — 2026-09-07
Prima del codice della vista: ASCII di file/testo, mapping/preview, errori/duplicati e
totale, con feedback e approvazione del dev. Dopo: percorso da Edit Asset alle due
distribuzioni e giro dei tre import dated esistenti, risultati attesi e feedback operativo.

Il core CSV può avanzare mentre si chiude il catalogo A1, su codici concordati; l'integrazione
finale richiede quel catalogo e l'host AssetModal va coordinato con U1/U5. Un solo owner per
`CsvEditor`/`DataImportModal`, non implementazioni concorrenti per ogni dominio.

## Analisi per task — 2026-09-07

Baseline `a9138140`; dettagli in [06_piano_sprint.md](06_piano_sprint.md).

| ID | Stato, dipendenza e nota | Taglia | Sprint |
|---|---|---|---|
| A1 | ✅ Integrato e developer-reviewed con F: settori Corporate/Government lungo enum, API/UI e provider. [Piano](../17_assetDataOperations/plan-phase00AssetDataOperations.prompt.md). | S | SP03 |
| A2 | ✅ Integrato e developer-reviewed con F: import CSV strict su editor condiviso, senza regressioni dated. [Piano](../17_assetDataOperations/plan-phase00AssetDataOperations.prompt.md). | M | SP03 |

> **Aggiornamento 2026-09-11:** SP03 è integrato in `dev_release2` (`e50d66408`,
> follow-up review `cc57b6a38`); le note sopra restano il contratto storico, non task aperti.
