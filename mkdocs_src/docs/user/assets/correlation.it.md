# 🧪 Scheda Correlazione

La scheda **Correlazione** della [pagina Asset](index.md) pone le stesse domande su una **selezione di asset** che hai messo insieme — asset che possiedi, asset che osservi soltanto, o le posizioni di un broker. Aprila da **Asset** nella barra laterale, poi dalla scheda **Correlazione** nella barra degli strumenti. Una selezione non ha pesi, quindi la scheda mostra percentuali e rapporti, mai importi: per il tuo denaro, vedi la [scheda Rischio](../dashboard/risk.md) della Dashboard.

Ogni blocco qui sotto segue uno schema: a cosa risponde, uno screenshot, i suoi strumenti e come leggerli.

- 🧺 **[Costruire la selezione](#building-the-selection)** — quali asset vengono confrontati
- 🕸️ **[Correlazione](#correlation)** — quali di essi si muovono insieme
- 📉 **[Quanto ha fatto male ciascuno di questi?](#how-much-did-each-hurt)** — le perdite di ciascuno
- ⚖️ **[Quanto ha pagato ciascuno di questi per il suo rischio?](#what-did-each-pay)** — rischio contro rendimento
- ⏮️ **[E se…?](#what-if)** — un episodio passato, in replay
- 🚩 **[Avvisi e dati mancanti](#each-section-speaks-for-itself)** — cosa mancava ai dati

---

## 🧺 Costruire la selezione {: #building-the-selection }

La scheda in alto risponde a *quali asset vengono confrontati?* Ogni chip è un asset selezionato, e la scheda ricorda la tua selezione in questo browser.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-asset-picker" alt="Il pannello + aperto sopra la scheda della selezione: ricerca, filtri Tipo e Valuta, due asset selezionati con Aggiungi 2 e, in sola lettura, gli asset che non possono essere analizzati nel periodo, ciascuno con il suo motivo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Verifica di idoneità** — se un asset ha abbastanza prezzi nel periodo per essere analizzato → [Qualità dei dati](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Come leggerla**

- **Aggiungi asset con il +**, rimuovine uno con la sua **×**, o cambiane molti in una volta con **Seleziona tutto**, **Deseleziona tutto**, **Inverti** e **I miei asset** — fino a **100 asset**.
- **Il contatore** — *3 nell'analisi, di 42 analizzabili* — conta gli asset selezionati in analisi, rispetto a tutti quelli che potrebbero esserlo nel periodo impostato nella barra degli strumenti.
- **Un chip tratteggiato** non può essere analizzato in questo periodo: resta selezionato, ma fuori dai risultati. **Un chip ambra** è analizzato, con un avviso. Passa il mouse o tocca un chip per leggere il motivo.
- **Se il periodo lascia alcuni asset senza prezzi**, una striscia ambra offre **Usa il periodo in cui tutti hanno prezzi**, che sposta le date della pagina per includerli tutti.

---

## 🕸️ Correlazione {: #correlation }

Questa sezione risponde a *quali di questi si muovono insieme?* — per individuare gli asset che in realtà sono la stessa scommessa, e quelli che attutiscono gli altri.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-correlation" alt="La sezione Correlazione con cinque asset: la matrice triangolare con la sua legenda, i pulsanti di ordinamento e i badge di settore e regione; Le coppie più simili accosta RE Loan Roma a RE Loan Milano a 0,94, quasi identici, e Quelle che compensano è vuoto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Coefficiente di correlazione (ρ)** — quanto strettamente due asset si sono mossi insieme, da −1 (sempre opposti) a +1 (sempre insieme) → [Correlazione](../../financial-theory/technical-analysis/risk-metrics/correlation.md#interpretation)
- **Ordina per similarità** — l'ordine predefinito: gli asset strettamente legati si trovano fianco a fianco, così i gruppi ridondanti emergono come blocchi → [Correlazione](../../financial-theory/technical-analysis/risk-metrics/correlation.md#why-the-matrix-answers-am-i-diversified)

**Come leggerla**

- **Un quadrato per coppia**: blu quando i due asset si muovono insieme, rosso quando si muovono in direzioni opposte, pallido quando si muovono in modo indipendente. Passa il mouse o toccalo per il valore a parole.
- **Parti dalle due liste**: **Le più simili** nomina le coppie che sono quasi la stessa esposizione, **Quelle che compensano** le coppie che si attutiscono a vicenda. Una lista vuota è già di per sé un risultato. Clicca una coppia per trovarla nella matrice.
- **Un trattino non è uno zero**: non è stato possibile misurare la coppia — storico troppo breve, o un prezzo che non si è mai mosso.
- **I pulsanti di ordinamento** riorganizzano la matrice; non cambiano mai un valore.

---

## 📉 Quanto ha fatto male ciascuno di questi? {: #how-much-did-each-hurt }

Questa sezione mette ogni asset sulla stessa scala del danno: le sue perdite peggiori nel periodo, e quanto sta ancora sotto il suo massimo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-hurt-table" alt="La tabella Quanto ha fatto male ciascuno di questi?: una riga per asset con Giorno negativo, Mese negativo, Caduta peggiore e quanto è durata, Sotto il picco ora e Risalita al picco" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Giorno negativo** — la perdita media nei giorni peggiori, il 5% peggiore (CVaR al 95%) → [VaR condizionale](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Mese negativo** — la stessa cosa su periodi reali di un mese → [VaR condizionale](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Caduta peggiore** — il calo più profondo da un picco; *durata N d* conta i giorni fino a quando l'asset è tornato lì, o fino alla fine del periodo → [Drawdown massimo](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Sotto il picco ora** — quanto sta sotto il suo livello più alto nel periodo → [Drawdown attuale](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **Risalita al picco** — il guadagno necessario per tornarci: il 20% sotto richiede +25% → [Cosa serve per tornare](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md#what-it-takes-to-get-back)

**Come leggerla**

- **Ogni colonna è il suo orizzonte**, da un giorno all'intero periodo: confronta gli asset lungo una colonna, non sommare mai i valori tra colonne.
- **Non è una classifica**: la tabella si apre nell'ordine della tua selezione. Clicca il titolo di una colonna per ordinarla, o passaci il mouse per sapere cosa misura.
- **Su un periodo breve**, **Giorno negativo** e **Mese negativo** possono restare vuoti mentre le colonne del drawdown sono riempite: richiedono più storico.

---

## ⚖️ Quanto ha pagato ciascuno di questi per il suo rischio? {: #what-did-each-pay }

Questa sezione mette il rischio contro la ricompensa — quanto ha oscillato ogni asset, e quanto ha reso in media all'anno — in una tabella e in un grafico. Con un benchmark scelto sotto *Confrontato con*, mostra anche come ogni asset si è mosso con esso.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-risk-return" alt="Quanto ha pagato ciascuno di questi per il suo rischio? con S&P 500 come benchmark: la sua riga colorata che apre la tabella, la riga del periodo, e il grafico con i cerchi degli asset, il rombo del benchmark e la linea tratteggiata" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Volatilità** — quanto hanno oscillato i rendimenti, su base annua → [Volatilità](../../financial-theory/technical-analysis/risk-metrics/volatility.md)
- **Rend. ann.** — il *rendimento medio annuo*: il rendimento medio del periodo, rapportato a un anno → [Annualizzazione osservata](../../financial-theory/technical-analysis/risk-metrics/observed-annualization.md)
- **Sortino** — il rendimento guadagnato per unità di oscillazione al ribasso → [Indice di Sortino](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md)
- **Sharpe** — il rendimento guadagnato per unità di volatilità → [Indice di Sharpe](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Beta** — con un benchmark: quanto si è mosso l'asset quando si è mosso il benchmark → [Beta e rendimento attivo](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md#interpretation)
- **Correlazione** — con un benchmark: quanto strettamente i due si sono mossi insieme → [Selezione del benchmark](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#interpretation)
- **Linea rischio/rendimento** — con un benchmark: la linea tratteggiata tracciata attraverso di esso sul grafico → [La linea rischio/rendimento](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line)

**Come leggerla**

- **Non è una classifica**: la tabella si apre con la riga del benchmark, poi la tua selezione nel proprio ordine. Clicca il titolo di una colonna per ordinarla.
- **La riga di testo sotto la tabella** indica il periodo esatto dietro le cifre, e dice quando è più breve del tuo — di solito per un asset con uno storico più breve.
- **Sul grafico**, più a destra significa più oscillazione e più in alto significa più rendimento medio; il benchmark è il rombo. Un cerchio sopra la linea tratteggiata ha dato una ricompensa migliore per il suo rischio rispetto al benchmark. Clicca una riga o un cerchio per evidenziare quell'asset in entrambi.

!!! warning "Il rendimento medio annuo non è il rendimento che hai vissuto"

    Su un asset molto volatile, il rendimento effettivamente vissuto è inferiore: non leggere l'altezza di un punto come ciò che l'asset ha guadagnato. Deriva inoltre solo dai prezzi — cedole e dividendi non sono ancora inclusi.

### 🎯 Scegliere il benchmark {: #choosing-the-benchmark }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-benchmark-picker" alt="Il selettore Confrontato con aperto: ricerca, filtri Tipo e Valuta, gli asset utilizzabili, poi, in sola lettura, quelli non utilizzabili in questo periodo, ciascuno con il suo motivo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Un benchmark per ogni pagina del rischio**: la tua scelta sotto *Confrontato con* si applica anche alla Dashboard e alle pagine del rischio di broker e asset, così restano comparabili.
- **La sua riga apre la tabella**, con un trattino sotto **Beta** e **Correlazione**: il benchmark non viene confrontato con se stesso. Può anche essere uno dei tuoi asset selezionati.
- **Gli asset che non possono essere misurati nel periodo** sono elencati a parte nel selettore, in sola lettura. Un benchmark tra questi resta scelto ma non viene usato finché non scegli un periodo che gli si addice.

---

## ⏮️ E se…? {: #what-if }

Questa sezione risponde a *come è passato ciascuno di questi attraverso un episodio reale del passato?* — una crisi predefinita o un periodo che scegli tu, in replay con rendimenti reali. Clicca il suo titolo per aprirla. È offerto solo il replay storico: uno shock ipotetico o una simulazione richiederebbero dei pesi.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-replay" alt="E se…? dopo Esegui replay: il riquadro degli asset esclusi, raggruppati per motivo, con il pulsante che esegue il replay del periodo più breve, sopra la tabella con Rendimento ed Effetto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Replay storico** — il rendimento reale di ogni asset in un periodo passato → [Replay storico](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)

**Come leggerla**

- **Scegli un Preset**, come la *Crisi finanziaria globale*, oppure imposta il **Periodo**, poi premi **Esegui replay**. Cambiare la selezione o le date della pagina cancella il risultato.
- **La tabella** mostra il **Rendimento** di ogni asset, dal peggiore, con una barra: rossa per una perdita, verde per un guadagno. Non c'è un totale: una selezione non ha pesi da sommare.
- **Gli asset senza prezzi agli estremi del periodo** sono esclusi ed elencati sopra la tabella, con il motivo. Quando possibile, un pulsante esegue il replay del periodo più breve in cui hanno tutti dei prezzi.

---

## 🚩 Avvisi e dati mancanti {: #each-section-speaks-for-itself }

Quando qualcosa non va nei dati, la scheda lo dice una volta, subito sotto la scheda della selezione, e nomina i risultati che ne sono influenzati.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-notice" alt="Inizio della scheda Correlazione: il banner pieghevole di qualità dei dati, l'avviso Alcuni risultati sono parziali con i suoi badge Misurazioni interessate, e il banner ambra della sezione Correlazione Non disponibile per i dati selezionati" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Qualità dei dati** — prezzi e tassi di cambio mancanti o obsoleti, e i risultati che rendono parziali → [Qualità dei dati](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Come leggerla**

- **Il banner di qualità dei dati** elenca cosa correggere, ogni problema con la sua azione, come **Sincronizza prezzi** o **Sincronizza tassi**. Cliccalo per aprire l'elenco.
- **L'avviso** sotto di esso nomina i risultati **parziali** e la loro causa. Un risultato parziale mostra comunque le sue cifre: leggile tenendo presente quella causa.
- **Un banner ambra proprio di una sezione** significa che un risultato non è tornato affatto, spesso perché il periodo è troppo breve: scegline uno più lungo, o sincronizza i prezzi.
- **E se…?** segnala i suoi problemi all'interno della sua sezione.

---

## 🔎 Buono a sapersi {: #reading-the-numbers }

- **Un periodo per tutti gli asset.** Ogni cifra copre gli stessi giorni per ogni asset selezionato, così le righe possono essere confrontate. Un asset con uno storico più breve accorcia quel periodo per tutti, e le loro cifre cambiano: è previsto → [Qualità dei dati](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs)
- **Una valuta.** I rendimenti sono misurati nella tua **Valuta predefinita**, impostata nelle [Preferenze](../settings/preferences.md) (quella predefinita dell'istanza se non ne hai mai scelta una), movimenti del tasso di cambio inclusi.
- **Un trattino non è uno zero.** Non è stato possibile misurare la cifra per quell'asset in questo periodo; passa il mouse o toccala per leggere il motivo.
- **Un'altra pagina, un'altra cifra.** Un'altra pagina o un'altra selezione misura su giorni diversi: confronta le cifre solo quando coprono lo stesso periodo.

---

## 🔗 Correlati {: #related }

- 📋 **[Elenco asset](index.md)** — la scheda Asset, la sua barra degli strumenti e il suo intervallo di date
- 🛡️ **[Scheda Rischio della Dashboard](../dashboard/risk.md)** — le stesse domande, per il tuo portafoglio
- 📊 **[Metriche di rischio](../../financial-theory/technical-analysis/risk-metrics/index.md)** — la teoria dietro ogni sezione di questa scheda
- 🛠️ **[Dettagli tecnici](../../developer/frontend/components/features/risk-lab.md)** — per gli sviluppatori: come funziona questa scheda al suo interno
