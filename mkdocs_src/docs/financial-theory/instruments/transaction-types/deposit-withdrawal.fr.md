# ![](../../../static/icons/transactions/deposit.png){: width="32" style="vertical-align: middle;" } Dépôts et Retraits ![](../../../static/icons/transactions/withdrawal.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-deposit" alt="Formulaire de Transaction — DÉPÔT">
</div>

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

## 💡 Pourquoi c'est important

Les dépôts et les retraits ne modifient pas la valeur marchande de votre portefeuille, mais ils sont critiques pour la **mesure de la performance** :

- **Money-Weighted Return (MWR)** : prend en compte le moment et la taille des flux de trésorerie — est directement affecté par les dépôts/retraits
- **Time-Weighted Return (TWR)** : élimine l'effet des flux de trésorerie pour mesurer la performance "pure" du portefeuille

Sans un suivi précis des dépôts et retraits, il est impossible de distinguer les rendements *générés* par le portefeuille des rendements *causés* par l'ajout ou le retrait de liquidités.

!!! tip "Learn more"

    Consultez **[📈 Rendements et Taux de Croissance](../../fundamentals/returns.md)** pour les formules et la méthodologie.

---

## 🔗 Liens connexes

- 📈 **[Rendements et Taux de Croissance](../../fundamentals/returns.md)** — Calcul TWR vs MWR
- 🛒 **[Achat et Vente](buy-sell.md)** — Transactions qui utilisent la trésorerie déposée
