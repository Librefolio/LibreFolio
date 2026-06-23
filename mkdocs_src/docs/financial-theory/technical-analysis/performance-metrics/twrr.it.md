# ⏱️ TWRR (Rendimento Ponderato nel Tempo)

*[⬅️ Torna alla Panoramica delle Metriche di Performance](index.md)*

## 💡 Cos'è?
Il TWRR (dall'inglese *Time-Weighted Rate of Return*) misura la **performance "pura"** dei tuoi asset e della tua strategia d'investimento (Il Mercato), ignorando completamente il tempismo (timing) e l'entità dei tuoi depositi o prelievi.

È la metrica standard utilizzata dai fondi comuni di investimento e dagli ETF perché i gestori di fondi non hanno alcun controllo su quando i clienti decidono di versare o prelevare capitali; devono quindi essere valutati unicamente sui rendimenti generati dagli investimenti sottostanti.

---

## 🧩 Cos'è un Sotto-periodo?
Per isolare la performance degli asset dal timing dei flussi di cassa, il TWRR suddivide la linea temporale di valutazione in intervalli più piccoli chiamati **sotto-periodi**.

Un **sotto-periodo** è un intervallo di tempo continuo compreso tra due flussi di cassa esterni consecutivi (depositi o prelievi).

Per definizione:
* Un nuovo sotto-periodo inizia immediatamente dopo qualsiasi flusso di cassa esterno.
* Durante un determinato sotto-periodo, **nessun capitale esterno viene aggiunto o rimosso** dal portafoglio.
* Di conseguenza, qualsiasi variazione del valore del portafoglio durante un sotto-periodo è dovuta esclusivamente alla performance degli asset (oscillazioni di prezzo, dividendi, interessi).

---

## 🧮 Come funziona
Il TWRR calcola il tasso di rendimento di ciascun sotto-periodo individualmente e poi li collega (moltiplica) tra loro.

$$
R_{\text{TWRR}} = \prod_{i=1}^{n} (1 + r_i) - 1 = (1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1
$$

**Descrizione delle Variabili:**

* $r_i$ = Il tasso di rendimento del sotto-periodo $i$.
* $n$ = Il numero totale di sotto-periodi.

---

??? note "Esempio di Srotolamento del TWRR"

    ### 1. Lo Scenario

    * **Giorno 0:** Avvii il tuo portafoglio con un deposito iniziale di **1.000 €**.
    * **Giorno 10:** Il mercato sale. Il tuo portafoglio vale ora **1.100 €**. Lo stesso giorno effettui un altro deposito di **500 €**.
    * **Giorno 20:** Il mercato scende. Il tuo portafoglio chiude con un valore finale di **1.440 €**.
    
    ### 2. Scomposizione dei Sotto-periodi
    La linea temporale viene divisa in due sotto-periodi a causa del flusso di cassa avvenuto al Giorno 10:
    
    **Sotto-periodo 1 (dal Giorno 0 al Giorno 10):**

    * Valore Iniziale (\(V_{\text{start}}\)): **1.000 €**
    * Valore Finale (\(V_{\text{end}}\) prima del flusso di cassa): **1.100 €**
    * Rendimento del Sotto-periodo (\(r_1\)):

    \[
    r_1 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1.100}{1.000} - 1 = +10\%
    \]
    
    **Sotto-periodo 2 (dal Giorno 10 al Giorno 20):**

    * Valore Iniziale (\(V_{\text{start}}\) dopo il flusso di cassa): 1.100 € + 500 € (deposito) = **1.600 €**
    * Valore Finale (\(V_{\text{end}}\)): **1.440 €**
    * Rendimento del Sotto-periodo (\(r_2\)):

    \[
    r_2 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1.440}{1.600} - 1 = -10\%
    \]
    
    ### 3. Srotolamento del Calcolo del TWRR
    Colleghiamo tra loro i rendimenti dei sotto-periodi:
    
    \[
    \begin{aligned}
    R_{\text{TWRR}} &= (1 + r_1) \times (1 + r_2) - 1 \\
    &= (1 + 0,10) \times (1 - 0,10) - 1 \\
    &= 1,10 \times 0,90 - 1 \\
    &= 0,99 - 1 \\
    &= -1\%
    \end{aligned}
    \]
    
    Gli asset che hai scelto sono saliti del 10% e poi scesi del 10%, risultando in un rendimento netto a livello di asset pari a **-1%**.
    
    ### 4. TWRR vs. ROI Semplice
    Calcoliamo il **ROI Semplice** sullo stesso identico scenario per vedere il contrasto:

    * Capitale netto totale investito = 1.000 € + 500 € = **1.500 €**
    * Valore finale del portafoglio = **1.440 €**
    * ROI Semplice:

    \[
    ROI = \frac{1.440 - 1.500}{1.500} = -4\%
    \]
    
    **Perché sono diversi?**

    * **Il ROI Semplice (-4%)** mostra la performance reale e cruda del tuo portafoglio. È penalizzato perché hai depositato 500 € subito prima di un calo del -10%, rendendo la tua perdita maggiore in termini assoluti.
    * **Il TWRR (-1%)** isola la performance della strategia degli asset. Mostra cosa sarebbe accaduto se avessi investito una singola somma all'inizio e non l'avessi mai più toccata.

---

## 🎯 Quando usarlo
* Per valutare la qualità degli **asset e della strategia che hai scelto**, indipendentemente dal tuo risparmio personale o dal tempismo dei versamenti.
* Per confrontare la performance del tuo portafoglio direttamente con benchmark esterni (come l'S&P 500 o un ETF su indice).

---

!!! tip "Analizzare la Differenza di Performance"

    Per comprendere in che modo i tuoi flussi di cassa personali hanno fatto deviare i tuoi rendimenti effettivi da quelli della strategia pura (TWRR), vedi la pagina dell'[Effetto Timing](timing-effect.md).

