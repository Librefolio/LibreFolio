# 🔀 Diversification

La diversification est la stratégie de gestion des risques la plus fondamentale : en combinant des actifs qui n'évoluent pas en parfaite synchronisation, un investisseur peut **réduire la volatilité de son portefeuille** sans nécessairement réduire le rendement attendu.

---

## 📐 Les Mathématiques

### 📊 Variance d'un portefeuille à deux actifs

Pour un portefeuille de deux actifs avec des pondérations $w_1$ et $w_2 = 1 - w_1$ :

$$
\sigma_p^2 = w_1^2 \sigma_1^2 + w_2^2 \sigma_2^2 + 2 w_1 w_2 \sigma_1 \sigma_2 \rho_{12}
$$

où :

- $\sigma_1, \sigma_2$ sont les volatilités individuelles des actifs
- $\rho_{12}$ est le **coefficient de corrélation** ($-1 \leq \rho \leq +1$)

La magie de la diversification réside dans le **terme croisé** : lorsque $\rho_{12} < 1$, la variance du portefeuille est **inférieure** à la moyenne pondérée des variances individuelles.

### 🔑 Effets de la corrélation

| Corrélation $\rho$ | Effet | Exemple |
|---|---|---|
| $+1$ | Aucun bénéfice de diversification — les actifs évoluent de manière identique | Deux ETF S&P 500 |
| $0$ | Réduction significative de la variance | Actions vs Or |
| $-1$ | Couverture parfaite — la variance peut atteindre zéro | Position longue en actions + option put |

### 📈 Généralisation à N actifs

Pour $N$ actifs :

$$
\sigma_p^2 = \sum_{i=1}^{N} \sum_{j=1}^{N} w_i w_j \sigma_i \sigma_j \rho_{ij}
$$

À mesure que $N$ augmente, la contribution des variances individuelles diminue (proportionnellement à $1/N$), mais la contribution des covariances subsiste. Cela conduit au concept de **risque systématique**.

---

## 🎯 Risque Systématique vs Risque Idiosyncrasique

### 📊 Risque Idiosyncrasique (Diversifiable)

Risque spécifique à une seule entreprise ou à un seul actif. Exemples :

- Départ du PDG
- Rappel de produit
- Expiration d'un brevet

Ce risque **peut être éliminé par la diversification** en détenant de nombreux actifs. Avec environ 30 actions non corrélées, le risque idiosyncrasique tend vers zéro.

### 🌍 Risque Systématique (Non Diversifiable)

Risque affectant l'ensemble du marché. Exemples :

- Variations des taux d'intérêt
- Récessions
- Pandémies
- Événements géopolitiques

Ce risque **ne peut pas être éliminé** par la diversification. C'est le risque pour lequel les investisseurs sont rémunérés — le fondement du Modèle d'Évaluation des Actifs Financiers (MEDAF).

$$
\sigma_{portfolio}^2 = \underbrace{\sigma_{systematic}^2}_{\text{non supprimable}} + \underbrace{\sigma_{idiosyncratic}^2}_{\xrightarrow{N \to \infty} 0}
$$

---

## ⚠️ Pièges de la Diversification

!!! warning "Instabilité de la corrélation"

    Les corrélations ne sont **pas constantes** — elles ont tendance à augmenter lors des crises de marché (précisément quand la diversification est la plus nécessaire). Ce phénomène, appelé **rupture de corrélation**, signifie que la diversification offre moins de protection lors d'événements extrêmes que ne le suggèrent les données historiques.

!!! info "Sur-diversification"

    Au-delà d'un certain point, l'ajout d'actifs supplémentaires augmente la complexité et les coûts (frais de transaction, complexité fiscale) sans réduire significativement le risque. Le point d'équilibre pour la plupart des investisseurs se situe entre 20 et 40 positions réparties sur différentes classes d'actifs et zones géographiques.

---

## 🔗 Liens connexes

- ⚖️ **[Allocation d'actifs](asset-allocation.md)** — Comment déterminer l'allocation du portefeuille
- 📊 **[Volatilité](risk-metrics/volatility.md)** — Mesurer le risque que la diversification réduit
- 📈 **[Max Drawdown](risk-metrics/max-drawdown.md)** — La métrique du pire scénario possible
