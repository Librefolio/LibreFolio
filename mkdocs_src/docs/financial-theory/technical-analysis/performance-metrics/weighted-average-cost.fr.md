# 📊 Prix Moyen Pondéré (PMP)

## 💡 Qu'est-ce que le PMP ?

Le **Prix Moyen Pondéré** (PMP) est le prix unitaire moyen d'un actif dans un portefeuille, pondéré par la quantité acquise à chaque prix.

Il répond à la question : _"En moyenne, combien ai-je payé par unité pour cet actif ?"_

!!! info "Autres noms"

    - **PMC** — Prezzo Medio di Carico (Italie)
    - **ACB** — Average Cost Basis (Canada, États-Unis)
    - **WAC** — Weighted Average Cost (international)

## 🧮 Formule

Le PMP est calculé **itérativement** au fur et à mesure que chaque transaction est traitée chronologiquement :

$$
PMP_{nouveau} = \frac{PMP_{actuel} \times Q_{pool} + Coût_{unitaire} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Où :

- $PMP_{actuel}$ = prix moyen pondéré actuel avant cette transaction
- $Q_{pool}$ = quantité totale détenue dans le pool avant cette transaction
- $Coût_{unitaire}$ = coût d'acquisition unitaire de la nouvelle transaction
- $Q_{tx}$ = quantité ajoutée par la nouvelle transaction

## ⚙️ Comment LibreFolio calcule le PMP

LibreFolio utilise un **algorithme itératif conscient des inventaires** qui traite toutes les transactions éligibles pour une paire (courtier, actif) donnée dans l'ordre chronologique.

### 🏷️ Effets des transactions

Chaque transaction contribue au calcul du PMP d'une de ces manières :

| Effet | Condition | Impact sur le PMP |
|--------|-----------|---------------|
| **Pondéré** | `qty > 0` et `unit_cost > 0` | Le PMP évolue vers le nouveau coût d'acquisition |
| **Quantité réduite** | `qty < 0` | Sortie au PMP actuel — PMP inchangé, pool réduit |
| **Dilution** | `qty > 0` mais `unit_cost = 0` | Le pool augmente, numérateur inchangé → le PMP **diminue** |
| **PMP Auto** | `qty > 0`, `cost_basis_mode = "auto"` | Pool inchangé — les unités entrent au PMP actuel |

### 📅 Ordre le même jour

Lorsque plusieurs transactions ont lieu à la même date :

1. **D'abord les ajouts** (qty > 0) — traités avant les réductions
2. **Ensuite les réductions** (qty < 0) — garantit que le pool ne devient pas transitoirement négatif

### 🔻 Épuisement du pool

- Quand `new_qty = 0` : le PMP se réinitialise à 0 (position fermée)
- Quand `new_qty < 0` (cas limite d'arrondi) : limité à 0

## 📝 Exemples pratiques

??? example "Exemple 1 : Deux achats — le PMP augmente"

    | Date | Type | Qté | Coût unitaire | Qté du pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1er avril | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avril | ACHAT | 5 | 180 $ | 15 | 160,00 $ |

    $$
    PMP = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160,00
    $$

    Le deuxième achat à un prix plus élevé **fait monter le PMP**.

??? example "Exemple 2 : Achat puis vente — le PMP inchangé"

    | Date | Type | Qté | Coût unitaire | Qté du pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1er avril | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avril | VENTE | -5 | (au PMP) | 5 | 150,00 $ |

    La VENTE retire des unités au PMP actuel (150 $). Le PMP reste **inchangé** — seul le pool diminue.

??? example "Exemple 3 : Acquisition à coût nul — Dilution"

    | Date | Type | Qté | Coût unitaire | Qté du pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1er avril | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 1er mai | AJUSTEMENT | +5 | 0 $ | 15 | 100,00 $ |

    $$
    PMP = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100,00
    $$

    Le PMP est **dilué** car 5 unités sont entrées à coût nul (ex. division d'actions, airdrop, don).

## 🔄 Surcharge du coût de base

Pour les transferts et ajustements, LibreFolio prend en charge une **surcharge du coût de base** : un coût unitaire spécifié par l'utilisateur qui représente le coût historique des unités transférées.

**Lorsqu'il est défini (mode manuel) :**

- La transaction entre dans le calcul du PMP comme une acquisition pondérée normale
- Cela préserve la continuité des coûts entre courtiers (ex. lors d'un transfert du courtier A au courtier B)

**Lorsqu'il n'est pas défini (aucun mode spécifié) :**

- La transaction entre avec `unit_cost = 0` (effet de dilution)
- Cela est approprié pour les divisions d'actions, dons ou airdrops où aucun prix d'achat n'existe

**Lorsqu'en mode auto (`cost_basis_mode = "auto"`) :**

- La transaction entre au **PMP actuel du pool** — le PMP reste algébriquement inchangé
- Cela est approprié pour les transferts ou ajustements où le coût de base doit être hérité du pool du courtier source

$$
PMP_{nouveau} = \frac{PMP \times Q_{pool} + PMP \times Q_{tx}}{Q_{pool} + Q_{tx}} = PMP
$$

!!! tip "PMP Auto dans l'interface"

    Dans le formulaire de transaction, le bouton "Auto" utilise ce mode. Le tableau des transactions éligibles affiche le badge d'effet **PMP Auto** (ou **PMC Auto** en italien), indiquant que les unités sont entrées au coût actuel du pool sans modifier le PMP.

??? example "Exemple 4 : Transfert en mode Auto — le PMP inchangé"

    | Date | Type | Qté | Coût unitaire | Qté du pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1er avril | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avril | ACHAT | 5 | 180 $ | 15 | 160,00 $ |
    | 1er mai | TRANSFERT (auto) | +3 | 160 $ (=PMP) | 18 | 160,00 $ |

    $$
    PMP = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160,00
    $$

    Le destinataire du transfert en **mode auto** hérite du PMP actuel comme coût unitaire. Le pool augmente mais le PMP reste **inchangé**.

## 🌍 Gestion multi-devises

Lorsqu'un portefeuille contient des acquisitions dans différentes devises, LibreFolio :

1. Détermine la **devise cible** à partir de la surcharge de la requête lorsqu'elle est fournie ; sinon utilise la devise de l'acquisition la plus récente (déterministe), avec repli sur la devise de l'actif
2. Convertit tous les coûts unitaires dans la devise cible en utilisant les taux de change historiques
3. Calcule le PMP dans la devise cible unifiée

!!! warning "Disponibilité des taux de change"

    Si un taux de change requis est manquant, le calcul du PMP peut être incomplet. L'interface avertit des paires de change manquantes et propose des actions rapides pour les ajouter ou les synchroniser.

## 🎯 Où le PMP est utilisé dans LibreFolio

- **Coût de base** : $\text{CB}(a,b,t) = q(a,b,t) \times \text{PMP}(a,b,t) \times \text{fx}(\cdot)$
- **P&L réalisé lors d'une VENTE** : $\text{réalisé} = P_{\text{vente}} - q_{\text{vendu}} \times \text{PMP}_{\text{pré-vente}}$
- **Décomposition du pool de liquidités** : VENTE rend $C = q_{\text{vendu}} \times \text{PMP}$ au Pool de Capital
- **Formulaire de transfert** : suggère automatiquement une surcharge du coût de base pour les transferts sortants

!!! warning "Le PMP n'est jamais utilisé pour l'évaluation des actifs"

    Le PMP est une construction comptable pour le coût de base. La chaîne d'évaluation pour la valeur de marché utilise : `MARKET_PRICE → LAST_BUY_PRICE → MISSING`. Consultez [Résolution des Prix](portfolio-engine/price-resolution.md).

## ⚙️ Implémentation : Portée au niveau de la position

Le PMP est maintenu **par position** $(a, b)$ — c'est-à-dire par paire (actif, courtier). Le même actif détenu chez deux courtiers a deux pools de PMP indépendants.

$$
\text{PMP}(a, b_1, t) \neq \text{PMP}(a, b_2, t) \quad \text{en général}
$$

Le moteur calcule le PMP en ligne pendant la boucle quotidienne des transactions — aucune requête séparée à la base de données n'est nécessaire. Cela atteint un coût amorti O(1) par transaction au lieu du coût O(N) de réinterroger l'historique complet.

### 📅 Ordre des transactions le même jour

À l'intérieur d'une même date, **les ajouts sont traités avant les réductions** :

$$
\text{ACHAT}_1, \text{ACHAT}_2, \ldots \quad \text{puis} \quad \text{VENTE}_1, \text{VENTE}_2, \ldots
$$

Cela évite les quantités négatives transitoires et garantit que VENTE lit toujours le PMP correct qui inclut les ACHATS du même jour.

## 🔗 Liens connexes

- 🔬 **[Analyse des lots FIFO](fifo-engine/fifo-lot-analysis.md)** — Complément par lot : suit chaque lot d'acquisition individuellement au lieu de les fusionner en une moyenne
- 🔁 **[Achat & Vente](../../instruments/transaction-types/buy-sell.md)** — Transactions qui alimentent le pool PMP
- 📈 **[VNI / Valeur nette](portfolio-engine/nav.md)** — Comment la valeur comptable basée sur le PMP diffère de la VNI au prix du marché
