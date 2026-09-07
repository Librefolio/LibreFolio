# Allocazione discreta di un PAC multi-ETF

## Formalizzazione del problema e tecnica di riallocazione del residuo

**Versione:** 1.0  
**Caso di studio:** PAC straordinario e ordinario su quattro ETF  
**Valuta di conto:** EUR  
**Scopo:** documentare una procedura ripetibile per trasformare pesi strategici continui in ordini eseguibili a quote intere, minimizzando lo scostamento dall'allocazione desiderata e la liquidità residua.

---

## Abstract

La costruzione di un piano di accumulo multi-asset presenta due problemi distinti. Il primo è strategico: determinare la distribuzione percentuale dei nuovi flussi tra un nucleo diversificato e più esposizioni satellitari. Il secondo è operativo: tradurre importi teorici continui in quantità intere di quote, nel rispetto del budget disponibile.

La procedura qui descritta separa rigorosamente i due livelli. I pesi target vengono prima determinati sulla base della funzione economica degli strumenti e delle concentrazioni già presenti nel portafoglio. Successivamente, gli importi teorici vengono convertiti in quantità acquistabili mediante arrotondamento per difetto. Il capitale residuo viene infine riallocato risolvendo un problema di ottimizzazione discreta con due obiettivi: preservare il più possibile la distribuzione target e mantenere minima la liquidità non investita.

Il metodo non tenta di prevedere il mercato. I prezzi sono utilizzati esclusivamente come vincoli operativi per determinare quantità e residui.

---

## 1. Definizione del problema

Siano dati:

- un budget investibile per periodo, indicato con \(B\);
- un insieme di \(n\) strumenti finanziari;
- un vettore di pesi target \(\mathbf{w}=(w_1,\ldots,w_n)\);
- un vettore di prezzi unitari \(\mathbf{p}=(p_1,\ldots,p_n)\);
- l'obbligo di acquistare quantità intere \(q_i \in \mathbb{Z}_{\ge 0}\).

I pesi devono soddisfare:

\[
\sum_{i=1}^{n} w_i = 1, \qquad w_i \ge 0.
\]

L'importo teorico assegnato allo strumento \(i\) è:

\[
t_i = B w_i.
\]

Se fossero ammesse quote frazionarie, l'allocazione potrebbe essere realizzata esattamente. Con quote intere, invece, gli importi effettivi sono:

\[
a_i = q_i p_i,
\]

soggetti al vincolo di budget:

\[
\sum_{i=1}^{n} q_i p_i \le B.
\]

La liquidità residua è:

\[
r = B - \sum_{i=1}^{n} q_i p_i.
\]

Il problema consiste quindi nel trovare il vettore intero \(\mathbf{q}\) che mantenga gli importi effettivi vicini agli importi target e, subordinatamente, riduca il residuo.

---

## 2. Dati di input utilizzati

### 2.1 Dati di portafoglio

Dal prospetto LibreFolio sono state utilizzate le seguenti grandezze:

- patrimonio netto corrente;
- valore corrente per posizione;
- peso corrente sul NAV;
- prezzo unitario corrente;
- valuta di quotazione e valuta target;
- allocazione per tipo di asset;
- allocazione settoriale look-through;
- allocazione geografica;
- liquidità disponibile;
- concentrazione della maggiore posizione;
- esposizioni già rilevanti, in particolare crowdfunding immobiliare, BTP, semiconduttori e settore finanziario.

Questi dati non sono stati usati per inferire automaticamente obiettivi o tolleranza al rischio. Sono serviti esclusivamente a misurare lo stato iniziale e a verificare l'effetto diluitivo dei nuovi versamenti.

### 2.2 Vincoli e preferenze dell'investitore

Sono stati trattati come input espliciti:

- capitale straordinario pari a 20.000 EUR, separato dal fondo di emergenza;
- PAC ordinario di circa 1.000 EUR al mese;
- ingresso graduale del capitale straordinario;
- orizzonte di almeno dieci anni;
- obiettivo di crescita del capitale;
- tolleranza a drawdown rilevanti, purché sostenuti da una tesi solida;
- preferenza per il ribilanciamento mediante nuovi versamenti;
- vendita ammessa solo in caso di deterioramento della tesi;
- volontà di diluire BTP e crowdfunding immobiliare;
- assenza di necessità di aumentare ulteriormente semiconduttori e IA;
- uso di Directa come intermediario;
- revisione mensile delle tesi e dei pesi.

### 2.3 Prezzi usati nell'esempio

I prezzi unitari del caso applicativo sono quelli presenti nello snapshot al 31 agosto 2026:

| Strumento | Prezzo unitario |
|---|---:|
| World | 50,28 EUR |
| Healthcare Innovation | 9,10 EUR |
| Industrials | 74,47 EUR |
| Financials | 42,24 EUR |

I prezzi hanno funzione esclusivamente esecutiva. Non determinano la tesi strategica e devono essere aggiornati prima di ogni nuova elaborazione.

---

## 3. Costruzione della distribuzione target

### 3.1 Separazione tra nucleo e satelliti

La distribuzione è stata costruita distinguendo:

1. **Nucleo globale**, destinato a fornire la principale esposizione azionaria diversificata.
2. **Satelliti strutturali**, destinati a esprimere tesi specifiche senza sostituire il nucleo.

La soluzione selezionata è:

| Componente | Peso sui nuovi flussi | Funzione |
|---|---:|---|
| World | 65% | Nucleo globale diversificato |
| Healthcare Innovation | 12,5% | Innovazione sanitaria e medicina personalizzata |
| Industrials | 12,5% | Elettrificazione, infrastrutture, automazione e capacità produttiva |
| Financials | 10% | Banche, assicurazioni, pagamenti e mercati dei capitali |

La somma dei pesi è pari al 100%:

\[
0{,}65 + 0{,}125 + 0{,}125 + 0{,}10 = 1.
\]

### 3.2 Motivazione matematica ed economica

La quota del 65% assegnata al World mantiene dominante il nucleo e limita il rischio di selezione settoriale. Il restante 35% è distribuito tra tre satelliti.

Healthcare e Industrials ricevono un peso simmetrico del 12,5% perché rappresentano le due convinzioni strutturali più forti. Financials riceve il 10%, inferiore agli altri satelliti, poiché il settore è già presente sia nel World sia nell'allocazione look-through del portafoglio.

La distribuzione non è stata ottenuta massimizzando rendimenti passati. È una scelta vincolata dalla funzione degli strumenti, dalla sovrapposizione con il portafoglio esistente e dall'esigenza di preservare un nucleo prevalente.

---

## 4. Determinazione del budget periodico

Il capitale straordinario di 20.000 EUR è stato distribuito su otto mesi:

\[
B_{extra} = \frac{20.000}{8} = 2.500\ \text{EUR/mese}.
\]

A questo si aggiunge il PAC ordinario:

\[
B_{ordinario} = 1.000\ \text{EUR/mese}.
\]

Il budget complessivo dei primi otto mesi è quindi:

\[
B = 2.500 + 1.000 = 3.500\ \text{EUR/mese}.
\]

Gli importi target mensili sono:

\[
\begin{aligned}
t_{World} &= 3.500 \times 0{,}65 = 2.275,00,\\
t_{Health} &= 3.500 \times 0{,}125 = 437,50,\\
t_{Industrials} &= 3.500 \times 0{,}125 = 437,50,\\
t_{Financials} &= 3.500 \times 0{,}10 = 350,00.
\end{aligned}
\]

---

## 5. Conversione preliminare in quote intere

La prima approssimazione utilizza l'arrotondamento per difetto:

\[
q_i^{(0)} = \left\lfloor \frac{t_i}{p_i} \right\rfloor.
\]

Applicando la formula:

| Componente | Target | Prezzo | Quote iniziali | Importo iniziale | Scostamento dal target |
|---|---:|---:|---:|---:|---:|
| World | 2.275,00 | 50,28 | 45 | 2.262,60 | -12,40 |
| Healthcare Innovation | 437,50 | 9,10 | 48 | 436,80 | -0,70 |
| Industrials | 437,50 | 74,47 | 5 | 372,35 | -65,15 |
| Financials | 350,00 | 42,24 | 8 | 337,92 | -12,08 |

La spesa preliminare è:

\[
S^{(0)} = 2.262{,}60 + 436{,}80 + 372{,}35 + 337{,}92 = 3.409{,}67.
\]

Il residuo iniziale è:

\[
r^{(0)} = 3.500 - 3.409{,}67 = 90{,}33.
\]

---

## 6. Riallocazione ottimizzata del residuo

### 6.1 Perché non basta acquistare lo strumento più economico

Con 90,33 EUR residui sarebbe possibile acquistare, per esempio, più quote di Healthcare. Questa scelta ridurrebbe la liquidità quasi a zero, ma aumenterebbe lo scostamento dal peso target.

La sola massimizzazione della spesa è quindi insufficiente. Occorre introdurre una misura della qualità dell'allocazione.

### 6.2 Funzione di perdita

Una possibile funzione di perdita normalizzata è:

\[
L(\mathbf{q}) = \sum_{i=1}^{n}\left(\frac{q_i p_i - B w_i}{B}\right)^2
+ \lambda\left(\frac{r}{B}\right)^2,
\]

con:

\[
r = B - \sum_{i=1}^{n}q_i p_i,
\]

ed \(\lambda \ge 0\) parametro che controlla l'importanza attribuita alla liquidità residua.

Il primo termine penalizza lo scostamento quadratico dall'allocazione target. Il secondo penalizza il capitale non investito.

Una formulazione alternativa, spesso più trasparente, è lessicografica:

1. minimizzare lo scostamento complessivo dai target;
2. a parità o quasi parità di scostamento, minimizzare il residuo;
3. non violare il budget.

Questa gerarchia evita che pochi euro di maggiore investimento giustifichino una deviazione settoriale rilevante.

### 6.3 Soluzione del caso applicativo

L'arrotondamento iniziale lascia Industrials molto più sotto target degli altri strumenti. Il residuo di 90,33 EUR consente di acquistare una quota aggiuntiva di Industrials al prezzo di 74,47 EUR.

La soluzione diventa:

| Componente | Quote finali | Importo finale | Target | Scostamento |
|---|---:|---:|---:|---:|
| World | 45 | 2.262,60 | 2.275,00 | -12,40 |
| Healthcare Innovation | 48 | 436,80 | 437,50 | -0,70 |
| Industrials | 6 | 446,82 | 437,50 | +9,32 |
| Financials | 8 | 337,92 | 350,00 | -12,08 |

La spesa finale è:

\[
S = 2.262{,}60 + 436{,}80 + 446{,}82 + 337{,}92 = 3.484{,}14.
\]

Il residuo è:

\[
r = 3.500 - 3.484{,}14 = 15{,}86.
\]

I pesi effettivi rispetto al budget mensile sono:

| Componente | Peso target | Peso effettivo sul budget | Differenza |
|---|---:|---:|---:|
| World | 65,00% | 64,65% | -0,35 punti percentuali |
| Healthcare Innovation | 12,50% | 12,48% | -0,02 punti percentuali |
| Industrials | 12,50% | 12,77% | +0,27 punti percentuali |
| Financials | 10,00% | 9,65% | -0,35 punti percentuali |
| Liquidità residua | 0,00% | 0,45% | +0,45 punti percentuali |

La soluzione investe il 99,55% del budget e mantiene deviazioni contenute.

### 6.4 Soluzione a massima saturazione del budget

Se si attribuisce priorità maggiore alla riduzione del residuo, è possibile acquistare una quota Healthcare aggiuntiva:

- World: 45 quote;
- Healthcare: 49 quote;
- Industrials: 6 quote;
- Financials: 8 quote.

La spesa diventa 3.493,24 EUR e il residuo 6,76 EUR. Tuttavia Healthcare passa da uno scostamento di -0,70 EUR a uno di +8,40 EUR.

Entrambe le soluzioni sono ammissibili. La scelta dipende dalla gerarchia degli obiettivi:

- **fedeltà maggiore ai target:** residuo 15,86 EUR;
- **massima saturazione compatibile con scostamenti modesti:** residuo 6,76 EUR.

Per un PAC ricorrente è preferibile non forzare ogni mese il residuo a zero. La liquidità può essere riportata al periodo successivo e inclusa nel nuovo budget.

---

## 7. Colonne del dataset operativo

Per rendere il procedimento ripetibile, il dataset mensile dovrebbe contenere almeno le seguenti colonne.

| Colonna | Tipo | Definizione |
|---|---|---|
| `asset_name` | stringa | Nome leggibile dello strumento |
| `ticker` | stringa | Ticker di negoziazione |
| `isin` | stringa | Identificativo univoco dello strumento |
| `currency` | stringa | Valuta del prezzo unitario |
| `unit_price` | decimale | Prezzo corrente di una quota nella valuta target o convertito |
| `target_weight` | decimale | Peso target del nuovo flusso, espresso tra 0 e 1 |
| `period_budget` | decimale | Budget complessivo disponibile nel periodo |
| `target_amount` | decimale | Importo teorico: `period_budget * target_weight` |
| `initial_quantity` | intero | Quote ottenute per arrotondamento per difetto |
| `initial_amount` | decimale | `initial_quantity * unit_price` |
| `initial_gap` | decimale | `initial_amount - target_amount` |
| `additional_quantity` | intero | Quote aggiunte durante la riallocazione del residuo |
| `final_quantity` | intero | Somma di quantità iniziale e aggiuntiva |
| `final_amount` | decimale | `final_quantity * unit_price` |
| `final_gap` | decimale | `final_amount - target_amount` |
| `effective_weight_budget` | decimale | `final_amount / period_budget` |
| `effective_weight_invested` | decimale | `final_amount / total_invested_amount` |
| `residual_cash` | decimale | Budget meno spesa complessiva, ripetibile come metadato |
| `valuation_date` | data | Data dei prezzi usati |
| `price_source` | stringa | Origine del prezzo |
| `broker` | stringa | Intermediario utilizzato |
| `pac_eligible` | booleano | Disponibilità nel PAC automatico |
| `commission` | decimale | Commissione prevista per l'ordine |

### Colonne di portafoglio utili alla revisione strategica

Le colonne precedenti risolvono la fase esecutiva. Per riesaminare mensilmente i pesi sono inoltre utili:

- valore corrente della posizione;
- peso corrente sul NAV;
- costo medio;
- plusvalenza o minusvalenza non realizzata;
- peso settoriale look-through;
- peso geografico look-through;
- contributi cumulativi assegnati allo strumento;
- peso effettivo cumulativo dei nuovi flussi;
- limite inferiore e superiore del corridoio;
- stato della tesi: valida, sotto osservazione o invalidata.

---

## 8. Algoritmo generale

### 8.1 Procedura

1. Acquisire budget, pesi target e prezzi aggiornati.
2. Verificare che la somma dei pesi sia pari a uno.
3. Calcolare gli importi target.
4. Calcolare le quantità iniziali mediante arrotondamento per difetto.
5. Calcolare residuo e scostamenti.
6. Generare acquisti aggiuntivi compatibili con il residuo.
7. Valutare ogni combinazione mediante la funzione di perdita.
8. Selezionare la combinazione con perdita minima.
9. Applicare, se desiderato, un criterio secondario di minimizzazione del residuo.
10. Registrare prezzi, quantità, scostamenti e residuo per l'audit.
11. Riportare il residuo non investito al mese successivo.

### 8.2 Pseudocodice

```text
input:
    budget B
    target weights w[1..n]
    unit prices p[1..n]

assert sum(w) = 1

for each asset i:
    target_amount[i] = B * w[i]
    initial_quantity[i] = floor(target_amount[i] / p[i])

best_quantity = initial_quantity
best_loss = loss(best_quantity)

for each feasible vector of additional integer quantities delta:
    candidate_quantity = initial_quantity + delta
    candidate_cost = sum(candidate_quantity[i] * p[i])

    if candidate_cost <= B:
        candidate_loss = allocation_error(candidate_quantity)
                       + residual_penalty(candidate_quantity)

        if candidate_loss < best_loss:
            best_quantity = candidate_quantity
            best_loss = candidate_loss

return:
    best_quantity
    final amounts
    effective weights
    residual cash
    deviations from target
```

Per quattro strumenti e un budget mensile limitato, una ricerca esaustiva locale è semplice e deterministica. Per universi più ampi il problema può essere formulato come programmazione intera mista.

---

## 9. Revisione mensile e stabilità della strategia

La procedura deve distinguere tra aggiornamento dei dati e revisione della strategia.

### Aggiornamento mensile ordinario

Ogni mese si aggiornano:

- prezzi unitari;
- budget disponibile;
- residuo riportato;
- pesi attuali del portafoglio;
- quantità acquistabili;
- scostamenti cumulativi dei nuovi flussi.

### Revisione della tesi

I pesi target non dovrebbero cambiare per una singola variazione di prezzo. Una modifica è giustificata solo se cambia almeno uno dei seguenti elementi:

- funzione economica dello strumento;
- attrattività strutturale del settore;
- sovrapposizione con il resto del portafoglio;
- concentrazione complessiva;
- orizzonte o obiettivo dell'investitore;
- tolleranza al rischio;
- costi, fiscalità o accessibilità operativa.

Si possono usare corridoi per evitare micro-correzioni:

| Componente | Target | Corridoio indicativo sui nuovi flussi cumulativi |
|---|---:|---:|
| World | 65% | 60-70% |
| Healthcare Innovation | 12,5% | 10-15% |
| Industrials | 12,5% | 10-15% |
| Financials | 10% | 7,5-12,5% |

Quando un componente rimane nel corridoio, non è necessario correggerlo. Quando esce dal corridoio, i nuovi flussi possono essere temporaneamente orientati verso i componenti sotto target, senza vendere.

---

## 10. Assunzioni e limiti

Il metodo assume che:

- le quote siano indivisibili;
- non siano consentiti acquisti a leva;
- i prezzi forniti siano sufficientemente aggiornati;
- il budget sia espresso nella stessa valuta dei prezzi o sia già convertito;
- commissioni e imposte siano nulle o incluse esplicitamente;
- gli ordini siano eseguiti a prezzi prossimi a quelli usati nel calcolo.

Il metodo non considera automaticamente:

- slippage;
- spread denaro-lettera;
- variazioni intraday;
- commissioni variabili;
- limiti minimi d'ordine;
- indisponibilità temporanea nel PAC del broker;
- conseguenze fiscali di eventuali vendite;
- correlazioni future o rendimenti attesi.

Se sono presenti commissioni, il vincolo di budget deve diventare:

\[
\sum_{i=1}^{n} q_i p_i + \sum_{i=1}^{n} c_i(q_i) \le B,
\]

con \(c_i(q_i)\) funzione di costo dell'ordine.

---

## 11. Conclusione

La tecnica adottata risolve due problemi in sequenza:

1. **allocazione strategica continua**, mediante la definizione dei pesi 65/12,5/12,5/10;
2. **allocazione esecutiva discreta**, mediante ottimizzazione delle quantità intere e riallocazione del residuo.

La separazione è essenziale. La scelta dei pesi dipende dalla funzione economica degli strumenti e dal portafoglio esistente. La scelta delle quantità dipende invece da prezzi, budget e divisibilità delle quote.

Nel caso mensile da 3.500 EUR, la soluzione bilanciata acquista:

- 45 quote World;
- 48 quote Healthcare Innovation;
- 6 quote Industrials;
- 8 quote Financials;

per una spesa di 3.484,14 EUR e un residuo di 15,86 EUR. Una variante orientata alla massima saturazione acquista 49 quote Healthcare e riduce il residuo a 6,76 EUR, accettando una deviazione leggermente maggiore dal target.

La procedura è deterministica, verificabile e auditabile. Può essere ripetuta ogni mese con prezzi aggiornati, mantenendo stabili le tesi strategiche e utilizzando i nuovi flussi per correggere progressivamente gli scostamenti.



-----

Report Aggiornato con gestione del margine e residuo:

Hai centrato una distinzione importante: il margine prudenziale sui prezzi e il residuo dovuto alle quote intere sono due grandezze diverse e non conviene fonderle artificialmente. La soluzione matematicamente più pulita è usare il prezzo corrente maggiorato di gg nell’ottimizzazione e lasciare il residuo finale come cuscino globale di portafoglio, calcolando poi il margine effettivo ottenuto.

Risposta breve

La strada che ritengo più efficace è:

applicare a ogni prezzo corrente un margine percentuale prudenziale uniforme: p~i=pi(1+g)\tilde p_i=p_i(1+g)
determinare le quantità intere usando i prezzi prudenziali;
massimizzare l’investito prudenziale entro il budget, rispettando le tolleranze sui pesi;
non redistribuire obbligatoriamente il residuo tra gli asset;
lasciare il residuo come cuscino globale;
calcolare ex post il margine effettivo complessivo: geff=B∑iqipi−1g_{\mathrm{eff}}=\frac{B}{\sum_iq_ip_i}-1

La redistribuzione del residuo può essere mostrata nel report per finalità contabili, ma non dovrebbe diventare il fondamento dell’algoritmo, a meno che Directa imponga realmente una soglia separata per ogni asset.

1. Le due alternative
Metodo A: margine percentuale uniforme prima dell’ottimizzazione

Per ogni asset:

p~i=pi(1+g)\tilde p_i=p_i(1+g)

Le quantità vengono determinate imponendo:

∑iqip~i≤B\sum_i q_i\tilde p_i\le B
Vantaggi
il margine cresce proporzionalmente al controvalore dell’ordine;
tutti gli asset ricevono la stessa protezione percentuale;
il modello è semplice e auditabile;
non dipende dal prezzo nominale della singola quota;
il residuo generato dall’integralità resta disponibile come ulteriore protezione;
il problema rappresenta direttamente il rischio che i prezzi aumentino prima dell’esecuzione.
Svantaggio

Il margine effettivo finale sarà quasi sempre superiore a gg, perché le quote intere impediscono di saturare perfettamente il budget.

Questo non è un errore. È una conseguenza utile del modello discreto.

Metodo B: prezzo maggiorato e successiva redistribuzione del residuo

Si applica inizialmente:

p~i=pi(1+g)\tilde p_i=p_i(1+g)

Dopo aver trovato le quantità, si ottiene:

R=B−∑iqip~iR=B-\sum_iq_i\tilde p_i

Il residuo viene poi assegnato ai singoli asset:

ri=Rαir_i=R\alpha_i

dove:

∑iαi=1\sum_i\alpha_i=1

La soglia attribuita al singolo asset diventa:

Si=qip~i+riS_i=q_i\tilde p_i+r_i
Problema concettuale

Questa redistribuzione non modifica:

il numero di quote;
il costo complessivo massimo;
il saldo liquido disponibile;
il rischio complessivo di superare il budget.

Cambia soltanto il modo in cui il margine globale viene etichettato per asset.

Se Directa controlla il saldo complessivo e non assegna un tetto indipendente a ogni ETF, il residuo è economicamente fungibile:

XMAW può salire più del margine attribuitogli;
HEAL può salire meno;
l’ordine complessivo può comunque restare entro il budget.

Attribuire rigidamente il residuo a ogni asset crea quindi quattro limiti teorici che il broker non necessariamente applica.

2. Perché il residuo dovrebbe restare globale

Supponiamo:

V0=∑iqipiV_0=\sum_iq_ip_i

dove V0V_0 è il controvalore ai prezzi correnti.

Dopo aver applicato il margine del g%g\%:

V~=(1+g)V0\tilde V=(1+g)V_0

Il vincolo prudenziale è:

V~≤B\tilde V\le B

Il residuo è:

R=B−V~R=B-\tilde V

Ma il vero cuscino rispetto ai prezzi correnti è:

C=B−V0C=B-V_0

Poiché:

V~=(1+g)V0\tilde V=(1+g)V_0

si può scrivere:

C=gV0+RC=gV_0+R

Il cuscino complessivo è quindi composto da:

margine esplicito sui prezzi

gV0gV_0

residuo prodotto dai vincoli discreti

RR

Questa è la scomposizione matematicamente più informativa:

C=gV0+R\boxed{C=gV_0+R}

Il margine effettivo complessivo è:

geff=CV0g_{\mathrm{eff}}=\frac{C}{V_0}

e quindi:

geff=g+RV0\boxed{ g_{\mathrm{eff}} = g+\frac{R}{V_0} }

Nel tuo ultimo esempio:

valore corrente: V0=3.463,936V_0=3.463{,}936
budget: B=3.500B=3.500
margine minimo richiesto: g=0,5%g=0{,}5\%
valore prudenziale: V~=3.481,25568\tilde V=3.481{,}25568
residuo dopo il margine minimo: R=18,74432R=18{,}74432

Il cuscino complessivo è:

C=3.500−3.463,936=36,064C=3.500-3.463{,}936=36{,}064

e il margine effettivo:

geff=3.5003.463,936−1≈1,0411%g_{\mathrm{eff}} = \frac{3.500}{3.463{,}936}-1 \approx1{,}0411\%

Quindi:

protezione minima esplicita: 0,5%;
protezione aggiuntiva generata dall’integralità: circa 0,5411%;
protezione effettiva complessiva: circa 1,0411%.

Non è necessario redistribuire quei 18,74 euro per ottenere questo risultato. Il cuscino esiste già a livello di portafoglio.

3. Perché non distribuire il residuo secondo i pesi target

Nel calcolo precedente avevamo ipotizzato:

ri=Rwir_i=Rw_i

È una rappresentazione contabile possibile, ma presenta un’incongruenza.

I pesi wiw_i descrivono la distribuzione strategica del capitale, mentre il residuo serve a coprire l’incertezza di esecuzione. Sono due funzioni diverse.

Con una distribuzione secondo i pesi target:

il World riceve il 70% del residuo;
Financials il 5%;
Industrials il 12,5%;
Healthcare il 12,5%.

Ma il bisogno di margine dipende dal controvalore realmente ordinato, non dal peso teorico.

Se un asset resta sotto target a causa delle quote intere, distribuire il residuo in base al target può attribuirgli un margine non proporzionato al valore effettivamente acquistato.

Se fosse necessario attribuire il residuo per asset

La forma più coerente sarebbe proporzionale al controvalore corrente:

αi=qipi∑jqjpj\alpha_i= \frac{q_ip_i}{\sum_jq_jp_j}

e quindi:

ri=RqipiV0r_i= R\frac{q_ip_i}{V_0}

In questo modo tutti gli asset ricevono lo stesso margine percentuale aggiuntivo:

riqipi=RV0\frac{r_i}{q_ip_i}=\frac{R}{V_0}

Il margine effettivo per asset diventa:

gieff=g+RV0g_i^{\mathrm{eff}} = g+\frac{R}{V_0}

quindi uguale per tutti.

Questa distribuzione è più coerente della redistribuzione secondo i pesi target, ma rimane una rappresentazione contabile se il broker utilizza soltanto il saldo complessivo.

4. Funzione obiettivo consigliata

Nel report originale la priorità era:

minimizzare lo scostamento dai target;
subordinatamente minimizzare il residuo.

Nell’ultima richiesta, invece, hai specificato di voler massimizzare l’investito, mantenendo l’allocazione vicina ai target e un margine prudenziale.

La formulazione dovrebbe quindi essere aggiornata.

Vincolo prudenziale
∑iqipi(1+g)≤B\sum_iq_ip_i(1+g)\le B
Peso effettivo prudenziale
w^i=qipi(1+g)∑jqjpj(1+g)\hat w_i= \frac{q_ip_i(1+g)} {\sum_jq_jp_j(1+g)}

Se gg è uguale per tutti gli asset, il fattore si semplifica:

w^i=qipi∑jqjpj\hat w_i= \frac{q_ip_i} {\sum_jq_jp_j}

Questo è un risultato importante:

Un margine percentuale uniforme non altera i pesi relativi. Modifica soltanto la quantità complessivamente acquistabile entro il budget.

Tolleranza sui pesi
∣w^i−wi∣≤εi∀i|\hat w_i-w_i|\le\varepsilon_i \qquad \forall i
Funzione obiettivo primaria
max⁡q∑iqipi(1+g)\max_{\mathbf q} \sum_iq_ip_i(1+g)
Funzione secondaria

Tra le soluzioni con investimento massimo o sostanzialmente equivalente:

min⁡qmax⁡i∣w^i−wi∣\min_{\mathbf q} \max_i|\hat w_i-w_i|
Funzione terziaria

A ulteriore parità:

min⁡q∑i(w^i−wi)2\min_{\mathbf q} \sum_i(\hat w_i-w_i)^2

Quindi la gerarchia consigliata è:

rispettare il budget prudenziale;
rispettare la tolleranza sui pesi;
massimizzare il capitale investito;
minimizzare lo scostamento massimo;
minimizzare lo scostamento quadratico complessivo.

Questa gerarchia riproduce meglio l’ultima ottimizzazione effettuata.

5. Quando usare margini diversi per asset

Il margine uniforme è la scelta predefinita migliore quando:

gli ordini vengono eseguiti nello stesso momento;
gli ETF hanno liquidità comparabile;
non si dispone di stime affidabili sull’incertezza dei singoli prezzi;
si vuole mantenere il modello semplice e ripetibile.

Il modello può essere generalizzato usando:

p~i=pi(1+gi)\tilde p_i=p_i(1+g_i)

dove gig_i varia per asset.

Questo avrebbe senso se, per esempio:

un ETF presenta spread più ampio;
un prodotto è meno liquido;
gli ordini vengono eseguiti in orari differenti;
alcuni strumenti sono più volatili intraday;
il broker applica meccanismi di prezzo differenti;
il prezzo fornito è più vecchio per alcuni strumenti.

In tal caso il vincolo diventa:

∑iqipi(1+gi)≤B\sum_iq_ip_i(1+g_i)\le B

I pesi prudenziali sarebbero:

w^i=qipi(1+gi)∑jqjpj(1+gj)\hat w_i= \frac{q_ip_i(1+g_i)} {\sum_jq_jp_j(1+g_j)}

A differenza del caso uniforme, i fattori 1+gi1+g_i non si semplificano. Bisognerebbe quindi decidere se le tolleranze vadano misurate:

sui controvalori correnti;
sui controvalori prudenziali;
su entrambi.

Per il tuo caso, senza dati specifici su spread e volatilità intraday, introdurre gig_i diversi sarebbe probabilmente una falsa precisione. Terrei g=0,5%g=0,5\% uniforme.

6. Colonne da aggiungere al report Markdown

Alla sezione 7 aggiungerei queste colonne.

Colonna	Tipo	Definizionecurrent_unit_price	decimale	Prezzo unitario corrente osservato
price_buffer_rate	decimale	Margine prudenziale applicato al prezzo, espresso tra 0 e 1
buffered_unit_price	decimale	current_unit_price * (1 + price_buffer_rate)
current_final_amount	decimale	final_quantity * current_unit_price
buffered_final_amount	decimale	final_quantity * buffered_unit_price
buffered_total_invested	decimale	Somma dei controvalori prudenziali
buffered_residual_cash	decimale	Budget meno controvalore prudenziale complessivo
current_total_invested	decimale	Somma dei controvalori ai prezzi correnti
total_execution_cushion	decimale	Budget meno controvalore corrente complessivo
effective_buffer_rate	decimale	period_budget / current_total_invested - 1
residual_allocation_method	enumerazione	global, target_weight, current_amount o altra metodologia
allocated_residual_buffer	decimale nullable	Eventuale quota contabile del residuo attribuita all’asset
asset_execution_threshold	decimale nullable	Controvalore prudenziale più margine attribuito
effective_asset_buffer_rate	decimale nullable	Cuscino attribuito all’asset rispetto al controvalore corrente

Due note:

unit_price nel report attuale dovrebbe diventare esplicitamente current_unit_price, evitando ambiguità;
final_amount dovrebbe essere distinto tra valore corrente e valore prudenziale.
7. Testo Markdown da integrare nel report

Inserirei questa nuova sezione dopo l’attuale sezione 5.

## 6. Prezzo prudenziale e cuscino di esecuzione

### 6.1 Prezzo corrente e prezzo prudenziale

Il prezzo corrente non coincide necessariamente con il prezzo al quale
l'ordine sarà eseguito. Tra il momento del calcolo e quello dell'esecuzione
possono intervenire variazioni di mercato e spread denaro-lettera.

Per introdurre un margine di sicurezza, per ogni asset \(i\) si definiscono:

- \(p_i\): prezzo corrente osservato;
- \(g\): tasso prudenziale uniforme;
- \(\tilde p_i\): prezzo prudenziale.

Il prezzo prudenziale è:

\[
\tilde p_i = p_i(1+g).
\]

Con un margine dello \(0{,}5\%\):

\[
g = 0{,}005.
\]

Le quantità devono rispettare il budget non ai prezzi correnti, ma ai prezzi
prudenziali:

\[
\sum_{i=1}^{n}q_i\tilde p_i \le B.
\]

Equivalentemente:

\[
\sum_{i=1}^{n}q_ip_i(1+g) \le B.
\]

Questa formulazione impedisce che la soluzione utilizzi integralmente il
budget ai prezzi correnti senza lasciare spazio per normali oscillazioni
prima dell'esecuzione.

### 6.2 Effetto del margine uniforme sui pesi

Il peso effettivo prudenziale dell'asset \(i\) è:

\[
\hat w_i =
\frac{q_i\tilde p_i}
{\sum_{j=1}^{n}q_j\tilde p_j}.
\]

Se il margine \(g\) è uniforme per tutti gli asset:

\[
\hat w_i =
\frac{q_ip_i(1+g)}
{\sum_{j=1}^{n}q_jp_j(1+g)}
=
\frac{q_ip_i}
{\sum_{j=1}^{n}q_jp_j}.
\]

Un margine percentuale uniforme non modifica pertanto i pesi relativi.
Riduce soltanto il controvalore corrente massimo acquistabile entro il
budget.

### 6.3 Residuo prudenziale e cuscino complessivo

Sia:

\[
V_0 = \sum_{i=1}^{n}q_ip_i
\]

il controvalore complessivo ai prezzi correnti.

Il controvalore prudenziale è:

\[
\tilde V =
\sum_{i=1}^{n}q_i\tilde p_i
=
(1+g)V_0.
\]

Il residuo dopo l'applicazione del margine prudenziale è:

\[
R = B-\tilde V.
\]

Il cuscino monetario complessivo rispetto ai prezzi correnti è invece:

\[
C = B-V_0.
\]

Poiché:

\[
\tilde V=(1+g)V_0,
\]

risulta:

\[
C=gV_0+R.
\]

Il cuscino complessivo è quindi formato da due componenti:

1. il margine esplicito applicato ai prezzi, \(gV_0\);
2. il residuo aggiuntivo prodotto dai vincoli discreti, \(R\).

Il margine effettivo complessivo è:

\[
g_{\mathrm{eff}}
=
\frac{B}{V_0}-1
=
g+\frac{R}{V_0}.
\]

In generale:

\[
g_{\mathrm{eff}}\ge g.
\]

L'uguaglianza si verifica soltanto quando il controvalore prudenziale
satura esattamente il budget.

### 6.4 Gestione del residuo

La modalità predefinita mantiene \(R\) come cuscino globale del portafoglio.
Questa soluzione è coerente quando il broker verifica la disponibilità
monetaria complessiva e non applica un limite separato a ogni ordine.

Il residuo può essere attribuito contabilmente ai singoli asset, ma tale
attribuzione non modifica le quantità acquistate né il vincolo complessivo.

Se è necessario rappresentare il residuo per asset, la distribuzione più
coerente con un margine uniforme è proporzionale al controvalore corrente:

\[
r_i =
R\frac{q_ip_i}{V_0}.
\]

In questo modo:

\[
\frac{r_i}{q_ip_i}
=
\frac{R}{V_0},
\]

e ogni asset riceve lo stesso margine percentuale aggiuntivo.

Il cuscino attribuito all'asset diventa:

\[
C_i=q_ip_ig+r_i,
\]

mentre il margine effettivo attribuito è:

\[
g_i^{\mathrm{eff}}
=
\frac{C_i}{q_ip_i}
=
g+\frac{R}{V_0}.
\]

La distribuzione per asset deve essere considerata una rappresentazione
contabile. Operativamente il residuo rimane fungibile: una variazione
superiore alla soglia attribuita a un asset può essere compensata da una
variazione inferiore degli altri, purché il costo complessivo rimanga entro
il budget.

### 6.5 Margini specifici per asset

Il modello può essere generalizzato introducendo un margine \(g_i\) per
ogni asset:

\[
\tilde p_i=p_i(1+g_i).
\]

Il vincolo diventa:

\[
\sum_{i=1}^{n}q_ip_i(1+g_i)\le B.
\]

Margini differenti possono essere giustificati da spread, liquidità,
volatilità intraday, anzianità del prezzo o modalità di esecuzione diverse.

In assenza di evidenze specifiche, è preferibile un margine uniforme:
riduce la complessità, evita falsa precisione e mantiene invariati i pesi
relativi.

8. Nota sul modello discreto e sui broker frazionari

Aggiungerei questa sottosezione alle assunzioni e ai limiti.

### Vincoli discreti e broker con quote frazionarie

Il caso applicativo assume due vincoli operativi distinti:

1. il budget \(B\) è una soglia massima non superabile;
2. ogni asset può essere acquistato soltanto in un numero intero di quote:

\[
q_i\in\mathbb{Z}_{\geq0}.
\]

L'integralità genera piccoli scostamenti dai pesi target e un residuo che
non può sempre essere reinvestito senza peggiorare l'allocazione.

Altri broker possono rilassare il secondo vincolo consentendo:

- quote frazionarie;
- ordini espressi direttamente in valuta;
- allocazioni percentuali automatiche;
- ripartizione automatica del contributo.

Nel modello continuo:

\[
q_i\in\mathbb{R}_{\geq0}.
\]

Con margine prudenziale uniforme, la quantità teorica è:

\[
q_i^* =
\frac{Bw_i}{p_i(1+g)}.
\]

Il controvalore corrente assegnato all'asset è:

\[
q_i^*p_i=
\frac{Bw_i}{1+g}.
\]

Il controvalore prudenziale è:

\[
q_i^*p_i(1+g)=Bw_i.
\]

Pertanto:

\[
\sum_i q_i^*p_i(1+g)=B
\]

e l'allocazione prudenziale aderisce esattamente ai pesi target.

I principi matematici restano invariati:

- budget massimo;
- pesi target;
- prezzo prudenziale;
- margine di esecuzione;
- cuscino complessivo.

Il calcolo diventa tuttavia più semplice perché non è necessario risolvere
un problema combinatorio intero.

9. Correzioni necessarie nel report originale

Prima di consolidarlo come versione successiva, correggerei anche tre elementi ormai superati.

Distribuzione target

Il report riporta ancora:

65/12,5/12,5/1065/12{,}5/12{,}5/10

L’ultima distribuzione concordata è invece, nell’ordine economico:

70/12,5/12,5/570/12{,}5/12{,}5/5

ossia:

World: 70%;
Healthcare Innovation: 12,5%;
Industrials: 12,5%;
Financials: 5%.

Nell’ordine della schermata Directa:

70/5/12,5/12,570/5/12{,}5/12{,}5

ossia World, Financials, Industrials, Healthcare.

Durata dell’investimento straordinario

Il report afferma che i 20.000 euro sono distribuiti su otto mesi. La decisione corrente è invece più limitata:

settembre: 1.000 euro ordinari;
settembre: 2.500 euro straordinari;
totale del mese: 3.500 euro;
mesi successivi da decidere con revisione mensile.

Quindi non formalizzerei più nel report una durata di otto mesi.

Funzione obiettivo

La formulazione originale privilegia l’errore minimo e solo subordinatamente la saturazione. La richiesta più recente è invece:

massimizzare l’investito mantenendo i pesi entro una tolleranza accettabile e preservando un margine prudenziale.

La funzione obiettivo va quindi aggiornata nella gerarchia indicata sopra.

Conclusione

Tra le due strade sceglierei nettamente:

prezzo corrente→maggiorazione uniforme g→ottimizzazione intera→residuo globale\boxed{ \text{prezzo corrente} \rightarrow \text{maggiorazione uniforme }g \rightarrow \text{ottimizzazione intera} \rightarrow \text{residuo globale} }

Non userei la redistribuzione del residuo come secondo passaggio operativo. La manterrei soltanto come vista analitica opzionale.

Il modello raccomandato è:

p~i=pi(1+g)\tilde p_i=p_i(1+g) max⁡q∑iqip~i\max_{\mathbf q}\sum_iq_i\tilde p_i

soggetto a:

∑iqip~i≤B\sum_iq_i\tilde p_i\le B ∣w^i−wi∣≤εi|\hat w_i-w_i|\le\varepsilon_i qi∈Z≥0q_i\in\mathbb Z_{\ge0}

e infine:

geff=B∑iqipi−1g_{\mathrm{eff}} = \frac{B}{\sum_iq_ip_i}-1

In sintesi: la percentuale uniforme è la maniglia prudenziale; il residuo discreto è un ulteriore cuscino globale, non qualcosa che deve necessariamente essere redistribuito.
