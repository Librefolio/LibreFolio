# ⚙️ Portfolio Engine — Modello Matematico

*[⬅️ Torna a Panoramica Metriche di Performance](index.md)*

## 💡 Panoramica

Questa pagina definisce formalmente il modello matematico alla base del motore di calcolo del portafoglio di LibreFolio. Tutte le altre pagine relative alle metriche ([NAV](nav.md), [Book Value](book-value.md), [Period P&L](period-pnl.md), [PMC](weighted-average-cost.md), [Deposited Capital](deposited-capital.md)) fanno riferimento a questa pagina per le loro precise regole di computazione.

---

## 📐 1. Notazione e Insiemi

| Simbolo | Significato |
|--------|---------|
| $V(u)$ | Tutti i broker visibili all'utente $u$ |
| $S \subseteq V(u)$ | Ambito dei broker selezionati (filtrati) |
| $A$ | Insieme degli asset con posizioni |
| $C^*$ | Valuta target |
| $[t_0, t_1]$ | Frame di valutazione richiesto |
| $q(a,b,t)$ | Quantità dell'asset $a$ presso il broker $b$ alla data $t$ |
| $p(a,t)$ | Prezzo di valutazione dell'asset $a$ alla data $t$ |
| $\mathrm{fx}(c_1, c_2, t)$ | Tasso di cambio dalla valuta $c_1$ alla $c_2$ alla data $t$ |

---

## 📐 2. Prezzo di Valutazione {: #2-valuation-price }

$$
p(a, t) = \begin{cases}
p_{\text{mkt}}(a, t) & \text{se esiste un PriceHistory} \leq t \\
p_{\text{buy}}(a, t) & \text{se esiste l'ultimo BUY da } V(u) \\
\varnothing & \text{altrimenti (escluso dal NAV)}
\end{cases}
$$

- $p_{\text{mkt}}$ = riempimento a ritroso (backward-fill) da PriceHistory (ultima chiusura con data $\leq t$)
- $p_{\text{buy}}$ = prezzo unitario dell'acquisto (BUY) più recente di $a$ tra tutti i broker in $V(u)$, con data $\leq t$
- Il PMC **non** viene mai utilizzato come prezzo di valutazione

---

## 📐 3. Stato della Posizione {: #3-position-state }

Per ogni posizione $(a, b)$ con $q(a,b,t) > 0$:

$$
\mathrm{MV}(a,b,t) = q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}\bigl(\mathrm{ccy}_p, C^*, t\bigr)
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}\bigl(\mathrm{ccy}_w, C^*, t\bigr)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Dove $w(a,b,t)$ è il [prezzo medio di carico (PMC)](weighted-average-cost.md) per la posizione $(a,b)$ alla data $t$.

---

## 📐 4. Aggiornamento Iterativo PMC

Mantenuto per singola posizione $(a,b)$ con stato del pool $(\hat{q}, \hat{c})$:

**Acquisizione** (qty $> 0$, costo unitario $u$):

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + u \cdot q_{\text{tx}}, \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

**Riduzione** (qty $< 0$):

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

!!! info "Ordinamento"

    Entro la stessa data: le aggiunte vengono elaborate prima delle riduzioni. Questo assicura che l'operazione di SELL legga il PMC corretto, inclusi gli ACQUISTI dello stesso giorno.

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

## 📐 6. Modello Cash a Tre Pool — Per Broker $(K_b, R_b, W)$ {: #6-three-pool-cash-model-per-broker-k_b-r_b-w }

Tre pool di accumulo tracciano la provenienza della liquidità. $K$ e $R$ sono mantenuti **per broker** $b$; $W$ è globale (esce completamente dal sistema).

| Pool | Ambito | Significato |
|------|-------|---------|
| $K_b$ | Per broker | Capitale esterno ancora presente nel broker $b$ come cash |
| $R_b$ | Per broker | Rendimenti generati ancora presenti nel broker $b$ come cash |
| $W$ | Globale | Rendimenti che hanno lasciato il sistema (nascosti, recuperabili al ri-deposito) |

!!! info "Proprietà chiave"

    Un acquisto (BUY) sul broker $b_1$ può consumare solo $R_{b_1}$, mai $R_{b_2}$. La liquidità non si "teletrasporta" tra i broker — solo i trasferimenti espliciti spostano i saldi dei pool.

### Regole di aggiornamento (per transazione sul broker $b$, cronologiche)

| Icona e Tipo | Formule di Aggiornamento | Logica e Descrizione |
|:---:|---|---|
| ![](../../../static/icons/transactions/deposit.png){: width="24" }<br>**DEPOSITO**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Ripristina i rendimenti precedentemente prelevati dal tracker globale $W$ prima di aggiungere il restante al capitale $K_b$. |
| ![](../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**PRELIEVO**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$ <br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consuma prima il capitale $K_b$, poi sposta i rendimenti rimanenti $\rho$ nel tracker globale $W$. |
| ![](../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDENDO / INTERESSE**<br>$I > 0$ | $R_b \mathrel{+}= I$ | I rendimenti incrementano direttamente il pool dei rendimenti $R_b$. |
| ![](../../../static/icons/transactions/fee.png){: width="24" } ![](../../../static/icons/transactions/tax.png){: width="24" }<br>**COMMISSIONE / IMPOSTA**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{se } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consuma prima i rendimenti $R_b$; se $R_b$ diventa negativo, attinge dal capitale $K_b$. |
| ![](../../../static/icons/transactions/buy.png){: width="24" }<br>**ACQUISTO**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consuma prima i rendimenti $R_b$, poi preleva il resto dal capitale $K_b$. |
| ![](../../../static/icons/transactions/sell.png){: width="24" }<br>**VENDITA** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{se } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | Il costo di base $C = |q_s| \cdot w_{\text{pre}}$ ritorna al capitale $K_b$; il guadagno $G$ va ai rendimenti $R_b$ (si comporta come una commissione se $G < 0$).<br><br>!!! warning "Ordinamento critico"<br><br>    $C$ deve essere calcolato **prima** che il pool PMC venga ridotto (altrimenti una vendita totale darebbe $C = 0$). |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="24" }<br>**TRASFERIMENTO DI LIQUIDITÀ**<br>(Interno, $s \to d$, $X > 0$) | **Tratta di uscita ($s$):**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Tratta di arrivo ($d$):**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho$ | I trasferimenti interni di liquidità spostano le allocazioni dei pool ($R_s \to R_d$, $K_s \to K_d$) in proporzione al saldo di partenza.<br>Il tracker globale $W$ **non** viene mai toccato (il capitale rimane nel sistema). |

Se le date di uscita e arrivo differiscono, il trasferimento è in transito (in-transit): sottratto da $s$ nel giorno di partenza, aggiunto a $d$ nel giorno di arrivo. Tra queste date, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ per l'importo in transito — gestito tramite riconciliazione proporzionale.

### Aggregazione per l'output

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### Invariante di riconciliazione

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Viene applicato uno scaling proporzionale per broker se il drift è $> 0.01$ (dovuto ad arrotondamenti FX o timing in-transit).

---

## 📐 7. Contributo di Periodo {: #7-period-contribution }

Per il periodo $[t_0, t_1]$, per posizione $(a,b)$:

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{Fees}(a,b)
$$

Insieme delle posizioni che contribuiscono:

$$
\mathcal{P} = \mathcal{P}(t_0) \cup \mathcal{P}(t_1) \cup \mathrm{keys}(\text{Realized}) \cup \mathrm{keys}(\text{Income}) \cup \mathrm{keys}(\text{Fees})
$$

Le voci non allocate (commissioni/redditi senza `asset_id`) sono raggruppate per broker.

---

## 📐 8. Guadagno/Perdita Realizzata (Realized Gain/Loss)

Su SELL di $|q_s|$ unità dalla posizione $(a,b)$:

$$
C = |q_s| \cdot w_{\text{pre}}(a,b) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

$$
\mathrm{Realized} = P_{\text{sell}} - C
$$

Dove $w_{\text{pre}}$ è il PMC **prima** della riduzione del pool (stesso valore usato dalla regola SELL a 3 pool sopra).

---

## 📐 9. Architettura Pre-Frame / Frame

| Fase | Intervallo date | Calcola |
|-------|-----------|----------|
| Pre-frame | $[t_{\mathrm{first}},\ t_0)$ | Cash, qty, PMC, pool — nessuna valutazione di mercato |
| Frame | $[t_0,\ t_1]$ | Completo giornaliero: prezzi, FX, stati delle posizioni, stati del portafoglio |

Le transazioni nel pre-frame aggiornano gli accumulatori (libro cassa, pool PMC, modello a 3 pool K/R/W) senza consumare dati di prezzo o FX. Ciò consente un caching efficiente basato su range.

---

## 📐 10. Metriche di Performance (Layer 2)

Calcolate **dopo** gli stati giornalieri, come passaggio separato:

| Metrica | Formula | Riferimento |
|--------|---------|-----------|
| PnL Totale | $\mathrm{NAV}(t) - \text{DepositedCapital}(t)$ | [Deposited Capital](deposited-capital.md) |
| PnL di Periodo | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [Period P&L](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (catena di sotto-periodi) | [TWRR](twrr.md) |
| MWRR | XIRR risolvendo $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| Simple ROI | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Timing Effect | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Timing Effect](timing-effect.md) |

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — valutazione istantanea (snapshot)
- 📖 [Book Value](book-value.md) — aggregato del costo di base
- 📊 [Period P&L](period-pnl.md) — guadagni/perdite in una finestra temporale con contributo
- 💸 [Deposited Capital](deposited-capital.md) — dettagli sui 3 pool ed esempi pratici
- 📈 [PMC](weighted-average-cost.md) — metodo di costo iterativo
