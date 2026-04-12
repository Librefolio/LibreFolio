# <img src="../../../static/icons/transactions/deposit.png" width="32" style="vertical-align: middle;" /> Depositi e Prelievi

I **depositi** e i **prelievi** registrano i movimenti di liquidità in entrata e in uscita da un conto broker. Non comportano alcun asset: cambia solo il saldo di cassa.

---

## 🔑 Proprietà Chiave

| Proprietà | Deposito | Prelievo |
|----------|---------|------------|
| **Codice** | `DEPOSIT` | `WITHDRAWAL` |
| **Effetto cassa** | ⬆️ Aumenta il saldo | ⬇️ Diminuisce il saldo |
| **Effetto asset** | — | — |
| **Evento fiscale** | No | No |

---

## 📊 Perché sono importanti

### 📐 Rendimento Ponderato per il Capitale

I depositi e i prelievi sono fondamentali per il calcolo del **rendimento ponderato per il capitale** (MWR / IRR). Senza il tracciamento dei flussi di cassa, è impossibile distinguere tra i rendimenti generati dal portafoglio e i rendimenti causati dall'immissione o dal prelievo di liquidità.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

dove $CF_i$ è ogni singolo flusso di cassa (depositi positivi, prelievi negativi, valore finale positivo).

### 📊 Rendimento Ponderato per il Tempo

Il **rendimento ponderato per il tempo** (TWR) elimina l'effetto dei flussi di cassa calcolando i rendimenti tra ogni evento di flusso di cassa e concatenandoli:

$$
R_{TWR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

Ciò fornisce una misura "pura" della performance del portafoglio, indipendente dal timing dei depositi e dei prelievi.

---

## 🔗 Correlati

- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Calcolo TWR vs MWR
- 🛒 **[Acquisto e Vendita](buy-sell.md)** — Transazioni che utilizzano la liquidità depositata
