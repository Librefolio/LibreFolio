# 💸 Capitale versato, PnL totale e pool di liquidità

## 💡 Panoramica del concetto

**Base del capitale** = capitale economico cumulato conferito dall'inizio:

$$
\mathrm{CapitalBaseline}(t)=
\sum_{\tau \leq t}\mathrm{ExternalCashFlow}(\tau)
+ \sum_{\tau \leq t}\mathrm{InKindCapital}(\tau)
$$

**PnL totale** = tutto il valore generato al di sopra dei conferimenti esterni:

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{CapitalBaseline}(t)}
$$

`InKindCapital` copre i titoli che entrano o escono dal perimetro senza liquidità:

- righe di rettifica valutate che riportano `cost_basis_override` (non collegate a uno split), **al costo**: il costo che una riga in entrata aggiunge alla posizione, o il costo medio che una riga in uscita rimuove;
- gambe TRANSFER la cui altra gamba non è nel perimetro — si trova presso un broker al di fuori della vista, manca, o non è mai stata collegata — **al valore di mercato** alla loro data: $+$ per titoli ricevuti, $-$ per titoli inviati, nulla se il titolo non può essere valutato quel giorno.

Queste righe spostano valore senza liquidità: sono capitale, non profitto o perdita.

---

## 🎯 Cosa conta

| Transazione | Effetto sulla base del capitale |
|------------|-----------------|
| DEPOSIT / WITHDRAWAL (non collegati) | ✅ Sì |
| CASH\_TRANSFER / FX\_CONVERSION la cui altra gamba è fuori dalla vista, manca, o non è mai stata collegata (orfana) | ✅ Sì, al suo importo, come un deposito o un prelievo |
| CASH\_TRANSFER / FX\_CONVERSION / TRANSFER con entrambe le gambe nella vista (coppia interna) | ❌ No. Per broker, una coppia tra due broker sposta capitale dal mittente al destinatario il giorno di arrivo, sommando a zero ([Trasferimenti interni](#internal-transfers-broker-lines)) |
| TRANSFER di titoli la cui altra gamba è fuori dalla vista, manca, o non è mai stata collegata (orfana) | ✅ Sì, capitale in natura al valore di mercato alla sua data |
| ADJUSTMENT con `cost_basis_override`, non collegato a split | ✅ Sì, capitale in natura al costo |
| ADJUSTMENT collegato a SPLIT | ❌ No, solo ridimensionamento della quantità |
| BUY, SELL, DIVIDEND, INTEREST, FEE, TAX | ❌ No |
| Movimento del tasso di cambio sulla liquidità detenuta in un'altra valuta (nessuna transazione) | ❌ No: un risultato, parte del TotalPnL; i flussi di capitale (depositi, prelievi, gambe di liquidità orfane) sono entrati nella base al tasso delle proprie date |

---

## 🔀 Trasferimenti interni nelle linee per broker {: #internal-transfers-broker-lines }

Con due o più broker nel perimetro, il [grafico P&L](../../../../user/dashboard/charts.md#pnl-line) traccia una linea per broker. Ogni broker $b \in S$ ha il proprio NAV, capitale e PnL:

$$
\mathrm{PnL}_b(t) = \mathrm{NAV}_b(t) - C_b(t)
$$

$$
\mathrm{NAV}_b(t) = \mathrm{MV}_b(t) + \mathrm{Cash}_b(t) + \mathrm{InTransit}_b(t)
$$

$$
C_b(t) = \sum_{\tau \leq t}\mathrm{ExternalCashFlow}_b(\tau) + \sum_{\tau \leq t}\mathrm{InKindCapital}_b(\tau) + \sum_{\tau \leq t}\mathrm{Internal}_b(\tau)
$$

$\mathrm{InTransit}_b$ è il valore in transito che ha lasciato $b$, e $\mathrm{Internal}_b$ è il lato di $b$ dei trasferimenti interni descritti di seguito. Poiché $\sum_b \mathrm{NAV}_b = \mathrm{NAV}$ e i flussi interni si annullano ogni giorno, le linee si sommano ai valori del perimetro:

$$
\sum_{b \in S}\mathrm{Internal}_b(t) = 0
\quad\Rightarrow\quad
\sum_{b \in S} C_b(t) = \mathrm{CapitalBaseline}(t),
\qquad
\sum_{b \in S}\mathrm{PnL}_b(t) = \mathrm{TotalPnL}(t)
$$

La linea di un broker è quindi il PnL maturato mentre il valore era presso quel broker, o in viaggio da esso. Non è la plusvalenza latente delle posizioni detenute dal broker.

### 📐 Il flusso interno

Una **coppia interna** è un CASH\_TRANSFER, FX\_CONVERSION o TRANSFER collegato le cui due gambe sono entrambe in $S$, su due broker diversi: il mittente $A$ (la gamba in uscita) e il destinatario $B$ (la gamba in entrata). Produce un flusso, il **giorno di arrivo** $t_{arr}$, la data della gamba più tarda:

$$
\mathrm{Internal}_A(t_{arr}) = -X,
\qquad
\mathrm{Internal}_B(t_{arr}) = +X,
\qquad
X = s_A \cdot V(t_{arr})
$$

$s_A$ è la [quota di proprietà](../../../../user/brokers/sharing.md) del mittente e $V(t_{arr})$ il valore completo che l'arrivo porta a $B$ quel giorno, valutato esattamente come lo valuta il NAV:

| Coppia | $V(t_{arr})$ |
|------|--------------|
| CASH\_TRANSFER | L'importo ricevuto, convertito a $\mathrm{fx}(c, C^*, t_{arr})$ |
| FX\_CONVERSION tra broker | La gamba ricevuta, convertita allo stesso modo: $-1.000$ USD presso $A$ → $+900$ EUR presso $B$ dà $V = 900$ EUR, e il costo di conversione resta nella linea di $A$ |
| TRANSFER di titoli | $\mathrm{MV}$ della quantità ricevuta al [prezzo di valutazione](index.md#2-valuation-price) di $t_{arr}$, l'ultimo prezzo noto mantenuto se non ce n'è uno quel giorno |

Con quote uguali, $X$ è esattamente ciò che l'arrivo aggiunge a $\mathrm{NAV}_B$, quindi nessuna delle due linee salta. Il $\mathrm{CapitalBaseline}$ del perimetro resta invariato, perché un movimento interno non è capitale esterno: NAV, CapitalBaseline, TotalPnL e le sue candele, ROI, TWRR, MWRR e liquidità sono gli stessi di senza il flusso. Cambia solo la ripartizione della base tra i broker.

### ✈️ Valore in transito

Quando le gambe cadono in giorni diversi, il valore viaggia dal giorno di partenza $t_{dep}$ al giorno prima di $t_{arr}$. Nel frattempo fa parte di $\mathrm{InTransit}_A$, alla quota $s_A$ del mittente, valutato ogni giorno: liquidità al tasso di cambio di quel giorno, titoli al prezzo di valutazione di quel giorno (al costo registrato sul trasferimento se il titolo non ha alcun prezzo). Nessun flusso avviene mentre il valore viaggia, quindi i suoi movimenti di prezzo e tasso di cambio restano nella linea di $A$, incluso il movimento del giorno di arrivo; la linea di $B$ parte dal valore ricevuto.

Ad esempio, $A$ riceve un deposito di 1.000 USD il giorno 0 a 0,90 EUR per USD ($C_A = 900$) e invia i dollari il giorno 1; $B$ li riceve il giorno 4. Con il tasso a 0,90, 0,91, 0,92, 0,93 nei giorni 1–4, la linea di $A$ legge 0, +10, +20, +30 e quella di $B$ resta a 0. Il giorno 4, $X = 930$ e $C_A = 900 - 930 = -30$. Una volta arrivati, i dollari sono liquidità di $B$, rivalutata ogni giorno, quindi dal giorno 5 la linea di $B$ si muove con il tasso: a 0,94, legge +10.

### 🧩 Casi speciali

- **Quote di proprietà diverse.** $X$ usa $s_A$, come il valore in transito, mentre l'arrivo aggiunge $s_B \cdot V(t_{arr})$ a $\mathrm{NAV}_B$. La linea di $B$ mantiene un gradino residuo di $(s_B - s_A)\,V(t_{arr})$ il giorno di arrivo, e TotalPnL mostra lo stesso gradino, con o senza il flusso.
- **Valore sconosciuto il giorno di arrivo.** Se $V(t_{arr})$ non può essere calcolato — il titolo non ha osservazioni il giorno $t_{arr}$ o prima ($\operatorname{mark} = \varnothing$), oppure manca un tasso di cambio — allora $X = 0$, che è ciò che l'arrivo aggiunge a $\mathrm{NAV}_B$. Non si indovina nulla: il salto resta, e il valore di un titolo compare nella linea del broker che lo detiene dal suo primo prezzo.
- **Commissioni.** Non fanno parte di $X$. Una riga FEE di 5 registrata presso il mittente, o gli stessi 5 come differenza tra le gambe ($-1.000$ inviati, $+995$ ricevuti, quindi $X = 995$), resta nella linea di $A$ come una perdita di 5.
- **Coppie sullo stesso broker.** Due gambe sullo stesso broker, come una conversione di valuta all'interno di un conto, non richiedono alcun flusso: il valore non lascia mai la linea.
- **Coppie di rettifiche.** Non sono coppie interne: ciascuna gamba resta capitale in natura al costo (vedi la tabella sopra). Il capitale del mittente diminuisce del costo medio rimosso e quello del destinatario aumenta del costo aggiunto, quindi la linea ricevente assorbe il guadagno maturato presso il mittente. Con la configurazione dell'esempio sotto ed entrambe le gambe il giorno 2 a un costo di 10, le linee leggono $A = 0$, $B = +20$; una coppia TRANSFER dà $A = +20$, $B = 0$.

### 🔍 Viste filtrate

In una vista con solo alcuni broker, una gamba TRANSFER la cui altra gamba è fuori da $S$ — o manca, o non è mai stata collegata — non può formare una coppia interna. È capitale in natura al valore di mercato alla propria data: $+\mathrm{MV}$ per titoli ricevuti, $-\mathrm{MV}$ per titoli inviati, alla quota di quel broker, e nulla se il titolo non può essere valutato quel giorno. A differenza di un flusso interno, sposta il CapitalBaseline della vista, quindi TotalPnL, ROI, TWRR e MWRR della vista lo trattano come capitale, come una rettifica in natura. Una gamba CASH\_TRANSFER o FX\_CONVERSION nella stessa posizione è liquidità esterna al suo importo, come un deposito o un prelievo.

Una gamba perde il collegamento quando il broker che detiene l'altra gamba viene eliminato. Una tale orfana segue le stesse regole in ogni vista, inclusa quella completa.

Confrontando la vista di un singolo broker con la vista combinata:

- **Il destinatario da solo coincide con la propria linea nella vista combinata.** Nella vista propria di $B$ i titoli ricevuti sono capitale al loro valore di mercato il giorno $t_{arr}$, che è la $X$ della vista combinata. Questo vale con quote uguali e un prezzo che entrambe le viste possono vedere: un prezzo che proviene solo da scambi presso $A$ non è visibile nella vista propria di $B$.
- **Il mittente da solo perde i movimenti in transito.** Nella vista propria di $A$ il suo capitale diminuisce il giorno di partenza di $s_A \cdot V(t_{dep})$, mentre nella vista combinata il valore resta con $A$ fino all'arrivo.

Indicando con $\mathrm{PnL}_A^{(S)}$ la linea di $A$ nella vista del perimetro $S$, a partire dal giorno di partenza:

$$
\mathrm{PnL}_A^{(A)}(t) = \mathrm{PnL}_A^{(A,B)}(t) - s_A\bigl[V(\min(t, t_{arr})) - V(t_{dep})\bigr]
$$

### 📦 Esempio — Titoli in transito

Tutti gli importi in EUR, quote 100%. $A$ riceve un deposito di 100 e acquista 10 unità a 10 il giorno 0. Il prezzo è 10, 11, 12, 13, 14, 15 nei giorni 0–5. $A$ invia le 10 unità il giorno 1, e $B$ le riceve il giorno 3.

**Vista combinata** (entrambi i broker in $S$):

| Giorno | Prezzo | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|-----|-------|------------------|-------|------------------|------------------|-------|------------------|----------|
| 0 | 10 | 100 | 100 | 0 | 0 | 0 | 0 | 0 |
| 1 | 11 | 110 (in transito) | 100 | +10 | 0 | 0 | 0 | +10 |
| 2 | 12 | 120 (in transito) | 100 | +20 | 0 | 0 | 0 | +20 |
| 3 | 13 | 0 | −30 | +30 | 130 | 130 | 0 | +30 |
| 4 | 14 | 0 | −30 | +30 | 140 | 130 | +10 | +40 |
| 5 | 15 | 0 | −30 | +30 | 150 | 130 | +20 | +50 |

Il giorno 3 il flusso $X = 10 \times 13 = 130$ sposta capitale da $A$ a $B$. $A$ mantiene i +30 maturati mentre le unità erano presso $A$ o in viaggio (10 → 13), e $B$ guadagna da 13 in poi. $C_A$ diventa negativo perché $A$ ha trasferito più valore (130) del capitale che ha ricevuto (100): la differenza è il suo guadagno. TotalPnL è lo stesso con o senza il flusso; senza di esso, il giorno 3 la linea di $A$ scenderebbe a $0 - 100 = -100$ e quella di $B$ salterebbe a $130 - 0 = +130$.

**Viste per singolo broker**:

| Giorno | $B$ da solo: $C_B$ | $B$ da solo: $\mathrm{PnL}_B$ | $A$ da solo: $C_A$ | $A$ da solo: $\mathrm{PnL}_A$ |
|-----|------------------|-----------------------------|------------------|-----------------------------|
| 0 | — | — | 100 | 0 |
| 1 | — | — | −10 | +10 |
| 2 | — | — | −10 | +10 |
| 3 | 130 | 0 | −10 | +10 |
| 4 | 130 | +10 | −10 | +10 |
| 5 | 130 | +20 | −10 | +10 |

La vista propria di $B$ inizia dalla sua prima transazione e coincide con $B$ nella vista combinata. Nella vista propria di $A$ le unità escono il giorno 1 a $10 \times 11 = 110$, quindi $C_A = 100 - 110 = -10$ e la linea resta a +10: il movimento da 11 a 13 durante il viaggio non è incluso, e $+30 - (130 - 110) = +10$. Se conteggiato come guadagno o perdita invece che come capitale, lo stesso trasferimento metterebbe $A$ da solo a −100 dal giorno 1 e $B$ da solo a +130 il giorno 3.

### 💶 Esempio — Liquidità tra due broker

$A$ riceve un deposito di 5.000. Più tardi, $A$ invia 1.000 a $B$, entrambe le gambe lo stesso giorno.

| Caso | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|------|------------------|-------|------------------|------------------|-------|------------------|----------|
| Dopo il deposito | 5.000 | 5.000 | 0 | 0 | 0 | 0 | 0 |
| Dopo il trasferimento | 4.000 | 4.000 | 0 | 1.000 | 1.000 | 0 | 0 |
| $B$ riceve 995 (commissione 5) | 4.000 | 4.005 | −5 | 995 | 995 | 0 | −5 |
| $B$ posseduto al 50% | 4.000 | 4.000 | 0 | 500 | 1.000 | −500 | −500 |
| Senza il flusso | 4.000 | 5.000 | −1.000 | 1.000 | 0 | +1.000 | 0 |

L'ultima riga è lo stesso trasferimento letto senza il flusso interno: il movimento appare come una perdita per $A$ e un guadagno per $B$. Con $B$ posseduto al 50%, il gradino di −500 è il residuo $(s_B - s_A)\,V = (0{,}5 - 1) \times 1.000$, e TotalPnL lo mostra anch'esso.

---

## 📊 Modello di liquidità a tre pool {: #three-pool-cash-model }

Il grafico di crescita scompone la liquidità corrente in due aggregati visibili più un tracker globale nascosto:

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Pool | Perimetro | Significato |
|------|-------|---------|
| $K_b$ | Per broker | Capitale esterno ancora presso il broker $b$ |
| $R_b$ | Per broker | Rendimenti generati ancora presso il broker $b$ |
| $W$ | Globale | Rendimenti che hanno lasciato il sistema (ripristinabili al nuovo deposito) |

!!! info "Proprietà chiave"

    - $\mathrm{CapitalBaseline}$ = somma storica dei flussi di liquidità e capitale in natura. $\sum K_b$ = quanta liquidità corrente è capitale esterno. Divergono dopo BUY/SELL.
    - Un BUY sul broker $b_1$ consuma solo $R_{b_1}$, mai $R_{b_2}$.
    - I giroconti tra broker spostano $R$ e $K$ dall'origine alla destinazione senza toccare $W$.
    - Un risultato di cambio sulla liquidità che un broker detiene in un'altra valuta va in $R_b$; una perdita maggiore di $R_b$ esce da $K_b$, come fa una FEE. $\mathrm{CapitalBaseline}$ non si muove ([Portfolio Engine — §6](index.md#exchange-result-on-foreign-cash)).

🔗 Regole complete di aggiornamento per broker: **[Portfolio Engine — §6 Modello a tre pool](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)**

---

## 📝 Esempi svolti

### 🧾 A — Deposito → Acquisto → Vendita in guadagno

| Passo | Tx | $K$ | $R$ | Liquidità |
|------|----|-----|-----|------|
| 1 | DEPOSIT €1.000 | 1.000 | 0 | 1.000 |
| 2 | BUY €1.000 | 0 | 0 | 0 |
| 3 | SELL P=€1.200, C=€1.000 | 1.000 | 200 | 1.200 |

TotalPnL = 1.200 − 1.000 = **+€200** ✓

### 💸 B — Dividendo poi Prelievo

| Passo | Tx | $K$ | $R$ | $W$ | Liquidità |
|------|----|-----|-----|-----|------|
| 1 | DEPOSIT €1.000 | 1.000 | 0 | 0 | 1.000 |
| 2 | DIVIDEND €50 | 1.000 | 50 | 0 | 1.050 |
| 3 | WITHDRAWAL €100 (prima K) | 900 | 50 | 0 | 950 |
| 4 | WITHDRAWAL €950 (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DEPOSIT €30 (ripristina min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Dopo il passo 5: Liquidità=30, K=0, R=30 ✓ (rendimenti ripristinati da W)

### 🧪 C — Regressione su vendita totale

| Passo | Tx | $K$ | $R$ | Liquidità |
|------|----|-----|-----|------|
| 1 | DEPOSIT €1.000, BUY 1@€1.000 | 0 | 0 | 0 |
| 2 | SELL 1@€1.005 (C=1000, G=5) | 1.000 | 5 | 1.005 |

Il capitale ritorna correttamente a $K$; solo €5 di guadagno a $R$. **Non** tutti i €1.005 a $R$.

### 💱 D — Dollari detenuti mentre il tasso si muove

Un solo broker, valuta di riferimento EUR, tassi in EUR per USD; $\varepsilon$ è il [risultato di cambio sulla liquidità](index.md#exchange-result-on-foreign-cash).

| Passo | Evento | $\varepsilon$ | $K$ | $R$ | Liquidità | TotalPnL |
|------|-------|---------------|-----|-----|------|----------|
| 1 | DEPOSIT 1.000 USD a 0,90 | — | 900 | 0 | 900 | 0 |
| 2 | Il tasso sale a 0,95 | +50 | 900 | 50 | 950 | +50 |
| 3 | Il tasso scende a 0,85 ($R$ = 50 − 100, $K$ assorbe −50) | −100 | 850 | 0 | 850 | −50 |
| 4 | BUY per 1.000 USD a 0,85 (€850) | — | 0 | 0 | 0 | MV − 900 |

La CapitalBaseline resta a €900 per tutto l'esempio: i risultati di cambio sono profitti e perdite, non capitale. Dopo il passo 4, TotalPnL è il valore di mercato MV del titolo meno i €900 depositati — −50 il giorno dell'acquisto se MV è uguale al prezzo pagato di €850.

---

## ⚙️ Implementazione

Il modello a 3 pool viene eseguito in un **singolo ciclo per transazione** (event-driven, non delta giornaliero):

1. Prendi la quota della transazione dal pool del costo medio della sua posizione, calcolata prima del replay — per un SELL, il costo che rimuove ($C$ = PMC pre-vendita × quantità venduta, a tassi storici)
2. Aggiorna K/R/W secondo le regole del tipo di transazione, con quel $C$ per un SELL

In ogni giorno in cui cambia il tasso di cambio di una valuta estera detenuta come liquidità, anche il risultato di cambio di ciascun broker su quella liquidità viene registrato nei suoi pool, dopo i movimenti di cassa del giorno e prima delle transazioni del giorno ([§6](index.md#exchange-result-on-foreign-cash)).

La serie di input per ROI/TWRR/MWRR deriva dalle variazioni giorno per giorno di `cumulative_external_cash_flow`, la base del capitale. Non deriva dal campo `external_cash_flow`, che considera solo la liquidità.

🔗 Vedi **[Portfolio Engine — §6](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** per tutte le regole formali.

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — l'altro termine nel PnL totale
- 📊 [P&L periodo](period-pnl.md) — versione a finestra
- ⚙️ [Portfolio Engine](index.md) — modello matematico completo
- 📈 [Panoramica delle metriche di performance](../index.md) — tutte le metriche di performance a colpo d'occhio
