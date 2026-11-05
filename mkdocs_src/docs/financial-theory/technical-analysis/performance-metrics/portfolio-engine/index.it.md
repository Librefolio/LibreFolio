# ⚙️ Motore del portafoglio — Modello matematico

## 💡 Panoramica

Questa pagina definisce formalmente il modello matematico alla base del motore di calcolo del portafoglio di LibreFolio. Tutte le altre pagine delle metriche ([NAV](nav.md), [Valore contabile](book-value.md), [P&L periodo](period-pnl.md), [Rendimento sul costo](yield-on-cost.md), [PMC](../weighted-average-cost.md), [Capitale versato](deposited-capital.md)) fanno riferimento a questa pagina per le loro regole di calcolo precise.

---

## 📐 1. Notazione e insiemi

| Simbolo | Significato |
|--------|---------|
| $V(u)$ | Tutti i broker visibili all'utente $u$ |
| $S \subseteq V(u)$ | Ambito dei broker selezionati (filtrati) |
| $A$ | Insieme degli asset con posizioni |
| $C^*$ | Valuta obiettivo |
| $[t_0, t_1]$ | Intervallo di valutazione richiesto |
| $q(a,b,t)$ | Quantità dell'asset $a$ presso il broker $b$ alla data $t$ |
| $p(a,t)$ | Prezzo di valutazione dell'asset $a$ alla data $t$ |
| $\mathrm{fx}(c_1, c_2, t)$ | Tasso di cambio dalla valuta $c_1$ a $c_2$ alla data $t$ |

---

## 📐 2. Prezzo di valutazione {: #2-valuation-price }

$$
\operatorname{mark}(a,t)=
\begin{cases}
\text{MARKET}(a,t) & \text{quotazione dello stesso giorno del sistema asset}\\
\operatorname{avg}(\text{TRADE}(a,t)) & \text{osservazioni di ACQUISTO/VENDITA dello stesso giorno, o stime del costo di trasferimento}\\
\text{ultima osservazione precedente a }t & \text{mantenuta (LOCF)}\\
\varnothing & \text{nessuna osservazione in }t\text{ o precedente}
\end{cases}
$$

- Il resolver unificato è l'unico motore di valutazione: `MARKET → TRADE_AVG → CARRIED → MISSING`.
- Le quotazioni di mercato e le operazioni di acquisto/vendita sono osservazioni. Una RETTIFICA non lo è mai, in entrata o in uscita, con o senza un costo di carico: il suo costo di carico è un costo, non ciò che l'asset valeva quel giorno.
- Il costo di un TRASFERIMENTO ASSET in entrata (il suo costo di carico per unità, nella valuta del costo di carico) è un'osservazione TRADE, stimata, solo finché l'asset non ha, in quel giorno o prima, alcuna quotazione di mercato e nessun'altra operazione — nessun ACQUISTO o VENDITA, nessuna RETTIFICA, nessun trasferimento in uscita; altri trasferimenti in entrata non lo fermano. Viene mantenuto finché una quotazione o un'operazione reale non lo sostituisce, e non ne sovrascrive mai una: un titolo quotato spostato tra broker conserva la quotazione mantenuta ([Costo del trasferimento come stima](price-resolution.md#transfer-cost-estimate)).
- `CARRIED` è l'ultima osservazione mantenuta (LOCF). Trasporta i metadati di obsolescenza `days_back`.
- `estimated=True` indica origine TRADE. Una quotazione MARKET mantenuta e obsoleta è obsoleta, non stimata.
- I mark restano nella valuta originaria; ogni consumatore li converte in $C^*$ alla data di valutazione $t$.
- Il cambio del costo di carico resta ancorato alla data della transazione.
- La liquidità resta nella valuta in cui è stata registrata, broker per broker, ed è valutata al tasso di $t$ (§5); ogni movimento di liquidità viene comunque registrato, e ogni flusso di cassa esterno entra nel capitale, al tasso della propria data.
- Il PMC **non** viene mai usato come prezzo di valutazione. Una posizione il cui asset non ha alcun mark ($\varnothing$) viene invece conteggiata al suo costo di carico, come stima dichiarata, non come prezzo (§3).

Vedi [Risoluzione del prezzo](price-resolution.md) per il contratto del resolver e la semantica della qualità dei dati.

---

## 📐 3. Stato della posizione {: #3-position-state }

Una posizione $(a, b)$ è **detenuta** in $t$ quando la sua quantità supera la soglia dust $\varepsilon = 10^{-5}$ unità: $q(a,b,t) > \varepsilon$. Per ogni posizione detenuta:

$$
\mathrm{MV}(a,b,t) =
\begin{cases}
\dfrac{q(a,b,t)}{qbq(a)}\cdot \operatorname{mark}(a,t)\cdot \mathrm{fx}\bigl(\mathrm{ccy}_{mark}, C^*, t\bigr) & \operatorname{mark}(a,t) \neq \varnothing\\
\mathrm{CB}(a,b,t) & \operatorname{mark}(a,t) = \varnothing \text{ e il costo di } (a,b) \text{ è completo}
\end{cases}
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Dove $w(a,b,t)$ è il [Prezzo medio di carico (PMC)](../weighted-average-cost.md) per la posizione $(a,b)$ alla data $t$, mantenuto in $C^*$ a tassi storici (§4): il costo di carico non applica alcun tasso di cambio a $t$, quindi per un asset estero l'effetto del tasso di cambio fa parte di $\mathrm{UGL}$.

Il secondo caso copre un asset senza ancora alcuna osservazione — nessuna quotazione, nessun ACQUISTO o VENDITA e nessuna stima del costo di trasferimento in $t$ o prima, come per una posizione ricevuta tramite RETTIFICHE, o tramite trasferimenti senza costo di carico. La posizione è valutata al suo costo di carico, fonte di valutazione `ESTIMATED_AT_COST`: una stima dichiarata, non un prezzo. Non riporta alcun prezzo unitario, non si muove con i tassi di cambio e il suo $\mathrm{UGL}$ è zero, senza né un effetto prezzo né un effetto tasso di cambio. La scelta viene fatta giorno per giorno, senza look-ahead: dalla prima osservazione in poi, vince il mark, anche se vecchio e mantenuto. Una posizione il cui costo è incompleto (§4) non ha valore di mercato in un giorno siffatto (`MISSING`) ed è esclusa da $\mathrm{MV}(t)$. Le fonti di valutazione si ordinano quindi `MARKET_PRICE` > `LAST_TRADE_PRICE` > `ESTIMATED_AT_COST` > `MISSING` ([Risoluzione del prezzo](price-resolution.md)).

Una quantità pari o inferiore a $\varepsilon$ unità — il dust che una vendita di quasi tutte le unità può lasciare dietro di sé — non è detenuta: non ha stato di posizione, quindi nessun valore di mercato, nessun costo di carico, nessuna quota di allocazione e nessuno snapshot, e il dust senza mark non rende incompleto il giorno. La stessa soglia decide quali posizioni le righe di Performance includono (§7), quindi il portafoglio e le sue righe contano le stesse posizioni; dove finisce il costo del dust è spiegato nel §7.

---

## 📐 4. Aggiornamento iterativo del PMC

Mantenuto per posizione $(a,b)$ con stato del pool $(\hat{q}, \hat{c})$, il costo $\hat{c}$ mantenuto in $C^*$:

**Acquisizione** (quantità $> 0$, importo $P$ pagato nella valuta $c$ alla data $d$):

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + P \cdot \mathrm{fx}(c, C^*, d), \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

$P$ è la liquidità pagata per un ACQUISTO, oppure il costo di carico per unità specificato moltiplicato per $q_{\text{tx}}$ per un TRASFERIMENTO ASSET o una RETTIFICA; $\mathrm{fx}(C^*, C^*, d) = 1$. Quando non esiste alcun tasso in data $d$ o precedente, oppure l'acquisizione non ha costo di carico, la quantità entra e il costo no: il costo della posizione viene contrassegnato come incompleto invece di essere conteggiato come zero.

**Riduzione** (quantità $< 0$):

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

**Split** (collegato a un evento split): $\hat{q}$ cambia, $\hat{c}$ no.

!!! info "Ordinamento"

    All'interno della stessa data: le aggiunte vengono elaborate prima delle riduzioni. Ciò garantisce che una VENDITA legga il PMC corretto, inclusi gli ACQUISTI dello stesso giorno.

---

## 📐 5. Aggregazione del portafoglio {: #5-portfolio-aggregation }

$$
\mathrm{MV}(t) = \sum_{(a,b) \in S} \mathrm{MV}(a,b,t)
$$

$$
\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)
$$

$$
\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)
$$

$$
\mathrm{UGL}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

$\mathrm{MV}(t)$ e $\mathrm{OCB}(t)$ considerano le posizioni detenute in $t$ (§3): il dust, pari o inferiore alla soglia, non è in nessuna delle due, quindi non è né in NAV né in Book.

$\mathrm{Cash}(t)$ è la liquidità di ciascun broker, mantenuta nelle valute in cui è stata registrata e valutata al tasso di $t$:

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

dove $N_{b,c}(t)$ è il saldo del broker $b$ nella valuta $c$ dopo i suoi movimenti datati in $t$ o precedenti, scalato per la [quota di proprietà](../../../../user/brokers/sharing.md) del broker, e $\mathrm{fx}(c, C^*, t)$ è il tasso più recente in $t$ o precedente ($1$ per $c = C^*$). Lo stesso termine è in NAV e in Book, quindi l'effetto del tasso di cambio sulla liquidità si annulla in UGL: viene registrato come risultato di cambio (§6) e appartiene al P&L totale.

### 🔀 Due valori non realizzati {: #two-unrealized-figures }

$\mathrm{InTransit}(t)$ e $\mathrm{InTransitBook}(t)$ contengono la stessa liquidità in transito, e i titoli in viaggio tra due broker di $S$ al valore di mercato, $\mathrm{MV}^{\mathrm{tr}}(t)$, nel primo e al costo storico, $\mathrm{CB}^{\mathrm{tr}}(t)$, nel secondo. La liquidità si annulla, quindi con $\mathrm{OCB}(t)$ il costo di carico delle posizioni detenute (§3):

$$
\mathrm{UGL}(t) = \bigl[\mathrm{MV}(t) - \mathrm{OCB}(t)\bigr] + \bigl[\mathrm{MV}^{\mathrm{tr}}(t) - \mathrm{CB}^{\mathrm{tr}}(t)\bigr]
$$

Il motore riporta due valori non realizzati:

| Valore | Definizione | Dove compare |
|--------|-----------|----------------|
| Non realizzato del portafoglio | $\mathrm{UGL}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)$, titoli in transito inclusi | `unrealized_gain_loss` del riepilogo e dei punti storici del report del portafoglio (`POST /portfolio/report`) e dei riepiloghi di portafoglio e broker di AI Export; [Valore contabile — Non realizzato](book-value.md) |
| Non realizzato del periodo | $\mathrm{MV}(t) - \mathrm{OCB}(t)$ a ogni confine di periodo, solo posizioni detenute | `period_unrealized_gain_loss_start`, `_end`, `_delta` e la loro suddivisione per valuta; la **Variazione non realizzata** della dashboard; il $\Delta\mathrm{UGL}$ del [P&L periodo](period-pnl.md) e le righe per posizione del §7 |

Differiscono solo per i titoli in transito: in un giorno in cui nessuno è in viaggio, sono uguali. Un titolo in transito a un confine di periodo è in NAV, quindi nel P&L periodo, ma nello stato di nessuna posizione: la sua parte del risultato è nel residuo del §7, non in $\Delta\mathrm{UGL}$.

### 🏦 Il broker intero {: #whole-broker }

Ogni importo del broker $b$ — le sue quantità, la liquidità e i flussi — conta alla [quota di proprietà](../../../../user/brokers/sharing.md) $s_b$ del broker: la quota di un proprietario, $1$ per un editor o un visualizzatore. La vista **broker intero**, pensata per la pagina del broker, imposta $s_b = 1$ per ogni broker, come lo vede un editor, qualunque sia la quota dell'utente; la dashboard mantiene la quota del proprietario. Un broker del valore di 10 000 € posseduto al 30 % vale 3 000 € nella dashboard e 10 000 € intero; posseduto allo 0 %, 0 € e 10 000 €.

Per un singolo broker i rapporti sono gli stessi in entrambe le viste: ogni flusso e ogni valore è moltiplicato per la stessa costante $s_b$, che si annulla in TWRR, MWRR, ROI semplice, nei pesi e nelle percentuali di periodo. Cambiano solo gli importi.

---

## 📐 6. Modello di liquidità a tre pool — Per broker $(K_b, R_b, W)$ {: #6-three-pool-cash-model-per-broker-k_b-r_b-w }

Tre pool di accumulo tracciano la provenienza della liquidità. $K$ e $R$ sono mantenuti **per broker** $b$; $W$ è globale (esce completamente dal sistema).

| Pool | Ambito | Significato |
|------|-------|---------|
| $K_b$ | Per broker | Capitale esterno ancora presente nel broker $b$ sotto forma di liquidità |
| $R_b$ | Per broker | Rendimenti generati ancora presenti nel broker $b$ sotto forma di liquidità |
| $W$ | Globale | Rendimenti usciti dal sistema (nascosti, ripristinabili al nuovo deposito) |

!!! info "Proprietà chiave"

    Un ACQUISTO sul broker $b_1$ può consumare solo $R_{b_1}$, mai $R_{b_2}$. La liquidità non si teletrasporta tra broker — solo i trasferimenti espliciti spostano i saldi dei pool.

### 🔁 Regole di aggiornamento (per transazione sul broker $b$, in ordine cronologico)

| Icona e tipo | Formule di aggiornamento | Logica e descrizione |
|:---:|---|---|
| ![](../../../../static/icons/transactions/deposit.png){: width="24" }<br>**DEPOSITO**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Ripristina prima i rendimenti precedentemente prelevati dal tracker globale $W$, poi aggiunge il resto al capitale $K_b$. |
| ![](../../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**PRELIEVO**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consuma prima il capitale $K_b$, poi sposta i rendimenti rimanenti $\rho$ nel tracker globale $W$. |
| ![](../../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDENDO / INTERESSE**<br>$I > 0$ | $R_b \mathrel{+}= I$ | I proventi incrementano direttamente il pool dei rendimenti $R_b$. |
| ![](../../../../static/icons/transactions/fee.png){: width="24" } ![](../../../../static/icons/transactions/tax.png){: width="24" }<br>**COMMISSIONE / IMPOSTA**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consuma prima i rendimenti $R_b$; se $R_b$ diventa negativo, attinge dal capitale $K_b$. |
| ![](../../../../static/icons/transactions/buy.png){: width="24" }<br>**ACQUISTO**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consuma prima i rendimenti $R_b$, poi attinge il resto dal capitale $K_b$. |
| ![](../../../../static/icons/transactions/sell.png){: width="24" }<br>**VENDITA** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | Il costo di carico $C = |q_s| \cdot w_{\text{pre}}$ torna al capitale $K_b$; la plusvalenza $G$ va ai rendimenti $R_b$ (se $G < 0$, si comporta come una COMMISSIONE).<br><br>!!! warning "Ordinamento critico"<br><br> $C$ deve essere calcolato **prima** che il pool PMC venga ridotto (altrimenti una vendita totale darebbe $C = 0$). |
| ![](../../../../static/icons/transactions/cash-transfer.png){: width="24" } ![](../../../../static/icons/transactions/fx-conversion.png){: width="24" }<br>**GIROCONTO / CONVERSIONE FX**<br>(Interno, $s \to d$, $X > 0$ esce, $Y > 0$ arriva) | **Tratta di partenza ($s$):**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Tratta di arrivo ($d$):**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho + (Y - X)$<br>$\text{if } R_d < 0\text{: } K_d \mathrel{+}= R_d,\; R_d = 0$ | La partenza preleva prima i rendimenti $R_s$, poi il capitale $K_s$. L'arrivo riporta ciò che la partenza ha prelevato da ciascun pool. $X$ e $Y$ sono in $C^*$ al tasso della data di ciascuna tratta, ciascuno ponderato per la quota di proprietà del suo broker, quindi possono differire: lo spread di una conversione rispetto al tasso di riferimento, la variazione del tasso mentre la liquidità viaggia, due broker posseduti a quote diverse. Nessuna delle due tratte è un flusso esterno, quindi la baseline del capitale non si muove e il P&L totale conta già la differenza $Y - X$: è un **risultato**, registrato come il [risultato di cambio sulla liquidità a riposo](#exchange-result-on-foreign-cash) — una plusvalenza va ai rendimenti, una minusvalenza intacca prima i rendimenti e poi il capitale, come una COMMISSIONE. Con $Y = X$: $K_d \mathrel{+}= \kappa$, $R_d \mathrel{+}= \rho$.<br>Una CONVERSIONE FX ha entrambe le tratte presso lo stesso broker ($s = d$), in due valute.<br>Il tracker globale $W$ non viene **mai** toccato (il capitale resta all'interno del sistema). |
| ![](../../../../static/icons/transactions/cash-transfer.png){: width="24" } ![](../../../../static/icons/transactions/fx-conversion.png){: width="24" }<br>**GIROCONTO / CONVERSIONE FX**<br>(Tratta esterna o orfana su $b$: $Y > 0$ arriva, oppure $X > 0$ esce) | **In entrata ($Y$), come DEPOSITO:**<br>$r = \min(Y,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= Y - r$<br><br>**In uscita ($X$), come PRELIEVO:**<br>$k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Una tratta la cui altra tratta si trova presso un broker fuori da $S$, o che ha perso il proprio abbinamento — il collegamento cancellato, o la riga abbinata scomparsa — è un flusso esterno: la baseline del capitale la conta per il suo importo, come un deposito o un prelievo. I suoi pool si muovono come farebbero quel deposito o quel prelievo: un arrivo ripristina prima i rendimenti prelevati $W$ in $R_b$, il resto è capitale $K_b$; una partenza preleva prima il capitale $K_b$, poi i rendimenti $R_b$, che vanno in $W$. A differenza di una coppia interna, questa tratta **tocca** $W$, e non registra né assume alcuna ripartizione. |

Ad esempio, con $C^* = \mathrm{EUR}$, un broker con $K = 1000$, $R = 300$ converte 650 EUR in 715 USD a un tasso di riferimento di 0.92 EUR per USD ($Y = 657.80$): in seguito $K = 1000$ e $R = 307.80$ — il capitale è ancora uguale a quanto depositato, e lo spread di 7.80 è un risultato. Tra broker posseduti a quote diverse, $A$ al 100 % che invia 400 a $B$ al 50 % dà $X = 400$, $Y = 200$: una perdita di 200, intaccando prima i rendimenti.

Ogni partenza registra la propria ripartizione $(\rho, X)$ finché il suo arrivo non la assume, una volta. Un arrivo la cui partenza è sconosciuta — nessuna ripartizione registrata, o $X = 0$ — va interamente a $K_d$. Quando entrambe le tratte cadono nello stesso giorno, l'arrivo viene applicato dopo gli altri movimenti di quel giorno, qualunque siano i loro ID di transazione, così trova sempre la ripartizione della sua partenza. Un trasferimento o una conversione la cui altra tratta è fuori da $S$, o che ha perso il proprio abbinamento, non è interno e non segue questa regola: muove i pool come un DEPOSITO o un PRELIEVO (la riga sopra). In una vista del solo broker $B$, $650$ in arrivo da un broker $A$ fuori dalla vista fanno sì che un $B$ vuoto abbia $K_B = 650$, $R_B = 0$; un $B$ con $K_B = 100$, $R_B = 100$ finisce a $K_B = 750$, $R_B = 100$. Se invece il $B$ con $K_B = 100$, $R_B = 100$ invia $150$ fuori dalla vista, mantiene $K_B = 0$, $R_B = 50$ e $W = 50$: il successivo afflusso — un deposito o un'altra tratta dall'esterno — ripristina prima quei $50$ in $R_B$, e un successivo ACQUISTO spende prima $R_B$, come al solito. Nella vista di $A$ e $B$ insieme, la stessa coppia è interna e segue la regola precedente.

Se le date di partenza e arrivo differiscono, il trasferimento è in transito: sottratto da $s$ il giorno della partenza, aggiunto a $d$ il giorno dell'arrivo. Tra quelle date, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ per l'importo in transito — la riconciliazione di seguito interpreta quella liquidità con la composizione corrente dei pool finché l'arrivo non riporta la ripartizione della partenza.

### 💱 Risultato di cambio sulla liquidità estera {: #exchange-result-on-foreign-cash }

Ogni movimento di liquidità entra nella liquidità del broker, e nei suoi pool, al tasso della propria data; il saldo detenuto in seguito segue il tasso (§5). In ogni giorno $t$ in cui cambia il tasso di una valuta estera detenuta come liquidità in $S$ — incluso il suo primo tasso noto — dopo i movimenti di liquidità di quel giorno e prima che le transazioni di quel giorno aggiornino i pool, ogni broker $b$ che detiene liquidità estera viene rivalutato:

$$
\varepsilon_b(t) = \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t) - \mathrm{Cash}^{\text{replay}}_b(t)
$$

$$
\mathrm{Cash}^{\text{replay}}_b \mathrel{+}= \varepsilon_b, \qquad
R_b \mathrel{+}= \varepsilon_b, \qquad
\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0
$$

$\mathrm{Cash}^{\text{replay}}_b(t)$ è la liquidità che il replay trasporta per $b$: il suo valore alla rivalutazione precedente più ogni movimento successivo al tasso della propria data. Una plusvalenza va ai rendimenti; una minusvalenza li consuma prima e poi il capitale, esattamente come una COMMISSIONE. La baseline del capitale non si muove: un risultato di cambio è un risultato, non un conferimento, quindi è in NAV, P&L totale, ROI, TWRR e MWRR, mai nel capitale versato.

### 🧮 Aggregazione per l'output

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### ⚖️ Invariante di riconciliazione

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Entrambi i pool vengono prima limitati a zero per broker. Se i pool non sono vuoti e lo scostamento supera ancora $0.01$, i pool **sommati** vengono riscalati a $\mathrm{Cash}_{\text{like}}$, la liquidità più la liquidità in transito — una scalatura aggregata, non per broker, con ciascun risultato limitato inferiormente a zero:

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t) \cdot \frac{\mathrm{Cash}_{\text{like}}(t)}{\sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)}, \qquad
\mathrm{CashFromReturns}(t) = \mathrm{Cash}_{\text{like}}(t) - \mathrm{CashFromCapital}(t)
$$

Altrimenti $\mathrm{CashFromCapital}(t) = \min\bigl(\sum_b K_b(t),\, \mathrm{Cash}_{\text{like}}(t)\bigr)$ e $\mathrm{CashFromReturns}$ è il resto, limitato inferiormente a zero. I risultati di cambio sulla liquidità a riposo vengono registrati nei pool (sopra); la scalatura assorbe due scostamenti:

- **Liquidità in transito.** La partenza ha lasciato i pool, mentre $\mathrm{Cash}_{\text{like}}$ conta ancora la liquidità in transito — e la variazione del suo tasso di cambio mentre viaggia — quindi $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$. Fino all'arrivo, la scalatura interpreta quella liquidità con la composizione corrente dei pool. Un broker con $K = 1000$, $R = 300$ invia $650$ in $C^*$ a un broker vuoto di $S$: mantiene $K = 650$, $R = 0$, il fattore di scalatura è $1300 / 650 = 2$, quindi $\mathrm{CashFromCapital} = 1300$ e $\mathrm{CashFromReturns} = 0$ durante il transito. All'arrivo la ripartizione ritorna: $1000$ e $300$.
- **Liquidità negativa (scoperto).** Entrambi i pool sono limitati a zero per broker, quindi un broker la cui liquidità scende sotto zero lascia pool che non sommano più alla sua liquidità — anche nei giorni successivi, poiché i valori limitati vengono mantenuti.

---

## 📐 7. Contributo del periodo {: #7-period-contribution }

Per il periodo $[t_0, t_1]$, per posizione $(a,b)$:

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0) + T(a,b)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

Insieme delle posizioni del contributo:

$$
\mathcal{P} = \text{posizioni con attività di ACQUISTO/VENDITA/RETTIFICA/TRASFERIMENTO o quantità ai confini}
$$

$\mathrm{UGL}(a,b,t)$ è lo stato della posizione del §3 alla fine del giorno $t$, quello che il portafoglio aggrega (§5): il mark del §2 — un mark derivato da operazioni, rideterminato attraverso eventuali split successivi —, il costo di carico quando l'asset non ha alcun mark, il tasso di cambio di $t$ stesso. Una posizione non detenuta in $t$ conta 0. Una posizione detenuta in $t$ il cui $\mathrm{UGL}(a,b,t)$ è sconosciuto — nessun tasso, un costo incompleto — rende $\Delta\mathrm{UGL}(a,b)$ sconosciuto, mai il lato noto meno zero. Quando ogni riga è nota, le righe sommano alla variazione del portafoglio, quella delle posizioni detenute — il non realizzato del periodo del [§5](#two-unrealized-figures), titoli in transito esclusi:

$$
\sum_{(a,b) \in \mathcal{P}} \Delta\mathrm{UGL}(a,b) = \Delta\mathrm{UGL} = \bigl[\mathrm{MV}(t_1) - \mathrm{OCB}(t_1)\bigr] - \bigl[\mathrm{MV}(t_0) - \mathrm{OCB}(t_0)\bigr]
$$

L'identità vale anche con il dust: una riga e lo stato del portafoglio del §3 usano la stessa soglia, quindi una posizione rimasta con $10^{-5}$ unità o meno non è detenuta su nessuno dei due lati — nessun valore, nessun non realizzato, in nessuna riga e non in $\Delta\mathrm{UGL}$. Il suo costo esce dal costo di carico aperto senza che la posizione venga venduta, quindi non è né in $\Delta\mathrm{UGL}$ né in Realized: finisce nel residuo del periodo (sotto).

**Trasferimenti interni.** $T(a,b)$ ripartisce il risultato di un titolo spostato tra due broker di $S$: ogni broker risponde per il proprio tratto. Per ogni TRASFERIMENTO ASSET collegato di $a$ dal broker $s$ al broker $d$ che parte dopo $t_0$ e arriva in $t_1$ o prima, con $V$ il valore delle unità spostate il giorno dell'arrivo (§3) e $C$ il costo storico a cui il pool del mittente ha rinunciato per esse (§4):

$$
T(a,s) \mathrel{+}= V - C, \qquad T(a,d) \mathrel{-}= V - C
$$

Il mittente risponde delle unità fino al loro arrivo, transito incluso, il ricevente dal loro arrivo; i termini si annullano, quindi il totale resta invariato. Un trasferimento già in transito a $t_0$, ancora in transito a $t_1$, o con $V$ o $C$ sconosciuti non aggiunge nulla: i valori ai confini restano validi.

??? example "Esempio: 10 unità spostate dal broker A al broker B"

    A detiene 10 unità acquistate a 80 ($C = 800$). Il prezzo è 100 a $t_0$, 120 il giorno in cui si spostano verso B ($V = 1{,}200$), 150 a $t_1$:

    $$
    \Delta\mathrm{UGL}(a,A) = 0 - (1{,}000 - 800) + (1{,}200 - 800) = +200
    $$

    $$
    \Delta\mathrm{UGL}(a,B) = (1{,}500 - 800) - 0 - (1{,}200 - 800) = +300
    $$

    A risponde per 100 → 120, B per 120 → 150: +500 in totale, il $\Delta\mathrm{UGL}$ del portafoglio ($700 - 200$). Senza $T$, A mostrerebbe −200 e B +700.

Il P&L periodo a livello di portafoglio espone anche un residuo:

$$
\mathrm{Other} =
\mathrm{PnL}_{period} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Poiché l'UGL non può contenere il risultato di cambio sulla liquidità (§5), Other si scompone nel risultato di cambio di ciascun broker nel periodo e in ciò che resta:

$$
\mathrm{Other} = \sum_{b \in S} \mathrm{FXonCash}_b + \mathrm{Residual}
$$

Commissioni/proventi non allocati senza `asset_id` sono raggruppati per broker come altri effetti del periodo, e lo stesso vale per $\mathrm{FXonCash}_b$: una riga per ogni broker che detiene liquidità estera, mostrata quando il suo risultato non è zero. Vedi [P&L periodo — effetto cambio sulla liquidità](period-pnl.md#fx-on-cash).

Quando ogni riga è nota, le righe e gli altri effetti del periodo chiudono insieme $\mathrm{PnL}_{period}$. Poiché le righe sono valutate come il portafoglio, il residuo non contiene alcuna differenza di valutazione tra esse, solo ciò che nessuna posizione detiene: ciò che viaggia tra due broker, il costo di un cambio valuta, una dismissione esclusa da Realized, il costo del dust.

??? example "Esempio: una vendita che lascia 0.00001 unità"

    10 unità vengono acquistate a 100,000 prima del periodo, e il prezzo è 100,000 a $t_0$: il NAV è 1,000,000 e il non realizzato 0. All'interno del periodo, 9.99999 unità vengono vendute a 120,000 per 1,199,998.80: il Realized è $9.99999 \times 20{,}000 = 199{,}999.80$, e restano 0.00001 unità; anche il prezzo è 120,000 a $t_1$, quindi valgono 1.20 a un costo di 1.00. Sono dust: non sono in nessuna riga e non nel NAV, quindi il $\Delta\mathrm{UGL}$ della riga e quello del portafoglio sono entrambi 0, e il NAV a $t_1$ è la liquidità della vendita. $\mathrm{PnL}_{period} = 1{,}199{,}998.80 - 1{,}000{,}000 = 199{,}998.80$, e

    $$
    \mathrm{Other} = 199{,}998.80 - 0 - 199{,}999.80 = -1.00
    $$

    il costo del dust. Se valutato nel NAV, il dust avrebbe immesso $1.20 - 1.00 = 0.20$ nel $\Delta\mathrm{UGL}$ del portafoglio che nessuna riga aveva.

---

## 📐 8. Plusvalenza/minusvalenza realizzata {: #8-realized-gain-loss }

In caso di dismissione di $|q_s|$ unità dalla posizione $(a,b)$ alla data $t$ — una VENDITA, o una RETTIFICA in uscita non collegata a uno split:

$$
C = |q_s| \cdot w_{\text{pre}}(a,b)
$$

$$
\mathrm{Realized} = P \cdot \mathrm{fx}(c_P, C^*, t) - C
$$

$P$ è il corrispettivo delle unità, nella sua valuta $c_P$: il ricavato di una VENDITA, nella valuta della sua liquidità; $0$ per una RETTIFICA in uscita, che non ha valore qualunque sia il costo di carico detenuto dalla riga ([Rettifica in uscita](../../../instruments/transaction-types/adjustment.md#outgoing-adjustments)), quindi realizza $-C$. $w_{\text{pre}}$ è il PMC in $C^*$ **prima** della riduzione del pool (lo stesso valore usato dalla regola di VENDITA a tre pool sopra): le unità escono al loro costo storico, senza conversione a $t$, mentre $P$ viene convertito a $t$. Una dismissione il cui $P$ non può essere convertito, o che riguarda una posizione il cui costo è incompleto, è esclusa da Realized.

Una RETTIFICA in uscita non muove liquidità, quindi nessun pool del §6 cambia, e nemmeno il capitale: la baseline del capitale non si muove ([Capitale versato — Rettifica in uscita](deposited-capital.md#outgoing-adjustments)).

---

## 📐 9. Un unico replay giornaliero

| Intervallo | Intervallo di date | Ruolo |
|-------|-----------|------|
| Replay | $[\min(t_{\mathrm{first}},\ t_0),\ t_1]$ | Ogni giorno, con le stesse regole: liquidità, quantità, PMC, pool, prezzi, FX, stati delle posizioni e del portafoglio |
| Frame | $[t_0,\ t_1]$ | I giorni i cui stati vengono restituiti |

C'è un solo replay, dal primo movimento $t_{\mathrm{first}}$ (o $t_0$, quando precedente) a $t_1$. Un movimento datato prima di $t_0$ segue le stesse regole di qualsiasi altro: viene convertito al tasso della propria data e muove i pool PMC e i tre pool K/R/W, e in ogni giorno in cui cambia il tasso di una valuta estera detenuta, la liquidità viene rivalutata e il risultato di cambio entra nei pool (§6). Gli stati vengono restituiti da $t_0$, quindi lo stato di un giorno non dipende dal frame in cui viene letto. Un giorno in cui nessun termine del modello cambia porta lo stato del giorno precedente. Un giorno lo cambia quando porta un movimento, una variazione di un tasso letto dal giorno, una quotazione, uno split, un confine di transito, un prezzo che diventa obsoleto o un tasso che diventa obsoleto; il primo giorno riprodotto e l'inizio del frame vengono sempre calcolati.

**Quando un prezzo diventa obsoleto.** Un prezzo mantenuto è obsoleto quando la sua ultima osservazione $o$ (una quotazione o un'operazione di ACQUISTO/VENDITA) ha più di $\theta = 7$ giorni. Il flag di ogni giorno viene calcolato come prima, ma il motore avvia un nuovo stato il primo giorno obsoleto, $o+\theta+1$, solo quando il prezzo è ancora mantenuto in quel momento:

$$
\text{cambio di obsolescenza a } o+\theta+1 \iff \text{nessuna osservazione dell'asset cade in } (o,\ o+\theta+1]
$$

Un'osservazione più recente all'interno di quel tratto è un cambiamento a sé e rinnova l'età del prezzo: con una quotazione di venerdì seguita da una quotazione di lunedì, venerdì + 8 giorni non è un cambio di stato, perché il prezzo in uso allora è quello di lunedì e non è obsoleto.

**Quando un tasso diventa obsoleto.** Un tasso letto per valutare i titoli detenuti (la valuta dell'asset e delle sue quotazioni rispetto a $C^*$) diventa obsoleto allo stesso modo: quando la riga memorizzata da cui proviene, datata $r$, ha più di $\theta$ giorni, il giorno $r+\theta+1$ avvia un nuovo stato, a meno che una riga più recente non lo sostituisca prima. Lo stato porta allora la coppia `CCY/C*` con la data $r$ della sua riga, e il report la elenca in `data_quality.stale_fx_pairs` come `{pair, last_rate_date, stale_days}` per il giorno di valutazione. Il tasso è comunque l'ultimo noto: l'obsolescenza è un flag, non un valore diverso.

### 🪜 Stati giornalieri come gradini {: #daily-states-as-steps }

Tra due giorni che cambiano lo stato, ogni valore del report è identico. Il report del portafoglio quindi non restituisce un punto per ogni giorno di calendario: restituisce **un punto per ogni tratto senza novità**, che vale dalla sua `date` alla sua `through`, entrambe incluse. La risposta contiene `range {start, end}`, la finestra dopo il ritaglio ai giorni che hanno uno stato.

```json
{
  "range": {"start": "2026-10-23", "end": "2026-10-26"},
  "history": [
    {"date": "2026-10-23", "through": "2026-10-25", "nav_value": {"code": "EUR", "amount": "10450.00"}, "twrr": "0", "roi": "0.045000"},
    {"date": "2026-10-26", "through": "2026-10-26", "nav_value": {"code": "EUR", "amount": "10462.50"}, "twrr": "0.001196", "roi": "0.046250"}
  ],
  "mwrr_line": [
    {"date": "2026-10-23", "annualized": "0", "cumulative": "0"},
    {"date": "2026-10-25", "annualized": "0", "cumulative": "0"},
    {"date": "2026-10-26", "annualized": "0.156557", "cumulative": "0.001196"}
  ]
}
```

Un fondo detenuto venerdì 23, sabato 24, domenica 25 e lunedì 26 ottobre, quotato venerdì e lunedì (le cifre sono illustrative e gli altri campi di un punto sono omessi). Il NAV di sabato è il NAV del passo che lo contiene: $\mathrm{NAV}(t)$ viene letto dal punto con `date` $\le t \le$ `through`, con una ricerca per data e nessun calcolo.

- **Quali serie.** `history`, `allocation_history.*`, `broker_pnl_history[].points` e `pnl_candles.points`. Le serie di eventi (proventi, costi, depositi, finanziamento delle acquisizioni) sono invariate: un punto per evento.
- **Passi massimali.** Due passi adiacenti non portano mai valori identici; i passi di un broker sono massimali per il suo P&L, non per quello del portafoglio.
- **Lacune.** Un giorno che nessun passo copre non ha valore: un broker che inizia a metà finestra, o un giorno senza una candela di P&L (un asset detenuto non è stato valutabile).
- **TWRR e ROI** restano all'interno dei passi. In un giorno tranquillo il fattore TWRR è esattamente 1 e il ROI non cambia. Il primo punto del TWRR è fissato a 0, essendo relativo al periodo. Un passo in cui il NAV è zero o inferiore non porta TWRR (`null`), secondo la stessa regola della scheda ([Quando non viene mostrato alcun TWRR](twrr.md#when-no-twrr)); la catena continua a comporsi attraverso di esso, quindi il TWRR ritorna quando il NAV è di nuovo sopra zero. Il capitale del ROI è quello della scheda ([Il ROI di un periodo](roi.md#dashboard-period-roi)).
- **MWRR** si muove ogni giorno, perché il tempo passa, e con più flussi non ha forma chiusa: non risiede nei passi ma in `mwrr_line`, una serie di **valori effettivi**, ciascuno uguale al [MWRR](mwrr.md) del periodo che termina quel giorno, secondo la stessa regola della scheda (nessun tasso quando il valore del portafoglio o il capitale netto investito non è positivo). La linea ha un punto alla `date` e alla `through` di ogni passo; all'interno di un passo più lungo di 62 giorni aggiunge l'ultimo giorno di ogni mese di calendario strettamente interno, al massimo 24 per passo, distribuiti uniformemente. Il suo primo punto è fissato a 0.
- **Qualità dei dati** segue la stessa idea: `incomplete_nav_ranges`, `incomplete_book_value_ranges`, `incomplete_allocation_ranges` e `incomplete_valuation_ranges` sono elenchi di `{start, end}` con giorni consecutivi uniti. `missing_fx_pairs[].dates` contiene solo le date dei movimenti, e `missing_fx_pairs[].ranges` i giorni di valutazione, uniti. I vecchi elenchi `incomplete_*_dates` sono transitori.

---

## 📐 10. Metriche di performance (Livello 2)

Calcolate **dopo** gli stati giornalieri, come passaggio separato:

| Metrica | Formula | Riferimento |
|--------|---------|-----------|
| P&L totale | $\mathrm{NAV}(t) - \text{CapitalBaseline}(t)$ | [Capitale versato](deposited-capital.md) |
| P&L periodo | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [P&L periodo](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (catena di sottoperiodi) | [TWRR](twrr.md) |
| MWRR | XIRR che risolve $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| ROI semplice | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Rendimento annualizzato netto | $(1+r_{\mathrm{net}})^{365/d}-1$, soppresso sotto i 30 giorni | [Rendimento annualizzato netto](net-annualized-return.md) |
| Rendimento sul costo | Proventi lordi delle transazioni negli ultimi 365 giorni per unità storica ammissibile, divisi per il PMC unitario residuo a $t_1$ | [Rendimento sul costo](yield-on-cost.md) |
| Effetto timing | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Effetto timing](timing-effect.md) |

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — valutazione snapshot
- 🧭 [Risoluzione del prezzo](price-resolution.md) — resolver di valutazione unificato
- 📈 [Rendimento annualizzato netto](net-annualized-return.md) — definizioni CAGR per posizioni, periodo e FIFO
- 💸 [Rendimento sul costo](yield-on-cost.md) — proventi lordi registrati su base trailing rispetto al PMC unitario residuo
- 📖 [Valore contabile](book-value.md) — aggregato del costo di carico
- 📊 [P&L periodo](period-pnl.md) — utile/perdita su finestra con contributo
- 💸 [Capitale versato](deposited-capital.md) — dettagli sui 3 pool ed esempi svolti
- 📈 [PMC](../weighted-average-cost.md) — metodo del costo iterativo
- 📈 [Panoramica delle metriche di performance](../index.md) — tutte le metriche di performance a colpo d'occhio
