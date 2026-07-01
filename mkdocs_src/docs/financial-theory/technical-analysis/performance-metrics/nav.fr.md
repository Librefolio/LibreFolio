# 💼 Valeur Liquidative (NAV) / Patrimoine Net

*[⬅️ Retour à l'aperçu des indicateurs de performance](index.md)*

## 💡 Qu'est-ce que la NAV ?

La **Valeur Liquidative (NAV - Net Asset Value)** est la valorisation totale du marché de votre portefeuille à un instant $t$. Elle répond à la question : *"Combien vaut le portefeuille en ce moment ?"*

---

## 🧮 Formule

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Où $\mathrm{MV}(t) = \sum_{(a,b) \in S} q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}(\mathrm{ccy}_p, C^*, t)$

🔗 Voir **[Portfolio Engine — §5 Agrégation du Portefeuille](portfolio-engine.md#5-agregation-du-portefeuille)** pour la dérivation complète.

---

## 🔗 Chaîne de prix de valorisation

Le prix $p(a,t)$ suit une priorité stricte :

1. **Prix du marché** — Backward-fill de PriceHistory (le plus récent $\leq t$)
2. **Dernier prix d'achat** — prix unitaire d'achat (ACHAT) le plus récent provenant de $V(u)$ (tous les courtiers visibles)
3. **Manquant** — la position est exclue de la NAV

Le PMP n'est **jamais** utilisé pour la valorisation. Voir **[Portfolio Engine — §2](portfolio-engine.md#2-prix-devaluation)**.

---

## 📝 Exemple

| Composant | Montant |
|-----------|--------|
| Valeur de marché des actifs | 32 759 € |
| Solde de trésorerie | 631 € |
| En cours de transfert | 0 € |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinctions clés

- **NAV vs [Valeur Comptable (Book Value)](book-value.md)** : NAV = valeur de marché ; Book = coût d'acquisition. Différence = plus-values latentes.
- **NAV vs [PnL de période](period-pnl.md)** : NAV = instantané ; PnL de période = variation ajustée des flux au fil du temps.

---

## ⚠️ Qualité des données

| Source de valorisation | Confiance |
|-----------------|------------|
| `MARKET_PRICE` | Totale — PriceHistory disponible |
| `LAST_BUY_PRICE` | Partielle — utilise le prix de transaction |
| `MISSING` | Nulle — exclue de la NAV |
