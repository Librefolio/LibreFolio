# ![](../../../static/icons/transactions/cash-transfer.png){: width="32" style="vertical-align: middle;" } Transfert de fonds

Les **transferts de fonds** (virements bancaires / bonifici) déplacent de l'argent entre des comptes de courtage. Le solde diminue à la source et augmente à la destination — aucun actif n'est impliqué.

---

## 🔑 Propriétés Clés

| Propriété | Origine (source) | Destination (destination) |
|----------|---------------|-------------------|
| **Code** | `CASH_TRANSFER` | `CASH_TRANSFER` |
| **Effet sur les liquidités** | ⬇️ Diminue | ⬆️ Augmente |
| **Effet sur les actifs** | — | — |
| **Courtier** | Courtier source | Courtier de destination |
| **Devise** | Identique des deux côtés | Identique des deux côtés |
| **Événement fiscal** | Non | Non |

---

## 📊 Comment ça fonctionne

Un transfert de fonds enregistre **deux écritures** : un retrait chez le courtier source et un dépôt chez le courtier de destination. Les deux partagent la même devise avec des montants symétriques. Les deux côtés peuvent avoir des **dates différentes** — par exemple, un virement envoyé le lundi peut arriver le mercredi.

Scénarios courants :

- Virement de fonds d'un courtier à un autre
- Déplacement de liquidités vers un compte d'épargne
- Envoi d'argent entre comptes personnels

!!! note "Dates différentes"

    Contrairement aux transferts d'actifs où les deux côtés sont généralement réglés à la même date, les virements bancaires peuvent s'étaler sur plusieurs jours. LibreFolio prend en charge des dates distinctes pour chaque côté.

---

## 🔀 Relation avec les Dépôts/Retraits

En arrière-plan, un transfert de fonds est composé d'un Retrait et d'un Dépôt. LibreFolio prend en charge :

| Opération | Résultat |
|-----------|--------|
| **Division** (dissocier) | Transfert de fonds → Retrait + Dépôt indépendants |
| **Promotion** (lier) | Retrait + Dépôt → Transfert de fonds |

**Contraintes de promotion** : même devise, courtiers différents, montants de liquidités opposés.

---

## 🔗 Liens connexes

- 🔄 **[Transfert d'actifs](transfer.md)** — Déplacement de titres (pas de liquidités)
- 💵 **[Dépôt & Retrait](deposit-withdrawal.md)** — Mouvements de liquidités à sens unique
- 💱 **[Conversion FX](fx-conversion.md)** — Change de devises
