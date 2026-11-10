# 🧮 ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Ajustement

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-adjustment" alt="Formulaire de transaction — Ajustement">
</div>

Les **ajustements** sont des corrections autonomes de quantité d'actifs. Ils sont sans flux de trésorerie dans le schéma de transaction livré : la quantité change, la trésorerie non. Contrairement aux types appariés (Transfert d'actif, Virement, Conversion FX), chaque ajustement est une ligne unique et indépendante.

---

## 🔑 Propriétés clés

| Propriété | Valeur |
|----------|-------|
| **Code** | `ADJUSTMENT` |
| **Effet sur la trésorerie** | Aucun — `ADJUSTMENT` est sans flux de trésorerie |
| **Effet sur l'actif** | Requis (± toute quantité) |
| **Événement fiscal** | Non |

---

## 📊 Cas d'usage

Les ajustements sont utilisés lorsqu'aucun autre type de transaction ne convient :

- **Correction d'erreurs d'importation** — par ex. un import de courtier a manqué une opération sur titres
- **Division / regroupement d'actions** — ajuster la quantité sans mouvement de trésorerie
- **Dons** — recevoir ou donner des actions
- **Positions héritées ou issues d'une succession** — les titres arrivent en nature, sans mouvement de trésorerie chez le courtier
- **Configuration du solde initial** — initialiser un portefeuille à partir d'un instantané
- **Opérations sur titres** non couvertes par d'autres types (scissions, fusions, etc.)

Exemples importés : les instantanés `patrimonio` d'Intesa Sanpaolo utilisent des `ADJUSTMENT` positifs pour initialiser des positions existantes avec un `cost_basis_override` par unité ; les lignes de succession de Crédit Agricole (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) sont également modélisées comme des `ADJUSTMENT` positifs sans flux de trésorerie, et non comme des `TRANSFER` appariés, car le dossier source est extérieur à LibreFolio.

!!! note "Promouvoir en transfert"

    Deux lignes `ADJUSTMENT` avec des **quantités opposées**, le **même actif** et des **courtiers différents** peuvent être **promues** en une paire de transferts d'actif. C'est utile lorsque vous avez d'abord enregistré des ajustements séparés et que vous souhaitez ensuite les lier comme un transfert. Aucune des deux lignes ne peut être liée à un événement d'actif, une division par exemple : un transfert ne peut pas porter ce lien, LibreFolio ne suggère donc ni n'accepte une telle promotion.

---

## 📐 Impact sur le coût de base

Les ajustements à quantité positive **augmentent** le nombre de lots (FIFO). Le coût de base
des lots créés par ajustement dépend de la présence ou non d'un **Override du coût de base** :

- **Avec override** : la valeur spécifiée est utilisée comme **coût d'acquisition unitaire** (PRU — prix de revient unitaire), dans la devise du coût de base, qui est aussi la devise du lot FIFO ouvert par l'ajustement (et non la devise de la ligne elle-même, souvent vide puisqu'un ajustement ne déplace aucune trésorerie) ; un override de **zéro** enregistre une acquisition gratuite, comme un airdrop
- **Sans override** : le lot FIFO s'ouvre à coût nul, mais le prix de revient unitaire (PRU) traite le coût comme **inconnu**, et non comme gratuit : les unités rejoignent la position sans coût, son PRU reste incomplet jusqu'à la clôture de la position, le tableau de bord affiche son PRU et son P&L latent comme indisponibles, et un avertissement de qualité des données nomme l'actif (voir [Override du coût de base](../../technical-analysis/performance-metrics/weighted-average-cost.md#cost-basis-override))

Un ajustement positif ne peut pas être enregistré sans coût de base : saisissez-en un, ou choisissez **Auto**, qui enregistre le PRU de la position que les unités rejoignent (zéro si elle n'en détient encore aucun). Deux types de lignes peuvent toutefois en être dépourvues : un ajustement lié à une **division**, qu'Auto enregistre sans coût de base car la division conserve le coût déjà détenu et le répartit sur la nouvelle quantité, et les lignes enregistrées avant que le coût de base ne devienne obligatoire.

!!! info "Valeur unitaire"

    L'Override du coût de base est le coût moyen **par unité** de l'actif.
    Pour obtenir le coût total du bloc transféré, multipliez par la quantité :

    $$\text{Coût total} = \text{PRU} \times \text{quantité}$$

### 📤 Ajustements sortants {: #outgoing-adjustments }

Les ajustements à quantité négative **diminuent** la position : unités données, envoyées vers un compte que LibreFolio ne suit pas, ou retirées par une correction. Un tel ajustement **n'a pas de valeur** — il ne fait que réduire la quantité — il ne prend donc aucun **Override du coût de base** :

- **Capital et rendements** : aucun capital ne sort, l'ajustement n'est donc pas un flux pour la [base de capital](../../technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#outgoing-adjustments), le TWRR ou le MWRR : la valeur des unités quitte la NAV, et les rendements l'interprètent comme une perte.
- **Coût moyen** : la position abandonne le coût moyen de ces unités, le prix de revient unitaire (PRU) de ce qui reste ne change donc pas.
- **Réalisé** : les unités sortent à **zéro**, l'ajustement réalise donc un montant négatif égal à leur coût, soit $-q \times \text{AverageCost}$ sur le tableau de bord. Les lots FIFO consomment les lots ouverts du courtier du plus ancien au plus récent, comme lors d'une vente, et les clôturent à zéro : $q$ unités prélevées sur un lot réalisent $-q \times \text{LotUnitCost}$, sans produit de cession.

Pour enregistrer des unités cédées contre de l'argent, utilisez une **Vente**. L'API refuse un coût de base sur un ajustement sortant (`costBasisNotAllowed`) ; un coût de base stocké sur une telle ligne par une version antérieure reste en base mais est ignoré. Un ajustement lié à une **division** fait exception : la division ne fait que répartir le coût déjà détenu sur la nouvelle quantité et ne réalise rien.

!!! example "Deux actions données"

    Tous les montants sont dans la devise du rapport. Achat de 10 actions à 50 (500 investis) ; le cours monte à 80, la position vaut donc 800 et son P&L total est de $800 - 500 = +300$. Un ajustement de −2 actions en donne deux :

    - il reste 8 actions, valant $8 \times 80 = 640$ ; le capital investi reste 500 et le coût moyen 50 ;
    - réalisé : $0 - 2 \times 50 = -100$ ; latent : $8 \times (80 - 50) = +240$ ;
    - P&L total : $640 - 500 = +140$, soit $-100 + 240$ ;
    - le TWRR du jour : $640 / 800 - 1 = -20\%$, puisqu'aucun flux ne compense la valeur sortie.

### 🏦 Coût de base automatique sur les transferts et les initialisations

Lors d'un transfert d'actif entre courtiers, LibreFolio **calcule automatiquement** l'Override du coût de base côté réception en utilisant le **prix de revient unitaire (PRU)** de la position du courtier source. Les lignes d'amorçage issues d'un import de courtier peuvent quant à elles le définir directement à partir du rapport source. La valeur est toujours **unitaire**, et non la valeur totale de la position ; pour un instantané dont la valeur fiscale totale est \(C\) et la quantité \(q\), les plugins stockent :

$$\text{Override du coût de base} = \frac{C}{q}$$

Cela enregistre du capital en nature, et non du P&L : l'ajustement crée/modifie des lots mais ne crée ni apport de trésorerie ni plus-value réalisée.

!!! tip "En savoir plus"

    Pour la formule complète, des exemples et les cas limites, consultez la page dédiée :
    **[📊 Prix de revient unitaire (PRU)](../../technical-analysis/performance-metrics/weighted-average-cost.md)**

??? note "✏️ Quand forcer manuellement"

    La formule automatique convient au cas standard (même régime fiscal, aucun événement fiscal
    lors du transfert). Dans les scénarios suivants, l'utilisateur doit définir la valeur manuellement :

    | Scénario | Quoi définir |
    |----------|------------|
    | **Transfert normal** | Laissez le coût sur **Auto** — calculé à partir de vos achats |
    | **Exit Tax** | Valeur de marché à la date du transfert (selon la juridiction) |
    | **Héritage** | Juste valeur de marché à la date du décès (ou base réévaluée) |
    | **Don** | Coût de base d'origine du donateur (base reportée) |
    | **Opération sur titres** | Base ajustée selon les termes de l'opération sur titres |

    !!! warning "Responsabilité de l'utilisateur"

        Lorsqu'il force manuellement le coût de base, l'utilisateur est responsable de
        l'exactitude de la valeur. LibreFolio ne valide pas les montants de l'override
        au regard des règles fiscales — consultez un conseiller fiscal pour les spécificités de votre juridiction.

---

## 🔗 Voir aussi

- 📊 **[Prix de revient unitaire (PRU)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Comment le coût de base automatique est calculé
- 🔄 **[Transfert d'actif](transfer.md)** — Deux ajustements liés peuvent être promus en transfert
- 🛒 **[Achat & Vente](buy-sell.md)** — Transactions d'actifs standard avec trésorerie
- 💰 **[Frais & Impôt](fee.md)** — Corrections portant uniquement sur la trésorerie (utilisez Frais/Impôt plutôt qu'un ajustement)
