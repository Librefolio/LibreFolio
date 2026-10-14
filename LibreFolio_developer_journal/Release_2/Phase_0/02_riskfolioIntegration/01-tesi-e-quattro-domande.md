# 01 — Tesi e quattro domande

**Data**: 16 Settembre 2026
**Stato**: ✅ approvata dal developer
**Ruolo**: fonte di ogni decisione successiva. Se una scelta non discende da qui, è
arbitraria.

---

## 1. La diagnosi

La prima campagna ha risposto alla domanda:

> ❌ *«Quali strumenti di analisi del rischio esistono?»*

Risposta ineccepibile — 9 analytics, 6 segnali rolling, contratto matematico rigoroso.
Ma da quella domanda discende una catena obbligata:

```text
ogni metrica pesa uguale
  → le implementi tutte
    → la UI diventa una lista verticale
      → l'utente non sa dove guardare
        → banner beta
```

Non è sfortuna né mancanza di tempo: è la conseguenza della domanda iniziale.

---

## 2. La tesi

> # Risk non deve rispondere «quanto rischio ho?» (un numero).
> # Deve rispondere «il mio portafoglio è quello che credo che sia?» (una sorpresa).

Un numero di rischio isolato non produce alcuna decisione: l'utente lo legge, non sa se
sia alto o basso, e chiude la pagina. Una **discrepanza** fra ciò che crede e ciò che è
produce sempre una decisione — anche solo quella di non fare niente, ma consapevolmente.

Conseguenza operativa: ogni vista Risk deve poter finire con la frase *«non lo sapevo»*.
Se una sezione non può produrre quella frase, non serve.

---

## 3. Le quattro domande

| | Domanda | Natura | Strumenti |
|---|---|---|---|
| **L1** | **Quanto può fare male?** | fatti osservati, magnitudo | CVaR/VaR · max drawdown + durata · drawdown corrente |
| **L2** | **Sono diversificato come credo?** | struttura, composizione | correlazione · contributo al rischio |
| **L3** | **Sto venendo pagato per questo rischio?** | relatività, confronto | volatilità annua · Sortino/Sharpe · beta · active return |
| **L4** | **Cosa succede se…?** | proiezione | replay storico · shock preset · simulazione |

### Perché esattamente quattro

L1, L2 e L4 sono **autoreferenziali**: guardano dentro il portafoglio. L3 è l'unica che
guarda **fuori**.

Questo spiega perché Sharpe, Sortino, beta, tracking error e information ratio
apparivano come card orfane nel pannello attuale: rispondono a una domanda che non era
nell'elenco. Non erano metriche sbagliate, erano metriche **senza casa**.

L3 è anche la domanda che un investitore fai-da-te ha davvero in testa e raramente
formula: *«tutta questa complessità rende più di un singolo ETF mondiale, o mi sto solo
dando da fare?»*

### L1 — la scala temporale

Il difetto del pannello attuale non era includere il VaR: era **accostare una perdita a
un giorno a un drawdown pluriennale senza dichiarare la scala**, così che l'utente le
sommasse mentalmente. La cura è una scala esplicita e crescente, in una sola sezione:

```text
Quanto può fare male

  Una giornata storta   (peggiori 5%)      −1,8%        −2.340 €
  Un mese storto        (peggiori 5%)      −7,2%        −9.360 €
  La peggior discesa    (vissuta davvero) −38,4%      −49.900 €
                        durata 19 mesi · recupero richiesto +62,3%
```

Regole di L1:

- il **CVaR** è il numero principale, il VaR è secondario — il VaR dichiara una soglia
  e tace su cosa c'è oltre, il CVaR dice quanto è brutto oltre;
- ogni riga porta **gli euro accanto alla percentuale**;
- ogni riga porta il proprio link alla pagina di documentazione, non un link generico
  per la sezione;
- nulla in L1 è stimato: sono tutti fatti osservati sul campione.

### L4 — gradiente interno

L4 non è omogenea: contiene cose a distanza crescente dai dati. L'ordine interno deve
renderlo visibile.

```text
replay storico       → rendimenti reali di un periodo reale
shock ipotetico      → deterministico, ipotesi dichiarata dall'utente
simulazione          → modello probabilistico, assunzioni del modello
```

Solo l'ultimo gradino è un modello. È lì, e solo lì, che ha senso un avvertimento.

---

## 4. La regola dei pesi

Emersa dall'analisi di Asset Global, vale per tutto il sottosistema:

> ## 🔑 I pesi sono la linea di demarcazione
>
> **Con pesi → euro → «io».**  Dashboard, Broker Detail.
> **Senza pesi → percentuali → «questi».**  Asset Global.

Non è una regola estetica, è il rimedio a una trappola cognitiva reale: oggi il filtro
broker di Asset Global produce *il set di asset* di un broker senza pesi, mentre Broker
Detail produce un'analisi *con* pesi — stessa parola, semantica opposta, nessun segnale
visivo che le distingua. Un utente che confronta i due numeri conclude che uno dei due
è rotto.

Se Asset Global **non mostra mai un euro**, la confusione diventa impossibile per
costruzione, senza bisogno di alcun disclaimer.

Corollario: il pannello `others` di Asset Global (asset di altri utenti) parla la stessa
lingua del laboratorio — mai euro.

---

## 5. Il laboratorio

Asset Global è l'unica pagina dove si possono analizzare **asset che non si possiedono**.
Quello è il suo valore, e oggi non è dichiarato da nessuna parte: è presentata come
«un'altra vista del tuo portafoglio», e quindi confonde.

Lo split F15 round-2 in tre pannelli (`own` / `others` / `analysis`) rende il concetto
già presente nel modello dati: il pannello `analysis` **è** il laboratorio.

Le domande vere del laboratorio sono:

- *«questi due ETF che sto per comprare sono la stessa cosa?»*
- *«se aggiungo questo, la mia diversificazione migliora davvero?»*
- *«come si sono comportati davvero, questi tre, nel 2008?»*

Nessuna richiede pesi. Tutte richiedono **pochi asset**, non cento.

---

## 6. Il criterio di taglio

Da questa tesi discende un criterio meccanico, che non richiede negoziazione:

> **Ogni strumento che non risponde a una delle quattro domande viene tagliato.**

Applicandolo, tracking error e information ratio cadono da soli — misurano lo
scostamento da un mandato che un investitore privato non ha. Il criterio ha quindi già
dimostrato di funzionare.

---

## 7. Cosa NON è cambiato

La tesi riguarda **direzione e priorità**, non correttezza. Restano validi e non si
riaprono:

- il contratto matematico (annualizzazione osservata, calendario congiunto, derivazione
  dei rendimenti dal TWRR);
- l'obbligo di calcolo in processi `spawn`;
- il modello di qualità del dato (`carried_forward` / `partial`, FX incluso), che resta
  **non negoziabile**: un numero di rischio senza la sua qualità del dato è peggio di
  nessun numero;
- la separazione backend calcola / frontend presenta.
