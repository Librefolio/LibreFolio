# ![](../../../static/icons/transactions/fee.png){: width="32" style="vertical-align: middle;" } Commissioni e Tasse ![](../../../static/icons/transactions/tax.png){: width="32" style="vertical-align: middle;" }

Le **commissioni** e le **tasse** rappresentano costi che riducono il valore del tuo portafoglio. Sono tipi di transazione separati per distinguere tra i costi addebitati dal broker e gli obblighi imposti dal governo.

---

## 🔑 Proprietà Chiave

| Proprietà | Commissione | Tassa |
|----------|-----|-----|
| **Codice** | `FEE` | `TAX` |
| **Effetto cassa** | ⬇️ Diminuisce il saldo | ⬇️ Diminuisce il saldo |
| **Effetto asset** | — | — |
| **Esempi** | Commissione, costo di custodia, spread | Tassa sulle plusvalenze, ritenuta d'acconto, imposta di bollo |

---

## 📊 Tipi di Commissioni

| Tipo di Commissione | Descrizione | Frequenza |
|----------|-------------|-----------|
| **Commissione di trading** | Costo per operazione addebitato dal broker | Per transazione |
| **Costo di custodia** | Canone di mantenimento del conto | Mensile/Trimestrale |
| **Spread** | Differenza tra prezzo bid e ask | Implicito per operazione |
| **Commissione di conversione FX** | Costo della conversione valutaria | Per conversione |
| **Commissione di gestione (TER)** | Spesa annuale di ETF/Fondo | Detratta dal NAV |

---

## 💰 Tipi di Tasse

| Tipo di Tassa | Descrizione | Quando viene addebitata |
|----------|-------------|-------------|
| **Tassa sulle plusvalenze** | Tassa sul profitto realizzato dalla vendita | Alla vendita |
| **Ritenuta d'acconto** | Tassa detratta alla fonte (dividendi, interessi) | Al pagamento |
| **Imposta di bollo** | Tassa di transazione (es. stamp duty nel Regno Unito) | All'acquisto |
| **Tassa sulle transazioni finanziarie** | Tassa sulle operazioni (es. Tobin tax italiana) | All'operazione |

---

## 📐 Impatto sui Rendimenti

Commissioni e tasse riducono direttamente il tuo rendimento netto. La relazione tra performance lorda e netta è:

$$
R_{net} = R_{gross} - \frac{\text{Commissioni} + \text{Tasse}}{V_{start}}
$$

Dove:

- $R_{gross}$ = rendimento prima dei costi (ciò che il mercato ti ha dato)
- $R_{net}$ = rendimento dopo i costi (ciò che effettivamente trattieni)
- $V_{start}$ = valore del portafoglio all'inizio del periodo

### 📉 Effetto Composto delle Commissioni

Su lunghi periodi di detenzione, anche piccole commissioni ricorrenti erodono significativamente i rendimenti a causa del **trascinamento composto** (compounding drag):

$$
V_{final} = V_0 \times (1 + r - f)^n
$$

Dove:

- $V_0$ = investimento iniziale
- $r$ = tasso di rendimento lordo annuale (es. 0.07 per il 7%)
- $f$ = tasso di commissione annuale (es. 0.01 per l'1%)
- $n$ = numero di anni

!!! example "Il trascinamento dell'1% su 30 anni"

    Con $10,000 investiti a un rendimento lordo del 7%:

    - **Senza commissioni**: $10,000 × $(1.07)^{30}$ = **$76,123**
    - **Con commissione dell'1%**: $10,000 × $(1.06)^{30}$ = **$57,435**

    La commissione annuale dell'1% ti costa **$18,688** — una riduzione del 26% del valore finale.

---

## 🔗 Correlati

- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Come vengono misurati i rendimenti (lordi vs netti)
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Teoria completa della tassazione ed efficienza fiscale
- 🛒 **[Acquisto e Vendita](buy-sell.md)** — Commissioni di trading associate alle transazioni
- 💱 **[Conversione valutaria](fx-conversion.md)** — Spread FX nascosti come commissioni implicite
