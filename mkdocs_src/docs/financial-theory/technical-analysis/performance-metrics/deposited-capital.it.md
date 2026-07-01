# 💸 Capitale Depositato, PnL Totale e Pool di Liquidità

*[⬅️ Torna a Panoramica Metriche di Performance](index.md)*

## 💡 Panoramica del Concetto

**Capitale Depositato** = capitale esterno netto cumulativo versato dall'inizio:

$$
\mathrm{DepCap}(t) = \sum_{\tau \leq t} D(\tau) - \sum_{\tau \leq t} W(\tau)
$$

**PnL Totale** = tutto il valore generato oltre i contributi esterni:

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{DepCap}(t)}
$$

---

## 🎯 Cosa viene conteggiato

| Transazione | Effetto su DepCap |
|------------|-----------------|
| DEPOSITO / PRELIEVO (non collegati) | ✅ Sì |
| TRASFERIMENTO DI LIQUIDITÀ collegato-esterno | ✅ Sì |
| TRASFERIMENTO DI LIQUIDITÀ collegato-interno | ❌ No |
| ACQUISTO, VENDITA, DIVIDENDO, INTERESSE, COMMISSIONE, IMPOSTA | ❌ No |

---

## 📊 Modello di Liquidità a Tre Pool

Il Grafico di Crescita scompone la liquidità corrente in due aggregati visibili più un tracker globale nascosto:

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Pool | Ambito | Significato |
|------|-------|---------|
| $K_b$ | Per-broker | Capitale esterno ancora presso il broker $b$ |
| $R_b$ | Per-broker | Rendimenti generati ancora presso il broker $b$ |
| $W$ | Globale | Rendimenti che hanno lasciato il sistema (ripristinabili in caso di nuovo deposito) |

!!! info "Proprietà chiave"

    - $\mathrm{DepCap}$ = somma storica di tutti i flussi. $\sum K_b$ = quanta della liquidità corrente è capitale esterno. I due valori divergono dopo un ACQUISTO/VENDITA.
    - Un ACQUISTO sul broker $b_1$ consuma solo $R_{b_1}$, mai $R_{b_2}$.
    - I trasferimenti di liquidità tra broker spostano $R$ e $K$ dalla sorgente alla destinazione senza toccare $W$.

🔗 Regole complete di aggiornamento per broker: **[Portfolio Engine — §6 Modello Cash a Tre Pool](portfolio-engine.md#6-modello-cash-a-tre-pool-per-broker-k_b-r_b-w)**

---

## 📝 Esempi Svolti

### A — Deposito → Acquisto → Vendita in Gain

| Passaggio | Tx | $K$ | $R$ | Liquidità |
|------|----|-----|-----|------|
| 1 | DEPOSITO €1.000 | 1.000 | 0 | 1.000 |
| 2 | ACQUISTO €1.000 | 0 | 0 | 0 |
| 3 | VENDITA P=€1.200, C=€1.000 | 1.000 | 200 | 1.200 |

TotalPnL = 1.200 − 1.000 = **+€200** ✓

### B — Dividendo e poi Prelievo

| Passaggio | Tx | $K$ | $R$ | $W$ | Liquidità |
|------|----|-----|-----|-----|------|
| 1 | DEPOSITO €1.000 | 1.000 | 0 | 0 | 1.000 |
| 2 | DIVIDENDO €50 | 1.000 | 50 | 0 | 1.050 |
| 3 | PRELIEVO €100 (prima K) | 900 | 50 | 0 | 950 |
| 4 | PRELIEVO €950 (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | NUOVO DEPOSITO €30 (ripristina min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Dopo il passaggio 5: Liquidità=30, K=0, R=30 ✓ (rendimenti ripristinati da W)

### C — Scenario di Vendita Completa

| Passaggio | Tx | $K$ | $R$ | Liquidità |
|------|----|-----|-----|------|
| 1 | DEPOSITO €1.000, ACQUISTO 1@€1.000 | 0 | 0 | 0 |
| 2 | VENDITA 1@€1.005 (C=1000, G=5) | 1.000 | 5 | 1.005 |

Il capitale ritorna correttamente in $K$; solo il guadagno di €5 va in $R$. **Non** tutti i €1.005 vanno in $R$.

---

## ⚙️ Implementazione

Il modello a 3 pool gira in un **unico loop per transazione** (event-driven, non delta giornaliero):

1. Lettura del PMC prima della modifica della pool
2. Aggiornamento di K/R/W secondo le regole del tipo di transazione
3. Riduzione del pool PMC (per le VENDITE)

🔗 Vedi **[Portfolio Engine — §6](portfolio-engine.md#6-modello-cash-a-tre-pool-per-broker-k_b-r_b-w)** per tutte le regole formali.

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — l'altro termine nel Total PnL
- 📊 [Period PnL](period-pnl.md) — versione a finestra temporale
- ⚙️ [Portfolio Engine](portfolio-engine.md) — modello matematico completo
