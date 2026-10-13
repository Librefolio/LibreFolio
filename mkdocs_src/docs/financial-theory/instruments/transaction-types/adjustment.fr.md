# 🧮 ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Ajustement

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-adjustment" alt="Formulaire de transaction — Ajustement">
</div>

Les **ajustements** sont des corrections autonomes de la quantité d'un actif. Dans le schéma des transactions, ils ne déplacent pas de trésorerie : la quantité change, la trésorerie non. Contrairement aux types appairés (Transfert, Virement, Conversion FX), chaque ajustement constitue une ligne unique et indépendante.

---

## 🔑 Propriétés clés

| Propriété | Valeur |
|----------|-------|
| **Code** | `ADJUSTMENT` |
| **Effet trésorerie** | Aucun — `ADJUSTMENT` ne déplace pas de trésorerie |
| **Effet actif** | Requis (± toute quantité) |
| **Événement fiscal** | Non |

---

## 📊 Cas d'utilisation

Les ajustements sont utilisés lorsqu'aucun autre type de transaction ne convient :

- **Correction d'erreurs d'importation** — par exemple, un import de courtier ayant omis une opération sur titres
- **Divisions / divisions inverses d'actions** — ajuster la quantité sans mouvement de trésorerie
- **Dons** — réception ou don d'actions
- **Héritages ou successions** — les titres arrivent en nature, sans mouvement de trésorerie chez le courtier
- **Configuration du solde initial** — amorçage d'un portefeuille à partir d'un instantané (snapshot)
- **Opérations sur titres** non couvertes par d'autres types (scissions/spinoffs, fusions, etc.)

Exemples issus des imports : les instantanés `patrimonio` d'Intesa Sanpaolo utilisent des `ADJUSTMENT` positifs pour amorcer les positions existantes avec un `cost_basis_override` unitaire ; les lignes de succession du Crédit Agricole (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) sont elles aussi modélisées comme des `ADJUSTMENT` positifs sans trésorerie, et non comme des paires de `TRANSFER`, car le dossier source est en dehors de LibreFolio.

!!! note "Promouvoir en Transfert"

    Deux lignes `ADJUSTMENT` avec des **quantités opposées**, le **même actif** et des **courtiers différents** peuvent être **promues** en une paire de Transfert d'actifs. Ceci est utile lorsque vous avez initialement enregistré des ajustements séparés et que vous souhaitez ultérieurement les lier comme un transfert. Aucune des deux lignes ne peut être liée à un événement d'actif, une division par exemple : un transfert ne peut pas porter ce lien, donc LibreFolio ne suggère ni n'accepte une telle promotion.

---

## 📐 Impact sur le prix de revient

Les ajustements avec une quantité positive **augmentent** le nombre de lots (FIFO). Le prix de revient pour les lots créés par ajustement dépend de la présence d'un **Forçage du coût de base (Cost Basis Override)** :

- **Avec forçage** : la valeur spécifiée est utilisée comme **coût d'acquisition unitaire** (Prix de Revient Unitaire — PRU) ; un forçage à **zéro** enregistre une acquisition gratuite, comme un airdrop
- **Sans forçage** : le lot FIFO s'ouvre à un coût nul, mais le coût moyen (PRU) traite le coût comme **inconnu**, et non gratuit : les unités rejoignent la position sans coût, son PRU reste incomplet jusqu'à la clôture de la position, le Tableau de bord affiche son coût moyen et son P&L latent comme indisponibles, et un avertissement de qualité des données nomme l'actif (voir [Remplacement du coût de base](../../technical-analysis/performance-metrics/weighted-average-cost.md#cost-basis-override))

Un ajustement positif ne peut pas être enregistré sans coût de base : saisissez-en un, ou choisissez **Auto**, qui enregistre le coût moyen de la position que rejoignent les unités (zéro si elle n'en contient pas encore). Deux types de lignes peuvent encore en être dépourvues : un ajustement lié à une **division**, qu'Auto enregistre sans coût de base parce que la division conserve le coût déjà détenu et le répartit sur la nouvelle quantité, et les lignes enregistrées avant que le coût de base ne devienne obligatoire.

!!! info "Valeur unitaire"

    Le Forçage du coût de base correspond au coût moyen **par unité** de l'actif.
    Pour obtenir le coût total du bloc transféré, multipliez par la quantité :

    $$\text{Coût total} = \text{PRU} \times \text{quantité}$$

### 🏦 Coût de base automatique sur les transferts et les amorçages

Lors du transfert d'actifs entre courtiers, LibreFolio **calcule automatiquement** le Forçage du coût de base du côté destinataire en utilisant le **Prix de Revient Unitaire (PRU)** de la position du courtier source. Les amorçages issus d'un import de courtier peuvent aussi le fixer directement à partir du relevé source. La valeur est toujours **unitaire**, et non la valeur totale de la position ; pour un instantané de valeur fiscale totale \(C\) et de quantité \(q\), les plugins enregistrent :

$$\text{Forçage du coût de base} = \frac{C}{q}$$

Cela enregistre un capital en nature, pas un P&L : l'ajustement crée ou modifie des lots, mais ne crée ni apport de trésorerie ni gain réalisé.


!!! tip "En savoir plus"

    Pour la formule complète, des exemples et les cas particuliers, consultez la page dédiée :
    **[📊 Prix de Revient Unitaire (PRU)](../../technical-analysis/performance-metrics/weighted-average-cost.md)**

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

- 📊 **[Prix de Revient Unitaire (PRU)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Comment le prix de revient automatique est calculé
- 🔄 **[Transfert d'actifs](transfer.md)** — Deux ajustements liés peuvent être promus en transfert
- 🛒 **[Achat & Vente](buy-sell.md)** — Transactions d'actifs standard avec trésorerie
- 💰 **[Frais & impôts](fee.md)** — Corrections uniquement de trésorerie (utilisez Frais/Impôts au lieu d'Ajustement)