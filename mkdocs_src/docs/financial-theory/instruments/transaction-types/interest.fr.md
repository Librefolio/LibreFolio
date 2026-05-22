# ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" } Intérêt (Transaction)

Une **transaction d'intérêt** enregistre les revenus d'intérêt reçus provenant d'obligations, de comptes d'épargne, de prêts P2P ou d'autres instruments à revenu fixe. Elle représente l'impact au niveau du portefeuille d'un [événement d'intérêt](../asset-events/interest.md).

---

## 🔑 Propriétés Clés

| Propriété | Détail |
|----------|--------|
| **Code** | `INTEREST` |
| **Effet sur la trésorerie** | ⬆️ Augmente le solde |
| **Effet sur l'actif** | — (le principal reste inchangé) |
| **Événement fiscal** | Oui (revenu imposable) |

---

## 📊 Sources d'intérêt

| Source | Description | Fréquence |
|--------|-------------|-----------|
| **Coupons obligataires** | Paiements à taux fixe ou variable | Semestriel / Annuel |
| **Intérêt d'épargne** | Intérêt sur les dépôts de liquidités | Mensuel / Trimestriel |
| **Paiements de prêts P2P** | Partie intérêt des remboursements de prêt | Mensuel |
| **Rendements du Crowdfunding** | Rendements à taux fixe sur des projets | Variable |

---

## 💡 Quand l'utiliser

Utilisez une transaction `INTEREST` lorsque des liquidités arrivent sur votre compte courtier sous forme de revenus d'intérêt. Ceci est distinct de :

- **Dividende** — revenu provenant de capitaux propres (actions, ETF de distribution)
- **Règlement à l'échéance** — remboursement du principal à l'échéance d'une obligation

!!! tip "Théorie & formules"

    Pour les mathématiques de l'accumulation d'intérêt (simple vs composé, conventions de comptage des jours, mesures de rendement), voir :

    - **[📈 Événements d'intérêt](../asset-events/interest.md)** — Mécanismes d'accumulation et impact sur le prix
    - **[📅 Conventions de comptage des jours](../../fundamentals/day-count.md)** — Comment les périodes d'intérêt sont calculées

---

## 🔗 Liens connexes

- 📈 **[Événements d'intérêt](../asset-events/interest.md)** — Mécanismes d'accumulation et de coupons
- 🏛️ **[Obligations](../asset-types/bonds.md)** — Le principal actif producteur d'intérêt
- 📈 **[Rendements & Taux de croissance](../../fundamentals/returns.md)** — Mesurer le rendement des revenus
- 📅 **[Conventions de comptage des jours](../../fundamentals/day-count.md)** — Comment les périodes d'intérêt sont calculées
