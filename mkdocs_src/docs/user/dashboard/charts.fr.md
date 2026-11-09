# 📊 Graphiques

Sous les cartes KPI, le graphique **Croissance du portefeuille** et le panneau **Allocation des actifs** montrent l'historique de votre portefeuille et sa composition. Tous deux suivent la plage temporelle et le filtre de courtier du tableau de bord, et la page d'un courtier les affiche pour ce courtier uniquement.

---

## 📈 Graphique de croissance du portefeuille {: #portfolio-growth-chart }

Le graphique de croissance montre l'évolution de votre portefeuille sur la période sélectionnée : le sélecteur **Abs / % / P&L** dans son coin supérieur droit bascule entre les valeurs absolues, les taux de rendement et l'argent réellement gagné.

Sur une longue période, le graphique regroupe les jours pour rester lisible : en semaines, puis en mois et, pour un historique de plusieurs décennies, en années. Un badge **Hebdomadaire**, **Mensuel** ou **Annuel** en haut à gauche du graphique indique le regroupement appliqué. Lorsque rien n'est regroupé, aucun badge n'apparaît.

### 〰️ Comment les lignes sont tracées {: #line-shape }

Chaque graphique relie ses points selon l'une de trois formes : **Segments** (par défaut, une ligne droite entre deux points), **Marches** (chaque valeur se maintient jusqu'à la suivante) ou **Courbe lissée** (une ligne douce qui ne dépasse jamais les deux points voisins, ni vers le haut ni vers le bas, de sorte qu'elle ne trace aucune valeur qui n'a jamais existé). Vous choisissez la forme sur la première page de la visite de bienvenue, puis dans **Paramètres → Préférences** ; elle est conservée avec votre compte et s'applique à tous les graphiques, dans chaque navigateur depuis lequel vous vous connectez, jusqu'à ce que vous donniez à un graphique une forme propre. Tant que vous n'en choisissez pas une, elle suit la valeur par défaut de l'administrateur. Sur les pages de détail d'un actif et d'une paire FX, les paramètres du graphique comportent aussi une ligne **Forme de la ligne**, afin de donner à ce graphique une forme propre. La forme ne change que la manière dont les points sont reliés : la valeur d'un jour dans l'infobulle est toujours celle que le rapport contient pour ce jour. Lorsqu'un graphique affiche des semaines ou des mois, les points ne sont pas des marches ; **Marches** y dessine donc des segments.

Le graphique mémorise votre dernière vue, sous-vue P&L comprise, dans ce navigateur et pour chaque utilisateur, et la partage avec les pages des courtiers. Il démarre sur **Abs**. Sans données de taux de rendement, **%** est grisé et le graphique affiche **Abs**, mais conserve votre choix : **%** revient dès qu'il y a des données à tracer — après un changement de période ou de courtier, ou à la prochaine ouverture du graphique — sauf si vous choisissez une autre vue entre-temps.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Mode absolu" alt="Graphique de croissance — Mode absolu">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Graphique de croissance — Mode absolu">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Mode pourcentage" alt="Graphique de croissance — Mode pourcentage">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Graphique de croissance — Mode pourcentage">
  </div>
</div>

**Masquer les montants** (le bouton en forme d'œil dans la barre supérieure) remplace chaque montant sur l'axe et dans les infobulles par `•••` ; les signes, les devises, les lignes et les couleurs restent. Voir [Mode confidentialité](../settings/preferences.md#privacy-mode).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="Le tableau de bord avec Masquer les montants activé : le bouton en forme d'œil barré dans l'en-tête, les montants des cartes KPI et des Soldes de trésorerie affichés sous la forme ••• avec leur signe et leur devise, les pourcentages toujours lisibles et l'axe Croissance du portefeuille masqué" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💶 Abs — valeurs absolues

| Élément | Couleur | Signification |
|---------|-------|---------|
| Zone — **Coût d'achat** | Bleu | Ce que vous coûtent les positions que vous détenez (coût moyen × quantité) |
| Zone — **Rendements** | Émeraude | Rendements conservés en liquidités (dividendes, intérêts, plus-values réalisées non encore réinvesties, gains de change sur les liquidités que vous détenez dans une autre devise) |
| Zone — **Capital** | Gris-vert | Dépôts non encore investis, conservés en liquidités |
| Ligne — **[Valeur nette (NAV)](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Vert foncé, trait plein | Valeur totale du portefeuille aux prix de marché actuels |
| Ligne — **[Capital versé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Gris, pointillés | Capital externe net apporté au fil du temps |

**L'écart entre les deux lignes correspond à votre P&L total** : tous les gains accumulés depuis l'origine (latents, réalisés, intérêts, dividendes et gains ou pertes de change sur les liquidités détenues dans une autre devise) moins les frais et impôts. L'infobulle affiche les deux lignes, le P&L total en vert ou en rouge, et la décomposition : **Actifs au coût** (la zone bleue, y compris les actifs déplacés entre vos courtiers), **Rendements** et **Capital**.

**Les actifs valorisés à leur prix d'achat**, comme les prêts P2P sans prix de marché en direct, maintiennent la NAV proche du coût d'achat ; l'écart peut donc être faible : lisez le **P&L total** dans l'infobulle.

**Argent provenant d'un courtier hors du périmètre affiché.** Sur la page d'un courtier, ou avec le filtre de courtier activé, l'argent reçu d'un courtier hors du périmètre affiché est du **Capital**, comme le serait un dépôt — ou de nouveau des **Rendements**, s'il rapporte des rendements que vous aviez retirés auparavant. L'argent envoyé à un courtier hors du périmètre affiché sort d'abord du **Capital**, puis des **Rendements**, comme le ferait un retrait. Il en va de même pour la moitié d'un transfert dont l'autre moitié a été supprimée ou dissociée, dans toutes les vues.

🔗 **Théorie** : [Capital versé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Décomposition des liquidités](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### 📉 % — taux de rendement

Chaque ligne représente le rendement accumulé depuis le début de la période sélectionnée :

| Série | Ce qu'elle montre |
|-------|--------------|
| **[MWRR cumulé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Votre rendement personnel pondéré par les flux, y compris le calendrier des dépôts |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rendement pur de la stratégie d'actifs, sans tenir compte du moment de vos dépôts |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rendement brut sur le capital net investi |

L'écart entre le MWRR et le TWRR constitue l'[Effet timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md). La ligne MWRR comporte une interruption les jours sans MWRR — une valeur nulle ou négative, ou des retraits nets qui ne laissent aucun capital investi — selon la même règle que les cartes MWRR ([MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)). La ligne TWRR comporte une interruption les jours où votre portefeuille vaut zéro ou moins, par exemple après que vous avez tout vendu et retiré les liquidités, selon la même règle que la carte TWRR ; après de nouveaux dépôts, elle reprend là où elle se trouvait ([Quand aucun TWRR n'est affiché](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr)). La ligne ROI n'a pas d'interruption. Lorsque le dernier jour de la période n'en a pas, la [bannière de qualité des données](index.md#data-quality-banner) indique *Le MWRR ne peut pas être calculé pour cette période*.

### 💰 P&L — l'argent que vous avez gagné {: #pnl-mode }

**P&L** trace votre **P&L total** (NAV moins le capital versé) : combien d'argent le portefeuille a réellement gagné depuis l'origine. Un zoom avant ne relance pas le décompte à zéro.

Un second sélecteur, en haut à gauche du graphique, choisit le mode de tracé (icônes uniquement sur un graphique étroit) :

| Vue | Ce qu'elle dessine | La question à laquelle elle répond |
|------|---------------|------------------------|
| **Ligne** | P&L cumulé sous forme d'une seule ligne | Comment mon résultat a-t-il évolué dans le temps ? |
| **Bougies** | Une bougie par période, d'un jour à une année | Quelle a été l'amplitude à l'intérieur de chaque période ? |
| **Revenus** | Barres des liquidités qui ont réellement circulé | D'où vient l'argent, et combien m'a-t-il coûté ? |

#### Ligne — P&L cumulé {: #pnl-line }

- La ligne est **verte au-dessus de zéro et rouge en dessous**.
- Une **ligne grise en pointillés** marque le P&L du premier jour de la vue : l'écart avec elle correspond à ce que vous avez gagné ou perdu depuis le bord gauche.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Le graphique Croissance du portefeuille en mode P&L, vue Ligne : la ligne du P&L total en vert, la ligne grise en pointillés au niveau du P&L du premier jour de la vue, et une ligne en pointillés par courtier">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-line" alt="Le graphique Croissance du portefeuille en mode P&L, vue Ligne : la ligne du P&L total en vert, la ligne grise en pointillés au niveau du P&L du premier jour de la vue, et une ligne en pointillés par courtier">
  </div>
</div>

**Lignes par courtier.** Avec deux courtiers ou plus dans le périmètre, chaque courtier obtient une ligne en pointillés et une ligne d'infobulle avec sa part du total ; les parts s'additionnent au total chaque jour. La ligne d'un courtier représente le P&L réalisé pendant que la valeur se trouvait chez ce courtier : déplacer de l'argent ou des titres entre deux de vos courtiers n'est ni un gain ni une perte, donc aucune ligne ne saute à l'arrivée d'un transfert.

- **En transit** — jusqu'à l'arrivée du transfert, la valeur et ses variations de prix ou de taux de change restent chez le courtier qu'elle a quitté.
- **Parts de propriété différentes** — lorsque les deux courtiers ont des [parts de propriété](../brokers/sharing.md) différentes, la ligne de réception conserve un palier le jour de l'arrivée : le même palier que celui affiché par le total.
- **Aucune valeur le jour de l'arrivée** — si un taux de change manque, ou si le titre n'a pas encore de prix et qu'aucun coût n'a été enregistré à son arrivée, le saut subsiste : rien n'est deviné. Un titre sans aucun prix est transféré au coût que le courtier de réception enregistre pour lui, la valeur que LibreFolio lui attribue à cet endroit ; si une partie de ce que ce courtier a payé pour l'actif était déjà inconnue, sa propre ligne absorbe l'écart.
- **Courtiers hors du périmètre affiché** — sur la page d'un courtier, ou avec le filtre de courtier activé, les titres envoyés à un courtier hors du périmètre affiché ou reçus de celui-ci comptent comme du capital à leur valeur de marché ce jour-là — à leur coût s'ils n'ont aucun prix — et non comme un gain ou une perte ; l'argent compte comme un dépôt ou un retrait. Lorsque l'autre courtier d'un transfert est supprimé, la moitié restante n'est plus un transfert : les titres deviennent un ajustement, compté comme du capital à leur coût plutôt qu'à leur valeur de marché, et l'argent comme un dépôt ou un retrait (voir [Modifier ou supprimer un courtier](../brokers/index.md)). Seuls les titres envoyés dont le coût moyen nécessite un taux de change manquant restent un transfert, comptés à leur valeur de marché.

Avec un seul courtier, ou sur la page d'un courtier, seul le total est tracé.

🔗 **Théorie** : [Transferts internes dans les lignes par courtier](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#internal-transfers-broker-lines)

#### Bougies — l'amplitude au sein de la période {: #pnl-candles }

Chaque période de la [largeur que vous choisissez](#pnl-width) devient une **bougie** constituée de valeurs de P&L, et non de prix. Sa **clôture** correspond exactement au P&L total que **Ligne** affiche pour ce jour.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Le graphique Croissance du portefeuille en mode P&L, vue Bougies à 3D : les bougies de P&L synthétiques, les boutons de largeur de 3D à 6M dans le coin supérieur droit du graphique, les étiquettes de période sur l'axe et la légende Synthétique sous le graphique">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-candles" alt="Le graphique Croissance du portefeuille en mode P&L, vue Bougies à 3D : les bougies de P&L synthétiques, les boutons de largeur de 3D à 6M dans le coin supérieur droit du graphique, les étiquettes de période sur l'axe et la légende Synthétique sous le graphique">
  </div>
</div>

!!! warning "Les plus hauts et les plus bas sont hypothétiques"

    Le haut et le bas d'une bougie additionnent les plus hauts et les plus bas quotidiens de chaque actif, qui n'ont pas été atteints au même moment : cet état du portefeuille n'a peut-être jamais existé, comme l'indique la légende sous le graphique (*Synthétique — les plus hauts/plus bas croisés entre actifs sont hypothétiques et non simultanés*). Lisez-les comme l'amplitude que le portefeuille *aurait pu* atteindre.

Attendez-vous aussi à :

- **Aucun volume** — le P&L d'un portefeuille n'a pas de volume échangé.
- **Corps fins, longues mèches** — l'ouverture et la clôture sont généralement proches, tandis que l'amplitude cumulée est large.
- **Lacunes** — un jour où un actif détenu n'a pas pu être valorisé n'a pas de bougie, plutôt qu'une bougie devinée.

L'infobulle donne la période, **Ouverture**, **Clôture**, **Haut** et **Bas**, plus une ligne par courtier lorsque deux courtiers ou plus sont dans le périmètre.

#### Revenus — les liquidités qui ont réellement circulé {: #pnl-income }

**Revenus** laisse de côté les valorisations et trace vos flux de trésorerie réels. Chaque barre est la **somme** des flux de sa période, répartie en trois colonnes au maximum :

| Colonne | Barres | Ce qu'elle représente |
|--------|------|--------------------|
| Revenus et coûts | **Dividende** · **Intérêts** au-dessus de zéro, **Frais et impôts** en dessous de zéro | Ce que le portefeuille vous a versé, et ce que l'activité vous a coûté |
| Dépôts | **Dépôt** | Argent frais que vous avez apporté (les retraits ne sont pas tracés) |
| Achats | **Coût d'achat**, en deux zones : **Nouveau capital** en bas, **Réinvesti** en haut | Ce que vous avez dépensé pour vos achats, réparti selon l'origine de l'argent |

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Le graphique Croissance du portefeuille en mode P&L, vue Revenus à 1M : groupes mensuels de barres pour les Intérêts, les Frais et impôts sous zéro, le Dépôt et le Coût d'achat">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-income" alt="Le graphique Croissance du portefeuille en mode P&L, vue Revenus à 1M : groupes mensuels de barres pour les Intérêts, les Frais et impôts sous zéro, le Dépôt et le Coût d'achat">
  </div>
</div>

Comment le lire :

- **Nouveau capital ou réinvesti.** Un achat dépense d'abord les rendements déjà détenus en liquidités chez ce courtier (**Réinvesti**, en vert comme dans **Abs**) ; le reste constitue le **Nouveau capital** (en bleu). L'argent transféré depuis ou vers un courtier hors du périmètre affiché modifie ces liquidités comme le ferait un dépôt ou un retrait, comme dans **Abs** ci-dessus. Les ventes ne sont jamais tracées.
- **Les signes sont conservés.** Une correction négative sur un dividende passé réduit la barre Dividende ; les frais et impôts restent sous zéro.
- **Cela correspond aux KPI.** Pour les mêmes dates et courtiers, **Dividende** et **Intérêts** totalisent exactement la ligne **Dividendes et intérêts** de la [carte P&L période](kpi-cards.md#card-1-period-pl).
- **Une seule entrée de légende.** Les deux zones d'achat portent le nom **Coût d'achat** : un clic masque les deux, ainsi que l'aire **Abs** du même nom.
- **Taux de change manquants.** Un montant qui ne peut pas être converti à sa date est omis, et non compté comme zéro ; la [bannière de qualité des données](index.md#data-quality-banner) le signale.

!!! warning "Les barres d'achat ne sont pas le KPI Coût d'achat"

    Les barres représentent un **flux** : ce que vous avez dépensé pour vos achats au cours de chaque période. La ligne **Coût d'achat** de la [carte Valeur nette](kpi-cards.md#card-3-net-worth) est un **niveau** : ce que les positions que vous détenez encore vous ont coûté à la date de fin. Les ventes et les achats antérieurs comptent dans le KPI mais n'ont pas de barre.

#### Largeur des bougies — de 1D à 1Y {: #pnl-width }

Dans **Bougies** et **Revenus**, les boutons du coin supérieur droit du graphique, de **1D** à **1Y**, définissent la durée couverte par une bougie, ou par un groupe de barres. Le graphique affiche toujours toute la plage, et le zoom ne change jamais la largeur.

- **Périodes calendaires.** **1W** va du lundi au dimanche, **1M** correspond à un mois calendaire, **3M** à un trimestre, **6M** à un semestre, **1Y** à une année ; **3D** et **2W** sont des blocs fixes de jours.
- **Étiquettes de l'axe.** Chaque étiquette nomme le début de sa période, même si la plage ne la couvre qu'en partie ; les mois et les années n'apparaissent que lorsqu'ils changent, et les étiquettes trop serrées s'inclinent ou se raréfient.
- **Seules les largeurs qui tiennent** dans le graphique et dans la plage sont proposées ; **Revenus** commence à **1W**.
- **Point de départ.** **Bougies** prend la largeur la plus fine disponible ; **Revenus** s'ouvre sur **1M**, ou sur la largeur disponible la plus proche, chaque fois que vous y entrez. Le rechargement de la page réinitialise la largeur.
- **Les périodes partielles sont estompées.** Une période que la plage commence en cours de route, ou une dernière période écourtée par une plage se terminant dans le passé, est dessinée estompée, et son infobulle indique *Partiel : N jours sur M*. Sinon, la période en cours est dessinée en entier, avec *En cours : N jours sur M*.

---

## 🥧 Panneau d'allocation {: #allocation-panel }

Le panneau **Allocation des actifs** montre comment votre portefeuille est réparti, aujourd'hui et dans le temps. Choisissez une dimension avec les onglets **Par type**, **Par secteur**, **Géographique** et **Par actif**, et une vue avec les deux boutons du coin supérieur droit : le diagramme circulaire pour **Maintenant**, le graphique en aires pour **Historique**.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Par type (actuel)" alt="Allocation par type — Actuelle">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Allocation par type — Actuelle">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par secteur (actuel)" alt="Allocation par secteur — Actuelle">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Allocation par secteur — Actuelle">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par géographie (actuel)" alt="Allocation par géographie — Actuelle">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Allocation par géographie — Actuelle">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par type (historique)" alt="Historique de l'allocation par type">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Historique de l'allocation par type">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par secteur (historique)" alt="Historique de l'allocation par secteur">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Historique de l'allocation par secteur">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par géographie (historique)" alt="Historique de l'allocation par géographie">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Historique de l'allocation par géographie">
  </div>
</div>

### 🗂️ Trois dimensions

| Onglet | Ce qu'il montre |
|-----|--------------|
| **Par type** | Ce qu'est chaque position — son [type d'actif](../../financial-theory/instruments/asset-types/index.md), comme Action, ETF, Obligation, Fonds ou Crypto — plus **Liquidités** pour votre trésorerie. Les sous-types sont comptés avec leur [famille](../../financial-theory/instruments/asset-types/index.md#families-and-subtypes), par exemple un **ETF actions** avec vos autres ETF. |
| **Par secteur** | Secteur d'activité : 💻 Technologie, 🏦 Finance, 💊 Santé, etc. |
| **Géographique** | Où vos actifs sont investis, pays par pays, selon la distribution géographique de chaque actif |
| **Par actif** | Le poids de chaque actif pris individuellement : une part par actif, avec **Liquidités** pour votre trésorerie. Voir [Par actif](#allocation-by-asset). |

### 🕰️ Maintenant et historique

- **Maintenant** — l'allocation au dernier jour de la plage sélectionnée : un diagramme en anneau pour **Par type** et **Par secteur**, une carte mondiale pour **Géographique**. Survolez une part ou un pays pour obtenir son pourcentage et son montant ; par type, l'infobulle affiche aussi le type d'actif sous forme de badge (Liquidités, votre trésorerie, n'en a pas). Pour le type, le diagramme en anneau peut comporter [deux anneaux](#allocation-type-rings).
- **Historique** — un graphique en aires empilées à 100 % montrant l'évolution de l'allocation dans le temps, pratique pour visualiser les rééquilibrages. Pour le type, chaque famille correspond à une aire ; en survolant une date, ses sous-types sont listés, par exemple *ETF générique* et *ETF actions*.

Le panneau mémorise la vue et l'onglet dans ce navigateur, pour chaque utilisateur, et les partage avec les pages des courtiers.

### 🧩 Par actif {: #allocation-by-asset }

Quels actifs individuels pèsent le plus ? **Par actif** décompose le portefeuille actif par actif plutôt que par catégorie.

- **Maintenant** — un diagramme circulaire avec le poids de chaque actif au dernier jour de la plage sélectionnée. Chaque part affiche l'icône de son actif — la sienne, ou celle de son type s'il n'en a pas ou si elle ne se charge pas ; les liquidités affichent celle de Liquidités. Il n'y a pas de légende : survolez une part pour lire le type d'actif, sous forme de badge, puis le nom, la part et le montant.
- **Historique** — l'évolution de la distribution par actif dans le temps. **Les positions clôturées sont incluses**, de sorte qu'un actif que vous avez vendu apparaît encore les jours où vous le déteniez.
- **Les couleurs** suivent le poids actuel : l'actif le plus lourd reçoit la première couleur, puis les autres par poids, puis les actifs clôturés, les plus récemment clôturés en premier. Le diagramme circulaire et l'historique utilisent la même couleur pour le même actif ; les courbes de [Rendement des positions](positions.md#return-of-the-positions) aussi.

### 🍩 Deux anneaux par type {: #allocation-type-rings }

Dès que vous détenez un actif avec un sous-type, comme un **ETF actions** ou un **Crowdfunding immobilier**, le diagramme en anneau **Maintenant** de **Par type** dessine deux anneaux :

- **Anneau intérieur** — une part par famille, avec son icône lorsque la place le permet : tous vos ETF (l'**ETF** générique et chaque sous-type) ensemble, **Crowdfund** avec **Crowdfunding immobilier**, et tous les autres types, **Liquidités** incluses, à part. Ce sont les familles que le [menu Type](../assets/create-edit.md#choosing-the-asset-type) de l'actif regroupe.
- **Anneau extérieur** — plus fin et détaché, il divise chaque famille comportant un sous-type en ses membres, dans des nuances de la couleur de la famille, avec une légende lorsqu'il y a de la place. Le membre générique s'intitule *ETF générique* ou *Crowdfund générique*.
- **Survolez** une part pour obtenir sa proportion et son montant ; sur l'anneau extérieur, une dernière ligne commençant par **↳** donne la part de la famille entière.
- **La légende** ne liste que les familles : cliquer sur l'une d'elles masque ses parts sur les deux anneaux.

Sans aucun sous-type, le diagramme en anneau conserve un seul anneau.

### 💵 La trésorerie en Liquidités

Votre trésorerie constitue la part **Liquidités** de **Par type**, **Par secteur** et **Par actif** ; la carte **Géographique** l'exclut, car la trésorerie n'appartient à aucun pays. Avec le filtre de courtier activé, le panneau n'affiche que les actifs et la trésorerie des courtiers sélectionnés.

### ➖ Trésorerie négative {: #allocation-negative-cash }

Le pourcentage de chaque part est son montant divisé par la somme de toutes les parts, trésorerie incluse ; une trésorerie négative modifie donc les proportions :

- **Trésorerie sous zéro, actifs au-dessus** — par exemple 1 500 € d'actions avec une trésorerie à −500 € sur un découvert : les parts totalisent 1 000 €, donc **Liquidités** affiche −50 % et les actions 150 %. Les pourcentages totalisent toujours 100 %.
- **Rien à partager** — lorsque les parts totalisent zéro ou moins, aucune part n'a de pourcentage : 500 € d'actions achetées avec un découvert de −500 €, ou un portefeuille que vous avez vidé, dont la seule part est **Liquidités** à zéro. Chaque part affiche `—` au lieu d'un pourcentage et conserve son montant, et le graphique n'a rien à tracer et l'indique. Dans **Historique**, un jour où les parts totalisent zéro ou moins n'a pas non plus de pourcentages.
- **Un reliquat infime** de 0,00001 unité ou moins, qu'une vente de presque toutes les unités peut laisser, n'est pas une position : il n'a pas de part.

---

## 🔗 Voir aussi

- 💰 **[Cartes KPI](kpi-cards.md)** — Valeur nette, P&L période, Rendements
- 💼 **[NAV / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capital versé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Effet timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
- 🛠️ **[Fonctionnement interne des graphiques](../../developer/frontend/components/charts.md)** — pour les développeurs : comment ces graphiques sont construits

---

*[⬅️ Retour à la vue d'ensemble du tableau de bord](index.md)*
