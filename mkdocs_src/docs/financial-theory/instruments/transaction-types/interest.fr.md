# ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" } Intérêts (Transaction)

Une **transaction d'intérêts** enregistre les revenus d'intérêts reçus provenant d'obligations, de comptes d'épargne, de prêts P2P ou d'autres instruments à revenu fixe. Elle représente l'impact au niveau du portefeuille d'un [événement d'intérêts](../asset-events/interest.md).

---

## 🔑 Propriétés Clés

| Propriété | Détail |
|----------|--------|
| **Code** | `INTEREST` |
| **Effet sur la trésorerie** | ⬆️ Augmente le solde |
| **Effet sur l'actif** | — (principal inchangé) |
| **Événement fiscal** | Oui (revenu imposable) |

---

## 📊 Sources d'Intérêts

| Source | Description | Fréquence |
|--------|-------------|-----------|
| **Coupons obligataires** | Paiements à taux fixe ou variable | Semestrielle / Annuelle |
| **Intérêts d'épargne** | Intérêts sur les dépôts de trésorerie | Mensuelle / Trimestrielle |
| **Paiements de prêts P2P** | Partie intérêts des remboursements de prêts | Mensuelle |
| **Rendements du crowdfunding** | Rendements à taux fixe sur des projets | Variable |

---

## 📐 Intérêt Simple vs Composé

### 📏 Intérêt Simple

Intérêt calculé uniquement sur le principal d'origine :

$$
I = P \times r \times t
$$

### 📈 Intérêt Composé

Intérêt calculé sur le principal + les intérêts accumulés :

$$
A = P \times (1 + r)^t
$$

La différence entre l'intérêt simple et l'intérêt composé est le fondement du benchmark [Croissance Linéaire vs Composée](../../technical-analysis/synthetic-benchmarks/index.md).

---

## 🔗 Liens connexes

- 📈 **[Événements d'intérêts](../asset-events/interest.md)** — Mécanismes des intérêts courus et des coupons
- 🏛️ **[Obligations](../asset-types/bonds.md)** — Le principal actif producteur d'intérêts
- 📅 **[Conventions de décompte des jours](../../fundamentals/day-count.md)** — Comment les périodes d'intérêts sont calculées
