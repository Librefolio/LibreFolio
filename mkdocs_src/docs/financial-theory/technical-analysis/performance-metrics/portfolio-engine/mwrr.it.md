# 💵 MWRR (tasso di rendimento ponderato per i flussi di cassa) / XIRR

## 💡 Cos'è?
Il MWRR (noto anche come tasso di rendimento interno) misura la **tua performance personale** come investitore. A differenza delle metriche relative ai soli asset, tiene conto sia della performance degli asset sottostanti sia della **tempistica e dell'entità** dei tuoi depositi e prelievi. 

Per offrire una visibilità completa, LibreFolio distingue due forme di questa metrica: **MWRR annualizzato** e **MWRR cumulato**.

---

## 📈 MWRR annualizzato vs. MWRR cumulato

### 📈 MWRR annualizzato {: #annualized-mwrr }
Il MWRR annualizzato è il tasso di rendimento annuo composto che rende pari a zero il Valore Attuale Netto (NPV) di tutti i flussi di cassa. 

Questo tasso composto è matematicamente equivalente al **CAGR** (tasso di crescita annuo composto) del tuo denaro effettivamente investito, e rappresenta il tasso di crescita annuo livellato necessario affinché il capitale cresca fino al saldo finale, tenendo conto di tutti i movimenti intermedi.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
$$

??? note "🧮 Come si sviluppa l'equazione del NPV"

    #### 1. Forma intuitiva del valore finale
    Immagina di provare a proiettare il tuo valore netto finale (NAV) facendo crescere ogni flusso di cassa a un tasso composto \(r\):
    
    \[
    NAV_{finale} = CF_0 \times (1 + r)^{\frac{d_0}{365}} + CF_1 \times (1 + r)^{\frac{d_1}{365}} + \dots + CF_n \times (1 + r)^{\frac{d_n}{365}}
    \]
    
    Dove \(d_i\) rappresenta il numero di giorni in cui ciascun flusso di cassa è rimasto investito durante il periodo.
    
    #### 2. Attualizzazione al Valore Attuale Netto (NPV = 0)
    Dividendo entrambi i membri dell'equazione per \((1 + r)^{\frac{\text{giorni totali}}{365}}\), riportiamo tutti i flussi di cassa all'inizio del periodo (\(t_0\)). Si ottiene così l'equazione standard del Valore Attuale Netto, in cui la somma dei flussi di cassa attualizzati è pari a zero:
    
    \[
    0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
    \]
    
    Dove \(t_i\) è il numero di giorni dall'inizio del periodo alla data del flusso di cassa \(i\).
    
    #### 3. Esempio di sviluppo dei flussi di cassa
    Vediamo come si distribuiscono i flussi di cassa per un portafoglio in un periodo di 31 giorni:
    
    * **Giorno 0:** Il valore iniziale del portafoglio è €1.000 (rappresentato come deposito/investimento).
    * **Giorno 15:** Effettui un deposito di €100.
    * **Giorno 31:** Il valore netto finale (NAV) del portafoglio è €1.150.
    
    Per prima cosa, costruiamo la tabella delle transazioni dal punto di vista dell'investitore (il denaro che entra nel portafoglio è negativo, il denaro che ritorna è positivo):
    
    | Passo (\(i\)) | Giorno (\(t_i\)) | Evento | Flusso di cassa personale (\(CF_i\)) |
    |------------|-------------|-------|---------------------------|
    | 0 | 0 | Saldo iniziale | **-€1.000** (Deflusso) |
    | 1 | 15 | Deposito | **-€100** (Deflusso) |
    | 2 | 31 | Liquidazione ipotetica (NAV) | **+€1.150** (Afflusso) |
    
    Ora espandiamo queste transazioni nella sommatoria del NPV:
    
    \[
    0 = -1000 + \frac{-100}{(1+r)^{\frac{15}{365}}} + \frac{1150}{(1+r)^{\frac{31}{365}}}
    \]
    
    Il risolutore matematico cerca iterativamente il valore di \(r\) (MWRR annualizzato) che rende il lato destro di questa equazione uguale a 0. 

    #### 4. Ancoraggio del grafico cumulato
    Questa convenzione di segno garantisce che, nel primissimo giorno (\(t_0\)), il deposito iniziale (\(CF_0 = -1000\)) e la liquidazione ipotetica (\(CF_1 = +1000\)) si annullino a vicenda:
    
    \[
    0 = -1000 + 1000 = 0\%
    \]
    
    Ciò ancora l'inizio del grafico del MWRR cumulato esattamente a **0%**.

**Descrizione delle variabili:**

* $r$ = MWRR annualizzato (che rappresenta il CAGR del tuo denaro effettivo).
* $CF_i$ = Flusso di cassa dal punto di vista dell'investitore:
    * **Flussi di cassa negativi ($CF_i < 0$):** Capitale impegnato nel portafoglio (depositi, investimenti). Rappresenta denaro che esce dalle disponibilità dell'investitore.
    * **Flussi di cassa positivi ($CF_i > 0$):** Capitale restituito all'investitore (prelievi, dividendi). Rappresenta denaro che ritorna nelle disponibilità dell'investitore.
    * **Valutazione finale ($CF_n > 0$):** Il valore netto finale (NAV) del portafoglio alla fine del periodo, trattato come un afflusso positivo (una liquidazione ipotetica in cui l'intero portafoglio viene riconvertito in liquidità che ritorna nelle disponibilità dell'investitore).
* $t_i$ = Giorni trascorsi dall'inizio del periodo ($t_0 = 0$).

**Concetti chiave:**

* Rappresenta una **velocità/tasso annuo** di crescita.
* È ideale per confronti di lungo periodo (ad esempio, confrontare la tua performance con un tasso di interesse bancario annuo o con il CAGR).
* **Avviso sulla volatilità:** Su periodi brevi (ad esempio, pochi giorni o settimane), il rendimento annualizzato può essere molto volatile e mostrare percentuali estreme, perché il calcolo estrapola il rendimento di una finestra breve a un anno intero di 365 giorni.

LibreFolio costruisce i flussi di cassa del MWRR a partire dalle variazioni rispetto alla base del capitale, non dalle sole righe di deposito. Il capitale di tipo Rettifica/Trasferimento valorizzato in natura è quindi trattato come capitale conferito, anziché come un'improvvisa performance di investimento. Una rettifica in uscita non ha valore: non restituisce nulla all'investitore e non è un flusso di cassa ([Capitale versato — Rettifiche in uscita](deposited-capital.md#outgoing-adjustments)).

### 📊 MWRR cumulato {: #cumulative-mwrr }
Il MWRR cumulato rappresenta il rendimento totale equivalente nel periodo selezionato, ottenuto capitalizzando il tasso annualizzato per la durata effettiva di quella finestra.

**Formula diretta (senza radici, usa direttamente $r$):**

$$
\text{MWRR}_{\text{cumulato}} = (1 + r)^{\frac{\text{giorni}}{365}} - 1
$$

**Formula con tasso giornaliero (con radice):**

$$
\text{MWRR}_{\text{cumulato}} = (1 + r_d)^{\text{giorni}} - 1 \quad \text{dove} \quad r_d = \sqrt{1 + r} - 1
$$

Entrambe le formule sono matematicamente equivalenti. Tuttavia, dal punto di vista computazionale, una volta trovato il tasso annualizzato $r$, si preferisce la formula diretta che usa $r$ (senza radici), poiché l'elevamento a potenza diretto è più semplice ed efficiente da calcolare per il software.

**Descrizione delle variabili:**

* $\text{giorni}$ = Il numero effettivo di giorni di calendario nella finestra temporale selezionata.

**Concetti chiave:**

* Rappresenta la **distanza totale percorsa** nel periodo.
* Parte da 0% e cresce lungo la linea temporale, il che lo rende la metrica corretta per la visualizzazione in un grafico seriale.
* **Non è un semplice HPR:** Pur rappresentando un rendimento cumulato, si tratta di un rendimento cumulato ponderato per i flussi di cassa. Non va confuso con il semplice rendimento del periodo di detenzione (ROI), che ignora la tempistica dei flussi di cassa.

---

## 🔢 Esempio numerico su 10 anni

Consideriamo uno scenario di 10 anni per vedere come la tempistica influisce sulla performance e come si convertono queste metriche:

* **Anno 0:** Depositi **€10.000**.
* **Anno 5:** Depositi altri **€90.000**.
* **Anno 10:** Il tuo valore netto finale (NAV) è **€200.000**.

### 📉 Confronto con il ROI semplice
Il ROI semplice è calcolato esclusivamente sui contributi netti totali:

$$
ROI = \frac{200.000 - 100.000}{100.000} = +100\%
$$

### ⏱️ Effetto timing sul MWRR
Se la maggior parte del tuo capitale (€90.000) è stata depositata nell'anno 5, subito prima di una massiccia ripresa pluriennale del mercato, il tuo denaro ha lavorato in modo molto efficiente. Poiché la somma maggiore è stata esposta agli anni di forte crescita, il tuo **MWRR annualizzato** sarebbe stato molto più alto del TWRR del mercato.

Utilizzando un risolutore matematico NPV per questo specifico scenario:
* Il **MWRR annualizzato ($r$)** è esattamente **13,02%**.

### 🔁 Conversione in MWRR cumulato
Capitalizzando questo rendimento annualizzato del 13,02% nell'arco del periodo di 10 anni:

$$
\text{MWRR}_{\text{cumulato}} = (1 + 0{,}130227)^{10} - 1 \approx +240{,}14\%
$$

### 💡 Che cosa significa +240,14%?
* **Non** significa che i tuoi contributi totali di €100.000 siano cresciuti fino a €340.140.
* Significa che un **euro teorico**, investito all'inizio del periodo di 10 anni e lasciato intatto, sarebbe cresciuto fino a €3,40, ottenendo un rendimento totale del 240,14% crescendo alla stessa velocità composta media dei tuoi flussi di cassa effettivi.

---

## 🖥️ Integrazione nell'interfaccia utente e utilizzo della dashboard

LibreFolio mostra queste metriche di performance in tutta la dashboard:

### 📊 Grafico percentuale (`%`)
Le serie tracciate usano **MWRR cumulato**, **TWRR cumulato** e **ROI semplice**. Ciò consente un confronto visivo diretto e affiancato, poiché tutte e tre le serie partono da 0% e rappresentano il progresso totale nell'intervallo di tempo selezionato.

### 📐 La linea del MWRR è composta da punti reali {: #mwrr-line }

A differenza del TWRR e del ROI, il MWRR cambia anche in un giorno in cui non succede nulla: il tempo passa e, con più flussi, non esiste una forma chiusa che lo estenda da un giorno all'altro. Nel report del portafoglio, pertanto, non viene memorizzato nei [passaggi giornalieri](index.md#daily-states-as-steps) dello storico, ma in una serie propria, `mwrr_line`, i cui punti sono **valori reali**: ciascuno è il MWRR del periodo che termina in quel giorno, risolto in quel giorno, annualizzato e cumulato, secondo la stessa regola delle schede (vedi sotto). La linea ha un punto all'inizio e alla fine di ogni passaggio dello storico, più uno alla fine di ogni mese di calendario all'interno dei passaggi più lunghi di 62 giorni (al massimo 24 per passaggio); il suo primo punto è 0. Nulla tra due punti viene stimato o memorizzato: il grafico li unisce.

### 🧾 Schede KPI
* **ROI semplice** (Metrica principale per il rendimento assoluto).
* **TWRR cumulato** (Indicatore di performance della strategia/allocazione).
* **MWRR cumulato** (Indicatore principale della tempistica personale).
* **MWRR annualizzato** (Mostrato come metrica secondaria/comparativa per comprendere il tasso annuo composto).

### 🚫 Quando non viene mostrato il MWRR

Le schede KPI e la linea del MWRR del grafico seguono la stessa regola in ogni giorno del periodo. Un giorno ha un MWRR solo quando:

* il valore del portafoglio in quel giorno è maggiore di zero, e
* il periodo conserva ancora **capitale netto investito** in quel giorno: il valore con cui è iniziato, più i depositi, meno i prelievi effettuati fino a quel giorno (i flussi di capitale descritti sopra), è maggiore di zero.

Altrimenti non c'è alcun tasso: la scheda mostra `—` e la linea presenta un vuoto (un punto senza valore). Dopo prelievi netti, il vuoto inizia il giorno in cui questi portano il capitale netto investito a zero o a un valore inferiore, e dura finché nuovi depositi non lo riportano sopra zero. Le schede mostrano sempre l'ultimo punto della linea, quindi una scheda senza MWRR corrisponde a una linea che termina con un vuoto. Un giorno è inoltre privo di MWRR quando nessun tasso risolve l'equazione dei flussi di cassa: LibreFolio non mostra mai un tasso che non la risolva.

!!! tip "Analizzare la differenza di performance"

    Per interpretare la differenza tra MWRR cumulato e TWRR cumulato, consulta la pagina [Effetto timing](timing-effect.md).
