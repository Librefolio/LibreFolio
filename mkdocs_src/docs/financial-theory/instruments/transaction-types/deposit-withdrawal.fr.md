# ![](../../../static/icons/transactions/deposit.png){: width="32" style="vertical-align: middle;" } Dépôts & Retraits

Les **dépôts** et les **retraits** suivent le mouvement des liquidités entrant et sortant d'un compte de courtier. Ils n'impliquent aucun actif — seul le solde de trésorerie change.

---

## 🔑 Propriétés Clés

| Propriété | Dépôt | Retrait |
|----------|---------|------------|
| **Code** | `DEPOSIT` | `WITHDRAWAL` |
| **Effet sur la trésorerie** | ⬆️ Augmente le solde | ⬇️ Diminue le solde |
| **Effet sur l'actif** | — | — |
| **Événement fiscal** | Non | Non |

---

## 💡 Pourquoi sont-ils importants ?

Les dépôts et les retraits ne modifient pas la valeur marchande de votre portefeuille, mais ils sont essentiels pour la **mesure de la performance** :

- **Rendement pondéré par les flux (MWR)** : tient compte du moment et de la taille des flux de trésorerie — directement affecté par les dépôts/retraits
- **Taux de rendement pondéré dans le temps (TWR)** : élimine l'effet des flux de trésorerie pour mesurer la performance « pure » du portefeuille

Sans un suivi précis des dépôts et des retraits, il est impossible de distinguer les rendements *générés* par le portefeuille de la performance induite par l'ajout ou le retrait de liquidités.

!!! tip "En savoir plus"

    Consultez **[📈 Rendements & Taux de Croissance](../../fundamentals/returns.md)** pour les formules et la méthodologie.

---

## 🔗 Liens connexes

- 📈 **[Rendements & Taux de Croissance](../../fundamentals/returns.md)** — Calcul TWR vs MWR
- 🛒 **[Achat & Vente](buy-sell.md)** — Transactions utilisant les liquidités déposées
