# 📖 Valeur comptable

## 💡 Qu'est-ce que la valeur comptable ?

**La valeur comptable** représente le coût comptable historique de votre portefeuille — le coût de base ouvert (OCB), plus les réserves de liquidités et la valeur comptable en transit. Elle ne fluctue pas avec les prix du marché et se distingue de la [Résolution des prix](price-resolution.md).

---

## 🧮 Formule

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

où le coût de base ouvert (OCB) :

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w^{C^*}(a,b,t)
$$

Ici $w^{C^*}(a,b,t)$ est le [PRU](../weighted-average-cost.md) conservé directement dans la devise demandée $C^*$ : chaque acquisition y a été enregistrée au taux de sa propre date $d_i$, à savoir $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ pour un montant $P_i$ effectivement payé. L'OCB n'utilise donc **aucun taux de change à la date de valorisation** $t$ : c'est la somme des coûts historiques — ce qui a été payé — et elle ne varie pas lorsque les taux de change varient.

Dans le terme en transit, les liquidités en transit sont converties à $t$, tandis que les actifs en transit portent leur coût gelé converti à leur date d'arrivée.

!!! note "Coût incomplet"

    Lorsqu'une partie du coût d'une position est inconnue — aucun taux de change à la date d'acquisition ou avant celle-ci, ou un transfert ou ajustement sans coût de base — l'OCB n'inclut que la partie connue, et la position elle-même est signalée : son coût moyen et sa plus-value ou moins-value latente ne sont pas affichés.

🔗 Voir **[Moteur de portefeuille — §3 État de position](index.md#3-position-state)** pour la dérivation complète.

---

## ⚖️ Plus-value ou moins-value latente

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

Étant donné que la NAV valorise les actifs au prix du marché du jour **et** au taux de change, tandis que la valeur comptable conserve les coûts historiques, la plus-value ou moins-value latente d'un actif libellé dans une autre devise inclut l'effet du taux de change. Par exemple, 10 unités achetées pour 400 € alors qu'elles valaient 500 USD conservent un OCB de 400 € ; si elles valent 550 USD un jour où 1 USD = 0,75 €, leur valeur de marché est de 412,50 € et la plus-value latente est de 12,50 € — le gain propre des unités (+37,50 €) moins la baisse du dollar (−25,00 €). [P&L période](period-pnl.md#unrealized-change-by-currency) montre comment le tableau de bord répartit les deux.

---

## 📝 Exemple

| Composant | Montant |
|-----------|--------|
| Coût de base ouvert | 27 000 € |
| Liquidités | 600 € |
| Valeur comptable en transit | 0 € |

$$
\mathrm{Book} = 27\,000 + 600 = 27\,600 \text{ EUR}
$$

Avec NAV = 33 000 € :

$$
\mathrm{Unrealized} = 33\,000 - 27\,600 = +5\,400 \text{ EUR}
$$

---

## 🔗 Voir aussi

- 📊 [PRU](../weighted-average-cost.md) — méthode du coût unitaire pour le coût de base ouvert (OCB)
- 💼 [NAV](nav.md) — contrepartie en valeur de marché
- 🧭 [Résolution des prix](price-resolution.md) — valorisations de marché/de négociation utilisées par la NAV, pas par la valeur comptable
- 📈 [P&L période](period-pnl.md) — P&L réalisé + P&L latent combinés
- 📈 [Vue d'ensemble des métriques de performance](../index.md) — toutes les métriques de performance en un coup d'œil
