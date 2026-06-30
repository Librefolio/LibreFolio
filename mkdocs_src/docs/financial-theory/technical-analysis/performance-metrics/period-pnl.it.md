# 📊 P&L del Periodo (Profit and Loss)

*[⬅️ Torna alla Panoramica delle Metriche di Performance](index.md)*

## 💡 Cos'è il P&L del Periodo?

Il **P&L del Periodo** (Profit and Loss / Profitto e Perdita) rappresenta il risultato monetario assoluto generato dal tuo portafoglio all'interno della finestra temporale selezionata, rettificato per i flussi di cassa esterni.

Risponde alla domanda diretta: _"Quanti soldi ho effettivamente guadagnato o perso durante questo periodo?"_

A differenza delle metriche percentuali (come il [ROI Semplice](roi.md) o il [TWRR](twrr.md)), il P&L del Periodo è espresso come un importo monetario assoluto (es. EUR, USD). La sua particolarità è che è **rettificato per i flussi di cassa**, il che significa che isola la performance reale degli investimenti dai tuoi versamenti e prelievi.

---

## 🧮 Formula

LibreFolio calcola il P&L del Periodo utilizzando la seguente equazione:

$$
\text{P}\&\text{L del Periodo} = \text{NAV}_{\text{fine}} - \text{NAV}_{\text{inizio}} - \text{Flussi Esterni Netti}
$$

Dove:

- **$\text{NAV}_{\text{inizio}}$**: Il [Net Asset Value (Net Worth)](nav.md) all'inizio della finestra temporale selezionata.
- **$\text{NAV}_{\text{fine}}$**: Il Net Asset Value alla fine della finestra temporale selezionata.
- **$\text{Flussi Esterni Netti}$**: Il capitale netto iniettato o prelevato dall'investitore durante il periodo, definito come:

$$
\text{Flussi Esterni Netti} = \text{Depositi} - \text{Prelievi}
$$

Solo i flussi che entrano o escono dallo scope del portafoglio selezionato contano come esterni. I trasferimenti interni tra broker o conti all'interno dello scope non influenzano questo calcolo.

---

## 📝 Esempio Pratico

Supponiamo che il tuo portafoglio abbia le seguenti metriche per un determinato anno:

- **NAV all'inizio**: €27.000
- **Depositi Totali**: €1.000
- **Prelievi Totali**: €0
- **NAV alla fine**: €33.000

Per prima cosa calcoliamo i Flussi Esterni Netti:

$$
\text{Flussi Esterni Netti} = 1.000 - 0 = \text{€}1.000
$$

Successivamente calcoliamo il P&L del Periodo:

$$
\text{P}\&\text{L del Periodo} = 33.000 - 27.000 - 1.000 = \text{€}5.000
$$

### 🔍 Spiegazione del Risultato

Sebbene la valutazione totale del tuo portafoglio sia aumentata di **€6.000** (da €27.000 a €33.000), **€1.000** di tale aumento è costituito da denaro aggiunto da te. Pertanto, i tuoi investimenti hanno generato un guadagno netto reale di **€5.000**.

Se la formula non tenesse conto dei flussi esterni, mostrerebbe erroneamente un profitto di €6.000, inducendoti a pensare che i tuoi asset abbiano performato meglio di quanto abbiano fatto in realtà.

---

## ⚖️ Differenze Chiave

- **vs. ROI / TWRR / MWRR**: Queste sono metriche percentuali che mostrano il tasso di rendimento. Il P&L del Periodo mostra l'importo monetario assoluto del profitto/perdita.
- **vs. Plusvalenza/Minusvalenza Latente**: La plusvalenza/minusvalenza latente è un'istantanea delle posizioni aperte correnti confrontate con il loro costo di acquisto originale. Il P&L del Periodo misura la performance sia delle posizioni aperte che di quelle chiuse (plusvalenze realizzate, dividendi, interessi) specificamente entro i limiti della finestra temporale scelta.

---

## 📊 Relazione con il P&L Totale

Il P&L del Periodo è la **versione limitata nel tempo** di un concetto più fondamentale: il **P&L Totale**.

$$
\text{P\&L Totale}(t) = \text{NAV}(t) - \text{Capitale Depositato}(t)
$$

Dove il **Capitale Depositato** è il capitale esterno netto cumulativo conferito dall'inizio — non solo nel periodo selezionato. Il P&L del Periodo è pari alla variazione del P&L Totale all'interno della finestra temporale scelta:

$$
\text{P\&L del Periodo} = \text{P\&L Totale}(t_{\text{fine}}) - \text{P\&L Totale}(t_{\text{inizio}})
$$

Il P&L Totale è visibile nel **tooltip del Grafico di Crescita** (in modalità ASS) come lo scostamento tra la linea del NAV e la linea tratteggiata del Capitale Depositato. Questo lo rende facile da leggere: se il NAV è al di sopra della linea di base, il portafoglio è in attivo; se è al di sotto, è in perdita.

🔗 Consulta **[Capitale Depositato & P&L Totale](deposited-capital.md)** per la teoria completa, l'algoritmo di scomposizione della liquidità ed esempi pratici svolti.

---

## 🔗 Correlati

- 💼 **[NAV / Patrimonio Netto](nav.md)** — il punto di arrivo di ogni formula del P&L
- 📚 **[Valore Contabile](book-value.md)** — usato nella scomposizione del P&L (variazione latente, base di costo)
- 💸 **[Capitale Depositato & P&L Totale](deposited-capital.md)** — versione da inizio operatività con scomposizione della liquidità
- ⏱️ **[Effetto Timing](timing-effect.md)** — l'impatto dei tempi di deposito sui rendimenti
