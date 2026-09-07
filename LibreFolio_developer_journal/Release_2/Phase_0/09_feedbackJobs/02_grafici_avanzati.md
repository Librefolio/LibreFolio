# 02 — Grafici avanzati

Task su visualizzazioni. Approvati dall'utente il 07/09/2026. La nota dell'utente sul
"rendimento a N" è incorporata nella relativa sezione (correzione di sede: asset, non dashboard).

---

## 📊 F8 — Dashboard: vista P&L assoluto e grafici avanzati

**Complessità**: M · **Origine**: feedback beta Alfy 30/08/2026
**Riferimento**: `Release_2/phases/06_betaTestingReportAndFixing/` (classificazione 01/09)

### Richiesta
- Grafico dashboard: vista **solo P&L assoluto** (senza cash, costo asset, ecc.).
- Possibilità di mostrare il P&L con **grafico a candela** per l'escursione giornaliera.
- Istogrammi per dividendi e interessi (gli altri parametri della KPI card 1).

### Note
- Va **spezzata in tre sotto-feature** indipendenti: (a) vista P&L-only, (b) candele,
  (c) istogrammi dividendi/interessi. Da pianificare una alla volta.
- La dashboard ha già toggle assoluto/% (main/main-pct nella gallery); la vista P&L-only è
  un terzo modo di leggere la stessa serie.

---

## 📉 Grafico guadagni per transazione

**Complessità**: M · **Origine**: nota del 20/02/2026 (Phase 8)

### Contesto (dalla nota originale)
Nel diagramma dei guadagni dalle varie transazioni di un asset:
- **Asse Y sinistra**: scala dei valori/percentuali dell'asset.
- **Asse Y destra**: scala di guadagno/perdita delle singole transazioni di buy.
- Per ogni evento di buy, un nuovo grafico parte da 0 in y a quella data.
- Una linea con area per la sommatoria cumulativa dei guadagni.
- Evento di vendita + tasse + commissione: doppia freccia verso il basso (da definire).

### Sotto al grafico
- Tabella con i buy in ogni riga; colonna "valore attualmente investito".
- Sotto: barra con valore stimato + guadagnato.
- Distinguere tra valore **potenziale** e **realizzato** (vendite parziali/totali).
- Selettore metodo di analisi (FIFO, LIFO, PMC, …) — attenzione: si collega alla questione
  regime fiscale (in TODO_FUTURI, futura); per il grafico partire da FIFO (l'unico oggi).

---

## 📊 Rendimento a N giorni (Asset)

**Complessità**: M · **Origine**: nota del 22/07/2026 (promosso), **corretta dall'utente il 07/09/2026**

### Contesto (come chiarito dall'utente)
Non un grafico del *prezzo*: una vista in **Asset** (non dashboard) che mostra il
**rendimento** di chi avesse comprato N giorni prima e vendesse oggi. Va nella pagina di
dettaglio asset, come vista/modo alternativo del grafico.

### Note implementative
- Per ogni punto "oggi" del range, la serie è `(prezzo_oggi / prezzo_{oggi-N} - 1)` — una
  serie di rendimento rolling a finestra fissa N (N selezionabile: es. 7/30/90/365).
- Riusa la serie prezzi già caricata per il grafico asset; è una trasformazione, non una
  nuova sorgente dati. Valutare se esporla anche come segnale backend (c'è già il pattern
  rolling return nei plugin segnali).
