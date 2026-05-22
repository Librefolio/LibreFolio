# 📊 Coût Moyen Pondéré (CMP)

## 💡 Qu'est-ce que le CMP ?

Le **Coût Moyen Pondéré** (CMP) est le coût unitaire moyen d'un actif dans un portefeuille, pondéré par la quantité acquise à chaque prix.

Il répond à la question : _"En moyenne, combien ai-je payé par unité pour cet actif ?"_

!!! info "Autres noms"

    - **PMC** — Prezzo Medio di Carico (Italie)
    - **ACB** — Average Cost Basis (Canada, États-Unis)
    - **CMP** — Coût Moyen Pondéré (France)

## 🧮 Formule

Le CMP est calculé de manière **itérative** à mesure que chaque transaction est traitée chronologiquement :

$$
WAC_{new} = \frac{WAC_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Où :

- $WAC_{current}$ = coût moyen pondéré actuel avant cette transaction
- $Q_{pool}$ = quantité totale détenue dans le pool avant cette transaction
- $Cost_{unit}$ = coût d'acquisition unitaire de la nouvelle transaction
- $Q_{tx}$ = quantité ajoutée par la nouvelle transaction

## ⚙️ Comment LibreFolio calcule le CMP

LibreFolio utilise un **algorithme itératif conscient de l'inventaire** qui traite toutes les transactions éligibles pour un couple (courtier, actif) donné dans l'ordre chronologique.

### 🏷️ Effets des transactions

Chaque transaction contribue au calcul du CMP de l'une des manières suivantes :

| Effet | Condition | Impact sur le CMP |
|--------|-----------|---------------|
| **Pondéré** | `qty > 0` et `unit_cost > 0` | Le CMP tend vers le nouveau coût d'acquisition |
| **Quantité réduite** | `qty < 0` | Sortie au CMP actuel — CMP inchangé, le pool rétrécit |
| **Dilution** | `qty > 0` mais `unit_cost = 0` | Le pool augmente, le numérateur reste inchangé → le CMP **diminue** |

### 📅 Ordonnancement le même jour

Lorsque plusieurs transactions surviennent à la même date :

1. **Ajouts d'abord** (qty > 0) — traités avant les réductions
2. **Réductions ensuite** (qty < 0) — garantit que le pool ne devienne pas transitoirement négatif

### 🔻 Épuisement du pool

- Lorsque `new_qty = 0` : le CMP est réinitialisé à 0 (position fermée)
- Lorsque `new_qty < 0` (cas limite d'arrondi) : plafonné à 0

## 📝 Exemples pratiques

??? example "Exemple 1 : Deux achats — le CMP augmente"

 | Date | Type | Qte | Coût Unitaire | Qte Pool | CMP |
 |------|------|-----|---------------|----------|-----|
 | 1 avr | ACHAT | 10 | $150 | 10 | $150.00 |
 | 15 avr | ACHAT | 5 | $180 | 15 | $160.00 |

 $$
 WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
 $$

 Le deuxième achat à un prix plus élevé **tire le CMP vers le haut**.

??? example "Exemple 2 : Achat puis Vente — CMP inchangé"

 | Date | Type | Qte | Coût Unitaire | Qte Pool | CMP |
 |------|------|-----|---------------|----------|-----|
 | 1 avr | ACHAT | 10 | $150 | 10 | $150.00 |
 | 15 avr | VENTE | -5 | (au CMP) | 5 | $150.00 |

 La VENTE retire des unités au CMP actuel ($150). Le CMP reste **inchangé** — seul le pool rétrécit.

??? example "Exemple 3 : Acquisition à coût nul — Dilution"

 | Date | Type | Qte | Coût Unitaire | Qte Pool | CMP |
 |------|------|-----|---------------|----------|-----|
 | 1 avr | ACHAT | 10 | $150 | 10 | $150.00 |
 | 1 mai | AJUSTEMENT | +5 | $0 | 15 | $100.00 |

 $$
 WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
 $$

 Le CMP est **dilué** car 5 unités sont entrées à coût nul (ex: division d'actions, airdrop, don).

## 🔄 Forçage du coût de base (Cost Basis Override)

Pour les transferts et les ajustements, LibreFolio prend en charge un **forçage du coût de base** : un coût unitaire spécifié par l'utilisateur qui représente le coût historique des unités transférées.

**S'il est renseigné :**

- La transaction entre dans le calcul du CMP comme une acquisition pondérée normale
- Cela préserve la continuité des coûts entre les courtiers (ex: lors d'un transfert du courtier A vers le courtier B)

**S'il n'est pas renseigné :**

- La transaction entre avec `unit_cost = 0` (effet de dilution)
- Ceci est approprié pour les divisions d'actions, les dons ou les airdrops où aucun prix d'achat n'existe

## 🌍 Gestion multi-devises

Lorsqu'un portefeuille contient des acquisitions dans différentes devises, LibreFolio :

1. Détermine la **devise cible** (la plus fréquente parmi les acquisitions)
2. Convertit tous les coûts unitaires dans la devise cible en utilisant les taux de change historiques
3. Calcule le CMP dans la devise cible unifiée

!!! warning "Disponibilité des taux de change"

    Si un taux de change requis est manquant, le calcul du CMP peut être incomplet. L'interface utilisateur avertit des paires de devises manquantes et propose des actions rapides pour les ajouter ou les synchroniser.

## 🎯 Où le CMP est-il utilisé dans LibreFolio

- **Formulaire de transfert** : suggère automatiquement le `cost_basis_override` pour les transferts sortants
- **Calcul du P&L** : gains réalisés = prix_de_vente − CMP (FIFO à l'exécution, CMP pour la base de coût)
- **Vue du portefeuille** : prix d'entrée moyen par position
