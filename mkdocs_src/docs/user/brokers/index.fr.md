# 🏦 Courtiers

Un **courtier** est l'un de vos comptes — dans une société de courtage, une banque ou une bourse : le lieu où vivent vos investissements et votre trésorerie. Chaque transaction et chaque rapport importé appartient à un courtier, vous en avez donc besoin d'au moins un pour commencer.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Liste des courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La page **Courtiers** affiche une carte par courtier, avec sa valeur (**NAV**) dans la devise choisie dans **Devise** en haut de la page. Cliquez sur une carte pour ouvrir le courtier.

!!! note "Les courtiers partagés affichent votre part"

    Sur un courtier que vous copossédez, les valeurs de sa carte et de son onglet **Vue d'ensemble** sont **mises à l'échelle selon votre part de propriété** : un Propriétaire à 50 % voit la moitié du compte. Les Éditeurs et les Lecteurs voient toujours les montants complets. Voir [Partage de courtier](sharing.md).

---

## ➕ Créer un courtier

1. Ouvrez **Courtiers** depuis la barre latérale et cliquez sur **Ajouter un courtier**.
2. Saisissez un **Nom** — le seul champ obligatoire — et définissez les options dont vous avez besoin.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Formulaire de modification du courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. Cliquez sur **Créer** : le courtier apparaît dans votre liste, prêt pour les transactions et les rapports.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="detail" alt="Formulaire de modification du courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

??? info "⚙️ Les champs facultatifs — à quoi sert chacun"

    - **Description** — vos propres notes.
    - **Plugin d'importation par défaut** — l'importateur que l'[Assistant d'importation](../transactions/import/index.md) propose pour les fichiers de ce courtier.
    - **URL du portail** — le site web du courtier, ouvert depuis la page du courtier. Son icône est utilisée lorsque vous ne définissez pas d'**URL d'icône personnalisée**.
    - **Compte ouvert** et **Compte actif** — la date d'ouverture du compte, et s'il est toujours ouvert. Un courtier fermé apparaît en grisé dans la liste.
    - **Options de trading** — **Autoriser l'achat à effet de levier** et **Autoriser la vente à découvert**, expliquées dans [Options de trading](info.md#trading-options).
    - **Soldes initiaux** (uniquement lors de la création) — votre trésorerie de départ. LibreFolio enregistre un **Dépôt** par devise, **daté d'aujourd'hui** : si l'argent était présent plus tôt, modifiez la date de ces dépôts sur la page [Transactions](../transactions/index.md).

??? warning "🏷️ « Un courtier nommé … existe déjà » — quand cela apparaît"

    Les noms de courtiers sont uniques sur l'ensemble du serveur, pour tous ses utilisateurs. Choisissez un autre nom, ou renommez le courtier existant s'il vous appartient.

    Les courtiers d'autres utilisateurs que vous ne pouvez pas ouvrir sont listés sous **Autres courtiers existants**. Leur bouton de partage indique qui a accès, vous savez donc à qui vous adresser : tout utilisateur connecté à ce LibreFolio peut le voir, pour n'importe quel courtier.

---

## ✏️ Modifier ou supprimer un courtier

- **Modifier** — le crayon sur la carte du courtier, ou **Modifier** dans la barre d'outils du courtier. Les Propriétaires et les Éditeurs peuvent modifier un courtier.
- **Supprimer** — la corbeille sur la carte du courtier. Seul un Propriétaire peut supprimer un courtier. S'il contient encore des transactions, LibreFolio indique combien et propose **Aller aux transactions** ou **Supprimer le courtier et les transactions**, ce qui les supprime également.

---

## 🗂️ À l'intérieur d'un courtier

La barre d'outils en haut s'applique à chaque onglet :

- la **plage de dates** et la **Devise** des chiffres ;
- **Modifier**, **Partager le courtier** (ouvre l'onglet **Info**) et **Actualiser** ;
- **Export IA**, qui copie dans votre presse-papiers une invite prête à l'emploi concernant ce courtier — voir [Export IA du courtier](../ai-export/broker.md).

En dessous, cinq onglets :

1. **Vue d'ensemble** — comment se porte le compte (ci-dessous).
2. **Positions** — ce que vous détenez chez ce courtier (ci-dessous).
3. **Risque** — l'analyse des risques du Tableau de bord, limitée à ce courtier (voir [Onglet Risque du Tableau de bord](../dashboard/index.md#risk-tab)).
4. **Transactions** — le registre du courtier, les saisies manuelles, les importations et les rapports importés (voir [Transactions du courtier](import.md)).
5. **Info** — les détails du compte, les options de trading et le partage (voir [Configuration et Info](info.md)).

---

## 📈 Onglet Vue d'ensemble

La **Vue d'ensemble** répond à « comment se porte ce compte ? » avec les mêmes blocs que la [Vue d'ensemble du Tableau de bord](../dashboard/index.md), limités à ce courtier :

- **Cartes KPI** — **P&L période**, **Rendements** et **Valeur nette** ([Cartes KPI](../dashboard/kpi-cards.md)).
- **Soldes de trésorerie** — la trésorerie détenue ici, par devise.
- **Graphique de croissance** — les vues **Abs**, **%** et **P&L**, avec le P&L en **Ligne**, **Bougies** ou **Revenu** ([Graphique de croissance du portefeuille](../dashboard/charts.md#portfolio-growth-chart), [Mode P&L](../dashboard/charts.md#pnl-mode)). La vue que vous choisissez est partagée avec le Tableau de bord.
- **Allocation** — par type, secteur et zone géographique ([Panneau d'allocation](../dashboard/charts.md#allocation-panel)).

Revenir sur un courtier que vous avez déjà ouvert affiche immédiatement ses derniers chiffres, actualisés en arrière-plan si quelque chose a changé ([Revenir et actualiser](../dashboard/index.md#coming-back-and-refreshing)). **Actualiser** recalcule à la demande, y compris l'onglet **Risque** et le panneau des lots.

---

## 🔍 Onglet Positions

L'onglet **Positions** liste ce que vous détenez chez ce courtier, dans le même panneau que les [Positions du Tableau de bord](../dashboard/positions.md) :

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Positions (Tableau)" alt="Vue tableau des positions du courtier">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Positions (Carte / Treemap)" alt="Vue carte des positions du courtier">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Performance (Tableau)" alt="Vue tableau des performances du courtier">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Performance (Carte / Graphique)" alt="Vue carte des performances du courtier">
</div>

- **Portefeuille** affiche vos positions (quantité, valeur, poids) ; **Période** affiche les gains et pertes de chaque position sur les dates sélectionnées. Les deux sont disponibles sous forme de **Tableau** ou de **Carte**.
- La colonne **YOC** correspond au [Rendement sur coût](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) de chaque position chez ce courtier.
- **Analyser les lots** ouvre le panneau [Analyse des lots FIFO](../dashboard/positions.md#fifo-lots-analysis) sous la liste : trouvez-le dans le menu **⋮** d'une ligne, ou faites un clic droit sur l'actif dans le tableau ou la carte.

---

## 📑 Dans cette section

- 📥 **[Transactions du courtier](import.md)** — ajoutez des transactions à ce courtier, importez des relevés et gérez ses rapports importés.
- ⚙️ **[Configuration et Info](info.md)** — détails du compte, options de trading et panneau de partage.
- 🧠 **[Export IA du courtier](../ai-export/broker.md)** — ce que contient un export de courtier, et les analyses que vous pouvez demander à une IA.
- 🤝 **[Partage de courtier](sharing.md)** — les rôles (Propriétaire, Éditeur, Lecteur) et les parts de propriété.

La page Courtiers, le formulaire **Ajouter un courtier** et la page du courtier disposent chacun d'un bref guide contextuel : relancez-les depuis [Paramètres → Préférences → Prise en main et guides](../settings/preferences.md#onboarding-and-guides).
