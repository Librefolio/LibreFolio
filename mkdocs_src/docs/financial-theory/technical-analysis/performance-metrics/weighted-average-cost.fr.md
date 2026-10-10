# 📊 Prix de Revient Unitaire (PRU)

## 💡 Qu'est-ce que le PRU ?

Le **prix de revient unitaire** (PRU) est le coût unitaire moyen d'un actif dans un portefeuille, pondéré par la quantité acquise à chaque prix.

Il répond à la question : _« En moyenne, combien ai-je payé par unité pour cet actif ? »_

!!! info "Autres noms"

    - **PMC** — Prezzo Medio di Carico (Italie)
    - **ACB** — Average Cost Basis (Canada, États-Unis)
    - **CMP** — Coût Moyen Pondéré (France)

## 🧮 Formule

Le PRU est calculé **de manière itérative** à mesure que chaque transaction est traitée chronologiquement :

$$
PRU_{new} = \frac{PRU_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Où :

- $PRU_{current}$ = prix de revient unitaire actuel avant cette transaction
- $Q_{pool}$ = quantité totale détenue dans le pool avant cette transaction
- $Cost_{unit}$ = coût d'acquisition unitaire de la nouvelle transaction — ce qui a été réellement payé, dans la devise dans laquelle le PRU est tenu, converti au taux de la date propre de la transaction (voir [Gestion multi-devises](#multi-currency-handling))
- $Q_{tx}$ = quantité ajoutée par la nouvelle transaction

De manière équivalente, LibreFolio conserve le coût total du pool $C_{pool}$ à côté de sa quantité, avec $PRU = C_{pool} / Q_{pool}$ : une acquisition ajoute son coût, une réduction de $q$ unités retire $C_{pool} \cdot q / Q_{pool}$.

## ⚙️ Comment LibreFolio calcule le PRU

LibreFolio utilise un **algorithme itératif prenant en compte l'inventaire** qui traite toutes les transactions éligibles pour un couple (courtier, actif) donné dans l'ordre chronologique. Le même algorithme sert à chaque écran qui affiche un coût moyen : le Tableau de bord, le tableau des positions, l'analyse des lots et l'aperçu de la transaction.

### 🏷️ Effets des transactions

Chaque transaction contribue au calcul du PRU d'une des manières suivantes :

| Effet | Condition | Impact sur le PRU |
|--------|-----------|---------------|
| **Pondéré** | `qty > 0` avec un coût connu supérieur à zéro | Le PRU évolue vers le nouveau coût d'acquisition |
| **Quantité réduite** | `qty < 0` | Sorties au PRU actuel — PRU inchangé, le pool diminue |
| **Dilution** | `qty > 0` à coût nul | Le pool augmente, numérateur inchangé → le PRU **diminue** |
| **Division** | Ajustement lié à un événement de division | Quantité redimensionnée, coût total inchangé → PRU divisé par le ratio de division |
| **Coût inconnu** | `qty > 0` avec aucun coût connu : un transfert ou un ajustement sans remplacement du coût de base | Le pool augmente sans coût — le PRU est **incomplet** (voir [Remplacement du coût de base](#cost-basis-override)) |

### 📅 Ordre des transactions le même jour

Lorsque plusieurs transactions ont lieu à la même date :

1. **Ajouts d'abord** (qty > 0) — traités avant les réductions
2. **Réductions ensuite** (qty < 0) — garantit que le pool ne devienne pas temporairement négatif

### 🔻 Épuisement du pool

- Lorsque la quantité atteint 0, la dernière réduction emporte **tout** le coût restant, ainsi le coût total est conservé exactement ; le pool repart de zéro, et un achat ultérieur ouvre un nouveau pool complet
- Une réduction supérieure au pool est plafonnée à la quantité disponible

## 📝 Exemples pratiques

??? example "Exemple 1 : Deux achats — le PRU augmente"

    | Date | Type | Qté | Coût unitaire | Qté du pool | PRU |
    |------|------|-----|-----------|----------|-----|
    | 1 avr. | Achat | 10 | $150 | 10 | $150.00 |
    | 15 avr. | Achat | 5 | $180 | 15 | $160.00 |

    $$
    PRU = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
    $$

    Le deuxième achat à un prix plus élevé **tire le PRU vers le haut**.

??? example "Exemple 2 : Achat puis vente — PRU inchangé"

    | Date | Type | Qté | Coût unitaire | Qté du pool | PRU |
    |------|------|-----|-----------|----------|-----|
    | 1 avr. | Achat | 10 | $150 | 10 | $150.00 |
    | 15 avr. | Vente | -5 | (au PRU) | 5 | $150.00 |

    La vente retire des unités au PRU actuel ($150). Le PRU reste **inchangé** — seul le pool diminue.

??? example "Exemple 3 : Acquisition à coût nul — Dilution"

    | Date | Type | Qté | Coût unitaire | Qté du pool | PRU |
    |------|------|-----|-----------|----------|-----|
    | 1 avr. | Achat | 10 | $150 | 10 | $150.00 |
    | 1 mai | Ajustement | +5 | $0 | 15 | $100.00 |

    $$
    PRU = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
    $$

    Le PRU est **dilué** parce que 5 unités sont entrées à coût nul — un ajustement dont le remplacement du coût de base est zéro, comme un airdrop. Une division 3 pour 2 liée à son événement de division atteint les mêmes $100.00 sans aucune acquisition : le pool conserve ses $1,500 et les répartit sur 15 unités.

## 🔄 Remplacement du coût de base {: #cost-basis-override }

Pour les transferts et les ajustements, LibreFolio prend en charge un **remplacement du coût de base** : un coût unitaire, dans une devise de votre choix, qui représente le coût historique des unités entrantes. Un transfert ou un ajustement qui ajoute de la quantité en a besoin : le formulaire de transaction l'exige.

**Lorsqu'il est défini (mode manuel) :**

- La transaction entre dans le calcul du PRU comme une acquisition pondérée normale coûtant $\text{remplacement} \times Q_{tx}$, convertie à la date de la transaction comme tout achat
- Cela préserve la continuité du coût entre courtiers (par ex., lors d'un transfert du courtier A vers le courtier B)
- Un remplacement de **zéro** est une acquisition gratuite : la dilution de l'exemple 3

**Lorsqu'il est absent :**

- Le coût de ces unités est **inconnu**, pas zéro : elles entrent dans le pool sans aucun coût, et le PRU reste incomplet jusqu'à la clôture de la position
- Le Tableau de bord affiche le coût moyen et le P&L latent de cette position comme indisponibles et avertit à propos du coût de base manquant ; l'aperçu de la transaction compte les unités à zéro (dilution)

**En mode auto (`cost_basis_mode = "auto"`) :**

- LibreFolio calcule le PRU de la position source — pour un transfert, la position du courtier émetteur lorsque les unités sont parties (la date de transfert sortant), avant la jambe sortante ; pour un ajustement, la position elle-même à la date de la transaction, sans cette transaction — et la stocke comme remplacement
- À partir de là, la transaction est une acquisition pondérée ordinaire à ce coût unitaire. Pour un ajustement sur la même position, le PRU reste donc algébriquement inchangé, dans la devise dans laquelle il a été calculé :

$$
PRU_{new} = \frac{PRU \times Q_{pool} + PRU \times Q_{tx}}{Q_{pool} + Q_{tx}} = PRU
$$

!!! tip "Mode auto dans l'interface"

    Dans le formulaire de transaction, l’interrupteur **Auto** calcule la valeur lorsque vous validez : l’aperçu affiche le PRU suggéré et les transactions dont il provient, chacune avec son effet.

??? example "Exemple 4 : Transfert en mode auto — le coût suit les unités"

    Le courtier A détient le pool de l'exemple 1 et envoie 3 unités au courtier B, qui n'en détenait aucune :

    | Courtier | Date | Type | Qté | Coût unitaire | Qté du pool | PRU |
    |--------|------|------|-----|-----------|----------|-----|
    | A | 1 avr. | Achat | 10 | $150 | 10 | $150.00 |
    | A | 15 avr. | Achat | 5 | $180 | 15 | $160.00 |
    | A | 1 mai | Transfert sortant | −3 | (au PRU) | 12 | $160.00 |
    | B | 1 mai | Transfert entrant (auto) | +3 | $160 (PRU de A) | 3 | $160.00 |

    En **mode auto**, le côté récepteur prend le PRU de l'émetteur comme remplacement du coût de base : le courtier B démarre à la moyenne du courtier A, et les $480 de coût se déplacent avec les 3 unités.

## 🌍 Gestion multi-devises {: #multi-currency-handling }

Le PRU est tenu dans une seule devise, la **devise cible** $T$, et chaque acquisition y entre à son **coût historique** : le montant réellement payé, converti au taux de la date propre de l'acquisition $d_i$ :

$$
c_i^{T} = P_i \cdot \mathrm{fx}\bigl(\mathrm{ccy}(P_i),\, T,\, d_i\bigr), \qquad \mathrm{fx}(T, T, d) = 1
$$

Ici, $P_i$ est la somme payée pour un achat, dans sa devise de paiement, ou $\text{remplacement} \times Q_{tx}$ dans la devise du remplacement pour un transfert ou un ajustement. Un montant déjà en $T$ n'a besoin d'aucun taux ; sinon, lorsque la date exacte n'a pas de taux, le dernier taux avant celle-ci est utilisé.

Le coût de base d'une position est alors

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \times \mathrm{PRU}^{T}(a,b,t)
$$

avec **aucun taux de change à $t$** : c'est ce qui a été payé, et cela ne bouge pas lorsque les taux de change bougent. Pour un actif valorisé dans une autre devise, l'effet de change se situe donc dans la plus-value/moins-value latente — valeur de marché au taux du jour moins coût historique — où le Tableau de bord l'isole (voir [P&L période](portfolio-engine/period-pnl.md#unrealized-change-by-currency)).

La devise cible dépend de l'endroit où le PRU est affiché :

| Où | Devise cible $T$ |
|-------|---------------------|
| Tableau de bord, tableau des positions, ventes réalisées, Rendement sur coût | La devise d'affichage (du rapport) |
| Lignes de PRU de l'analyse des lots | La devise de l'analyse |
| Aperçu de transaction, coût de base automatique, série PRU (`POST /portfolio/wac`) | La devise choisie dans l'aperçu, sinon la devise de la **dernière acquisition** |
| Planificateur PAC | La devise du planificateur |

La devise de la dernière acquisition est la devise payée par la transaction la plus récente qui a ajouté de la quantité — une règle déterministe ; en cas d'égalité, la première enregistrée gagne. Une division, ou une acquisition de coût inconnu, revient à la devise propre de l'actif.

??? example "Exemple 5 : Un actif en dollars acheté avec des euros, devise d'affichage EUR"

    | Date | Type | Qté | Payé | Taux USD→EUR | Coût en EUR |
    |------|------|-----|------|--------------|-------------|
    | 1 avr. | Achat | 10 | 400 € | — (payé en EUR) | 400,00 € |
    | 1 mai | Achat | 5 | 300 USD | 0,90 | 270,00 € |

    $$
    PRU^{EUR} = \frac{400 + 270}{10 + 5} = \frac{670}{15} \approx 44,67 \text{ EUR}
    $$

    Le premier achat n'a pas besoin de taux : son coût est exactement les 400 € payés. Le coût de base de la position reste 670 € quoi que fasse le dollar ensuite ; un dollar plus faible diminue la valeur de marché en euros et apparaît comme une moins-value latente.

!!! warning "Disponibilité du taux de change"

    Lorsqu'aucun taux n'existe à la date d'une acquisition ou avant celle-ci, LibreFolio ne compte jamais ce coût comme zéro. Les unités entrent dans le pool sans leur coût et le PRU est marqué comme incomplet : l'aperçu de la transaction n'affiche aucun PRU et liste la paire manquante avec ses dates, le Tableau de bord affiche le coût moyen et le P&L latent de la position comme indisponibles, et l'analyse des lots exclut ces jours de ses lignes de PRU. L'interface avertit à propos des paires FX manquantes et fournit des actions rapides pour les ajouter ou les synchroniser.

## 🎯 Où le PRU est utilisé dans LibreFolio

- **Coût de base** : $\text{CB}(a,b,t) = q(a,b,t) \times \text{PRU}^{T}(a,b,t)$, historique, sans conversion à $t$
- **P&L réalisé sur vente** : $\text{réalisé} = P_{\text{vente}} - q_{\text{vendues}} \times \text{PRU}^{T}_{\text{avant-vente}}$, avec le produit $P_{\text{vente}}$ converti à la date de vente et les unités vendues sortant à leur coût historique
- **Décomposition du pool de trésorerie** : la vente retourne $C = q_{\text{vendues}} \times \text{PRU}^{T}_{\text{avant-vente}}$ au pool de capital
- **Rendement sur coût** : le prix d'achat moyen du dénominateur du [Rendement sur coût](portfolio-engine/yield-on-cost.md)
- **Formulaire de transfert** : suggère automatiquement le cost_basis_override du côté récepteur à partir du PRU de la position émettrice

!!! warning "Le PRU n'est jamais utilisé pour l'évaluation d'un actif"

    Le PRU est une construction comptable destinée au coût de base. La valeur de marché utilise les niveaux unifiés du résolveur : `MARKET → TRADE_AVG → CARRIED → MISSING`, exposés aux lignes de portefeuille sous la forme `MARKET_PRICE`, `LAST_TRADE_PRICE` ou `MISSING`. Voir [Résolution des prix](portfolio-engine/price-resolution.md).

## ⚙️ Implémentation : portée au niveau de la position

Le PRU est maintenu **par position** $(a, b)$ — c.-à-d. par couple (actif, courtier). Le même actif détenu chez deux courtiers a deux pools PRU indépendants.

$$
\text{PRU}(a, b_1, t) \neq \text{PRU}(a, b_2, t) \quad \text{en général}
$$

Le coût moyen de chaque position dans un rapport est calculé **une seule fois, avant le rejeu quotidien**, avec toutes les conversions nécessaires regroupées dans une seule requête au service FX ; le rejeu quotidien suit ensuite le pool de chaque position étape par étape au lieu de le recalculer, et ne convertit jamais un coût lui-même.

### 📅 Ordre des transactions le même jour

Au sein d'une même date, **les ajouts sont traités avant les réductions** :

$$
\text{ACHAT}_1, \text{ACHAT}_2, \ldots \quad \text{puis} \quad \text{VENTE}_1, \text{VENTE}_2, \ldots
$$

Cela évite les quantités négatives transitoires et garantit que la vente lit toujours le PRU correct qui inclut les achats du même jour.

## 🔗 Voir aussi

- 🔬 **[Analyse des lots FIFO](fifo-engine/fifo-lot-analysis.md)** — Complément par lot : suit chaque lot d'acquisition individuellement au lieu de les fusionner en une moyenne unique
- 🔁 **[Achat et vente](../../instruments/transaction-types/buy-sell.md)** — Transactions qui alimentent le pool PRU
- 📈 **[NAV / Valeur nette](portfolio-engine/nav.md)** — En quoi la valeur comptable basée sur le PRU diffère de la NAV au prix de marché
- 📖 **[Valeur comptable](portfolio-engine/book-value.md)** — Coût de base ouvert : la somme des coûts historiques
- ⚖️ **[PRU et coût de base (Manuel développeur)](../../../developer/backend/transactions/wac.md)** — L'unique implémentation du coût moyen et ses appelants
