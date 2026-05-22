# ![](../../../static/icons/transactions/fx-conversion.png){: width="32" style="vertical-align: middle;" } Conversion de devise

**Les conversions de devise** permettent d'échanger une devise contre une autre au sein du **même compte de courtier**. Le solde d'une devise diminue tandis que celui d'une autre augmente — aucun titre ni courtier ne change.

---

## 🔑 Propriétés Clés

| Propriété | De (source) | À (cible) |
|----------|---------------|-------------|
| **Code** | `FX_CONVERSION` | `FX_CONVERSION` |
| **Effet sur la trésorerie** | ⬇️ Devise source | ⬆️ Devise cible |
| **Effet sur l'actif** | — | — |
| **Courtier** | Le même des deux côtés | Le même des deux côtés |
| **Devise** | Différente de chaque côté | Différente de chaque côté |
| **Événement fiscal** | Varie selon la juridiction | Varie |

---

## 📊 Comment ça fonctionne

Une conversion de devise enregistre **deux entrées** sur le même courtier avec **des devises différentes**. Le taux de conversion est implicite d'après les montants :

$$
FX_{rate} = \frac{\text{Amount}_{target}}{\lvert\text{Amount}_{source}\rvert}
$$

Les conversions de devise peuvent être :

- **Explicites** : L'utilisateur convertit délibérément des devises (ex: EUR → USD avant d'acheter des actions américaines)
- **Implicites** : Le courtier convertit automatiquement lors de l'achat d'un actif libellé dans une devise étrangère

!!! info "FX Implicite et Frais"

    Lorsqu'un courtier convertit automatiquement la devise, le taux effectif inclut souvent un spread. La différence entre le taux du marché et le taux effectif est essentiellement un frais caché :

    $$
    \text{Implicit Fee} = \lvert\text{Amount}_{source}\rvert \times (\text{Market Rate} - \text{Effective Rate})
    $$

---

## 📈 Taux Impliqué et Spread du Courtier

LibreFolio calcule automatiquement le **taux de change impliqué** à partir des deux montants :

$$
\text{Implied Rate} = \frac{\lvert\text{Amount}_{target}\rvert}{\lvert\text{Amount}_{source}\rvert}
$$

Celui-ci est comparé au **taux du marché** provenant du sous-système FX à la date de la transaction. La différence constitue le **spread du courtier** :

$$
\text{Spread} = \text{Implied Rate} - \text{Market Rate}
$$

$$
\text{%Spread} = \frac{\text{Spread}}{\text{Market Rate}} \times 100
$$

!!! warning "Disponibilité du Taux du Marché"

    La comparaison avec le taux du marché nécessite que la paire FX concernée soit configurée dans le système FX de LibreFolio. Si la paire n'est pas configurée ou si aucun taux n'existe pour la date de la transaction, seul le taux impliqué est affiché.

---

## 🔀 Relation avec les Dépôts/Retraits

En interne, une conversion de devise est composée d'un Retrait (devise source) et d'un Dépôt (devise cible). LibreFolio supporte :

| Opération | Résultat |
|-----------|--------|
| **Division** (délier) | Conversion de devise → Retrait + Dépôt indépendants |
| **Promote** (lier) | Retrait + Dépôt → Conversion de devise |

**Contraintes de promotion** : devises différentes, même courtier.

---

## 🔗 Liens connexes

- 💵 **[Dépôt & Retrait](deposit-withdrawal.md)** — Mouvements de trésorerie à sens unique
- 🔄 **[Transfert d'Actifs](transfer.md)** — Déplacement de titres entre courtiers
- 🏦 **[Transfert de trésorerie](cash-transfer.md)** — Virements bancaires entre courtiers

---

*Voir aussi : [💱 Taux FX](../../../user/fx/index.md) — comment configurer et synchroniser les taux de change dans LibreFolio.*
