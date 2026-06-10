# 📊 Coût Moyen Pondéré (WAC)

## 💡 Qu'est-ce que le WAC ?

Le **Coût Moyen Pondéré** (WAC - *Weighted Average Cost*) est le coût unitaire moyen d'un actif dans un portefeuille, pondéré par la quantité acquise à chaque prix.

Il répond à la question : _"En moyenne, combien ai-je payé par unité pour cet actif ?"_

!!! info "Autres noms"

    - **PMC** — Prezzo Medio di Carico (Italie)
    - **ACB** — Average Cost Basis (Canada, États-Unis)
    - **CMP** — Coût Moyen Pondéré (France)

## 🧮 Formule

Le WAC est calculé de manière **itérative** à mesure que chaque transaction est traitée chronologiquement :

$$
WAC_{new} = \frac{WAC_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Où :

- $WAC_{current}$ = coût moyen pondéré actuel avant cette transaction
- $Q_{pool}$ = quantité totale détenue dans le pool avant cette transaction
- $Cost_{unit}$ = coût d'acquisition unitaire de la nouvelle transaction
- $Q_{tx}$ = quantité ajoutée par la nouvelle transaction

## ⚙️ Comment LibreFolio calcule le WAC

LibreFolio utilise un **algorithme itératif tenant compte de l'inventaire** qui traite toutes les transactions éligibles pour un couple (courtier, actif) donné dans l'ordre chronologique.

### 🏷️ Effets des transactions

Chaque transaction contribue au calcul du WAC de l'une des manières suivantes :

| Effet | Condition | Impact sur le WAC |
|--------|-----------|---------------|
| **Pondéré** | `qty > 0` et `unit_cost > 0` | Le WAC se rapproche du nouveau coût d'acquisition |
| **Quantité réduite** | `qty < 0` | Sortie au WAC actuel — WAC inchangé, le pool rétrécit |
| **Dilution** | `qty > 0` mais `unit_cost = 0` | Le pool croît, le numérateur reste inchangé → le WAC **diminue** |
| **Auto WAC** | `qty > 0`, `cost_basis_mode = "auto"` | Le WAC du pool est inchangé — les unités entrent au WAC actuel |

### 📅 Ordonnancement le même jour

Lorsque plusieurs transactions ont lieu à la même date :

1. **Les ajouts d'abord** (qty > 0) — traités avant les réductions
2. **Les réductions ensuite** (qty < 0) — garantit que le pool ne devienne pas transitoirement négatif

### 🔻 Épuisement du pool

- Quand `new_qty = 0` : le WAC est réinitialisé à 0 (position fermée)
- Quand `new_qty < 0` (cas limite d'arrondi) : fixé à 0

## 📝 Exemples pratiques

??? example "Exemple 1 : Deux achats — le WAC augmente"

    | Date | Type | Qty | Coût Unitaire | Qty Pool | WAC |
    |------|------|-----|---------------|----------|-----|
    | 1 avr | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avr | ACHAT | 5 | 180 $ | 15 | 160,00 $ |

    $$
    WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160,00
    $$

    Le second achat à un prix plus élevé **tire le WAC vers le haut**.

??? example "Exemple 2 : Achat puis Vente — WAC inchangé"

    | Date | Type | Qty | Coût Unitaire | Qty Pool | WAC |
    |------|------|-----|---------------|----------|-----|
    | 1 avr | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avr | VENTE | -5 | (au WAC) | 5 | 150,00 $ |

    La VENTE retire des unités au WAC actuel (150 $). Le WAC reste **inchangé** — seul le pool rétrécit.

??? example "Exemple 3 : Acquisition à coût nul — Dilution"

    | Date | Type | Qty | Coût Unitaire | Qty Pool | WAC |
    |------|------|-----|---------------|----------|-----|
    | 1 avr | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 1 mai | AJUSTEMENT | +5 | 0 $ | 15 | 100,00 $ |

    $$
    WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100,00
    $$

    Le WAC est **dilué** car 5 unités sont entrées à coût zéro (ex: division d'actions, airdrop, don).

## 🔄 Forçage de la Base de Coût (Cost Basis Override)

Pour les transferts et les ajustements, LibreFolio prend en charge un **forçage de la base de coût** : un coût unitaire spécifié par l'utilisateur qui représente le coût historique des unités transférées.

**Quand il est défini (mode manuel) :**

- La transaction entre dans le calcul du WAC comme une acquisition pondérée normale
- Cela préserve la continuité des coûts entre les courtiers (ex: lors d'un transfert du courtier A vers le courtier B)

**Quand il n'est pas défini (aucun mode spécifié) :**

- La transaction entre avec `unit_cost = 0` (effet de dilution)
- Ceci est approprié pour les divisions d'actions, les dons ou les airdrops où il n'existe pas de prix d'achat

**Quand le mode auto est activé (`cost_basis_mode = "auto"`) :**

- La transaction entre au **WAC actuel du pool** — le WAC reste algébriquement inchangé
- Ceci est approprié pour les transferts ou les ajustements où la base de coût doit être héritée du pool du courtier source

$$
WAC_{new} = \frac{WAC \times Q_{pool} + WAC \times Q_{tx}}{Q_{pool} + Q_{tx}} = WAC
$$

!!! tip "Auto WAC dans l'interface"

    Dans le formulaire de transaction, l'interrupteur "Auto" utilise ce mode. Le tableau correspondant affiche le badge d'effet **Auto WAC** (ou **Auto PMC** en italien), indiquant que les unités sont entrées au coût actuel du pool sans modifier le WAC.

??? example "Exemple 4 : Transfert en mode Auto — WAC inchangé"

    | Date | Type | Qty | Coût Unitaire | Qty Pool | WAC |
    |------|------|-----|---------------|----------|-----|
    | 1 avr | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avr | ACHAT | 5 | 180 $ | 15 | 160,00 $ |
    | 1 mai | TRANSFERT (auto) | +3 | 160 $ (=WAC) | 18 | 160,00 $ |

    $$
    WAC = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160,00
    $$

    Le destinataire du transfert en **mode auto** hérite du WAC actuel comme coût unitaire. Le pool croît mais le WAC reste **inchangé**.

## 🌍 Gestion Multi-Devises

Lorsqu'un portefeuille contient des acquisitions dans différentes devises, LibreFolio :

1. Détermine la **devise cible** (la plus fréquente parmi les acquisitions)
2. Convertit tous les coûts unitaires dans la devise cible en utilisant les taux de change historiques
3. Calcule le WAC dans la devise cible unifiée

!!! warning "Disponibilité des taux de change"

    Si un taux de change requis est manquant, le calcul du WAC peut être incomplet. L'interface utilisateur avertit des paires de devises manquantes et propose des actions rapides pour les ajouter ou les synchroniser.

## 🎯 Utilisation du WAC dans LibreFolio

- **Formulaire de transfert** : suggère automatiquement le `cost_basis_override` pour les transferts sortants
- **Calcul du P&L** : gains réalisés = prix de vente − WAC (FIFO à l'exécution, WAC pour la base de coût)
- **Vue du portefeuille** : prix d'entrée moyen par position
