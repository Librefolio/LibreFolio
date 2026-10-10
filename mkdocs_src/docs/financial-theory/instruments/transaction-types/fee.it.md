# ![](../../../static/icons/transactions/fee.png){: width="32" style="vertical-align: middle;" } Commissioni e Imposte ![](../../../static/icons/transactions/tax.png){: width="32" style="vertical-align: middle;" }

Le **commissioni** e le **imposte** rappresentano costi che riducono il valore del tuo portafoglio. Sono tipi di transazione separati per distinguere tra i costi addebitati dal broker e gli obblighi imposti dal governo.

---

## 🔑 Proprietà Chiave

| Proprietà | Commissione | Imposta |
|----------|-----|-----|
| **Codice** | `FEE` | `TAX` |
| **Effetto cassa** | ⬇️ Diminuisce il saldo | ⬇️ Diminuisce il saldo |
| **Effetto asset** | — | — |
| **Esempi** | Commissione, costo di custodia, spread | Imposta sulle plusvalenze, ritenuta d'acconto, imposta di bollo |

---

## 📊 Tipi di Commissioni

| Tipo di Commissione | Descrizione | Frequenza |
|----------|-------------|-----------|
| **Commissione di trading** | Costo per operazione addebitato dal broker | Per transazione |
| **Costo di custodia** | Canone di mantenimento del conto | Mensile/Trimestrale |
| **Spread** | Differenza tra prezzo bid e ask | Implicito per operazione |
| **Commissione di conversione FX** | Costo della conversione di valuta | Per conversione |
| **Commissione di gestione (TER)** | Spesa annuale di ETF/Fondo | Detratta dal NAV |

---

## 💰 Tipi di imposte

| Tipo di imposta | Descrizione | Quando viene addebitata |
|----------|-------------|-------------|
| **Imposta sulle plusvalenze** | Imposta sul profitto realizzato dalla vendita | Alla vendita |
| **Ritenuta d'acconto** | Imposta trattenuta alla fonte (dividendi, interessi) | Al pagamento |
| **Imposta di bollo** | Imposta sulle transazioni (es. stamp duty nel Regno Unito) | All'acquisto |
| **Imposta sulle transazioni finanziarie** | Imposta sulle operazioni (es. Tobin tax italiana) | All'operazione |

---

## 📐 Impatto sui Rendimenti

Commissioni e imposte riducono direttamente il tuo rendimento netto. La relazione tra performance lorda e netta è:

$$
R_{net} = R_{gross} - \frac{\text{Commissioni} + \text{Tasse}}{V_{start}}
$$

Dove:

- $R_{gross}$ = rendimento prima dei costi (ciò che il mercato ti ha dato)
- $R_{net}$ = rendimento dopo i costi (ciò che effettivamente trattieni)
- $V_{start}$ = valore del portafoglio all'inizio del periodo

!!! note "Come LibreFolio attribuisce commissioni e imposte"

    Una `FEE` / `TAX` **collegata a un asset** viene allocata ai lotti specifici a cui si riferisce e determina il
    **P&L netto / rendimento netto** di quel lotto (vedi
    [Analisi dei Lotti FIFO → Costi e Metriche Nette](../../technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)).
    Un costo **senza asset** (`asset_id = null`, es. una commissione fissa della piattaforma) è a livello di
    portafoglio ed è gestito invece dal Portfolio Engine — non finisce mai su un singolo lotto.

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
- 💱 **[Conversione di valuta](fx-conversion.md)** — Spread FX nascosti come commissioni implicite
