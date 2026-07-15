# 💼 Valeur Nette d'Actif (NAV) / Valeur Nette

*[⬅️ Retour vers l'aperçu des métriques de performance](index.md)*

## 💡 Qu'est-ce que la NAV ?

**La Valeur Nette d'Actif (NAV)** est la valorisation totale de votre portefeuille sur le marché à un instant $t$. Elle répond à la question : *"Combien vaut le portefeuille actuellement ?"*

---

## 🧮 Formule

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Où $\mathrm{MV}(t) = \sum_{(a,b) \in S} q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}(\mathrm{ccy}_p, C^*, t)$

🔗 Voir **[Portfolio Engine — §5 Aggregation](portfolio-engine.md#5-portfolio-aggregation)** pour la démonstration complète.

---

## 🔗 Chaîne de prix de valorisation {: #valuation-price-chain }

Le prix $p(a,t)$ suit une priorité stricte :

1. **Prix de marché** — Remplissage rétroactif de PriceHistory (dernier $\leq t$)
2. **Dernier prix d'achat** — prix unitaire BUY le plus récent issu de $V(u)$ (tous les courtiers visibles)
3. **Manquant** — position exclue de la NAV

Le PMP n'est **jamais** utilisé pour la valorisation. Voir **[Portfolio Engine — §2](portfolio-engine.md#2-valuation-price)**.

---

## 📝 Exemple

| Composant | Montant |
|-----------|---------|
| Valeur de marché des actifs | 32 759 € |
| Solde de trésorerie | 631 € |
| En transit | 0 € |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinctions clés

- **NAV vs [Valeur Comptable](book-value.md)** : NAV = valeur de marché ; Valeur comptable = coût d'acquisition. La différence = plus-values latentes.
- **NAV vs [PnL de Période](period-pnl.md)** : NAV = instantané ; PnL de Période = variation ajustée des flux dans le temps.

---

## ⚠️ Qualité des données

| Source de valorisation | Confiance |
|-----------------|------------|
| `MARKET_PRICE` | Totale — PriceHistory disponible |
| `LAST_BUY_PRICE` | Partielle — utilisation du prix de transaction |
| `MISSING` | Aucune — exclu de la NAV |
