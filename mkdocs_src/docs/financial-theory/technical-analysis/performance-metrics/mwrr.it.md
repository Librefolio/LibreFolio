# 💵 MWRR (Rendimento Ponderato per il Capitale) / XIRR

*[⬅️ Torna alla Panoramica delle Metriche di Performance](index.md)*

## 💡 Cos'è?
Il MWRR (conosciuto anche come Tasso Interno di Rendimento) misura la **tua performance personale** come investitore. A differenza delle metriche focalizzate solo sugli asset, il MWRR tiene conto sia del rendimento degli strumenti sottostanti, sia del **tempismo (timing) e dell'entità** dei tuoi depositi e prelievi.

Per offrire una visibilità completa, LibreFolio distingue tra due forme di questa metrica: **MWRR Annualizzato** e **MWRR Cumulativo**.

---

## 📈 MWRR Annualizzato vs. MWRR Cumulativo

### MWRR Annualizzato {: #annualized-mwrr }
Il MWRR Annualizzato è il tasso composto annuo che rende il Valore Attuale Netto (NPV) di tutti i flussi di cassa pari a zero.

Questo tasso composto è matematicamente equivalente al **CAGR** (Compound Annual Growth Rate - Tasso di crescita annuale composto) del tuo capitale effettivamente investito, rappresentando il tasso di crescita annuo costante necessario affinché il capitale iniziale raggiunga il saldo finale, tenendo conto di tutti i movimenti intermedi.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
$$

??? note "🧮 Come si srotola l'equazione NPV"

    #### 1. Forma Intuitiva del Valore Finale
    Immagina di voler proiettare il valore finale del tuo portafoglio (NAV) facendo crescere ciascun flusso di cassa ad un tasso composto \(r\):
    
    \[
    NAV_{finale} = CF_0 \times (1 + r)^{\frac{d_0}{365}} + CF_1 \times (1 + r)^{\frac{d_1}{365}} + \dots + CF_n \times (1 + r)^{\frac{d_n}{365}}
    \]
    
    Dove \(d_i\) rappresenta il numero di giorni in cui ciascun flusso di cassa è rimasto investito durante il periodo.
    
    #### 2. Portare tutto al Valore Attuale (NPV = 0)
    Dividendo entrambi i membri dell'equazione per \((1 + r)^{\frac{\text{giorni totali}}{365}}\), riportiamo tutti i flussi di cassa all'inizio del periodo (\(t_0\)). Si ottiene così l'equazione standard del Valore Attuale Netto (NPV) dove la somma dei flussi attualizzati è pari a zero:
    
    \[
    0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
    \]
    
    Dove \(t_i\) è il numero di giorni trascorsi dall'inizio del periodo alla data del flusso di cassa \(i\).
    
    #### 3. Esempio di Srotolamento dei Flussi di Cassa
    Vediamo come si popolano i flussi di cassa per un portafoglio in un periodo di 31 giorni:
    
    * **Giorno 0:** Il portafoglio iniziale vale 1.000 € (rappresentato come deposito/investimento).
    * **Giorno 15:** Depositi 100 €.
    * **Giorno 31:** Il NAV finale del portafoglio è di 1.150 €.
    
    Innanzitutto, costruiamo la tabella delle transazioni dal punto di vista del portafoglio (il denaro che entra nel portafoglio investito è negativo, quello che ritorna indietro all'investitore è positivo):
    
    | Passo (\(i\)) | Giorno (\(t_i\)) | Evento | Flusso di Cassa Portafoglio (\(CF_i\)) |
    |-------------|----------------|--------|--------------------------------------|
    | 0 | 0 | Saldo Iniziale | **-1.000 €** (Uscita) |
    | 1 | 15 | Deposito | **-100 €** (Uscita) |
    | 2 | 31 | Liquidazione Ipotetica (NAV) | **+1.150 €** (Entrata) |
    
    Ora srotoliamo queste transazioni nella sommatoria NPV:
    
    \[
    0 = -1000 + \frac{-100}{(1+r)^{\frac{15}{365}}} + \frac{1150}{(1+r)^{\frac{31}{365}}}
    \]
    
    Il solver matematico cerca iterativamente il valore di \(r\) (MWRR Annualizzato) che rende il membro destro dell'equazione pari a 0.

    #### 4. Ancoraggio del Grafico Cumulativo
    Questa convenzione sui segni assicura che, nel primissimo giorno (\(t_0\)), il deposito iniziale (\(CF_0 = -1000\)) e la liquidazione ipotetica (\(CF_1 = +1000\)) si annullino perfettamente a vicenda:
    
    \[
    0 = -1000 + 1000 = 0\%
    \]
    
    Questo àncora l'inizio del grafico del MWRR Cumulativo esattamente allo **0%**.

**Descrizione delle Variabili:**

* $r$ = MWRR Annualizzato (che rappresenta il CAGR del tuo denaro reale).
* $CF_i$ = Flusso di cassa dal punto di vista dell'investitore:
    * **Flussi di cassa negativi ($CF_i < 0$):** Capitale versato nel portafoglio (depositi, acquisti). Questo rappresenta denaro che esce dal portafoglio/portafogli dell'investitore per essere investito.
    * **Flussi di cassa positivi ($CF_i > 0$):** Capitale restituito all'investitore (prelievi, dividendi). Questo rappresenta denaro che ritorna nel portafoglio personale.
    * **Valutazione finale ($CF_n > 0$):** Il Net Asset Value (NAV) finale del portafoglio alla fine del periodo, trattato come un afflusso positivo (una liquidazione ipotetica in cui l'intero portafoglio viene convertito nuovamente in liquidità che ritorna all'investitore).
* $t_i$ = Giorni trascorsi dall'inizio del periodo ($t_0 = 0$).

**Concetti Chiave:**

* Rappresenta una **velocità o tasso annuo composto** di crescita.
* È ideale per confronti a lungo termine (es. per confrontare la tua performance con un tasso di interesse bancario o con il CAGR).
* **Avviso di Volatilità:** Su periodi brevi (es. pochi giorni o settimane), il rendimento annualizzato può essere estremamente volatile e mostrare percentuali enormi perché la matematica ipotizza che il rendimento di pochi giorni si ripeta per l'intero anno (365 giorni).

### MWRR Cumulativo {: #cumulative-mwrr }
Il MWRR Cumulativo rappresenta il rendimento totale equivalente del periodo, ottenuto capitalizzando il tasso annualizzato per la durata reale della finestra temporale selezionata.

**Formula Diretta (senza radici, usa direttamente $r$):**

$$
\text{MWRR}_{\text{cumulativo}} = (1 + r)^{\frac{\text{giorni}}{365}} - 1
$$

**Formula per Tasso Giornaliero (con radice):**

$$
\text{MWRR}_{\text{cumulativo}} = (1 + r_d)^{\text{giorni}} - 1 \quad \text{dove} \quad r_d = \sqrt[365]{1 + r} - 1
$$

Le due formule sono matematicamente equivalenti. Tuttavia, a livello computazionale, si preferisce la formula diretta con $r$ (senza radici) una volta che il tasso annualizzato $r$ è stato trovato, poiché l'elevamento a potenza diretto è più semplice ed efficiente da calcolare per il software.

**Descrizione delle Variabili:**

* $\text{giorni}$ = Il numero effettivo di giorni di calendario nel periodo selezionato.

**Concetti Chiave:**

* Rappresenta la **distanza totale percorsa** nel periodo.
* Parte da 0% e cresce lungo la finestra temporale, rendendolo la metrica ideale da tracciare nel grafico seriale.
* **Non è un ROI semplice:** Sebbene rappresenti un rendimento cumulativo, si tratta di un rendimento cumulativo ponderato per il capitale (money-weighted). Non va confuso con il ROI semplice, che ignora il timing dei flussi di cassa.

---

## 🔢 Esempio Numerico su 10 Anni

Vediamo uno scenario su 10 anni per capire come il timing influenzi la performance e come si convertono queste metriche:

* **Anno 0:** Depositi **10.000 €**.
* **Anno 5:** Depositi altri **90.000 €**.
* **Anno 10:** Il valore finale del portafoglio (NAV) è **200.000 €**.

### Confronto ROI Semplice
Il ROI semplice viene calcolato esclusivamente sul totale netto dei versamenti:

$$
ROI = \frac{200.000 - 100.000}{100.000} = +100\%
$$

### Effetto Timing del MWRR
Se il grosso del capitale (90.000 €) è stato depositato all'Anno 5, subito prima di un forte recupero pluriennale del mercato, il tuo denaro ha lavorato con estrema efficienza. Poiché la cifra più consistente è rimasta esposta agli anni ad alta crescita, il tuo **MWRR Annualizzato** risulterà molto superiore al TWRR del mercato.

Utilizzando un solver matematico NPV per questo specifico scenario:
* Il **MWRR Annualizzato ($r$)** è esattamente del **13,02%**.

### Conversione in MWRR Cumulativo
Capitalizzando questo rendimento annualizzato del 13,02% per un periodo di 10 anni:

$$
\text{MWRR}_{\text{cumulativo}} = (1 + 0,130227)^{10} - 1 \approx +240,14\%
$$

### Cosa significa +240,14%?
* **Non** significa che i 100.000 € totali che hai versato siano diventati 340.140 €.
* Significa che un **euro teorico**, investito all'inizio del periodo di 10 anni e mai più toccato, sarebbe diventato 3,40 €, ottenendo un rendimento totale del 240,14% crescendo alla stessa velocità media composta generata dai tuoi flussi reali.

---

## 🖥️ Integrazione UI e Uso nella Dashboard

LibreFolio mostra queste metriche di performance nella dashboard:

### Grafico Percentuale (`%`)
Le serie tracciate utilizzano il **MWRR Cumulativo**, il **TWRR Cumulativo** e il **ROI Semplice**. Questo consente un confronto visivo diretto, in quanto tutte e tre le serie partono dallo 0% e mostrano l'avanzamento totale lungo il periodo temporale selezionato.

### Card dei KPI
* **ROI Semplice** (Metrica principale per il rendimento assoluto).
* **TWRR Cumulativo** (Indicatore della performance di strategia/allocazione).
* **MWRR Cumulativo** (Indicatore principale del timing personale).
* **MWRR Annualizzato** (Mostrato come metrica secondaria/comparativa per comprendere il tasso composto annuo).

!!! tip "Analizzare la Differenza di Performance"

    Per interpretare la differenza tra MWRR cumulativo e TWRR cumulativo, vedi la pagina dell'[Effetto Timing](timing-effect.md).

