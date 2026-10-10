# 🛡️ Scheda Rischio

La scheda **Rischio** della [Dashboard](index.md) mostra quanto è rischioso il tuo portafoglio, attraverso quattro semplici domande — da ciò che è realmente accaduto a ciò che potrebbe accadere. Si trova tra **Posizioni e Analisi** e **Transazioni**, e la pagina di ogni broker ha la stessa scheda per quel singolo broker.

Ogni blocco qui sotto segue uno schema fisso: a cosa risponde, uno screenshot, i suoi strumenti e come leggerli.

- 📉 **[Quanto può farmi male?](#how-much-can-it-hurt)** — le perdite che il tuo portafoglio ha effettivamente subito
- 🧩 **[Sono diversificato quanto penso?](#diversification)** — quali posizioni portano il rischio, e quali si muovono insieme
- ⚖️ **[Vengo pagato per questo rischio?](#being-paid)** — rendimento rispetto al rischio, posizione per posizione e rispetto a un benchmark
- 🔮 **[E se…?](#what-if)** — una crisi passata, uno shock che scegli tu, o una simulazione
- 🚩 **[Avvisi e dati mancanti](#notices)** — cosa mancava ai dati, e cosa fare al riguardo

---

## 📉 Quanto può farmi male? {: #how-much-can-it-hurt }

Quanto potresti perdere, e quanto è già stato grave? Ogni cifra qui è qualcosa che il tuo portafoglio ha realmente attraversato nel periodo; versamenti e prelievi non contano come guadagni o perdite.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-hurt" alt="Il blocco Quanto può farmi male?: le schede Una brutta giornata, Un brutto mese e Il peggior calo, ciascuna con il suo importo, e le loro righe di dettaglio (peggior giornata effettivamente vista, quanto è durato il calo, recupero necessario, drawdown a rischio, media oltre quella soglia); poi Tempo trascorso sotto il picco con l'indice di Ulcer, e la Distribuzione dei rendimenti giornalieri con la soglia VaR" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Una brutta giornata**, **Un brutto mese** — la tua perdita media nel 5% peggiore delle giornate, o di periodi di un mese → [VaR condizionale](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Soglia VaR** — su *Distribuzione dei rendimenti giornalieri*: la perdita giornaliera che solo il 5% peggiore delle giornate ha superato → [Value at Risk](../../financial-theory/technical-analysis/risk-metrics/value-at-risk.md)
- **Peggior giornata effettivamente vista** — la singola giornata peggiore del periodo → [peggior realizzazione](../../financial-theory/technical-analysis/risk-metrics/worst-realization.md)
- **Il peggior calo** — la discesa più profonda da un massimo a un minimo successivo → [drawdown massimo](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Drawdown a rischio** — quanto sotto il suo picco si trovava il portafoglio, a parte il 5% peggiore delle giornate → [drawdown a rischio](../../financial-theory/technical-analysis/risk-metrics/drawdown-at-risk.md)
- **Media oltre quella soglia** — quanto sotto il suo picco si trovava, in media, in quelle giornate peggiori → [drawdown a rischio condizionale](../../financial-theory/technical-analysis/risk-metrics/conditional-drawdown-at-risk.md)
- **Attualmente sotto il picco** — quanto sotto il suo ultimo massimo si trova oggi il portafoglio → [drawdown attuale](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **Indice di Ulcer** — sotto *Tempo trascorso sotto il picco*: quanto sono stati profondi e lunghi i cali; più basso è più calmo → [indice di Ulcer](../../financial-theory/technical-analysis/risk-metrics/ulcer-index.md)

**Come leggerlo**

- **Orizzonti diversi**: le schede vanno da un giorno a un mese al peggior calo, quindi non sommarle mai tra loro.
- **L'importo** sotto ogni percentuale è quella perdita applicata al tuo patrimonio netto.
- **Attualmente sotto il picco** compare solo mentre il tuo portafoglio è sotto il suo ultimo massimo.
- **Le icone ? e ⓘ** accanto a una cifra aprono la sua pagina teorica.

---

## 🧩 Sono diversificato quanto penso? {: #diversification }

Possedere molte posizioni non è la stessa cosa che essere diversificato. Questo blocco mostra quali posizioni portano davvero il tuo rischio, e quali si muovono insieme così strettamente da essere la stessa scommessa.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-diversification" alt="Il blocco Sono diversificato quanto penso?: la frase sotto il titolo; le schede Quante scommesse indipendenti ho davvero?, Distribuire il denaro è servito a qualcosa? e Quanto di me non è misurato qui?; le posizioni con peso, contributo al rischio e la barra a due lati; e Quali di queste sono la stessa scommessa?, con la sua matrice, Le più simili e Quelle che si compensano" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Quante scommesse indipendenti ho davvero?** — quanto è uniformemente distribuito il tuo denaro → [Concentration](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **Distribuire il denaro è servito a qualcosa?** — quanto le tue posizioni si attutiscono a vicenda → [Concentration](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **Quanto di me non è misurato qui?** — liquidità, più le posizioni senza prezzi utilizzabili → [qualità dei dati](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#excluded-weight)
- **Peso** e **contributo al rischio** — la quota di ciascuna posizione del tuo denaro, e del tuo rischio → [contributo al rischio](../../financial-theory/technical-analysis/risk-metrics/risk-contribution.md)
- **Quali di queste sono la stessa scommessa?** — quanto strettamente si muove insieme ogni coppia di posizioni → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md)

**Come leggerlo**

- **Una lunga barra rossa** sulla destra segnala una posizione il cui contributo al rischio supera quanto suggerisca il suo peso; quando una spicca, la frase sotto il titolo la nomina.
- **Nella matrice**, le coppie blu si muovono insieme, quindi tenerle entrambe aggiunge poco; le coppie rosse si muovono in direzioni opposte e si compensano a vicenda.
- **Passa il mouse su un quadrato** per il suo valore a parole. Gli elenchi *Le più simili* e *Quelle che si compensano* individuano le coppie che vale la pena guardare.

---

## ⚖️ Vengo pagato per questo rischio? {: #being-paid }

Vale la pena assumersi un rischio solo se ripaga. Questo blocco confronta il rendimento del tuo portafoglio e di ciascuna posizione con le sue oscillazioni — in una tabella e in un grafico — e, se ne scegli uno, con un benchmark.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-paid" alt="Il blocco Vengo pagato per questo rischio?, confrontato con MSCI World Index: la tabella espansa sulle righe Portafoglio e benchmark, con Peso, Volatilità, Rend. ann., Sortino, Sharpe, Beta e Correlazione; il grafico rischio/rendimento con i punti delle posizioni e del portafoglio dimensionati per peso, il rombo del benchmark e la linea tratteggiata dal tasso privo di rischio; e le note sotto il grafico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Volatilità** — quanto oscillano i rendimenti nell'arco di un anno → [volatilità](../../financial-theory/technical-analysis/risk-metrics/volatility.md)
- **Rend. ann.** — il rendimento medio, su base annua → [Observed Annualization](../../financial-theory/technical-analysis/risk-metrics/observed-annualization.md)
- **Sortino** — il rendimento ottenuto per ogni unità di oscillazioni al ribasso → [indice di Sortino](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md)
- **Sharpe** — il rendimento ottenuto per ogni unità di oscillazioni, al rialzo o al ribasso → [indice di Sharpe](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Beta** — quanto si muove una posizione quando si muove il benchmark → [Beta & Active Return](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md)
- **Correlazione** — quanto strettamente si muove una posizione con il benchmark → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md)
- **Confrontato con** e la linea tratteggiata — il tuo benchmark, e la linea tra chi è pagato meglio e chi peggio → [Benchmark Selection](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line)

**Come leggerlo**

- **Scegli un benchmark** in **Confrontato con** — un tracker di un ampio indice mondiale è il più significativo. Si applica a ogni pagina Rischio, e aggiunge le colonne **Beta** e **Correlazione**.
- **Sopra la linea tratteggiata**, un punto è stato pagato meglio per il suo rischio rispetto al benchmark — o, senza benchmark, rispetto al tuo portafoglio.
- **Clicca** sul titolo di una colonna per ordinare la tabella, o su una riga per trovare il suo punto nel grafico.
- **La riga Portafoglio** ripropone le posizioni di oggi, ai pesi di oggi, nel periodo — il titolo dice *sulla composizione attuale* — quindi non è la storia delle tue operazioni. I rendimenti derivano solo dai prezzi, senza dividendi né cedole per ora.

---

## 🔮 E se…? {: #what-if }

Cosa farebbe una crisi passata, o uno shock che immagini, al portafoglio che detieni oggi — e cosa potrebbe attenderci? Il blocco è inizialmente chiuso: clicca sul suo titolo per aprirlo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-whatif" alt="Il blocco E se…? aperto: l'avviso Replay storico: Parziale, Aggiungi: Shock ipotetico e Simulazione, e il riquadro Replay storico dopo Esegui replay, con il preset Crisi finanziaria globale e il suo periodo, il riquadro dell'asset escluso, la frase totale, e la tabella con Peso, Rendimento, Contributo, Impatto ed Effetto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Strumenti mostrati**

- **Replay storico** — un periodo passato reale, applicato al tuo portafoglio così com'è oggi → [replay storico](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)
- **Shock ipotetico** — un calo o un rialzo che assumi per ciascuna classe di attività, settore o regione → [shock ipotetico](../../financial-theory/technical-analysis/risk-metrics/hypothetical-shock.md)
- **Simulazione** — una gamma di futuri possibili, costruita dalla tua stessa storia → [Simulation Modes](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md)

**Come leggerlo**

- **Aggiungi uno strumento** con i pulsanti **Aggiungi:**; la sua **×** lo chiude e ne scarta il risultato. Gli strumenti che lasci aperti tornano la prossima volta, in questo browser.
- **Replay storico**: scegli una crisi in **Preset**, oppure il tuo **Periodo**, poi **Esegui replay**. Le posizioni senza prezzi per quel periodo vengono escluse, e un pulsante può offrire un periodo in cui tutte hanno prezzi.
- **Shock ipotetico**: clicca su uno scenario, come *Crollo azionario*, per eseguirlo; **Mostra lo shock per bucket** ti consente di modificarne le ipotesi.
- **Simulazione**: scegli una modalità — *Storia rimescolata* è quella consigliata — e un orizzonte, poi **Simula**. Leggi il cono come una gamma di possibilità, non come una previsione.

!!! note "La simulazione è ancora in beta"

    Il suo esito dipende fortemente da quanta storia contiene il periodo rispetto all'orizzonte — vedi [Why the Simulation Is Still in Beta](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="whatif-simulation" alt="Il riquadro E se…? Simulazione: l'avviso beta e l'avvertenza sul modello, le cinque modalità con Storia rimescolata consigliata, orizzonte, percorsi e seed, e dopo Simula le cifre terminali, il cono e Cosa ha assunto questa simulazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚩 Avvisi e dati mancanti {: #notices }

Una cifra di rischio vale solo quanto i prezzi che vi stanno dietro. Quando i dati mancano o sono obsoleti, la scheda lo dice, e cosa ha cambiato.

**Strumenti mostrati**

- **Qualità dei dati** — prezzi e tassi mancanti o obsoleti, e le posizioni che ne restano escluse → [qualità dei dati](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Come leggerlo**

- **Il banner in alto** elenca prezzi e tassi di cambio mancanti o obsoleti: sistemali con i suoi pulsanti, oppure con **Sync** in alto a destra.
- **L'avviso sopra i blocchi** dice quali risultati sono parziali, e perché.
- **Un banner dentro un blocco** nomina una cifra che non è stato possibile calcolare, con il motivo.
- **Un trattino (—)** significa che una cifra non ha potuto essere misurata: non significa mai zero.
- **Per riprovare**, premi **Aggiorna**, oppure esegui di nuovo lo strumento E se…?.

---

## 🔎 Buono a sapersi {: #good-to-know }

- **La scheda della Dashboard copre l'intero portafoglio** — ogni broker che possiedi con una quota superiore allo 0% — sull'intervallo di date e nella valuta della Dashboard. Ignora il filtro broker: un sottotitolo lo dice, e gli importi sotto le percentuali sono nascosti mentre un filtro è attivo.
- **Nella pagina di un broker**, la scheda mostra gli stessi blocchi per quel singolo broker.
- **Cambiare il periodo o la valuta** ricalcola ogni blocco e cancella i risultati di E se…?: eseguili di nuovo.
- **Dettagli di calcolo**, ripiegati in fondo a ogni blocco, mostrano su quanti dati si basano le cifre.

---

## 🔗 Correlati {: #related }

- 🧪 **[Scheda Correlazione](../assets/correlation.md)** — le stesse domande, poste a una selezione di asset che scegli tu
- 📚 **[Risk Metrics](../../financial-theory/technical-analysis/risk-metrics/index.md)** — la teoria dietro ogni cifra; l'icona del libro di ogni blocco la apre
- 📊 **[Dashboard](index.md)** — le altre schede, l'intervallo di date, la valuta e il filtro broker
- 🏦 **[Brokers](../brokers/index.md)** — la pagina di ogni broker, con la sua scheda Rischio
- 🛠️ **[Dettagli tecnici](../../developer/frontend/components/features/risk-lab.md#dashboard-risk-tab)** — per gli sviluppatori: come funziona questa scheda all'interno
