# 💵 MWRR (Money-Weighted Rate of Return) / XIRR

*[⬅️ Torna alla Panoramica delle Metriche di Performance](index.md)*

## 💡 Cos'è?
Il MWRR (conosciuto anche come Tasso Interno di Rendimento) misura la *tua performance personale*. Pesa fortemente i periodi in cui avevi investito la maggior quantità di denaro.

## 🧮 Come funziona
Analizza le date esatte e l'entità di tutti i tuoi flussi di cassa (depositi e prelievi) e il valore finale del portafoglio, calcolando il tasso di interesse costante che una banca avrebbe dovuto offrirti per raggiungere l'esatto stesso risultato finale.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

Dove $CF_i$ è ogni singolo flusso di cassa (depositi positivi, prelievi negativi, valore finale del portafoglio positivo).

## 🎯 Quando usarlo
- Per giudicare il **tuo timing personale**.
- Per vedere la realtà nuda e cruda dell'effettiva crescita del tuo denaro.

## 📈 Come viene calcolata la Serie Cumulativa (Grafico)
Per visualizzare il MWRR come un grafico storico nel tempo, il calcolo viene eseguito **cumulativamente** dall'inizio per ogni singolo giorno della serie. 

Per ogni punto dati tracciato al giorno $t_N$:

1. Il calcolo considera l'intera finestra temporale da $t_0$ a $t_N$.
2. Imposta l'equazione del Valore Attuale Netto (NPV) in cui il flusso di cassa iniziale a $t_0$ è il valore di partenza del portafoglio (rappresentato come un flusso di cassa negativo: un "investimento").
3. Tutti i flussi di cassa intermedi tra $t_0$ e $t_N$ vengono riportati sulla linea temporale.
4. Il flusso di cassa finale a $t_N$ rappresenta la liquidazione ipotetica del portafoglio, che è il NAV a $t_N$ (rappresentato come un flusso di cassa positivo). 

**Caso limite matematico importante:** 
Se un flusso di cassa esterno avviene esattamente nell'ultimo giorno $t_N$ del periodo valutato, il NAV a $t_N$ incorpora già quel flusso di cassa. Nell'equazione NPV per quel giorno specifico, il flusso di cassa netto finale deve tenere conto sia del NAV finale che del flusso di cassa effettuato in quello stesso giorno. 

**Esempio:**
Immagina di iniziare a $t_0$ con un portafoglio di \$1.000. 
- Il flusso di cassa a $t_0$ è -\$1.000.
- Al giorno $t_{31}$, depositi altri \$100.
- Il NAV del tuo portafoglio balza immediatamente a \$1.100 (assumendo che non ci sia stata crescita del mercato). 

Se l'algoritmo utilizzasse il NAV finale di +\$1.100 come flusso di cassa terminale senza compensare il deposito effettuato esattamente in quel giorno, la matematica assumerebbe che un investimento di \$1.000 sia cresciuto a \$1.100 puramente grazie alla performance del mercato (un falso guadagno del 10%). Includendo correttamente il deposito di -\$100 al giorno $t_{31}$ insieme al NAV terminale, il flusso di cassa netto finale diventa +\$1.000 (\$1.100 - \$100), dimostrando correttamente che il rendimento reale è stato dello 0%.

Questa logica assicura inoltre che, nel primissimo giorno ($t_0$), il NAV di partenza e l'investimento iniziale si annullino perfettamente a vicenda, ancorando l'inizio del grafico esattamente allo 0%.
