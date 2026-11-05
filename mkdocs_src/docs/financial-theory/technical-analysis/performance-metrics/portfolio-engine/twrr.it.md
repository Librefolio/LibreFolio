# ⏱️ TWRR (Tasso di Rendimento Ponderato per il Tempo)

## 💡 Che cos'è?
TWRR misura la **performance "pura"** degli asset e della strategia che hai scelto (il Mercato), ignorando completamente il momento e l'importo dei tuoi depositi o prelievi.

LibreFolio individua le interruzioni dei sottoperiodi dovute a flussi esterni a partire dalle variazioni della base di capitale. Questo include il capitale in natura valorizzato derivante da RETTIFICHE/TRASFERIMENTI, quindi gli asset iniziali sono trattati come capitale dell'investitore che affluisce al portafoglio, non come rendimento di mercato. Una rettifica in uscita non ha valore e non costituisce un flusso ([Capitale versato — Rettifiche in uscita](deposited-capital.md#outgoing-adjustments)): il valore delle relative quote esce dal NAV, e il rendimento del giorno registra questa uscita come una perdita.

È la metrica standard utilizzata dai fondi comuni e dagli ETF, perché i gestori dei fondi non hanno alcun controllo su quando i clienti depositano o prelevano capitale; devono essere valutati esclusivamente sui rendimenti degli investimenti sottostanti.

---

## 🧩 Che cos'è un sottoperiodo?
Per isolare la performance degli asset dalla tempistica dei flussi di cassa, TWRR suddivide la linea temporale di valutazione in intervalli più piccoli chiamati **sottoperiodi**.

Un **sottoperiodo** è un intervallo di tempo continuo tra due flussi di cassa esterni consecutivi (depositi o prelievi).

Per definizione:
* Un nuovo sottoperiodo inizia immediatamente dopo qualsiasi flusso di cassa esterno.
* Durante un dato sottoperiodo, **nessun capitale esterno viene aggiunto o rimosso** dal portafoglio.
* Di conseguenza, qualsiasi variazione del valore del portafoglio durante un sottoperiodo è determinata interamente dalla performance degli asset (fluttuazioni di prezzo, dividendi, interessi).

---

## 🧮 Come funziona
TWRR calcola il tasso di rendimento di ciascun sottoperiodo singolarmente e poi li collega (moltiplica) tra loro.

$$
R_{\text{TWRR}} = \prod_{i=1}^{n} (1 + r_i) - 1 = (1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1
$$

**Descrizione delle variabili:**

* $r_i$ = Il tasso di rendimento del sottoperiodo $i$.
* $n$ = Il numero totale dei sottoperiodi.

---

??? note "Esempio di sviluppo del TWRR"

    ### 🧾 1. Lo scenario

    * **Giorno 0:** inizi il tuo portafoglio con un deposito iniziale di **€1.000**.
    * **Giorno 10:** il mercato sale. Il tuo portafoglio ora vale **€1.100**. In questo stesso giorno depositi altri **€500** in contanti.
    * **Giorno 20:** il mercato scende. Il tuo portafoglio chiude con un valore finale di **€1.440**.
    
    ### 🧩 2. Suddivisione in sottoperiodi
    La linea temporale è divisa in due sottoperiodi a causa del flusso di cassa del Giorno 10:
    
    **Sottoperiodo 1 (dal Giorno 0 al Giorno 10):**

    * Valore iniziale (\(V_{\text{start}}\)): **€1.000**
    * Valore finale (\(V_{\text{end}}\) prima del flusso di cassa): **€1.100**
    * Rendimento del sottoperiodo (\(r_1\)):

    \[
    r_1 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1\,100}{1\,000} - 1 = +10\%
    \]
    
    **Sottoperiodo 2 (dal Giorno 10 al Giorno 20):**

    * Valore iniziale (\(V_{\text{start}}\) dopo il flusso di cassa): €1.100 + €500 di deposito = **€1.600**
    * Valore finale (\(V_{\text{end}}\)): **€1.440**
    * Rendimento del sottoperiodo (\(r_2\)):

    \[
    r_2 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1\,440}{1\,600} - 1 = -10\%
    \]
    
    ### 🧮 3. Sviluppo del calcolo del TWRR
    Colleghiamo tra loro i rendimenti dei sottoperiodi:
    
    \[
    \begin{aligned}
    R_{\text{TWRR}} &= (1 + r_1) \times (1 + r_2) - 1 \\
    &= (1 + 0{,}10) \times (1 - 0{,}10) - 1 \\
    &= 1{,}10 \times 0{,}90 - 1 \\
    &= 0{,}99 - 1 \\
    &= -1\%
    \end{aligned}
    \]
    
    Gli asset che hai scelto sono saliti del 10% e poi scesi del 10%, con un rendimento netto a livello di asset del **-1%**.
    
    ### ⚖️ 4. TWRR vs. ROI semplice
    Calcoliamo il **ROI semplice** per lo stesso identico scenario, per vedere il contrasto:

    * Totale liquidità netta investita = €1.000 + €500 = **€1.500**
    * Valore finale del portafoglio = **€1.440**
    * ROI semplice:

    \[
    ROI = \frac{1\,440 - 1\,500}{1\,500} = -4\%
    \]
    
    **Perché sono diversi?**

    * Il **ROI semplice (-4%)** mostra la performance effettiva e grezza del tuo portafoglio. È penalizzato dal fatto che hai depositato €500 subito prima di un calo del -10%, rendendo la tua perdita più pesante in termini assoluti.
    * Il **TWRR (-1%)** isola la performance della strategia degli asset. Mostra cosa sarebbe successo se avessi investito un'unica somma all'inizio e non l'avessi mai più toccata.

---

## 🎯 Quando usarlo
* Per valutare la qualità degli **asset e della strategia che hai scelto**, indipendentemente dal tuo tasso di risparmio personale o dalla tempistica.
* Per confrontare direttamente la performance del tuo portafoglio con benchmark esterni (come l'S&P 500 o un ETF indicizzato).

---

## 🚫 Quando il TWRR non viene mostrato {: #when-no-twrr }

La scheda KPI e la linea TWRR del grafico della dashboard seguono la stessa regola in ogni giorno del periodo: un giorno ha un TWRR solo quando il valore del portafoglio in quel giorno è maggiore di zero. Un portafoglio che hai svuotato — tutto venduto e la liquidità prelevata — o uno i cui debiti superano ciò che detiene non ha alcun rendimento ponderato per il tempo da mostrare.

In un giorno del genere la scheda mostra `—` e la linea presenta un vuoto. La scheda mostra sempre l'ultimo punto della linea, quindi una scheda senza TWRR va di pari passo con una linea che termina con un vuoto, e anche l'[Effetto timing](timing-effect.md), che richiede il TWRR, mostra `—`. Quando nuovi depositi riportano il valore sopra zero, la linea riprende dal rendimento a cui era arrivata prima del vuoto: i giorni a zero non aggiungono né guadagni né perdite, e la catena dei sottoperiodi continua a capitalizzare da quel punto.

Il primo punto della linea è l'eccezione: è sempre 0, il punto da cui parte ogni rendimento del periodo.

---

!!! tip "Analizzare la differenza di performance"

    Per capire in che modo i tuoi flussi di cassa personali hanno fatto deviare i tuoi rendimenti effettivi dal rendimento puro della strategia (TWRR), consulta la pagina [Effetto timing](timing-effect.md).
