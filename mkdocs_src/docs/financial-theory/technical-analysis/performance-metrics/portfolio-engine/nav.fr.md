# 💼 Valeur Netative Inventaire (NAV) / Patrimoine Net

## 💡 Qu'est-ce que le NAV ?

La **Valeur Netative Inventaire (NAV)** est la valorisation totale de marché de votre portefeuille à un instant $t$. Elle répond à la question : *"Combien vaut le portefeuille en ce moment ?"*

---

## 🧮 Formule

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Où :

$$
\mathrm{MV}(t)=
\sum_{(a,b)\in S}
\frac{q(a,b,t)}{qbq(a)}
\cdot \operatorname{mark}(a,t)
\cdot \mathrm{fx}(\mathrm{ccy}_{mark}, C^*, t)
$$

🔗 Voir **[Portfolio Engine — §5 Aggregation](index.md#5-portfolio-aggregation)** pour la dérivation complète.

---

## 🔗 Chaîne de Prix de Valorisation {: #valuation-price-chain }

Le cours $\operatorname{mark}(a,t)$ provient du resolver unifié :

1. **MARKET** — cours de clôture de marché du jour même.
2. **TRADE_AVG** — observation moyenne ACHAT/VENTE/AJUSTEMENT du jour même.
3. **CARRIED** — dernière observation antérieure à $t$, projetée en avant (LOCF).
4. **MISSING** — aucune observation à la date $t$ ou antérieurement.

Les marks restent en devise native jusqu'à la valorisation ; la conversion FX a lieu à $t$. Le PMP n'est **jamais** utilisé pour la valorisation. Voir [Résolution des Prix](price-resolution.md).

---

## 📝 Exemple

| Composant | Montant |
|-----------|---------|
| Valeur de Marché des Actifs | 32 759 € |
| Solde de Liquidités | 631 € |
| En Transit | 0 € |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinctions Clés

- **NAV vs [Book Value](book-value.md)** : NAV = valeur de marché ; Book = coût d'acquisition. Différence = plus-values non réalisées.
- **NAV vs [Period PnL](period-pnl.md)** : NAV = instantané ; Period PnL = variation ajustée des flux dans le temps.

---

## ⚠️ Qualité des Données

| Source de Valorisation | Confiance |
|-----------------------|-----------|
| `MARKET_PRICE` | Totale — cours réel, exact ou projeté |
| `LAST_TRADE_PRICE` | Partielle — mark du resolver d'origine transaction |
| `MISSING` | Aucune — exclu du NAV |

`estimated=True` s'applique uniquement aux marks d'origine TRADE. Une cotation MARKET périmée est stale mais pas estimated.

Les valorisations d'origine TRADE datant de plus de 14 jours déclenchent l'avertissement « actifs valorisés au coût / pas de prix de marché depuis plus de deux semaines » à la date de valorisation.
