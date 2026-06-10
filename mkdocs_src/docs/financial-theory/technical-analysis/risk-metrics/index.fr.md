# 📊 Mesures de Risque

Les mesures de risque fournissent des **mesures quantitatives** du risque d'un portefeuille. Chaque indicateur capture un aspect différent de l'incertitude, et aucun indicateur seul ne donne une image complète. L'utilisation de plusieurs indicateurs conjointement permet d'obtenir une vue globale du risque du portefeuille.

---

## 📋 Aperçu Comparatif

| Indicateur | Ce qu'il mesure | Formule | Plage | Détails |
|--------|-----------------|---------|-------|---------|
| **[Ratio de Sharpe](sharpe-ratio.md)** | Rendement ajusté au risque (volatilité totale) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Ratio de Sortino](sortino-ratio.md)** | Rendement ajusté au risque (risque de baisse uniquement) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Drawdown maximum](max-drawdown.md)** | Plus forte baisse du sommet au creux | $\frac{Creux - Sommet}{Sommet}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilité](volatility.md)** | Dispersion des rendements | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Quand utiliser chaque indicateur

| Scénario | Meilleur indicateur | Pourquoi |
|----------|-------------|-----|
| Comparer deux fonds | **Ratio de Sharpe** | Normalise le rendement par le risque total |
| Distributions de rendement asymétriques | **Ratio de Sortino** | Ne pénalise que la volatilité à la baisse |
| Analyse du pire scénario | **Drawdown maximum** | Montre la perte maximale historique |
| Évaluation générale du risque | **Volatilité** | Base de tous les autres indicateurs |
| Optimisation de portefeuille | **Les quatre** | Chacun capture une dimension différente |

---

## ⚠️ Pièges Courants

!!! warning "Limitations"

    - **Indicateurs historiques ≠ risque futur** : La volatilité passée peut ne pas prédire la volatilité future
    - **Hypothèse de distribution normale** : Sharpe et Sortino supposent que les rendements sont approximativement normaux ; les rendements financiers présentent des queues de distribution épaisses
    - **Sensibilité à la période d'observation** : Les indicateurs varient significativement selon la fenêtre temporelle choisie
    - **Dépendance au benchmark** : Sharpe et Sortino dépendent du taux sans risque, qui évolue dans le temps

---

## 🔗 Liens connexes

- 🔀 **[Diversification](../diversification.md)** — Comment fonctionne mathématiquement la réduction du risque
- ⚖️ **[Allocation d'actifs](../asset-allocation.md)** — Utiliser les mesures de risque pour guider l'allocation
- 📈 **[Rendements et Taux de Croissance](../../fundamentals/returns.md)** — Le côté "rendement" du couple risque-rendement
