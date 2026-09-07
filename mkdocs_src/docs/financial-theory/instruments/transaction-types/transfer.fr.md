# 🔄 ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Transfert d'actifs

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-transfer" alt="Formulaire de transaction — TRANSFERT">
</div>

Les **transferts d'actifs** déplacent des titres entre des comptes de courtage **sans vente**. La position quitte un courtier pour arriver chez un autre — aucun flux de trésorerie n'a lieu et, dans la plupart des juridictions, cela ne constitue pas un événement imposable.

---

## 🔑 Propriétés clés

| Propriété | De (source) | À (destination) |
|----------|---------------|-------------------|
| **Code** | `TRANSFER` | `TRANSFER` |
| **Effet sur la trésorerie** | — | — |
| **Effet actif** | ⬇️ Diminue | ⬆️ Augmente |
| **Courtier** | Courtier source | Courtier de destination |
| **Événement fiscal** | Varie selon la juridiction | Varie |

---

## 📊 Fonctionnement

Un transfert d'actif enregistre **deux écritures** : un débit chez le courtier source et un crédit chez le courtier de destination. Les deux font référence au **même actif** avec des quantités opposées.

Scénarios courants :

- Déplacement d'actions d'un courtier à un autre
- Héritage d'actifs
- Contributions en nature vers un type de compte différent (ex: ISA, 401k)

!!! info "Préservation du prix de revient"

    Lors du transfert d'actifs, le **prix de revient original** doit être préservé. Le transfert lui-même n'est pas un événement imposable dans la plupart des juridictions (bien que les règles varient). LibreFolio permet une **dérogation optionnelle au prix de revient** du côté du destinataire.

    Consultez **[📊 Coût Moyen Pondéré (CMP)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** pour savoir comment le prix de revient automatique est calculé.

---

## 🔀 Relation avec les Ajustements

En arrière-plan, un Transfert est composé de deux écritures d'Ajustement. LibreFolio supporte :

| Opération | Résultat |
|-----------|--------|
| **Division** (délier) | Transfert → deux Ajustements indépendants |
| **Promouvoir** (lier) | Deux Ajustements → Transfert |

**Contraintes de promotion** : même actif, courtiers différents, quantités opposées.

---

## 👵 Succession et courtiers d'origine non suivis

Un vrai `TRANSFER` nécessite deux courtiers dans LibreFolio : source et destination. Si le dossier source est en dehors de LibreFolio, la jambe entrante est mieux modélisée comme un `ADJUSTMENT` positif sans trésorerie avec un `cost_basis_override` par unité, plutôt que comme un transfert apparié. Les lignes de succession de Crédit Agricole (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) utilisent ce modèle : les titres hérités entrent en tant que capital en nature, aucun `DEPOSIT` de trésorerie n'est créé et la causale d'origine reste dans la description à des fins d'auditabilité.

---

## 🔗 Liens connexes

- 📊 **[Coût Moyen Pondéré](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Comment le prix de revient est calculé lors des transferts
- 🏦 **[Transfert de fonds](cash-transfer.md)** — Virements bancaires (cash, pas d'actifs)
- 💱 **[Conversion de devise](fx-conversion.md)** — Change de devises
- 📊 **[Ajustement](adjustment.md)** — Corrections manuelles
