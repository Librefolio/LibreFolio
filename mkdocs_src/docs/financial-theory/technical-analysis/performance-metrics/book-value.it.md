# 📖 Book Value

*[⬅️ Torna a Panoramica Metriche di Performance](index.md)*

## 💡 Cos'è il Book Value?

Il **Book Value** rappresenta il costo contabile storico del tuo portafoglio — quanto capitale hai investito al costo, più le riserve di liquidità. Non fluttua in base ai prezzi di mercato.

---

## 🧮 Formula

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

Dove l'Open Cost Basis è:

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

🔗 Vedi **[Portfolio Engine — §3 Stato della Posizione](portfolio-engine.md#3-position-state)** per la derivazione completa.

---

## ⚖️ Plusvalenza/Minusvalenza Non Realizzata

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

---

## 📝 Esempio

| Componente | Importo |
|-----------|--------|
| Open Cost Basis | €27,000 |
| Cash | €600 |
| In-Transit Book | €0 |

$$
\mathrm{Book} = 27\,000 + 600 = 27\,600 \text{ EUR}
$$

Con NAV = €33,000:

$$
\mathrm{Unrealized} = 33\,000 - 27\,600 = +5\,400 \text{ EUR}
$$

---

## 🔗 Correlati

- 📊 [PMC](weighted-average-cost.md) — metodo del costo unitario per OCB
- 💼 [NAV](nav.md) — corrispettivo basato sul valore di mercato
- 📈 [Period PnL](period-pnl.md) — combinazione di realizzato + non realizzato
