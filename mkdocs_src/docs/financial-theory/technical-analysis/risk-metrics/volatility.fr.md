# 📊 Volatilité

La volatilité mesure la **dispersion des rendements** — l'ampleur des fluctuations du prix d'un actif dans le temps. C'est la mesure de risque la plus fondamentale en finance et la brique de base de presque toutes les autres mesures de risque.

---

## 🔢 Formule {: #formula }

### 📐 Écart-type des rendements {: #standard-deviation-of-returns }

$$
\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
$$

où $R_i$ sont les rendements individuels de chaque période et $\bar{R}$ est le rendement moyen.

### 📈 Annualisation {: #annualization }

La volatilité par période est annualisée en la multipliant par la racine carrée du nombre de périodes contenues dans une année :

$$
\sigma_{annual} = \sigma_{period} \times \sqrt{f}
$$

Le facteur $f$ est **mesuré à partir des données observées**, et non fixé à l'avance : il correspond au nombre de rendements réellement utilisés, ramené à une année civile complète sur la période qu'ils couvrent.

$$
f = \frac{N \times 365}{D}
$$

où $N$ est le nombre total de rendements de période et $D$ le nombre de jours calendaires qu'ils couvrent.

!!! info "Pourquoi une racine carrée ?"

    Les rendements sont supposés indépendants d'une période à l'autre. La variance d'une somme de $f$ variables indépendantes est égale à $f$ fois la variance individuelle. Par conséquent :

    $$\text{Var}_{annual} = f \times \text{Var}_{period}$$

    $$\sigma_{annual} = \sqrt{f} \times \sigma_{period}$$

!!! info "√252 est un résultat, pas une constante"

    Une action cotée quotidiennement fournit environ 252 rendements sur une année civile complète, donc $f = 252 \times 365 / 365 = 252$ et l'on retrouve le fameux $\sqrt{252}$ — comme résultat de la mesure, et non comme hypothèse inscrite dans celle-ci. Un instrument coté chaque jour calendaire, comme les cryptos, donne $f \approx 365$ et donc $\approx \sqrt{365}$ : un $\sqrt{252}$ codé en dur **sous-estimerait** sa volatilité annualisée. Un fonds coté hebdomadairement donne $f \approx 52$.

    → Voir **[Annualisation observée](observed-annualization.md)** pour la dérivation, les exemples détaillés et ce que la couverture y ajoute.

---

## 💡 Interprétation {: #interpretation }

| Volatilité annualisée | Actifs typiques |
|---|---|
| 1-5 % | Marché monétaire, obligations à court terme |
| 5-15 % | Obligations d'État, obligations d'entreprises de qualité (investment grade) |
| 15-25 % | Actions à grande capitalisation, ETF actions diversifiés |
| 25-40 % | Actions à petite capitalisation, actions individuelles |
| 40-80 %+ | Crypto, actions mèmes, produits à effet de levier |

---

## 📊 Volatilité réalisée vs implicite {: #realized-vs-implied-volatility }

### 📈 Volatilité réalisée (historique) {: #realized-historical-volatility }

Calculée à partir des données de prix **passées**. C'est ce que calcule LibreFolio :

$$
\sigma_{realized} = \text{StdDev}(\text{rendements historiques})
$$

### 🔮 Volatilité implicite {: #implied-volatility }

Extraite des **prix d'options** à l'aide du modèle de Black-Scholes. Elle représente l'**anticipation** du marché concernant la volatilité future :

$$
C = f(S, K, T, r, \sigma_{implied})
$$

La volatilité implicite est prospective, mais elle n'est disponible que pour les actifs optionnables.

---

## 🔄 Volatilité en fenêtre glissante {: #rolling-window-volatility }

Plutôt que de calculer un seul chiffre de volatilité pour toute la période, la **volatilité en fenêtre glissante** calcule $\sigma$ sur une fenêtre glissante (par ex., 30 jours), produisant une série temporelle qui montre l'évolution de la volatilité :

$$
\sigma_t^{(w)} = \text{StdDev}(R_{t-w+1}, R_{t-w+2}, \ldots, R_t)
$$

Cela est utile pour :

- Identifier les **régimes de volatilité** (périodes calmes vs turbulentes)
- Détecter le **clustering de volatilité** (les jours à forte volatilité ont tendance à suivre les jours à forte volatilité)
- Ajuster dynamiquement la taille des positions (réduire l'exposition pendant les périodes de forte volatilité)

---

## 📐 Volatilité et théorie du portefeuille {: #volatility-and-portfolio-theory }

La volatilité joue un rôle central dans la [théorie moderne du portefeuille](../index.md) :

- Elle est le **dénominateur** du [ratio de Sharpe](sharpe-ratio.md)
- Elle détermine la **largeur** des [bandes de Bollinger](../../technical-analysis/indicators/bollinger-bands.md)
- Elle est la donnée d'entrée clé pour l'optimisation de portefeuille (minimiser $\sigma_p$ pour un $R_p$ cible)
- La [diversification](../../portfolio-theory/diversification.md) réduit la volatilité du portefeuille lorsque les corrélations entre actifs sont inférieures à 1

---

## ⚠️ Limites {: #limitations }

!!! warning "Volatilité ≠ Risque"

    La volatilité traite de la même manière les mouvements à la hausse et à la baisse. Un actif qui connaît fréquemment des pics à la hausse a une volatilité élevée mais peut être très attractif. Pour une mesure axée sur le risque de baisse, utilisez le [ratio de Sortino](sortino-ratio.md) ou la [perte maximale](max-drawdown.md).

!!! warning "Non-normalité"

    Les rendements financiers présentent généralement :

    - des **queues épaisses** (davantage d'événements extrêmes qu'une distribution normale n'en prédit)
    - une **asymétrie négative** (les fortes baisses sont plus fréquentes que les fortes hausses)
    - un **clustering de volatilité** (périodes calmes et turbulentes)

    L'écart-type seul ne capture pas ces caractéristiques.

---

## 🔗 Voir aussi {: #related }

- 📐 **[ratio de Sharpe](sharpe-ratio.md)** — Utilise la volatilité comme dénominateur du risque
- 📊 **[ratio de Sortino](sortino-ratio.md)** — Variante de volatilité uniquement à la baisse
- 📏 **[bandes de Bollinger](../../technical-analysis/indicators/bollinger-bands.md)** — Enveloppe de volatilité sur les graphiques
- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — Réduction de la volatilité du portefeuille
