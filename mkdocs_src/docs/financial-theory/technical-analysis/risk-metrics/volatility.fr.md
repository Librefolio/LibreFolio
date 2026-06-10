# 📊 Volatilité

La volatilité mesure la **dispersion des rendements** — à quel point le prix d'un actif fluctue au fil du temps. C'est la mesure de risque la plus fondamentale en finance et la base de presque toutes les autres métriques de risque.

---

## 🔢 Formule

### 📐 Écart-type des rendements

$$
\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
$$

où $R_i$ sont les rendements des périodes individuelles et $\bar{R}$ est le rendement moyen.

### 📈 Annualisation

La volatilité quotidienne est annualisée en multipliant par la racine carrée du nombre de jours de bourse :

$$
\sigma_{annual} = \sigma_{daily} \times \sqrt{252}
$$

!!! info "Pourquoi √252 ?"

    On suppose que les rendements sont indépendants d'un jour à l'autre. La variance d'une somme de $N$ variables indépendantes est $N$ fois la variance individuelle. Par conséquent :

    $$\text{Var}_{annual} = 252 \times \text{Var}_{daily}$$
    $$\sigma_{annual} = \sqrt{252} \times \sigma_{daily}$$

---

## 💡 Interprétation

| Volatilité Annualisée | Actifs Typiques |
|---|---|
| 1-5% | Marché monétaire, obligations à court terme |
| 5-15% | Obligations d'État, obligations d'entreprises de catégorie investissement |
| 15-25% | Actions à large capitalisation, ETF actions diversifiés |
| 25-40% | Actions à petite capitalisation, actions individuelles |
| 40-80%+ | Crypto, actions mèmes, produits à effet de levier |

---

## 📊 Volatilité Réalisée vs Implicite

### 📈 Volatilité Réalisée (Historique)

Calculée à partir des données de prix **passées**. C'est ce que LibreFolio calcule :

$$
\sigma_{realized} = \text{StdDev}(\text{historical returns})
$$

### 🔮 Volatilité Implicite

Extraite des **prix des options** en utilisant le modèle Black-Scholes. Elle représente l'**anticipation** du marché concernant la volatilité future :

$$
C = f(S, K, T, r, \sigma_{implied})
$$

La volatilité implicite est prospective, mais elle n'est disponible que pour les actifs faisant l'objet d'options.

---

## 🔄 Volatilité sur Fenêtre Glissante

Plutôt que de calculer un seul chiffre de volatilité pour toute la période, la **volatilité sur fenêtre glissante** calcule $\sigma$ sur une fenêtre mobile (par exemple, 30 jours), ce qui génère une série temporelle qui montre comment la volatilité évolue :

$$
\sigma_t^{(w)} = \text{StdDev}(R_{t-w+1}, R_{t-w+2}, \ldots, R_t)
$$

Ceci est utile pour :

- Identifier les **régimes de volatilité** (périodes calmes vs turbulentes)
- Détecter le **clustering de volatilité** (les jours de forte volatilité ont tendance à succéder aux jours de forte volatilité)
- Définir des tailles de position dynamiques (réduire l'exposition pendant les périodes de forte volatilité)

---

## 📐 Volatilité et Théorie du Portefeuille

La volatilité joue un rôle central dans la [Théorie Moderne du Portefeuille](../index.md) :

- Elle est le **dénominateur** du [Ratio de Sharpe](sharpe-ratio.md)
- Elle détermine la **largeur** des [Bandes de Bollinger](../../technical-analysis/indicators/bollinger-bands.md)
- Elle est l'entrée clé pour l'optimisation de portefeuille (minimiser $\sigma_p$ pour un $R_p$ cible)
- La [Diversification](../diversification.md) réduit la volatilité du portefeuille lorsque les corrélations entre actifs sont inférieures à 1

---

## ⚠️ Limitations

!!! warning "Volatilité ≠ Risque"

    La volatilité traite les mouvements à la hausse et à la baisse de la même manière. Un actif qui grimpe fréquemment a une volatilité élevée mais peut être très attractif. Pour une mesure axée sur le risque de baisse, utilisez le [Ratio de Sortino](sortino-ratio.md) ou le [drawdown maximal](max-drawdown.md).

!!! warning "Non-normalité"

    Les rendements financiers présentent typiquement :

    - Des **queues lourdes** (plus d'événements extrêmes que ce que prévoit une distribution normale)
    - Une **asymétrie négative** (les chutes importantes sont plus courantes que les gains importants)
    - Un **clustering de volatilité** (périodes calmes et turbulentes)

    L'écart-type seul ne capture pas ces caractéristiques.

---

## 🔗 Liens connexes

- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Utilise la volatilité comme dénominateur du risque
- 📊 **[Ratio de Sortino](sortino-ratio.md)** — Variante de la volatilité axée uniquement sur la baisse
- 📏 **[Bandes de Bollinger](../../technical-analysis/indicators/bollinger-bands.md)** — Enveloppe de volatilité sur les graphiques
- 🔀 **[Diversification](../diversification.md)** — Réduction de la volatilité du portefeuille
