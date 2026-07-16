# Log implementazione — FIFO UI v2: Consolidamento visuale

Piano sorgente: `refinment-work-v2.md`. Metodologia: diagnosi browser reale prima di ogni modifica (Playwright
one-shot, non persistito), poi implementazione per stream.

## Fase 0 — Diagnosi (browser reale)

Ambiente: server di test (porta 6041), DB ripopolato (`./dev.py test -q db populate --force --clean --with-static --with-reports`),
login `e2e_test_user`. Script diagnostici temporanei (`/tmp/libreFolio_v2_diagnosis*.py`, non persistiti).

Casi usati:
- **Coinbase / Bitcoin** (broker id=5, asset id=6): caso semplice, 1 solo lotto — utile per vedere isolatamente
  il grafico WAC e la modale su un lotto banale.
- **AAPL (asset id=1), vista Dashboard "All brokers"**: caso ricco — **10 lotti, 17 segmenti Gantt, 4 broker
  diversi** (Interactive Brokers, DEGIRO, eToro, Coinbase, Directa SIM), con transfer, adjustment a costo zero
  (righe Jul 8/Jul 11 con opening price 0,00 $) e stato `Degraded`. Scelto come caso principale per la
  rifinitura Gantt/tabella perché mostra tutte le casistiche visuali rilevanti in un colpo.

Screenshot salvati in `/tmp/libreFolio_v2_screens/` (non commitati, solo per questa sessione di lavoro).

### Conferme visive dei findings del piano

1. **Gantt — colonna fissa confermata visivamente**: screenshot `22_aapl_gantt_chart.png`/`24_aapl_gantt_all.png`
   mostrano la colonna sinistra con icona asset ripetuta 8 volte, label troncate ("Interactive B...", "Directa
   SI...", "Interactive Br..."), badge LONG, data breve senza anno ("May 27, 2026" — in realtà QUI l'anno c'è
   già nella colonna fissa, ma NON è presente nella label dentro il segmento ECharts, che oggi mostra solo
   `{broker} · {qty}` senza data). Il canvas del grafico occupa solo la porzione destra, staccato dalla colonna.
2. **Colori/spessore Gantt già corretti**: confermato che colore-per-broker e spessore-per-quantità già
   funzionano (Interactive Brokers·15 visibilmente più spesso di Interactive Brokers·5). Nessuna regressione da
   temere su questi due aspetti — vanno preservati durante la migrazione del custom series.
3. **Transfer visibile**: lotto 05/27 mostra Interactive Brokers·10 → tratto (transito) → DEGIRO·5. Nessuna
   azione richiesta da questo piano (la matematica FIFO/transfer non va toccata) — annotato solo come evidenza
   che il rendering multi-segmento con transito esiste già e deve essere preservato dopo la rimozione colonna.
4. **WAC chart — marker e legenda già ricchi** (`21_aapl_wac_chart.png`): legenda nativa ECharts con "WAC — Coinbase",
   "WAC — DEGIRO", "WAC — Directa SIM", "WAC — Interactive Brokers", "WAC — eToro", "WAC — Combined" — nomi
   reali già in uso, **nessuna label generica "WAC broker #N"** osservata nel caso reale. Marker: cerchi verdi
   (Buy), quadrati arancioni (Adjustment), rombo rosso (Sale), simbolo bidirezionale blu (Transfer) — tutti
   visibili e cliccabili. Confirma che serve solo il cambio simbolo BUY/SELL, non altro.
5. **Tabella AAPL** (`23_aapl_table.png`): 10 righe, colonne oggi visibili = Data apertura, Direzione, Stato,
   Custodia, Prezzo apertura, Quantità aperta, Valore corrente (troncato a destra). Confermato che Quantità
   iniziale/Valore apertura/Incassi cumulati/Open Return NON sono presenti nemmeno come colonne nascoste
   raggiungibili — vanno aggiunte come nuove `ColumnDef`.
6. **Modale già ricca ma senza 2 campi**: (`08_custody_modal.png`, caso Coinbase/BTC) Direction, Original/Open
   Quantity, Opening Unit Price, Current Value, FIFO P&L, Open Return, Status, Custody, Fragments, History
   tutti presenti. Confermato **assenti**: Valore apertura, Incassi cumulati. Titolo already mostra
   "Lot {Asset} — {data}" (non letteralmente "Custody"), quindi il gap è di contenuto/scoperta, non di copy.
7. **Comparison chart — checkbox custom confermate visivamente** (`09_comparison_value.png`,
   `10_comparison_return.png`, `11_comparison_price.png`): in ciascuna modalità è presente un checkbox
   `[✓] ● Lot 06/20` (duplica selezione tabella) più un secondo blocco modalità-specifico (`Total Value — Lot
   06/20` in Valore, `WAC — Coinbase` in Prezzo). Modalità Rendimento **non è vuota** per un lotto BUY-only
   (fix v1 già funzionante, confermato: curva +800% visibile) — nessuna regressione da correggere lì, solo
   rimuovere il checkbox duplicato.
8. **Modalità % primo grafico**: confermato che mostra oggi SOLO 2 serie normalizzate (Market Price, WAC del
   broker) — nessuna traccia di ROI/TWRR, coerente con l'assenza totale lato backend (verificata anche via
   grep). Nota positiva: ROI/TWRR **esistono già** a livello di intero portfolio nel KPI Dashboard
   (screenshot `dash_debug.png`: card "RETURNS" con ROI 11.54%, TWRR 11.65%, MWRR) — confonde solo la scala
   (asset vs portfolio), confermando che il riuso di `roi_utils.py` è la via corretta.
9. **Data Quality pre-esistente non correlata**: sul lotto Coinbase/BTC compaiono 2 banner "A transfer is
   missing its paired transaction, or the pair is invalid" — problema nei dati di mock/dati reali per quel
   lotto specifico, **non correlato al piano v2** (non è nè un bug di rendering nè richiesto dal piano). Non
   verrà toccato in questo lavoro; se rilevante lo segnalo separatamente a fine sessione (per la regola
   "segnalare bug fuori scope invece di correggerli silenziosamente").

### Verifica non completata (accettata, non bloccante)

Screenshot mobile+dark del pannello lotti non ottenuto in questa fase (la navigazione mobile della Dashboard
usa un layout con testo nascosto via classi responsive che ha richiesto più tempo del previsto per essere
guidato via script). Verrà rifatto con un test E2E reale (Playwright/TS, non script Python ad-hoc) durante la
fase di validazione finale del piano (già previsto: "dark mode; mobile" nella checklist §14).

## Esecuzione

Vedi commit/modifiche successive in questo stesso log e nel report finale
`fifo-ui-refinement-v2-final-report.md` per il dettaglio di ogni stream (A personale Gantt+WAC, B backend
ROI/TWRR, C tabella+modale, D grafico comparativo).
