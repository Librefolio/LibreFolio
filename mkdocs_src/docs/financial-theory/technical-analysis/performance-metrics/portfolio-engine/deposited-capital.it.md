# 💸 Capitale versato, P&L totale e pool di liquidità

## 💡 Panoramica del concetto

**Base di capitale** = capitale economico cumulativo conferito dall'inizio:

$$
\mathrm{CapitalBaseline}(t)=
\sum_{\tau \leq t}\mathrm{ExternalCashFlow}(\tau)
+ \sum_{\tau \leq t}\mathrm{InKindCapital}(\tau)
$$

**P&L totale** = tutto il valore generato al di sopra dei contributi esterni:

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{CapitalBaseline}(t)}
$$

`InKindCapital` copre i titoli che entrano o escono dal perimetro senza liquidità:

- righe di RETTIFICA in entrata che portano un costo di carico (`cost_basis_override`, non collegate a uno split), **al costo**: il costo che aggiungono alla posizione; una riga in uscita non conta mai: non ha valore ([Rettifiche in uscita](#outgoing-adjustments));
- gambe di TRASFERIMENTO la cui altra gamba non è nel perimetro — si trova presso un broker fuori dalla vista, è mancante o non è mai stata collegata — **al valore di mercato** alla propria data: $+$ per i titoli ricevuti, $-$ per i titoli inviati. Una gamba ricevuta con un costo di carico, per un titolo senza quotazione e senza altre operazioni alla sua data o prima, attribuisce al titolo il suo prezzo: il proprio costo, come [stima](price-resolution.md#transfer-cost-estimate), così alla sua data il suo valore di mercato è quel costo e la gamba è neutra. Un titolo senza alcun prezzo a quella data — nessuna quotazione, nessun ACQUISTO o VENDITA e nessuna stima del genere alla data o prima — viene invece conteggiato **al costo**: il costo che la gamba sposta nella sua posizione, il costo che una gamba ricevuta aggiunge o il prezzo medio di carico (PMC) che una gamba inviata rimuove. Un costo sconosciuto conta come zero, come nel costo proprio della posizione. Finché il costo della posizione è completo, il NAV valuta la posizione a quello stesso costo e la gamba è neutra; con parte del costo sconosciuta, la posizione non ha valore nel NAV, ma la gamba sposta comunque il suo costo noto, così non resta nulla nel capitale una volta esaurite le unità. Non conta nulla se il titolo non può essere valorizzato quel giorno: ha un prezzo, ma manca il tasso di cambio.

Queste righe spostano valore senza liquidità: sono capitale, non utile o perdita. Una RETTIFICA in uscita non è capitale: realizza come perdita il PMC a cui la sua posizione rinuncia.

---

## 🎯 Cosa conta

| Transazione | Effetto sulla base di capitale |
|------------|-----------------|
| DEPOSITO / PRELIEVO (non collegati) | ✅ Sì |
| GIROCONTO / CONVERSIONE FX la cui altra gamba è fuori dalla vista, mancante o mai collegata (orfana) | ✅ Sì, per il suo importo, come un deposito o un prelievo |
| GIROCONTO / CONVERSIONE FX / TRASFERIMENTO con entrambe le gambe nella vista (coppia interna) | ❌ No. Per broker, una coppia tra due broker sposta capitale dal mittente al destinatario il giorno di arrivo, con somma zero ([Trasferimenti interni](#internal-transfers-broker-lines)) |
| TRASFERIMENTO di titoli la cui altra gamba è fuori dalla vista, mancante o mai collegata (orfana) | ✅ Sì, capitale in natura al valore di mercato alla sua data, oppure al costo per un titolo senza alcun prezzo |
| RETTIFICA in entrata con `cost_basis_override`, non collegata a uno split | ✅ Sì, capitale in natura al costo |
| RETTIFICA in uscita | ❌ No: non ha valore e realizza come perdita il costo delle sue unità ([sotto](#outgoing-adjustments)) |
| RETTIFICA collegata a SPLIT | ❌ No, solo ridimensionamento della quantità |
| ACQUISTO, VENDITA, DIVIDENDO, INTERESSE, COMMISSIONE, IMPOSTA | ❌ No |
| Variazione del tasso di cambio sulla liquidità detenuta in un'altra valuta (nessuna transazione) | ❌ No: è un risultato, parte del P&L totale; i flussi di capitale (depositi, prelievi, gambe di liquidità orfane) sono entrati nella base di capitale al tasso delle proprie date |

---

## 📤 Rettifiche in uscita {: #outgoing-adjustments }

Una RETTIFICA che rimuove $|q|$ unità dell'asset $a$ dal broker $b$ alla data $d$ — unità regalate, inviate a un conto che LibreFolio non monitora o rimosse da una correzione — **non ha valore**, qualunque costo di carico porti la riga: riduce solo la quantità. La posizione rinuncia al costo storico di quelle unità, al suo [PMC](../weighted-average-cost.md) prima della rettifica, ogni acquisto al tasso della propria data, e non rientra nulla:

$$
C = s_b \cdot |q| \cdot w_{\text{pre}}(a,b)
$$

$$
\Delta\mathrm{CapitalBaseline}(d) = 0, \qquad \mathrm{Realized} = -C
$$

$s_b$ è la [quota di proprietà](../../../../user/brokers/sharing.md) del broker.

- **Capitale.** Nulla esce dalla base di capitale, né dal capitale della linea del broker $b$. Nessuna liquidità si muove, quindi i [pool di liquidità](#three-pool-cash-model) non cambiano.
- **Realizzato.** $-C$ conta nel P&L realizzato del periodo e nel contributo della posizione ([P&L periodo](period-pnl.md)), ed è escluso, come per una vendita, quando il costo della posizione è incompleto. Il PMC delle unità che restano non cambia.
- **Rendimenti.** TWRR e MWRR prendono i loro flussi dalle variazioni della base di capitale, quindi la rettifica non è un flusso: il valore delle unità esce dal NAV e il rendimento del giorno la interpreta come una perdita.

Una RETTIFICA collegata a uno split è l'eccezione (tabella sopra): ridimensiona solo la quantità. Le unità che escono in cambio di denaro sono una VENDITA.

!!! example "Due azioni regalate"

    Valuta di riferimento EUR, quota 100%. Un deposito di €500 acquista 10 azioni a €50; il prezzo sale a €80. Una RETTIFICA di −2 azioni ne regala due, con il prezzo invariato quel giorno: $C = 2 \times 50 = 100$.

    | Momento | NAV | CapitalBaseline | P&L totale | Realizzato |
    |--------|-----|-----------------|----------|----------|
    | Prima della rettifica | 800 | 500 | +300 | 0 |
    | Dopo la rettifica | 640 | 500 | +140 | −100 |

    Le 8 azioni rimaste mantengono un PMC di €50, quindi la loro plusvalenza latente è $8 \times (80 - 50) = 240$, e $-100 + 240 = +140$. Il flusso del giorno è 0, quindi il TWRR risulta $640 / 800 - 1 = -20\%$ quel giorno.

---

## 🔀 Trasferimenti interni nelle linee dei broker {: #internal-transfers-broker-lines }

Con due o più broker nel perimetro, il [grafico P&L](../../../../user/dashboard/charts.md#pnl-line) disegna una linea per broker. Ogni broker $b \in S$ ha il proprio NAV, capitale e P&L:

$$
\mathrm{PnL}_b(t) = \mathrm{NAV}_b(t) - C_b(t)
$$

$$
\mathrm{NAV}_b(t) = \mathrm{MV}_b(t) + \mathrm{Cash}_b(t) + \mathrm{InTransit}_b(t)
$$

$$
C_b(t) = \sum_{\tau \leq t}\mathrm{ExternalCashFlow}_b(\tau) + \sum_{\tau \leq t}\mathrm{InKindCapital}_b(\tau) + \sum_{\tau \leq t}\mathrm{Internal}_b(\tau)
$$

$\mathrm{InTransit}_b$ è il valore in transito che ha lasciato $b$, e $\mathrm{Internal}_b$ è il lato di $b$ dei trasferimenti interni descritti di seguito. Poiché $\sum_b \mathrm{NAV}_b = \mathrm{NAV}$ e i flussi interni si annullano ogni giorno, le linee si sommano alle cifre del perimetro:

$$
\sum_{b \in S}\mathrm{Internal}_b(t) = 0
\quad\Rightarrow\quad
\sum_{b \in S} C_b(t) = \mathrm{CapitalBaseline}(t),
\qquad
\sum_{b \in S}\mathrm{PnL}_b(t) = \mathrm{TotalPnL}(t)
$$

La linea di un broker è quindi il P&L guadagnato mentre il valore era presso quel broker, o in viaggio da esso. Non è la plusvalenza latente delle posizioni detenute dal broker.

### 📐 Il flusso interno

Una **coppia interna** è costituita da un GIROCONTO, CONVERSIONE FX o TRASFERIMENTO collegato le cui due gambe sono entrambe in $S$, su due broker diversi: il mittente $A$ (la gamba in uscita) e il destinatario $B$ (la gamba in entrata). Produce un flusso, nel **giorno di arrivo** $t_{arr}$, alla data della gamba successiva:

$$
\mathrm{Internal}_A(t_{arr}) = -X,
\qquad
\mathrm{Internal}_B(t_{arr}) = +X,
\qquad
X = s_A \cdot V(t_{arr})
$$

$s_A$ è la [quota di proprietà](../../../../user/brokers/sharing.md) del mittente e $V(t_{arr})$ il valore completo che l'arrivo porta a $B$ quel giorno, valorizzato esattamente come lo valuta il NAV:

| Coppia | $V(t_{arr})$ |
|------|--------------|
| GIROCONTO | L'importo ricevuto, convertito a $\mathrm{fx}(c, C^*, t_{arr})$ |
| CONVERSIONE FX tra broker | La gamba ricevuta, convertita allo stesso modo: $-1{,}000$ USD presso $A$ → $+900$ EUR presso $B$ dà $V = 900$ EUR, e il costo di conversione resta nella linea di $A$ |
| TRASFERIMENTO di titoli | $\mathrm{MV}$ della quantità ricevuta al [prezzo di valorizzazione](index.md#2-valuation-price) di $t_{arr}$, l'ultimo prezzo noto mantenuto se non ce n'è uno quel giorno. In assenza di qualsiasi prezzo alla data $t_{arr}$ o prima, il costo di carico che le unità aggiungono alla posizione di $B$ — il costo registrato sulla gamba di $B$, convertito alla data di quella gamba —, poiché il NAV valuta al costo una posizione senza prezzo ([§3](index.md#3-position-state)) |

Con quote uguali, $X$ è esattamente ciò che l'arrivo aggiunge a $\mathrm{NAV}_B$, quindi nessuna delle due linee salta. Il $\mathrm{CapitalBaseline}$ del perimetro resta intatto, perché uno spostamento interno non è capitale esterno: NAV, CapitalBaseline, P&L totale e le sue candele, ROI, TWRR, MWRR e liquidità sono gli stessi di senza il flusso. Cambia solo la ripartizione della base di capitale tra i broker.

### ✈️ Valore in transito

Quando le gambe cadono in giorni diversi, il valore viaggia dal giorno di partenza $t_{dep}$ al giorno prima di $t_{arr}$. Nel frattempo fa parte di $\mathrm{InTransit}_A$, alla quota del mittente $s_A$, valorizzato ogni giorno: la liquidità al tasso di cambio di quel giorno, i titoli al prezzo di valorizzazione di quel giorno (al costo registrato sul trasferimento se il titolo non ha alcun prezzo). Nessun flusso avviene mentre il valore viaggia, quindi le sue variazioni di prezzo e di tasso di cambio restano nella linea di $A$, inclusa la variazione del giorno di arrivo; la linea di $B$ parte dal valore ricevuto.

Ad esempio, $A$ riceve un deposito di 1,000 USD il giorno 0 a 0.90 EUR per USD ($C_A = 900$) e invia i dollari il giorno 1; $B$ li riceve il giorno 4. Con il tasso a 0.90, 0.91, 0.92, 0.93 nei giorni 1–4, la linea di $A$ segna 0, +10, +20, +30 e quella di $B$ resta a 0. Il giorno 4, $X = 930$ e $C_A = 900 - 930 = -30$. Una volta arrivati, i dollari sono liquidità di $B$, rivalutata ogni giorno, quindi dal giorno 5 la linea di $B$ si muove con il tasso: a 0.94, segna +10.

### 🧩 Casi speciali

- **Quote di proprietà diverse.** $X$ usa $s_A$, come il valore in transito, mentre l'arrivo aggiunge $s_B \cdot V(t_{arr})$ a $\mathrm{NAV}_B$. La linea di $B$ mantiene un salto residuo di $(s_B - s_A)\,V(t_{arr})$ il giorno di arrivo, e il P&L totale mostra lo stesso salto, con o senza il flusso.
- **Valore sconosciuto nel giorno di arrivo.** Se $V(t_{arr})$ non può essere calcolato — manca un tasso di cambio, oppure il titolo non ha osservazioni alla data $t_{arr}$ o prima ($\operatorname{mark} = \varnothing$) e il costo sulla gamba di $B$ è sconosciuto (nessun costo di carico, o uno senza tasso di cambio), così che l'arrivo non aggiunge nulla al costo della posizione di $B$ — allora $X = 0$. Non si indovina nulla: il salto resta, e il valore del titolo compare nella linea del broker che lo detiene a partire dal suo primo prezzo.
- **Nessun prezzo.** Un titolo senza osservazioni alla data $t_{arr}$ o prima si muove al costo che il suo arrivo aggiunge alla posizione di $B$ — il costo registrato sulla gamba di $B$, il PMC del mittente quando il trasferimento viene salvato con un costo di carico automatico — indipendentemente dal fatto che il costo di $B$ sia completo. Con il costo di $B$ completo, quello è il valore a cui il $\mathrm{NAV}_B$ prende le unità, quindi con quote uguali la linea di $B$ non salta. Il costo non deve coincidere con il valore che le unità avevano presso $A$ prima di partire (il costo di carico proprio di $A$, o nulla quando quel costo era incompleto); la differenza finisce nella linea di $A$, e il P&L totale la mostra anch'esso. Con il costo di $B$ incompleto — $B$ deteneva già unità di costo sconosciuto — la posizione di $B$ non ha valore nel NAV, che è incompleto: la linea di $B$ assorbe il divario, il proprio costo sconosciuto, e la linea di $A$ è la stessa di con un costo completo presso $B$.
- **Commissioni.** Non fanno parte di $X$. Una riga COMMISSIONE di 5 registrata presso il mittente, o gli stessi 5 come divario tra le gambe ($-1{,}000$ inviati, $+995$ ricevuti, quindi $X = 995$), restano nella linea di $A$ come una perdita di 5.
- **Coppie sullo stesso broker.** Due gambe sullo stesso broker, come una conversione di valuta all'interno di un singolo conto, non richiedono alcun flusso: il valore non lascia mai la linea.
- **Coppie di RETTIFICHE.** Non sono coppie interne: ogni gamba segue la propria regola (vedi la tabella sopra). Il capitale del destinatario aumenta del costo che la sua gamba aggiunge; la gamba del mittente non ha valore, quindi il suo capitale non si muove e realizza come perdita il proprio PMC ([Rettifiche in uscita](#outgoing-adjustments)). Con la configurazione dell'esempio sotto ed entrambe le gambe il giorno 2, la gamba ricevente a un costo di 10: la linea di $A$ scende a $-100$ e quella di $B$ segna $+20$, quindi il P&L totale scende da $+20$ a $-80$. Per spostare unità tra due broker senza quella perdita, collega le due rettifiche come coppia TRASFERIMENTO.

### 🔍 Viste filtrate

In una vista con solo alcuni broker, una gamba di TRASFERIMENTO la cui altra gamba è fuori da $S$ — o mancante, o mai collegata — non può formare una coppia interna. È capitale in natura al valore di mercato alla propria data: $+\mathrm{MV}$ per i titoli ricevuti, $-\mathrm{MV}$ per i titoli inviati, alla quota di quel broker — al costo per un titolo senza alcun prezzo, come sopra — e nulla se il titolo non può essere valorizzato quel giorno. A differenza di un flusso interno, sposta il CapitalBaseline della vista, quindi il P&L totale, il ROI, il TWRR e il MWRR della vista lo trattano come capitale, come una RETTIFICA in natura. Una gamba di GIROCONTO o CONVERSIONE FX nella stessa situazione è liquidità esterna per il suo importo, come un deposito o un prelievo, e sposta i [pool di liquidità](#three-pool-cash-model) come farebbe quel deposito o prelievo: la ripartizione della liquidità della vista tra capitale conferito e rendimenti generati, e il finanziamento dei suoi acquisti successivi, ne derivano.

Quando il broker che detiene l'altra gamba viene eliminato, la gamba rimanente diventa ciò che resta quando la coppia viene separata, e le gambe lasciate dalle versioni precedenti vengono convertite allo stesso modo all'avvio: i titoli diventano una RETTIFICA — una gamba ricevuta è capitale in natura al costo quando porta un costo di carico (tabella sopra), non più al valore di mercato; una gamba inviata è una RETTIFICA in uscita senza valore, che realizza come perdita il costo delle sue unità ([Rettifiche in uscita](#outgoing-adjustments)) — e la liquidità un DEPOSITO o un PRELIEVO. Le righe convertite seguono le stesse regole in ogni vista, inclusa quella completa.

Confrontando la vista propria di un broker con la vista combinata:

- **Il destinatario da solo coincide con la sua linea combinata.** Nella vista propria di $B$, i titoli ricevuti sono capitale al loro valore di mercato a $t_{arr}$, che è la $X$ della vista combinata. Questo vale con quote uguali e un prezzo che entrambe le viste possono vedere: un prezzo che deriva solo da scambi presso $A$ non è visibile nella vista propria di $B$.
- **Il mittente da solo perde i movimenti in transito.** Nella vista propria di $A$, il suo capitale diminuisce il giorno di partenza di $s_A \cdot V(t_{dep})$, mentre nella vista combinata il valore resta con $A$ fino all'arrivo.

Scrivendo $\mathrm{PnL}_A^{(S)}$ per la linea di $A$ nella vista del perimetro $S$, dal giorno di partenza in poi:

$$
\mathrm{PnL}_A^{(A)}(t) = \mathrm{PnL}_A^{(A,B)}(t) - s_A\bigl[V(\min(t, t_{arr})) - V(t_{dep})\bigr]
$$

### 📦 Esempio — Titoli in transito

Tutti gli importi in EUR, quote 100%. $A$ riceve un deposito di 100 e acquista 10 unità a 10 il giorno 0. Il prezzo è 10, 11, 12, 13, 14, 15 nei giorni 0–5. $A$ invia le 10 unità il giorno 1, e $B$ le riceve il giorno 3.

**Vista combinata** (entrambi i broker in $S$):

| Giorno | Prezzo | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | P&L totale |
|-----|-------|------------------|-------|------------------|------------------|-------|------------------|----------|
| 0 | 10 | 100 | 100 | 0 | 0 | 0 | 0 | 0 |
| 1 | 11 | 110 (in transito) | 100 | +10 | 0 | 0 | 0 | +10 |
| 2 | 12 | 120 (in transito) | 100 | +20 | 0 | 0 | 0 | +20 |
| 3 | 13 | 0 | −30 | +30 | 130 | 130 | 0 | +30 |
| 4 | 14 | 0 | −30 | +30 | 140 | 130 | +10 | +40 |
| 5 | 15 | 0 | −30 | +30 | 150 | 130 | +20 | +50 |

Il giorno 3 il flusso $X = 10 \times 13 = 130$ sposta capitale da $A$ a $B$. $A$ mantiene i +30 guadagnati mentre le unità erano presso $A$ o in viaggio (10 → 13), e $B$ guadagna da 13 in poi. $C_A$ diventa negativo perché $A$ ha trasferito più valore (130) del capitale che ha ricevuto (100): la differenza è il suo guadagno. Il P&L totale è lo stesso con o senza il flusso; senza di esso, il giorno 3 la linea di $A$ scenderebbe a $0 - 100 = -100$ e quella di $B$ salterebbe a $130 - 0 = +130$.

**Viste di singoli broker**:

| Giorno | $B$ da solo: $C_B$ | $B$ da solo: $\mathrm{PnL}_B$ | $A$ da solo: $C_A$ | $A$ da solo: $\mathrm{PnL}_A$ |
|-----|------------------|-----------------------------|------------------|-----------------------------|
| 0 | — | — | 100 | 0 |
| 1 | — | — | −10 | +10 |
| 2 | — | — | −10 | +10 |
| 3 | 130 | 0 | −10 | +10 |
| 4 | 130 | +10 | −10 | +10 |
| 5 | 130 | +20 | −10 | +10 |

La vista propria di $B$ inizia dalla sua prima transazione e coincide con $B$ nella vista combinata. Nella vista propria di $A$, le unità escono il giorno 1 a $10 \times 11 = 110$, quindi $C_A = 100 - 110 = -10$ e la linea resta a +10: il movimento da 11 a 13 durante il viaggio non è incluso, e $+30 - (130 - 110) = +10$. Conteggiato come guadagno o perdita invece che come capitale, lo stesso trasferimento porterebbe $A$ da solo a −100 dal giorno 1 e $B$ da solo a +130 il giorno 3.

### 💶 Esempio — Giroconto tra due broker

$A$ riceve un deposito di 5,000. Successivamente, $A$ invia 1,000 a $B$, entrambe le gambe nello stesso giorno.

| Caso | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | P&L totale |
|------|------------------|-------|------------------|------------------|-------|------------------|----------|
| Dopo il deposito | 5,000 | 5,000 | 0 | 0 | 0 | 0 | 0 |
| Dopo il giroconto | 4,000 | 4,000 | 0 | 1,000 | 1,000 | 0 | 0 |
| $B$ riceve 995 (commissione 5) | 4,000 | 4,005 | −5 | 995 | 995 | 0 | −5 |
| $B$ con quota al 50% | 4,000 | 4,000 | 0 | 500 | 1,000 | −500 | −500 |
| Senza il flusso | 4,000 | 5,000 | −1,000 | 1,000 | 0 | +1,000 | 0 |

L'ultima riga è lo stesso trasferimento interpretato senza il flusso interno: lo spostamento appare come una perdita per $A$ e un guadagno per $B$. Con una quota del 50% in $B$, il salto di −500 è il residuo $(s_B - s_A)\,V = (0.5 - 1) \times 1{,}000$, e il P&L totale lo mostra anch'esso.

---

## 📊 Modello a tre pool di liquidità {: #three-pool-cash-model }

Il grafico di crescita scompone la liquidità corrente in due aggregati visibili più un tracker globale nascosto:

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Pool | Perimetro | Significato |
|------|-------|---------|
| $K_b$ | Per broker | Capitale esterno ancora presso il broker $b$ |
| $R_b$ | Per broker | Rendimenti generati ancora presso il broker $b$ |
| $W$ | Globale | Rendimenti che hanno lasciato il sistema (ripristinabili al rideposito) |

!!! info "Proprietà chiave"

    - $\mathrm{CapitalBaseline}$ = somma storica dei flussi di liquidità e capitale in natura. $\sum K_b$ = quanta liquidità corrente è capitale esterno. Divergono dopo ACQUISTO/VENDITA.
    - Un ACQUISTO sul broker $b_1$ consuma solo $R_{b_1}$, mai $R_{b_2}$.
    - I giroconti tra broker e le conversioni di valuta con entrambe le gambe nel perimetro spostano $R$ e $K$ dalla sorgente alla destinazione senza toccare $W$: la partenza lascia uscire prima i rendimenti, e l'arrivo riporta ciò che ha preso dal capitale e dai rendimenti; qualsiasi divario tra le due gambe — un'altra valuta, il tasso di un altro giorno, un'altra quota di proprietà — è un risultato.
    - Una gamba di giroconto o conversione la cui altra gamba è fuori dal perimetro, o che ha perso la sua coppia, sposta i pool come un DEPOSITO o un PRELIEVO del suo importo: in arrivo, ripristina prima i rendimenti prelevati da $W$ in $R_b$ e il resto è $K_b$; in uscita, prende prima $K_b$, poi $R_b$, che va in $W$ ([esempio E](#e-cash-from-outside-the-view)).
    - Un risultato di cambio sulla liquidità che un broker detiene in un'altra valuta va in $R_b$; una perdita maggiore di $R_b$ esce da $K_b$, come fa una COMMISSIONE. $\mathrm{CapitalBaseline}$ non si muove ([Motore del portafoglio — §6](index.md#exchange-result-on-foreign-cash)).

🔗 Regole complete di aggiornamento per broker: **[Motore del portafoglio — §6 Modello a tre pool](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)**

---

## 📝 Esempi svolti

### 🧾 A — Deposito → Acquisto → Vendita in plusvalenza

| Passo | Tx | $K$ | $R$ | Liquidità |
|------|----|-----|-----|------|
| 1 | DEPOSITO €1,000 | 1,000 | 0 | 1,000 |
| 2 | ACQUISTO €1,000 | 0 | 0 | 0 |
| 3 | VENDITA P=€1,200, C=€1,000 | 1,000 | 200 | 1,200 |

P&L totale = 1,200 − 1,000 = **+€200** ✓

### 💸 B — Dividendo poi prelievo

| Passo | Tx | $K$ | $R$ | $W$ | Liquidità |
|------|----|-----|-----|-----|------|
| 1 | DEPOSITO €1,000 | 1,000 | 0 | 0 | 1,000 |
| 2 | DIVIDENDO €50 | 1,000 | 50 | 0 | 1,050 |
| 3 | PRELIEVO €100 (prima K) | 900 | 50 | 0 | 950 |
| 4 | PRELIEVO €950 (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RIDEPOSITO €30 (ripristina min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Dopo il passo 5: Liquidità=30, K=0, R=30 ✓ (rendimenti ripristinati da W)

### 🧪 C — Regressione sulla vendita totale

| Passo | Tx | $K$ | $R$ | Liquidità |
|------|----|-----|-----|------|
| 1 | DEPOSITO €1,000, ACQUISTO 1@€1,000 | 0 | 0 | 0 |
| 2 | VENDITA 1@€1,005 (C=1000, G=5) | 1,000 | 5 | 1,005 |

Il capitale ritorna correttamente a $K$; solo €5 di guadagno a $R$. **Non** tutti i €1,005 a $R$.

### 💱 D — Dollari detenuti mentre il tasso si muove

Un broker, valuta di riferimento EUR, tassi in EUR per USD; $\varepsilon$ è il [risultato di cambio sulla liquidità](index.md#exchange-result-on-foreign-cash).

| Passo | Evento | $\varepsilon$ | $K$ | $R$ | Liquidità | P&L totale |
|------|-------|---------------|-----|-----|------|----------|
| 1 | DEPOSITO 1,000 USD a 0.90 | — | 900 | 0 | 900 | 0 |
| 2 | Il tasso sale a 0.95 | +50 | 900 | 50 | 950 | +50 |
| 3 | Il tasso scende a 0.85 ($R$ = 50 − 100, $K$ assorbe −50) | −100 | 850 | 0 | 850 | −50 |
| 4 | ACQUISTO per 1,000 USD a 0.85 (€850) | — | 0 | 0 | 0 | MV − 900 |

Il CapitalBaseline resta €900 per tutto il periodo: i risultati di cambio sono utili e perdite, non capitale. Dopo il passo 4, il P&L totale è il valore di mercato MV del titolo meno i €900 depositati — −50 il giorno dell'acquisto se MV è uguale agli €850 pagati.

### 🔀 E — Liquidità dall'esterno della vista {: #e-cash-from-outside-the-view }

La vista del solo broker $B$; il broker $A$ è fuori da essa, quindi ogni giroconto tra loro è un flusso esterno della vista, come nelle Viste filtrate sopra.

| Passo | Tx presso $B$ | $K$ | $R$ | $W$ | Liquidità |
|------|-----------|-----|-----|-----|------|
| 1 | DEPOSITO €100, INTERESSE €100 | 100 | 100 | 0 | 200 |
| 2 | GIROCONTO €150 verso $A$, come PRELIEVO (K=100→0, R=100→50, W+=50) | 0 | 50 | 50 | 50 |
| 3 | GIROCONTO €100 da $A$, come DEPOSITO (ripristina min(100,W=50)=50, gli altri 50 a K) | 50 | 100 | 0 | 150 |
| 4 | ACQUISTO €100 (prima R) | 50 | 0 | 0 | 50 |

L'acquisto del passo 4 è interamente rendimento reinvestito, nessuna parte è nuovo capitale. Lo stesso vale per una gamba di trasferimento che ha perso la sua coppia, in ogni vista. Nella vista di $A$ e $B$ insieme, entrambi i trasferimenti sono invece coppie interne e spostano i pool da un broker all'altro, senza toccare $W$.

---

## ⚙️ Implementazione

Il modello a 3 pool funziona in un **unico ciclo per transazione** (guidato dagli eventi, non da delta giornalieri):

1. Prendi il passo della transazione nel pool del PMC della sua posizione, calcolato prima del replay — per una VENDITA, il costo che rimuove ($C$ = PMC pre-vendita × quantità venduta, ai tassi storici)
2. Aggiorna K/R/W secondo le regole del tipo di transazione, con quel $C$ per una VENDITA

In ogni giorno in cui cambia il tasso di cambio di una valuta estera detenuta come liquidità, anche il risultato di cambio di ciascun broker su quella liquidità viene registrato nei suoi pool, dopo i movimenti di liquidità del giorno e prima delle transazioni del giorno ([§6](index.md#exchange-result-on-foreign-cash)).

La serie di input per ROI/TWRR/MWRR deriva dalle variazioni giorno per giorno di `cumulative_external_cash_flow`, la base di capitale. Non deriva dal campo `external_cash_flow`, che riguarda solo la liquidità.

🔗 Vedi **[Motore del portafoglio — §6](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** per tutte le regole formali.

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — l'altro termine nel P&L totale
- 📊 [P&L periodo](period-pnl.md) — versione su finestra
- ⚙️ [Motore del portafoglio](index.md) — modello matematico completo
- 📈 [Panoramica delle metriche di performance](../index.md) — tutte le metriche di performance a colpo d'occhio
