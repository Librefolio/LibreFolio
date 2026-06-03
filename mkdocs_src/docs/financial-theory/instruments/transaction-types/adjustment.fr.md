# ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Ajustement

Les **ajustements** sont un type de transaction polyvalent permettant d'effectuer des corrections manuelles soit sur les soldes de trésorerie, soit sur les soldes d'actifs. Contrairement aux types appairés (Transfert, Transfert de trésorerie, Conversion FX), les ajustements sont **autonomes** — chaque ajustement constitue une ligne unique et indépendante.

---

## 🔑 Propriétés clés

| Propriété | Valeur |
|----------|-------|
| **Code** | `ADJUSTMENT` |
| **Effet trésorerie** | Optionnel (± tout montant) |
| **Effet actif** | Requis (± toute quantité) |
| **Événement fiscal** | Non |

---

## 📊 Cas d'utilisation

Les ajustements sont utilisés lorsqu'aucun autre type de transaction ne convient :

- **Correction d'erreurs d'importation** — par exemple, un import de courtier ayant omis une opération sur titres
- **Divisions / divisions inverses d'actions** — ajuster la quantité sans mouvement de trésorerie
- **Dons** — réception ou don d'actions
- **Configuration du solde initial** — amorçage d'un portefeuille à partir d'un instantané (snapshot)
- **Opérations sur titres** non couvertes par d'autres types (scissions/spinoffs, fusions, etc.)

!!! note "Promouvoir en Transfert"

    Deux lignes `ADJUSTMENT` avec des **quantités opposées**, le **même actif** et des **courtiers différents** peuvent être **promues** en une paire de Transfert d'actifs. Ceci est utile lorsque vous avez initialement enregistré des ajustements séparés et que vous souhaitez ultérieurement les lier comme un transfert.

---

## 📐 Impact sur le prix de revient

Les ajustements avec une quantité positive **augmentent** le nombre de lots (FIFO). Le prix de revient pour les lots créés par ajustement dépend de la présence d'un **Forçage du prix de revient (Cost Basis Override)** :

- **Avec forçage** : la valeur spécifiée est utilisée comme **coût d'acquisition unitaire** (Coût Moyen Pondéré — WAC)
- **Sans forçage** : le lot est créé avec un coût nul (acquisition gratuite — ex: dons, airdrops)

!!! info "Valeur unitaire"

    Le Forçage du prix de revient correspond au coût moyen **par unité** de l'actif.
    Pour obtenir le coût total du bloc transféré, multipliez par la quantité :

    $$\text{Coût total} = \text{WAC} \times \text{quantité}$$

### 🏦 Prix de revient automatique sur les transferts

Lors du transfert d'actifs entre courtiers, LibreFolio **calcule automatiquement** le Forçage du prix de revient du côté destinataire en utilisant le **Coût Moyen Pondéré (WAC)** de la position du courtier source.

!!! tip "En savoir plus"

    Pour la formule complète, des exemples et les cas particuliers, consultez la page dédiée :
    **[📊 Coût Moyen Pondéré (WAC)](../../portfolio-theory/weighted-average-cost.md)**

??? note "✏️ Quand forcer la valeur manuellement"

    La formule automatique fonctionne pour le cas standard (même régime fiscal, pas d'événements fiscaux lors du transfert). Dans les scénarios suivants, l'utilisateur doit définir la valeur manuellement :

    | Scénario | Ce qu'il faut définir |
    |----------|------------|
    | **Transfert normal** | Laisser vide — calculé automatiquement |
    | **Exit Tax** | Valeur de marché à la date du transfert (spécifique à la juridiction) |
    | **Héritage** | Juste valeur marchande à la date du décès (ou base actualisée) |
    | **Don** | Prix de revient d'origine du donateur (base reportée) |
    | **Opération sur titres** | Base ajustée selon les termes de l'opération sur titres |

    !!! warning "Responsabilité de l'utilisateur"

        Lors du forçage manuel du prix de revient, l'utilisateur est responsable de l'exactitude de la valeur. LibreFolio ne valide pas les montants de forçage par rapport aux règles fiscales — consultez un conseiller fiscal pour des directives spécifiques à votre juridiction.

---

## 🔗 Liens connexes

- 📊 **[Coût Moyen Pondéré (WAC)](../../portfolio-theory/weighted-average-cost.md)** — Comment le prix de revient automatique est calculé
- 🔄 **[Transfert d'actifs](transfer.md)** — Deux ajustements liés peuvent être promus en transfert
- 🛒 **[Achat & Vente](buy-sell.md)** — Transactions d'actifs standard avec trésorerie
- 💰 **[Frais & Taxes](fee.md)** — Corrections uniquement de trésorerie (utilisez Frais/Taxes au lieu d'Ajustement)
