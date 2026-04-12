# 📊 Ajustement de Prix

Un événement d'**ajustement de prix** représente un changement non monétaire de la juste valeur d'un actif — tel qu'une dépréciation, une correction mark-to-market, une décote (haircut) ou une réévaluation.

---

## 📖 Définition

Les ajustements de prix capturent les variations de valeur qui ne sont **pas causées par des transactions de marché** et qui **n'impliquent pas de flux de trésorerie** pour l'investisseur. Il s'agit de modifications algébriques (positives ou négatives) de la juste valeur calculée de l'actif.

Ces événements sont particulièrement pertinents pour les actifs qui n'ont pas de tarification de marché continue — comme la dette privée, les instruments illiquides ou les actifs suivis via le fournisseur Scheduled Investment.

### Scénarios courants

| Scénario | Montant | Description |
|----------|--------|-------------|
| **Dépréciation** | Négatif | Réduction de la valeur comptable due à une dépréciation |
| **Mark-to-market** | +/− | Réévaluation périodique pour refléter la juste valeur actuelle |
| **Décote (Haircut)** | Négatif | Réduction forcée (ex: lors d'une restructuration de dette) |
| **Réévaluation** | Positif | Révision à la hausse de la juste valeur après des événements positifs |
| **Ajustement de la NAV** | +/− | Correction de la Valeur Liquidative pour les fonds fermés |

---

## 📉 Impact sur le prix du marché

Pour les **actifs cotés** (actions, ETF), les ajustements de prix sont rares et généralement informatifs — le prix du marché reflète déjà l'événement.

Pour les **actifs évalués par modèle** (Scheduled Investment, manuel), l'ajustement modifie directement le prix calculé :

$$
\text{price}(d) = \text{base{\_}value}(d) + \sum_{i : d_i \leq d} \text{PRICE{\_}ADJUSTMENT}_i
$$

!!! example "Exemple : Dépréciation d'une obligation"

    Une obligation d'entreprise initialement évaluée à 1 000 € est partiellement dépréciée après que l'émetteur a signalé des difficultés financières.

    - **Avant ajustement** : Valeur calculée = 1 000 €
    - **Événement d'ajustement de prix** : montant = −200
    - **Après ajustement** : Valeur calculée = 800 €

    Il ne s'agit pas d'une transaction de marché — c'est une correction du modèle de juste valeur.

!!! example "Exemple : Décote d'un prêt P2P"

    Un prêt peer-to-peer de 5 000 € subit une décote de 20 % lors d'une restructuration de dette.

    - **Événement d'ajustement de prix** : montant = −1 000
    - **Nouvelle juste valeur** : 4 000 €

---

## 📊 Quand utiliser les ajustements de prix

Utilisez `PRICE_ADJUSTMENT` lorsque :

- ✅ La juste valeur de l'actif change sans transaction de marché
- ✅ Vous devez enregistrer une dépréciation ou une perte de valeur
- ✅ L'actif est évalué par modèle (Scheduled Investment) et nécessite une correction manuelle
- ✅ Une restructuration de dette affecte la valeur du principal

Ne **pas** utiliser pour :

- ❌ Les variations régulières du prix du marché (celles-ci sont capturées par les points de données de prix)
- ❌ Les paiements en espèces (utilisez `DIVIDEND` ou `INTEREST` à la place)
- ❌ Les changements de quantité d'actions (utilisez `SPLIT` à la place)

---

## 🧮 Comment LibreFolio gère les ajustements de prix

Dans LibreFolio, un événement `PRICE_ADJUSTMENT` est enregistré avec :

- **Date** : La date d'effet de l'ajustement
- **Montant** : Le changement algébrique (positif pour les augmentations, négatif pour les diminutions)
- **Devise** : La devise de l'ajustement
- **Notes** : Description de la raison (ex: "Dépréciation partielle due au défaut de l'émetteur")

Pour le fournisseur **Scheduled Investment**, les ajustements de prix font partie de la formule principale :

$$
\text{price}(d) = \text{initial{\_}value} + \text{accrued{\_}interest}(d) - \sum \text{INTEREST} + \sum \text{PRICE{\_}ADJUSTMENT}
$$

---

## 🔗 Liens connexes

- 📅 **[Aperçu des événements d'actifs](index.md)** — Tous les types d'événements
- 📈 **[Intérêts](interest.md)** — Paiements d'intérêts périodiques
- 🏁 **[Règlement à l'échéance](maturity-settlement.md)** — Retour final du capital
