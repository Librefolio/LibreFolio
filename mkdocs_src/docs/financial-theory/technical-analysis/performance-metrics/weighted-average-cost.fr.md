# 📊 Prix Moyen Pondéré (PMP)

## 💡 Qu'est-ce que le PMP ?

Le **Prix Moyen Pondéré** (PMP) est le coût unitaire moyen d'un actif dans un portefeuille, pondéré par la quantité acquise à chaque prix.

Il répond à la question : _"En moyenne, combien ai-je payé par unité pour cet actif ?"_

!!! info "Autres noms"

    - **PMC** — Prezzo Medio di Carico (Italie)
    - **ACB** — Average Cost Basis (Canada, États-Unis)
    - **PMP** — Prix Moyen Pondéré (France)

## 🧮 Formule

Le PMP est calculé de manière **itérative** à mesure que chaque transaction est traitée chronologiquement :

$$
PMP_{\text{nouveau}} = \frac{PMP_{\text{actuel}} \times Q_{\text{pool}} + Coût_{\text{unit}} \times Q_{\text{tx}}}{Q_{\text{pool}} + Q_{\text{tx}}}
$$

Où :

- $PMP_{\text{actuel}}$ = prix moyen pondéré actuel avant cette transaction
- $Q_{\text{pool}}$ = quantité totale détenue dans le pool avant cette transaction
- $Coût_{\text{unit}}$ = coût d'acquisition unitaire de la nouvelle transaction
- $Q_{\text{tx}}$ = quantité ajoutée par la nouvelle transaction

## ⚙️ Comment LibreFolio calcule le PMP

LibreFolio utilise un **algorithme itératif tenant compte de l'inventaire** qui traite toutes les transactions éligibles pour un couple (courtier, actif) donné dans l'ordre chronologique.

### 🏷️ Effets des transactions

Chaque transaction contribue au calcul du PMP de l'une des manières suivantes :

| Effet | Condition | Impact sur le PMP |
|--------|-----------|---------------|
| **Pondéré** | `qty > 0` et `unit_cost > 0` | Le PMP évolue vers le nouveau coût d'acquisition |
| **Quantité réduite** | `qty < 0` | Sortie au PMP actuel — PMP inchangé, le pool diminue |
| **Dilution** | `qty > 0` mais `unit_cost = 0` | Le pool augmente, le numérateur reste inchangé → le PMP **diminue** |
| **PMP Auto** | `qty > 0`, `cost_basis_mode = "auto"` | Pool inchangé — les unités entrent au PMP actuel |

### 📅 Ordonnancement du même jour

Lorsque plusieurs transactions ont lieu à la même date :

1. **Ajouts en premier** (qty > 0) — traités avant les réductions
2. **Réductions en second** (qty < 0) — garantit que le pool ne devienne pas transitoirement négatif

### 🔻 Épuisement du pool

- Quand `new_qty = 0` : le PMP est réinitialisé à 0 (position clôturée)
- Quand `new_qty < 0` (cas limite d'arrondi) : ramené à 0

## 📝 Exemples pratiques

??? example "Exemple 1 : Deux achats — le PMP augmente"

    | Date | Type | Qté | Coût Unitaire | Qté Pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1 avr | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avr | ACHAT | 5 | 180 $ | 15 | 160,00 $ |

    $$
    PMP = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160,00
    $$

    Le second achat à un prix plus élevé **tire le PMP vers le haut**.

??? example "Exemple 2 : Achat puis Vente — PMP inchangé"

    | Date | Type | Qté | Coût Unitaire | Qté Pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1 avr | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avr | VENTE | -5 | (au PMP) | 5 | 150,00 $ |

    La VENTE retire des unités au PMP actuel (150 $). Le PMP reste **inchangé** — seul le pool diminue.

??? example "Exemple 3 : Acquisition à coût zéro — Dilution"

    | Date | Type | Qté | Coût Unitaire | Qté Pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1 avr | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 1 mai | AJUSTEMENT | +5 | 0 $ | 15 | 100,00 $ |

    $$
    PMP = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100,00
    $$

    Le PMP est **dilué** car 5 unités sont entrées à un coût nul (ex: division d'actions, airdrop, cadeau).

## 🔄 Surcharge de la base de coût

Pour les transferts et les ajustements, LibreFolio prend en charge une **surcharge de la base de coût** (cost basis override) : un coût unitaire spécifié par l'utilisateur représentant le coût historique des unités transférées.

**Lorsqu'il est défini (mode manuel) :**

- La transaction entre dans le calcul du PMP comme une acquisition pondérée normale
- Cela préserve la continuité du coût entre les courtiers (ex: lors d'un transfert du courtier A vers le courtier B)

**Lorsqu'il n'est pas défini (aucun mode spécifié) :**

- La transaction entre avec `unit_cost = 0` (effet de dilution)
- Ceci est approprié pour les divisions d'actions, les cadeaux ou les airdrops où aucun prix d'achat n'existe

**En mode auto (`cost_basis_mode = "auto"`) :**

- La transaction entre au **PMP actuel du pool** — le PMP reste algébriquement inchangé
- Ceci est approprié pour les transferts ou ajustements où la base de coût doit être héritée du pool du courtier source

$$
PMP_{\text{nouveau}} = \frac{PMP \times Q_{\text{pool}} + PMP \times Q_{\text{tx}}}{Q_{\text{pool}} + Q_{\text{tx}}} = PMP
$$

!!! tip "PMP Auto dans l'interface"

    Dans le formulaire de transaction, l'interrupteur "Auto" utilise ce mode. Le tableau des transactions éligibles affiche le badge d'effet **Auto PMP** (en français, **Auto WAC** en anglais), indiquant que les unités sont entrées au coût actuel du pool sans modifier le PMP.

??? example "Exemple 4 : Transfert en mode Auto — PMP inchangé"

    | Date | Type | Qté | Coût Unitaire | Qté Pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1 avr | ACHAT | 10 | 150 $ | 10 | 150,00 $ |
    | 15 avr | ACHAT | 5 | 180 $ | 15 | 160,00 $ |
    | 1 mai | TRANSFERT (auto) | +3 | 160 $ (=PMP) | 18 | 160,00 $ |

    $$
    PMP = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160,00
    $$

    Le destinataire du transfert en **mode auto** hérite du PMP actuel comme coût unitaire. Le pool augmente mais le PMP reste **inchangé**.

## 🌍 Gestion multi-devises

Lorsqu'un portefeuille contient des acquisitions dans différentes devises, LibreFolio :

1. Détermine la **devise cible** (la plus fréquente parmi les acquisitions)
2. Convertit tous les coûts unitaires dans la devise cible en utilisant les taux de change historiques (FX)
3. Calcule le PMP dans la devise cible unifiée

!!! warning "Disponibilité des taux FX"

    Si un taux FX requis est manquant, le calcul du PMP peut être incomplet. L'interface avertit en cas de paires FX manquantes et propose des actions rapides pour les ajouter ou les synchroniser.

## 🎯 Où le PMP est utilisé dans LibreFolio

- **Base de coût** : $\text{CB}(a,b,t) = q(a,b,t) \times \text{PMP}(a,b,t) \times \text{fx}(\cdot)$
- **P&L réalisé sur la VENTE** : $\text{réalisé} = P_{\text{vente}} - q_{\text{vendue}} \times \text{PMP}_{\text{pré-vente}}$
- **Décomposition du pool de liquidités** : la VENTE renvoie $C = q_{\text{vendue}} \times \text{PMP}$ au Pool de Capital
- **Formulaire de transfert** : suggère automatiquement le `cost_basis_override` pour les transferts sortants

!!! warning "Le PMP n'est jamais utilisé pour la valorisation des actifs"

    Le PMP est une construction comptable pour la base de coût. La chaîne de valorisation pour la valeur de marché utilise : `MARKET_PRICE → LAST_BUY_PRICE → MISSING`. Voir [NAV](nav.md).

## ⚙️ Implémentation : Portée au Niveau de la Position

Le PMP est maintenu **par position** $(a, b)$ — c'est-à-dire par paire (actif, courtier). Le même actif détenu chez deux courtiers a deux pools PMP indépendants.

$$
\text{PMP}(a, b_1, t) \neq \text{PMP}(a, b_2, t) \quad \text{en général}
$$

Le moteur calcule le PMP inline pendant la boucle quotidienne des transactions — aucune requête de base de données distincte n'est nécessaire. Cela permet d'obtenir un coût amorti de O(1) par transaction au lieu du coût O(N) de ré-interroger l'historique complet.

### Ordre des transactions le même jour

Au cours de la même date, **les ajouts (achats) sont traités avant les réductions (ventes)** :

$$
\text{ACHAT}_1, \text{ACHAT}_2, \ldots \quad \text{puis} \quad \text{VENTE}_1, \text{VENTE}_2, \ldots
$$

Cela évite les quantités négatives transitoires et garantit que la VENTE lit toujours le PMP correct qui inclut les ACHATS du même jour.
