# 📊 Métriques de Risque

Les métriques de risque fournissent des **mesures quantitatives** du risque du portefeuille. Chaque métrique capture un aspect différent de l'incertitude, et aucune métrique seule ne permet d'avoir une vision complète. L'utilisation de plusieurs métriques ensemble offre une vue globale du risque du portefeuille.

---

## 📋 Aperçu Comparatif

| Métrique | Ce qu'elle mesure | Formule | Plage | Détails |
|--------|-----------------|---------|-------|---------|
| **[Ratio de Sharpe](sharpe-ratio.md)** | Rendement ajusté au risque (vol totale) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Ratio de Sortino](sortino-ratio.md)** | Rendement ajusté au risque (risque de baisse) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Maximum Drawdown](max-drawdown.md)** | Plus forte baisse du sommet au creux | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilité](volatility.md)** | Dispersion des rendements | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Quand utiliser chaque métrique

| Scénario | Meilleure métrique | Pourquoi |
|----------|-------------|-----|
| Comparaison de deux fonds | **Ratio de Sharpe** | Normalise le rendement par le risque total |
| Distributions de rendements asymétriques | **Ratio de Sortino** | Pénalise uniquement la volatilité à la baisse |
| Planification du pire scénario | **Maximum Drawdown** | Montre la perte maximale historique |
| Évaluation générale du risque | **Volatilité** | Base de toutes les autres métriques |
| Optimisation de portefeuille | **Les quatre** | Chacune capture une dimension différente |

---

## ⚠️ Pièges Courants

!!! warning "Limitations"

    - **Métriques historiques ≠ risque futur** : La volatilité passée peut ne pas prédire la volatilité future
    - **Hypothèse de distribution normale** : Sharpe et Sortino supposent que les rendements sont approximativement normaux ; les rendements financiers présentent des queues épaisses
    - **Sensibilité à la période d'analyse** : Les métriques changent significativement selon la fenêtre temporelle choisie
    - **Dépendance au benchmark** : Sharpe et Sortino dépendent du taux sans risque, qui évolue dans le temps

---

## 🔗 Liens connexes

- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — Comment fonctionne mathématiquement la réduction du risque
- ⚖️ **[Allocation d'actifs](../../portfolio-theory/asset-allocation.md)** — Utiliser les métriques de risque pour guider l'allocation
- 📈 **[Rendements & Taux de croissance](../../fundamentals/returns.md)** — Le côté "rendement" du couple risque-rendement
