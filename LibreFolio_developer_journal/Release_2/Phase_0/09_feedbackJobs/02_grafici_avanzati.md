# 02 — Grafici avanzati

Task su visualizzazioni. Approvati dall'utente il 07/09/2026. La nota dell'utente sul
"rendimento a N" è incorporata nella relativa sezione (correzione di sede: asset, non dashboard).
Analisi del codice e decisioni successive del 2026-09-07 in
[06_piano_sprint.md](06_piano_sprint.md); nessuna implementazione avviata.

---

## 📊 F8 — Dashboard: vista P&L assoluto e grafici avanzati

**Complessità**: F8a S · F8b L · F8c M · **Origine**: feedback beta Alfy 30/08/2026
**Riferimento**: `Release_2/phases/06_betaTestingReportAndFixing/` (classificazione 01/09)

### Richiesta
- Grafico dashboard: vista **solo P&L assoluto cumulato** (senza cash, costo asset, ecc.),
  usando la serie `total_pnl` già disponibile, senza rebase sull'intervallo selezionato.
- P&L con **candele sintetiche/ipotetiche**, secondo la decisione utente sotto:
  non rappresentano un'escursione simultanea osservata del portafoglio.
- Istogrammi per dividendi e interessi (gli altri parametri della KPI card 1).

### Note
- Va **spezzata in tre sotto-feature** indipendenti: (a) vista P&L-only, (b) candele,
  (c) istogrammi dividendi/interessi. Da pianificare una alla volta.
- La dashboard ha già toggle assoluto/% (main/main-pct nella gallery); la vista P&L-only è
  un terzo modo di leggere la stessa serie.

### Decisione candele — 2026-09-07
- Sommare i contributi OHLC di tutti gli asset, valorizzati con **quantità storiche di fine
  giornata**, ownership, quote-base e conversione nella valuta del grafico.
- L'utente accetta la natura ipotetica degli estremi: i massimi dei singoli asset possono
  verificarsi in momenti diversi. Etichetta esplicita; non usarli come intraday reale o
  varianza statistica. **Nessun volume**.
- Chiusura coerente con il P&L canonico: fissare nel piano esecutivo offset non-prezzo,
  policy FX giornaliera, posizioni negative e comportamento con OHLC mancanti/stale.
- **Compatibilità con vista aggregata obbligatoria**: prima composizione giornaliera fra
  asset, poi daily/weekly/monthly. Prima apertura, massimo high, minimo low, ultima chiusura;
  mai sommare i giorni o cambiare l'ordine delle due aggregazioni.
- Riusare calendario UTC, settimane ISO, bucket/representative date, zoom, filtri, cache e
  cambio risoluzione per viewport esistenti in `GrowthChart` / `timeSeriesAggregation`.
- Istogrammi redditi: servono serie backend distinte per dividendi/interessi, comprese
  righe senza asset. Nei bucket i flussi si sommano e riconciliano al KPI, non prendono
  l'ultimo valore come una serie NAV.

### Confronto UI obbligatorio — 2026-09-07
Per **ciascuna** F8a/F8b/F8c, prima della realizzazione produrre ASCII di controlli, modo
grafico, assi/legenda, aggregazione e stati senza dati/degradati, desktop/mobile.
Il dev deve poter correggere zone e interazioni prima del codice delle viste.

Dopo implementazione integrata: spiegare come raggiungere il grafico, attivare il modo,
cambiare periodo/zoom/risoluzione e leggere gli esiti; raccogliere feedback operativo,
correggere e riproporre. I test automatici non sostituiscono questa review.
Backend delle serie e prototipi UI possono avanzare in parallelo su contratti concordati;
`GrowthChart` e i file comuni restano sotto un unico owner.

---

## 📉 Grafico guadagni per transazione — ✅ GIÀ CONSEGNATO

**Complessità residua**: XS documentale · **Origine**: nota del 20/02/2026 (Phase 8)

> **Verifica 2026-09-07**: lo scopo funzionale è già implementato nell'analisi lotti
> (`LotsAnalysisPanel`, `LotComparisonChart`, `UnifiedLotsTable`), montata da dashboard
> e broker. Il testo seguente è contesto storico, **non una feature da ripianificare**.
> Costi/net sono già in tabella, custody e tooltip Gantt; curve nette parallele e disegno
> letterale delle doppie frecce non vengono promossi senza nuova decisione.
> Rimandi: [analisi G2](06_piano_sprint.md) e
> [piano FIFO v4](../../../RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-plan-v5.md).

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
- La proposta storica chiedeva un selettore FIFO/LIFO/PMC: oggi il matching lotti è FIFO,
  mentre WAC/PMC esiste come metrica/overlay distinta. Metodi fiscali alternativi fuori round.

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
- **Verifica 2026-09-07**: `RISK_ROLLING_RETURN` esiste già nel backend, ma conta
  osservazioni, non giorni di calendario. Manca la vista principale alternativa richiesta.
- Riutilizzare la piattaforma segnali backend; definire lookup calendario, lookback prima
  del range e staleness senza cambiare i segnali a osservazioni già salvati.
- Nessuna formula finanziaria nuova in TypeScript; evitare doppia trasformazione/rebase
  col normale modo percentuale del grafico e impedire editing dei ritorni come prezzi.

**Gate UX 2026-09-07:** prima ASCII della vista, selettore N, asse e stati indisponibili
con approvazione dev; dopo walkthrough dal dettaglio Asset, confronto prezzo/rendimento
e feedback operativo. Coordinate il file pagina con B3; il backend può procedere nei
moduli segnali senza attendere l'intera corsia dei grafici portfolio.

## Analisi per task — 2026-09-07

Baseline `a9138140`; superfici, rischi e DoD in [06_piano_sprint.md](06_piano_sprint.md).

| ID | Esito | Taglia | Sprint |
|---|---|---|---|
| G1a | Presentazione mancante, `total_pnl` già presente; cumulato confermato. | S | SP06 |
| G1b | Candele sintetiche approvate: EOD, no volume, aggregazione e zoom esistenti obbligatori. | L | SP07 |
| G1c | Totali disponibili; serie incassi per tipo/data assente. | M | SP07 |
| G2 | ✅ Già consegnato come analisi lotti; non ripianificare la vecchia wishlist. | XS residua | Nessun codice |
| G3 | Segnale presente; calendario e vista principale mancanti. | M | SP06 |
