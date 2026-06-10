# Algoritmi Finanziari: TWRR e MWRR

Questo documento descrive ad alto livello l'implementazione degli algoritmi per il calcolo del **Time-Weighted Rate of Return (TWRR)** e del **Money-Weighted Rate of Return (MWRR)** per LibreFolio.

## 1. Dati di Input Richiesti

Entrambi gli algoritmi richiedono di ricostruire la "storia" del portafoglio (o del singolo broker). I dati essenziali sono:

1. **Flussi di Cassa Esterni (Cash Flows)**: 
   * Depositi (Inflows) e Prelievi (Outflows).
   * *Nota sui Dividendi e Interessi*: I dividendi e gli interessi maturati **NON** sono considerati flussi di cassa esterni, perché non comportano nuova liquidità versata dalle tue tasche. L'incasso di un dividendo aumenta la liquidità del portafoglio (e quindi il NAV finale), aumentando in modo naturale il rendimento calcolato. Al contrario, se prelevi un dividendo per portarlo sul tuo conto corrente bancario (fuori da LibreFolio), quello figurerà come prelievo (Outflow).
2. **Valutazioni del Portafoglio (NAV - Net Asset Value)**:
   * Valore totale del portafoglio (Liquidità + Valore di mercato degli asset) calcolato alla fine della giornata in cui avviene un flusso di cassa e alla data di fine periodo.

---

## 2. Time-Weighted Rate of Return (TWRR)

Il TWRR misura la performance degli investimenti depurata dall'effetto temporale e dimensionale dei depositi e dei prelievi. È la metrica standard per valutare l'abilità di selezione degli asset e le performance generali del mercato.

### Algoritmo ad alto livello:
1. **Suddivisione in Sottoperiodi**:
   * Ogni volta che si verifica un flusso di cassa esterno (deposito/prelievo), il periodo di analisi viene spezzato in due sottoperiodi.
2. **Calcolo Rendimento del Sottoperiodo (HPR - Holding Period Return)**:
   * Per ogni sottoperiodo $i$, si valuta il portafoglio prima che avvenga il flusso di cassa.
   * La formula base è: $HPR_i = \frac{V_1 - V_0 - CF}{V_0 + CF_{in\_inizio\_periodo}}$ a seconda della convenzione (Solitamente si usa il metodo esatto: valutazione giornaliera esatta al momento del flusso).
   * In LibreFolio, valutando a fine giornata: $HPR_i = \frac{V_{fine\_giorno} - CF_{giorno} - V_{inizio\_giorno}}{V_{inizio\_giorno}}$
3. **Composizione Geometrica**:
   * Il TWRR totale è il prodotto dei rendimenti dei sottoperiodi:
   * $TWRR = [(1 + HPR_1) \times (1 + HPR_2) \times ... \times (1 + HPR_n)] - 1$

### Implementazione:
* **File unico `roi_utils.py`**: Poiché TWRR e MWRR condividono quasi esattamente gli stessi dati in ingresso (serie storica di NAV e date dei flussi), coesisteranno come funzioni pure separate all'interno di un unico file `backend/app/utils/financial/roi_utils.py`.
* **Input**: Lista temporale dei NAV nei giorni in cui c'è un movimento e Lista dei flussi di cassa.
* **Logica**: Identifica i giorni con Cash Flow, calcola l'HPR per i frame temporali successivi, e restituisce il compounding geometrico.

---

## 3. Money-Weighted Rate of Return (MWRR)

L'MWRR corrisponde al Tasso Interno di Rendimento (IRR) o XIRR (IRR esteso per flussi di cassa a date irregolari). Misura la performance effettiva dell'investitore, premiando o penalizzando il "timing" dei versamenti e dei prelievi in base alle fasi di mercato.

### Algoritmo ad alto livello:
1. **Identificazione dei Flussi (Cash Flows Set)**:
   * $CF_0$: Valore iniziale del portafoglio (investimento iniziale al tempo $t_0$, inserito come negativo ` -V_0 `).
   * $CF_1 ... CF_{n-1}$: Tutti i versamenti successivi (flussi in entrata sul broker, negativi per l'investitore) e prelievi (flussi in uscita dal broker, positivi per l'investitore).
   * $CF_n$: Valore finale del portafoglio alla data di fine analisi $t_n$ (figurativamente prelevato, quindi positivo ` +V_n `).
2. **Equazione di XIRR**:
   * Trovare il tasso di rendimento annuo $r$ che azzera il Net Present Value (NPV):
   * $NPV = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{d_i - d_0}{365}}} = 0$
3. **Risoluzione Numerica**:
   * Poiché non esiste una formula chiusa per $r$, si utilizza un metodo numerico iterativo (metodo di Newton-Raphson).

### Implementazione:
* Come per il TWRR, questa logica risiederà come funzione pura in `roi_utils.py`.
* **Input**: Lista di tuple `(Data, Importo_Flusso)` inclusivi del NAV iniziale e finale.
* **Logica**: Utilizzo della funzione `scipy.optimize.newton` per trovare la radice $r$ dell'equazione NPV. Affidarsi a `scipy` garantisce robustezza (scritto in C, fortemente testato) e previene fastidiosi edge-case di convergenza matematica (loop infiniti) che potrebbero occorrere con implementazioni custom del metodo Newton-Raphson quando i flussi di cassa cambiano di segno molte volte.

---

## 4. Return on Investment (ROI Semplice)

Accanto alle metriche complesse, verrà esposto anche il ROI Semplice, che è la metrica più immediata e facilmente comprensibile dall'utente: "Quanti soldi ho fatto rispetto a quelli che ho messo di tasca mia?".

* **Formula**: $ROI = \frac{Valore\_Attuale - Capitale\_Investito}{Capitale\_Investito} \times 100$
* **Implementazione**: Anche questa metrica verrà calcolata come funzione pura esportata da `roi_utils.py` e inclusa nella dashboard.

---

## 5. Edge Cases e Scelte Architetturali

1. **Portafoglio Vuoto all'inizio**: Se il portafoglio nasce da zero, il calcolo parte logicamente dal primo deposito reale. L'algoritmo deve gestire in sicurezza divisioni per zero.
2. **Orchestrazione e Conversioni FX**: Le logiche in `twrr_service.py` e `mwrr_service.py` non parleranno mai con il database. `portfolio_service.py` si occuperà di:
   - Estrarre le transazioni.
   - Convertire tutti i flussi e i prezzi degli asset nella *base_currency* dell'utente alle date di riferimento.
   - Applicare le `share_percentage` in caso di broker condivisi.
   - Fornire array puliti (date, NAVs, CFs) ai services matematici.
3. **Uso di librerie matematiche robuste**: Per il root-finding di XIRR si utilizzerà `scipy.optimize.newton`. Trattandosi di un software finanziario, la precisione e l'affidabilità su portafogli con anni di complessi movimenti è prioritaria rispetto al risparmio di qualche decina di MB nelle dipendenze del server.
