# ⚙️ Motore del Portafoglio — Modello Matematico

## 💡 Panoramica

Questa pagina definisce formalmente il modello matematico alla base del motore di calcolo del portafoglio di LibreFolio. Tutte le altre pagine delle metriche ([NAV](nav.md), [Valore contabile](book-value.md), [P&L periodo](period-pnl.md), [Rendimento sul costo](yield-on-cost.md), [PMC](../weighted-average-cost.md), [Capitale Versato](deposited-capital.md)) fanno riferimento a questa pagina per le loro precise regole di calcolo.

---

## 📐 1. Notazione e Insiemi

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

## 📐 2. Prezzo di Valutazione {: #2-valuation-price }

$$
\operatorname{mark}(a,t)=
\begin{cases}
\text{MARKET}(a,t) & \text{quotazione asset-sistema dello stesso giorno}\\
\operatorname{avg}(\text{TRADE}(a,t)) & \text{osservazioni BUY/SELL/ADJUSTMENT valorizzate dello stesso giorno}\\
\text{ultima osservazione prima di }t & \text{mantenuta (LOCF)}\\
\varnothing & \text{nessuna osservazione in data }t\text{ o precedente}
\end{cases}
$$

- Il resolver unificato è l'unico motore di valutazione: `MARKET → TRADE_AVG → CARRIED → MISSING`.
- `CARRIED` è l'ultima osservazione mantenuta (LOCF). Porta con sé i metadati di obsolescenza `days_back`.
- `estimated=True` significa origine TRADE. Una quotazione MARKET obsoleta mantenuta è obsoleta, non stimata.
- I prezzi di valutazione rimangono nella valuta nativa; ogni consumatore converte in $C^*$ alla data di valutazione $t$.
- L'FX del costo di carico rimane ancorato alla data della transazione.
- Il PMC **non** viene mai usato come prezzo di valutazione.

Vedi [Risoluzione del prezzo](price-resolution.md) per il contratto del resolver e la semantica della qualità dei dati.

---

## 📐 3. Stato della Posizione {: #3-position-state }

Per ogni posizione $(a, b)$ con $q(a,b,t) > 0$:

$$
\mathrm{MV}(a,b,t) =
\frac{q(a,b,t)}{qbq(a)}\cdot
\operatorname{mark}(a,t)\cdot
\mathrm{fx}\bigl(\mathrm{ccy}_{mark}, C^*, t\bigr)
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Dove $w(a,b,t)$ è il [Prezzo Medio di Carico (PMC)](../weighted-average-cost.md) per la posizione $(a,b)$ alla data $t$, mantenuto in $C^*$ ai tassi storici (§4): il costo di carico non applica alcun tasso di cambio a $t$, quindi per un asset estero l'effetto del tasso di cambio fa parte di $\mathrm{UGL}$.

---

## 📐 4. Aggiornamento Iterativo del PMC

Mantenuto per posizione $(a,b)$ con stato del pool $(\hat{q}, \hat{c})$, il costo $\hat{c}$ mantenuto in $C^*$:

**Acquisizione** (quantità $> 0$, importo $P$ pagato nella valuta $c$ alla data $d$):

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + P \cdot \mathrm{fx}(c, C^*, d), \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

$P$ è la liquidità pagata per un acquisto, o il costo di carico per unità sovrascritto moltiplicato per $q_{\text{tx}}$ per un trasferimento o una rettifica; $\mathrm{fx}(C^*, C^*, d) = 1$. Quando non esiste un tasso a o prima di $d$, o l'acquisizione non ha un costo di carico, la quantità viene registrata e il costo non viene registrato: il costo della posizione viene contrassegnato come incompleto invece di essere conteggiato come zero.

**Riduzione** (quantità $< 0$):

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

**Split** (collegato a un evento di split): $\hat{q}$ cambia, $\hat{c}$ no.

!!! info "Ordinamento"

    All'interno della stessa data: le aggiunte vengono elaborate prima delle riduzioni. Garantisce che la VENDITA legga il PMC corretto includendo gli ACQUISTI dello stesso giorno.

---

## 📐 5. Aggregazione del Portafoglio {: #5-portfolio-aggregation }

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

---

## 📐 6. Modello di Liquidità a Tre Pool — Per Broker $(K_b, R_b, W)$ {: #6-three-pool-cash-model-per-broker-k_b-r_b-w }

Tre pool di accumulo tracciano la provenienza della liquidità. $K$ e $R$ sono mantenuti **per broker** $b$; $W$ è globale (esce completamente dal sistema).

| Pool | Ambito | Significato |
|------|-------|---------|
| $K_b$ | Per broker | Capitale esterno ancora presso il broker $b$ come liquidità |
| $R_b$ | Per broker | Rendimenti generati ancora presso il broker $b$ come liquidità |
| $W$ | Globale | Rendimenti che hanno lasciato il sistema (nascosti, ripristinabili in caso di nuovo deposito) |

!!! info "Proprietà chiave"

    Un acquisto sul broker $b_1$ può consumare solo $R_{b_1}$, mai $R_{b_2}$. La liquidità non si teletrasporta tra broker — solo i trasferimenti espliciti spostano i saldi dei pool.

### 🔁 Regole di aggiornamento (per transazione sul broker $b$, in ordine cronologico)

| Icona e Tipo | Formule di Aggiornamento | Logica e Descrizione |
|:---:|---|---|
| ![](../../../../static/icons/transactions/deposit.png){: width="24" }<br>**DEPOSITO**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Ripristina prima i rendimenti precedentemente prelevati dal tracker globale $W$, poi aggiunge il resto al capitale $K_b$. |
| ![](../../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**PRELIEVO**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consuma prima il capitale $K_b$, poi sposta i rendimenti rimanenti $\rho$ al tracker globale $W$. |
| ![](../../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDENDO / INTERESSE**<br>$I > 0$ | $R_b \mathrel{+}= I$ | I rendimenti aumentano direttamente il pool dei rendimenti $R_b$. |
| ![](../../../../static/icons/transactions/fee.png){: width="24" } ![](../../../../static/icons/transactions/tax.png){: width="24" }<br>**COMMISSIONE / IMPOSTA**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consuma prima i rendimenti $R_b$; se $R_b$ diventa negativo, attinge dal capitale $K_b$. |
| ![](../../../../static/icons/transactions/buy.png){: width="24" }<br>**ACQUISTO**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consuma prima i rendimenti $R_b$, poi attinge il resto dal capitale $K_b$. |
| ![](../../../../static/icons/transactions/sell.png){: width="24" }<br>**VENDITA** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | Il costo di carico $C = |q_s| \cdot w_{\text{pre}}$ ritorna al capitale $K_b$; il guadagno $G$ va ai rendimenti $R_b$ (se $G < 0$, si comporta come una commissione).<br><br>!!! warning "Ordine critico"<br><br> $C$ deve essere calcolato **prima** che il pool PMC venga ridotto (una vendita totale darebbe $C = 0$ altrimenti). |
| ![](../../../../static/icons/transactions/cash-transfer.png){: width="24" }<br>**GIROCONTO**<br>(Interno, $s \to d$, $X > 0$) | **Tratta di partenza ($s$):**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Tratta di arrivo ($d$):**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho$ | I giroconti interni spostano le allocazioni dei pool ($R_s \to R_d$, $K_s \to K_d$) in proporzione al saldo di partenza.<br>Il tracker globale $W$ **non** viene mai toccato (il capitale rimane all'interno del sistema). |

Se le date di partenza e arrivo differiscono, il giroconto è in transito: sottratto da $s$ il giorno di partenza, aggiunto a $d$ il giorno di arrivo. Tra queste date, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ dell'importo in transito — gestito dalla riconciliazione proporzionale.

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

Ridimensionamento proporzionale per broker applicato se lo scostamento $> 0.01$ (da arrotondamento FX o tempistica in transito).

---

## 📐 7. Contributo del Periodo {: #7-period-contribution }

Per il periodo $[t_0, t_1]$, per posizione $(a,b)$:

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

Insieme delle posizioni contributive:

$$
\mathcal{P} = \text{posizioni con attività di ACQUISTO/VENDITA/RETTIFICA/TRASFERIMENTO o quantità limite}
$$

Il P&L periodo a livello di portafoglio espone anche un residuo:

$$
\mathrm{Other} =
\mathrm{PnL}_{period} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Commissioni/redditi non allocati senza `asset_id` sono raggruppati per broker come altri effetti del periodo.

---

## 📐 8. Plusvalenza/Minusvalenza Realizzata

Alla VENDITA di $|q_s|$ unità dalla posizione $(a,b)$ alla data $t$:

$$
C = |q_s| \cdot w_{\text{pre}}(a,b)
$$

$$
\mathrm{Realized} = P_{\text{sell}} \cdot \mathrm{fx}(\mathrm{ccy}_{\text{sell}}, C^*, t) - C
$$

Dove $w_{\text{pre}}$ è il PMC in $C^*$ **prima** della riduzione del pool (stesso valore usato dalla regola di VENDITA a 3 pool sopra): le unità vendute escono al loro costo storico, senza conversione alla data di vendita. Una vendita i cui proventi non possono essere convertiti, o che proviene da una posizione con costo incompleto, è esclusa dal P&L realizzato.

---

## 📐 9. Architettura Pre-Frame / Frame

| Fase | Intervallo di date | Calcola |
|-------|-----------|----------|
| Pre-frame | $[t_{\mathrm{first}},\ t_0)$ | Liquidità, quantità, PMC, pool — nessuna valutazione di mercato |
| Frame | $[t_0,\ t_1]$ | Giornaliero completo: prezzi, FX, stati delle posizioni, stati del portafoglio |

Le transazioni pre-frame aggiornano gli accumulatori (registro di cassa, pool PMC, K/R/W a 3 pool) senza consumare dati di prezzo o FX. Ciò consente un caching efficiente basato su intervalli.

---

## 📐 10. Metriche di Performance (Livello 2)

Calcolate **dopo** gli stati giornalieri, come passaggio separato:

| Metrica | Formula | Riferimento |
|--------|---------|-----------|
| P&L Totale | $\mathrm{NAV}(t) - \text{CapitalBaseline}(t)$ | [Capitale Versato](deposited-capital.md) |
| P&L periodo | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [P&L periodo](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (catena di sotto-periodi) | [TWRR](twrr.md) |
| MWRR | XIRR risolvendo $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| ROI Semplice | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Rendimento annualizzato netto | $(1+r_{\mathrm{net}})^{365/d}-1$, soppresso sotto i 30 giorni | [Rendimento Annualizzato Netto](net-annualized-return.md) |
| Rendimento sul costo | Reddito lordo da transazioni degli ultimi 365 giorni per unità storica ammissibile, diviso per il PMC unitario residuo a $t_1$ | [Rendimento sul costo](yield-on-cost.md) |
| Effetto timing | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Effetto timing](timing-effect.md) |

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — valutazione istantanea
- 🧭 [Risoluzione del prezzo](price-resolution.md) — resolver di valutazione unificato
- 📈 [Rendimento Annualizzato Netto](net-annualized-return.md) — definizioni di CAGR per posizioni, periodo e FIFO
- 💸 [Rendimento sul costo](yield-on-cost.md) — reddito lordo registrato degli ultimi 365 giorni rispetto al PMC unitario residuo
- 📖 [Valore contabile](book-value.md) — aggregato del costo di carico
- 📊 [P&L periodo](period-pnl.md) — guadagno/perdita su finestra con contributo
- 💸 [Capitale Versato](deposited-capital.md) — dettagli dei 3 pool ed esempi svolti
- 📈 [PMC](../weighted-average-cost.md) — metodo del costo iterativo
- 📈 [Panoramica delle Metriche di Performance](../index.md) — tutte le metriche di performance a colpo d'occhio
