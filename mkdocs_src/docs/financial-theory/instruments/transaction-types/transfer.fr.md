# ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Transfert d'actifs

Les **transferts d'actifs** déplacent des titres entre des comptes de courtage **sans vente**. La position quitte un courtier pour arriver chez un autre — aucun flux monétaire n'est échangé et, dans la plupart des juridictions, cela ne constitue pas un événement imposable.

---

## 🔑 Propriétés clés

| Propriété | De (source) | À (destination) |
|----------|---------------|-------------------|
| **Code** | `TRANSFER` | `TRANSFER` |
| **Effet sur les liquidités** | — | — |
| **Effet sur l'actif** | ⬇️ Diminue | ⬆️ Augmente |
| **Courtier** | Courtier source | Courtier de destination |
| **Événement fiscal** | Varie selon la juridiction | Varie |

---

## 📊 Comment ça marche

Un transfert d'actif enregistre **deux entrées** : un débit chez le courtier source et un crédit chez le courtier de destination. Les deux font référence au **même actif** avec des quantités miroirs.

Scénarios courants :

- Déplacement d'actions d'un courtier à un autre
- Héritage d'actifs
- Contributions en nature vers un autre type de compte (ex: ISA, 401k)

!!! info "Préservation du prix de revient"

    Lors du transfert d'actifs, le **prix de revient original** (cost basis) doit être préservé. Le transfert lui-même n'est pas un événement imposable dans la plupart des juridictions (bien que les règles varient). LibreFolio permet un **outrepassage optionnel du prix de revient** côté réception.

    Consultez **[📊 Coût Moyen Pondéré (WAC)](../../portfolio-theory/weighted-average-cost.md)** pour savoir comment le prix de revient automatique est calculé.

---

## 🔀 Relation avec les ajustements

En arrière-plan, un Transfert est composé de deux entrées d'Ajustement. LibreFolio prend en charge :

| Opération | Résultat |
|-----------|--------|
| **Division** (délier) | Transfert → deux Ajustements indépendants |
| **Promouvoir** (lier) | Deux Ajustements → Transfert |

**Contraintes de promotion** : même actif, courtiers différents, quantités opposées.

---

## 🔗 Liens connexes

- 📊 **[Coût Moyen Pondéré](../../portfolio-theory/weighted-average-cost.md)** — Comment le prix de revient est calculé lors des transferts
- 🏦 **[Transfert de fonds](cash-transfer.md)** — Virements bancaires (liquidités, pas d'actifs)
- 💱 **[Conversion de devise](fx-conversion.md)** — Change de devises
- 📊 **[Ajustement](adjustment.md)** — Corrections manuelles
