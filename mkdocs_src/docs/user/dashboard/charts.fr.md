# 📊 Graphiques

Sous les cartes KPI, le graphique **Croissance du portefeuille** et le panneau **Allocation d'actifs** montrent l'évolution passée de votre portefeuille et sa composition. Tous deux suivent la plage temporelle et le filtre de courtier du Tableau de bord, et la page d'un courtier les affiche pour ce courtier uniquement.

---

## 📈 Graphique de croissance du portefeuille {: #portfolio-growth-chart }

Le graphique de croissance montre l'évolution de votre portefeuille sur la période sélectionnée : le bouton **Abs / % / P&L** dans son coin supérieur droit bascule entre les valeurs absolues, les taux de rendement et l'argent réellement gagné.

Le graphique mémorise votre dernière vue, sous-vue P&L incluse, dans ce navigateur et pour chaque utilisateur, et la partage avec les pages des courtiers. Il démarre sur **Abs**. Sans données de taux de rendement, **%** est grisé et le graphique affiche **Abs** ; votre choix revient la prochaine fois que vous ouvrez le graphique avec des données à tracer.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Mode absolu" alt="Graphique de croissance — Mode absolu">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Graphique de croissance — Mode absolu">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Mode pourcentage" alt="Graphique de croissance — Mode pourcentage">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Graphique de croissance — Mode pourcentage">
  </div>
</div>

**Masquer les montants** (le bouton œil dans la barre supérieure) remplace chaque montant sur l'axe et dans les infobulles par `•••` ; les signes, les devises, les lignes et les couleurs restent. Voir [Mode confidentialité](../settings/preferences.md#privacy-mode).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="Le Tableau de bord avec Masquer les montants activé : le bouton œil barré dans l'en-tête, les montants des cartes KPI et des Soldes de trésorerie affichés par ••• avec leur signe et leur devise, les pourcentages toujours lisibles, et l'axe Croissance du portefeuille masqué" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💶 Abs — valeurs absolues

| Élément | Couleur | Signification |
|---------|-------|---------|
| Aire — **Coût d'achat** | Bleu | Ce que les positions que vous détenez vous ont coûté (coût moyen × quantité) |
| Aire — **Rendements** | Émeraude | Rendements détenus sous forme de liquidités (dividendes, intérêts, plus-values réalisées non encore réinvesties) |
| Aire — **Capital** | Gris-vert | Dépôts non encore investis, détenus sous forme de liquidités |
| Ligne — **[Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Vert foncé plein | Valeur totale du portefeuille aux prix de marché actuels |
| Ligne — **[Capital versé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Gris pointillé | Capital externe net apporté au fil du temps |

**L'écart entre les deux lignes correspond à votre P&L total** : tous les gains accumulés (latents, réalisés, intérêts et dividendes) moins les frais et les impôts. L'infobulle affiche les deux lignes, le P&L total en vert ou en rouge, et la décomposition : **Actifs au coût d'achat** (l'aire bleue, actifs circulant entre vos courtiers inclus), **Rendements** et **Capital**.

**Les actifs valorisés à leur prix d'achat**, comme les prêts P2P sans prix live de marché, maintiennent la NAV proche du coût d'achat, si bien que l'écart peut être mince : lisez le **P&L total** dans l'infobulle.

🔗 **Théorie** : [Capital versé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Décomposition des liquidités](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### 📉 % — taux de rendement

Chaque ligne représente le rendement accumulé depuis le début de la période sélectionnée :

| Série | Ce qu'elle montre |
|--------|--------------|
| **[MWRR cumulé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Votre rendement personnel pondéré par les flux, tenant compte du calendrier des dépôts |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rendement pur de la stratégie d'actifs, ignorant le moment de vos dépôts |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rendement brut du capital net investi |

L'écart entre le MWRR et le TWRR est l'[effet timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md). Si la [bannière de qualité des données](index.md#data-quality-banner) indique **Graphique MWRR indisponible**, la ligne MWRR est masquée ; le TWRR et le ROI restent affichés.

### 💰 P&L — l'argent que vous avez gagné {: #pnl-mode }

**P&L** trace votre **P&L total** (NAV moins capital versé) : combien d'argent le portefeuille a réellement gagné depuis sa création. Zoomer ne réinitialise pas le comptage à zéro.

Un second bouton, en haut à gauche du graphique, choisit le mode de tracé (icônes uniquement sur un graphique étroit) :

| Vue | Ce qu'elle trace | La question à laquelle elle répond |
|------|---------------|------------------------|
| **Ligne** | P&L accumulé sous forme d'une seule ligne | Comment mon résultat a-t-il évolué dans le temps ? |
| **Bougies** | Une bougie par période, d'un jour à un an | Quelle a été l'ampleur de la variation à l'intérieur de chaque période ? |
| **Revenus** | Barres des liquidités qui ont réellement circulé | D'où vient l'argent, et combien m'a-t-il coûté ? |

#### Ligne — P&L cumulé {: #pnl-line }

- La ligne est **verte au-dessus de zéro et rouge en dessous**.
- Une **ligne grise pointillée** marque le P&L du premier jour affiché : l'écart par rapport à celle-ci correspond à ce que vous avez gagné ou perdu depuis le bord gauche.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Le graphique Croissance du portefeuille en mode P&L, vue Ligne : la ligne P&L total en vert, la ligne grise pointillée au P&L du premier jour affiché, et une ligne pointillée par courtier">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-line" alt="Le graphique Croissance du portefeuille en mode P&L, vue Ligne : la ligne P&L total en vert, la ligne grise pointillée au P&L du premier jour affiché, et une ligne pointillée par courtier">
  </div>
</div>

**Lignes par courtier.** Avec deux courtiers ou plus dans le périmètre, chaque courtier dispose d'une ligne pointillée et d'une ligne d'infobulle indiquant sa part du total ; les parts s'additionnent au total chaque jour. Une part ne correspond pas à la performance propre du courtier : l'argent en transit est compté pour le courtier qu'il a quitté, si bien qu'une ligne de courtier peut faire un bond à la date d'un virement. Avec un seul courtier, ou sur la page d'un courtier, seul le total est tracé.

#### Bougies — la variation à l'intérieur de la période {: #pnl-candles }

Chaque période de la [largeur que vous choisissez](#pnl-width) devient une **bougie** constituée de valeurs de P&L, et non de prix. Sa **clôture** correspond exactement au P&L total que la vue **Ligne** affiche pour ce jour.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Le graphique Croissance du portefeuille en mode P&L, vue Bougies à 3D : les bougies P&L synthétiques, les boutons de largeur de 3D à 6M dans le coin supérieur droit du graphique, les étiquettes de période sur l'axe, et la légende Synthétique sous le graphique">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-candles" alt="Le graphique Croissance du portefeuille en mode P&L, vue Bougies à 3D : les bougies P&L synthétiques, les boutons de largeur de 3D à 6M dans le coin supérieur droit du graphique, les étiquettes de période sur l'axe, et la légende Synthétique sous le graphique">
  </div>
</div>

!!! warning "Les plus hauts et plus bas sont hypothétiques"

    Le sommet et le plancher d'une bougie additionnent le plus haut et le plus bas quotidiens propres à chaque actif, qui n'ont pas été atteints au même moment : cet état du portefeuille n'a peut-être jamais existé, comme l'indique la légende sous le graphique (*Synthétique — les plus hauts et plus bas entre actifs sont hypothétiques et non simultanés*). Lisez-les comme l'ampleur que le portefeuille *aurait pu* atteindre.

Attendez-vous également à :

- **Aucun volume** — le P&L d'un portefeuille n'a pas de volume échangé.
- **Corps fins, longues mèches** — l'ouverture et la clôture sont généralement proches tandis que l'amplitude cumulée est large.
- **Lacunes** — un jour où un actif détenu n'a pas pu être valorisé n'a pas de bougie plutôt qu'une bougie devinée.

L'infobulle donne la période, **Ouverture**, **Clôture**, **Plus haut** et **Plus bas**, plus une ligne par courtier lorsque deux courtiers ou plus sont dans le périmètre.

#### Revenus — les liquidités qui ont réellement circulé {: #pnl-income }

**Revenus** laisse de côté les valorisations et trace vos flux de trésorerie réels. Chaque barre est la **somme** des flux de sa période, sur jusqu'à trois colonnes :

| Colonne | Barres | Ce qu'elle représente |
|--------|------|--------------------|
| Revenus et coûts | **Dividende** · **Intérêt** au-dessus de zéro, **Frais et impôts** en dessous | Ce que le portefeuille vous a versé, et ce que l'activité vous a coûté |
| Dépôts | **Dépôt** | Argent frais que vous avez apporté (les retraits ne sont pas tracés) |
| Achats | **Coût d'achat**, en deux zones : **Nouveau capital** en bas, **Réinvesti** au-dessus | Ce que vous avez dépensé pour vos achats, réparti selon l'origine de l'argent |

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Le graphique Croissance du portefeuille en mode P&L, vue Revenus à 1M : groupes mensuels de barres pour Intérêt, Frais et impôts sous zéro, Dépôt et Coût d'achat">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-income" alt="Le graphique Croissance du portefeuille en mode P&L, vue Revenus à 1M : groupes mensuels de barres pour Intérêt, Frais et impôts sous zéro, Dépôt et Coût d'achat">
  </div>
</div>

Comment le lire :

- **Nouveau capital ou réinvesti.** Un achat dépense d'abord les rendements déjà détenus sous forme de liquidités chez ce courtier (**Réinvesti**, en vert comme dans **Abs**) ; le reste est du **Nouveau capital** (bleu). Les ventes ne sont jamais tracées.
- **Les signes sont conservés.** Une correction négative sur un dividende passé réduit la barre de dividende ; les frais et les impôts restent en dessous de zéro.
- **Cela correspond aux KPI.** Pour les mêmes dates et courtiers, **Dividende** et **Intérêt** correspondent exactement à la ligne **Dividendes et intérêt** de la [carte P&L période](kpi-cards.md#card-1-period-pl).
- **Une seule entrée de légende.** Les deux zones d'achat sont nommées **Coût d'achat** : un clic masque les deux, ainsi que l'aire **Abs** du même nom.
- **Taux de change manquants.** Un montant qui ne peut pas être converti à sa date est omis, et non compté comme zéro ; la [bannière de qualité des données](index.md#data-quality-banner) le signale.

!!! warning "Les barres d'achat ne sont pas le KPI Coût d'achat"

    Les barres sont un **flux** : ce que vous avez dépensé pour vos achats à chaque période. La ligne **Coût d'achat** de la [carte Valeur nette](kpi-cards.md#card-3-net-worth) est un **niveau** : ce que les positions que vous détenez encore vous ont coûté à la date de fin. Les ventes et les achats antérieurs comptent dans le KPI mais n'ont pas de barre.

#### Largeur des bougies — de 1D à 1Y {: #pnl-width }

Dans **Bougies** et **Revenus**, les boutons dans le coin supérieur droit du graphique, de **1D** à **1Y**, définissent la durée couverte par une bougie, ou un groupe de barres. Le graphique affiche toujours toute la plage, et le zoom ne modifie jamais la largeur.

- **Périodes calendaires.** **1W** va du lundi au dimanche, **1M** est un mois calendaire, **3M** un trimestre, **6M** un semestre, **1Y** une année ; **3D** et **2W** sont des blocs de jours fixes.
- **Étiquettes de l'axe.** Chaque étiquette nomme le début de sa période, même si la plage ne la couvre que partiellement ; les mois et les années n'apparaissent que là où ils changent, et les étiquettes trop serrées s'inclinent ou s'espacent.
- **Seules les largeurs qui tiennent dans le graphique et dans la plage** sont proposées ; **Revenus** démarre à **1W**.
- **Où cela commence.** **Bougies** prend la largeur la plus fine disponible ; **Revenus** s'ouvre sur **1M**, ou la largeur disponible la plus proche, chaque fois que vous y accédez. Le rechargement de la page réinitialise la largeur.
- **Les périodes partielles sont atténuées.** Une période qui a déjà commencé lorsque la plage démarre, ou une dernière période écourtée par une plage se terminant dans le passé, est tracée en atténué, et son infobulle indique *Partiel : N jours sur M*. Sinon, la période en cours est tracée entièrement, avec *En cours : N jours sur M*.

---

## 🥧 Panneau d'allocation {: #allocation-panel }

Le panneau **Allocation d'actifs** montre comment votre portefeuille est réparti, aujourd'hui et dans le temps. Choisissez une dimension avec les onglets **Par type**, **Par secteur** et **Géographique**, et une vue avec les deux boutons dans le coin supérieur droit : le camembert pour **Maintenant**, le graphique en aires pour **Historique**.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Par type (actuel)" alt="Allocation par type — Actuel">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Allocation par type — Actuel">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par secteur (actuel)" alt="Allocation par secteur — Actuel">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Allocation par secteur — Actuel">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par géographie (actuel)" alt="Allocation par géographie — Actuel">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Allocation par géographie — Actuel">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par type (historique)" alt="Historique d'allocation par type">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Historique d'allocation par type">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par secteur (historique)" alt="Historique d'allocation par secteur">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Historique d'allocation par secteur">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par géographie (historique)" alt="Historique d'allocation par géographie">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Historique d'allocation par géographie">
  </div>
</div>

### 🗂️ Trois dimensions

| Onglet | Ce qu'il montre |
|-----|--------------|
| **Par type** | Ce qu'est chaque position — son [type d'actif](../../financial-theory/instruments/asset-types/index.md), tel qu'Action, ETF, Obligation, Fonds ou Crypto — plus **Liquidités** pour votre trésorerie. Les sous-types comptent avec leur [famille](../../financial-theory/instruments/asset-types/index.md#families-and-subtypes), comme un **ETF actions** avec vos autres ETF. |
| **Par secteur** | Secteur d'activité : 💻 Technologie, 🏦 Financières, 💊 Santé, etc. |
| **Géographique** | Où vos actifs sont investis, pays par pays, selon la distribution géographique de chaque actif |

### 🕰️ Maintenant et Historique

- **Maintenant** — l'allocation au dernier jour de la plage sélectionnée : un donut pour **Par type** et **Par secteur**, une carte du monde pour **Géographique**. Survolez une part ou un pays pour obtenir son pourcentage et son montant. Par type, le donut peut avoir [deux anneaux](#allocation-type-rings).
- **Historique** — un graphique en aires empilées à 100 % montrant l'évolution de l'allocation dans le temps, pratique pour visualiser le rééquilibrage. Par type, chaque famille est une aire ; survoler une date liste ses sous-types, tels que *ETF générique* et *ETF actions*.

Le panneau mémorise la vue et l'onglet dans ce navigateur, pour chaque utilisateur, et les partage avec les pages des courtiers.

### 🍩 Deux anneaux par type {: #allocation-type-rings }

Dès que vous détenez un actif doté d'un sous-type, comme un **ETF actions** ou un **Crowdfunding immobilier**, le donut **Maintenant** de **Par type** dessine deux anneaux :

- **Anneau intérieur** — une part par famille, avec son icône là où elle tient : tous vos ETF (l'**ETF** générique et chaque sous-type) ensemble, **Crowdfund** avec **Crowdfunding immobilier**, et tout autre type, y compris **Liquidités**, isolément. Ce sont les familles que le [menu Type](../assets/create-edit.md#choosing-the-asset-type) de l'actif regroupe.
- **Anneau extérieur** — plus fin et détaché, il divise chaque famille contenant un sous-type en ses membres, dans des nuances de la couleur de la famille, légendés là où il y a de la place. Le membre générique affiche *ETF générique* ou *Crowdfund générique*.
- **Survolez** une part pour obtenir sa proportion et son montant ; sur l'anneau extérieur, une dernière ligne commençant par **↳** donne la part de toute la famille.
- **La légende** liste uniquement les familles : cliquer sur l'une d'elles masque ses parts sur les deux anneaux.

Sans aucun sous-type, le donut conserve un seul anneau.

### 💵 La trésorerie comme liquidités

Votre trésorerie constitue la part **Liquidités** de **Par type** et **Par secteur** ; la carte **Géographique** l'exclut, car la trésorerie n'appartient à aucun pays. Avec le filtre de courtier activé, le panneau affiche uniquement les actifs et la trésorerie des courtiers sélectionnés.

---

## 🔗 Liens connexes

- 💰 **[Cartes KPI](kpi-cards.md)** — Valeur nette, P&L période, Rendements
- 💼 **[NAV / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capital versé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Effet timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
- 🛠️ **[Fonctionnement interne des graphiques](../../developer/frontend/components/charts.md)** — pour les développeurs : comment ces graphiques sont construits

---

*[⬅️ Retour à la vue d'ensemble du Tableau de bord](index.md)*
