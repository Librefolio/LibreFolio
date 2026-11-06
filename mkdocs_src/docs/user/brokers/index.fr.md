# 🏦 Courtiers

Un **courtier** est l'un de vos comptes — auprès d'une société de courtage, d'une banque ou d'une bourse : l'endroit où vivent vos investissements et votre trésorerie. Chaque transaction et chaque rapport téléversé appartient à un courtier, vous en avez donc besoin d'au moins un avant de commencer.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Liste des courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La page **Courtiers** affiche une carte par courtier, avec sa valeur (**NAV**) dans la devise choisie dans **Devise** en haut de la page. Cliquez sur une carte pour ouvrir le courtier.

Le **Gain/Perte** est la NAV moins le capital versé dans le courtier : vos dépôts moins les retraits, plus le coût des titres que vous avez apportés sans liquidités, plus ce que vous avez fait entrer depuis vos autres courtiers moins ce que vous avez fait sortir, chaque mouvement étant valorisé au jour de son arrivée. Ainsi, déplacer de l'argent ou des titres entre deux de vos courtiers ne constitue pas un gain sur une carte et une perte sur l'autre, et tant qu'un transfert est en transit, sa valeur reste sur la carte du courtier émetteur. Les liquidités détenues dans une autre devise sont valorisées au dernier taux de change, de sorte que l'effet de change sur ces liquidités compte dans le Gain/Perte, et non dans le capital versé. Le pourcentage entre parenthèses est le gain par rapport à ce capital : il affiche 0,00 % lorsque ce capital est nul ou négatif, par exemple lorsque le courtier a envoyé plus qu'il n'a reçu. → [Transferts internes](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#internal-transfers-broker-lines)

!!! note "Les courtiers partagés affichent votre part sur la carte"

    Sur un courtier que vous co-détenez, les valeurs de sa carte sont **mises à l'échelle de votre part de propriété** : un Propriétaire à 50 % voit la moitié du compte. Les Éditeurs et les Lecteurs voient les montants complets. La page du courtier elle-même montre le compte entier à tout le monde — voir [La page du courtier est le Tableau de bord sur un seul courtier](#broker-page-is-dashboard). Voir [Partage de courtier](sharing.md).

---

## ➕ Créer un courtier

1. Ouvrez **Courtiers** depuis la barre latérale et cliquez sur **Ajouter un courtier**.
2. Saisissez un **Nom** — le seul champ obligatoire — et définissez les options dont vous avez besoin.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Formulaire de modification du courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. Cliquez sur **Créer** : le courtier apparaît dans votre liste, prêt pour les transactions et les rapports.

??? info "⚙️ Les champs facultatifs — ce que fait chacun d'eux"

    - **Description** — vos propres notes.
    - **Plugin d'import par défaut** — l'importateur que l'[Assistant d'importation](../transactions/import/index.md) propose pour les fichiers de ce courtier.
    - **URL du portail** — le site web du courtier, ouvert depuis la page du courtier. L'icône du courtier est, dans cet ordre : votre **URL d'icône personnalisée** ; l'icône du **Plugin d'import par défaut**, lorsque cet importateur est conçu pour ce courtier ; l'icône du site web ; l'icône d'un importateur générique tel que le Generic CSV ; sinon une mallette.
    - **Compte ouvert** et **Compte actif** — la date d'ouverture du compte et s'il est toujours ouvert. Un courtier fermé apparaît en grisé dans la liste.
    - **Options de trading** — **Autoriser l'achat à effet de levier** et **Autoriser la vente à découvert**, expliquées dans [Options de trading](info.md#trading-options).
    - **Soldes initiaux** (uniquement à la création) — vos liquidités de départ. LibreFolio enregistre un **Dépôt** par devise, **daté d'aujourd'hui** : si l'argent était présent plus tôt, modifiez la date de ces dépôts sur la page [Transactions](../transactions/index.md).

??? warning "🏷️ « Un courtier nommé … existe déjà » — quand cela apparaît"

    Les noms de courtier sont uniques sur tout le serveur, pour tous ses utilisateurs. Choisissez un autre nom, ou renommez le courtier existant s'il vous appartient.

    Les courtiers d'autres utilisateurs que vous ne pouvez pas ouvrir sont listés sous **Autres courtiers existants**. Leur bouton de partage indique qui a accès, afin que vous sachiez à qui vous adresser : chaque utilisateur connecté de ce LibreFolio peut le voir, pour n'importe quel courtier.

---

## ✏️ Modifier ou supprimer un courtier

- **Modifier** — le crayon sur la carte du courtier, ou **Modifier** dans la barre d'outils du courtier. Les Propriétaires et les Éditeurs peuvent modifier un courtier.
- **Supprimer** — la corbeille sur la carte du courtier. Seul un Propriétaire peut supprimer un courtier. S'il contient encore des transactions, LibreFolio indique combien et propose **Aller aux transactions** ou **Supprimer le courtier et les transactions**, ce qui les supprime également. Les actifs qu'il a transférés à un autre courtier, y compris un courtier partagé, y restent en tant que position d'ouverture à leur coût de transfert, à compter de la date de transfert : le gain de ce courtier comptabilise alors aussi les gains accumulés avant le transfert. Les actifs qu'un autre courtier lui a transférés quittent ce dernier sous forme d'un ajustement qui retire les unités : il n'a pas de valeur, de sorte que les unités ne réduisent que la quantité et que leur coût compte comme une perte réalisée chez lui ([Ajustements sortants](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)). Les virements avec un autre courtier deviennent chez ce dernier un dépôt ou un retrait.

---

## 🗂️ À l'intérieur d'un courtier

La carte d'un courtier ouvre sa page sur l'onglet **Vue d'ensemble** :

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="detail" alt="Détail du courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

L'en-tête affiche, en haut, le nom du courtier, son icône et, sous forme de badge, votre rôle et votre part de propriété. La barre d'outils ci-dessous s'applique à chaque onglet :

- la **plage de dates** et la **Devise** des chiffres, avec la même liste que sur le Tableau de bord, **Créer un forex** inclus ;
- **Modifier** (Propriétaires et Éditeurs) et **Partager le courtier**, qui ouvre l'onglet **Info** ;
- **Export IA**, qui copie dans votre presse-papiers une invite prête à l'emploi concernant ce courtier — voir [Export IA du courtier](../ai-export/broker.md) ;
- **Actualiser**, qui recalcule la page à la demande.

En dessous, cinq onglets :

1. **Vue d'ensemble** — l'état du compte (ci-dessous).
2. **Positions** — ce que vous détenez chez ce courtier (ci-dessous).
3. **Risque** — l'analyse des risques du Tableau de bord, limitée à ce courtier (voir [Onglet Risque du Tableau de bord](../dashboard/index.md#risk-tab)).
4. **Transactions** — le grand livre du courtier, les saisies manuelles, les imports et les rapports téléversés (voir [Transactions du courtier](import.md)).
5. **Info** — les détails du compte, les options de trading et le partage (voir [Configuration & Info](info.md)).

---

## 🧭 La page du courtier est le Tableau de bord sur un seul courtier {: #broker-page-is-dashboard }

La page d'un courtier est le [Tableau de bord](../dashboard/index.md) avec ce courtier déjà sélectionné, plus l'onglet **Info** propre au courtier. Les contrôles, les onglets et leurs panneaux fonctionnent comme décrit dans les pages du Tableau de bord ; il n'y a pas de filtre par courtier, car la page correspond à un seul courtier.

Ce qui est identique au Tableau de bord :

- **Période, devise et boutons.** La plage de dates, le menu **Devise**, **Export IA** et **Actualiser** sont ceux du Tableau de bord. Lorsque vous n'avez pas utilisé la page pendant deux minutes, **Actualiser** devient **Mises à jour en pause**, au même endroit : cliquez dessus pour actualiser de nouveau les prix (voir **Prix live** sur la page [Actifs](../assets/index.md)).
- **Les soldes de trésorerie suivent la période.** Ils affichent les liquidités à la fin de la période choisie.
- **Lots.** **Analyser les lots** ouvre le détail des lots sous la liste ; le bouton **Retour** du navigateur le ferme. **Voir tout →** ouvre la page Actifs sur la même période.
- **Bannière de qualité des données.** Les prix anciens et les taux de change manquants ou anciens sont également signalés ici, avec les mêmes boutons **Synchroniser les prix** et **Synchroniser les taux** ([Bannière de qualité des données](../dashboard/index.md#data-quality-banner)). Chaque rôle les voit, y compris un Lecteur : ils mettent à jour les prix et les taux de change partagés, et non le courtier lui-même.

Ce qui est différent :

- **Le courtier entier.** Chaque montant de la page, Risque inclus, est le montant **entier** du courtier (100 %), même lorsque vous en détenez moins de 100 %. Le badge de l'en-tête indique votre rôle et votre part. Le Tableau de bord filtré sur le même courtier affiche votre part de celui-ci.
- **Les transactions suivent la période.** L'onglet Transactions liste les transactions de la plage de dates choisie dans la barre d'outils, et **Voir dans Transactions** ouvre la page [Transactions](../transactions/index.md) avec la même période. **Importer**, **Ajouter une transaction**, **Modifier**, **Cloner**, **Supprimer** et la barre de sélection sont réservés aux Propriétaires et aux Éditeurs ; un Lecteur voit le tableau, l'historique des imports et **Voir dans Transactions**.

---

## 📈 Onglet Vue d'ensemble

La **Vue d'ensemble** répond à la question « comment se porte ce compte ? » avec les mêmes blocs que la [Vue d'ensemble du Tableau de bord](../dashboard/index.md), limités à ce courtier :

- **Cartes KPI** — **P&L période**, **Rendements** et **Valeur nette** ([Cartes KPI](../dashboard/kpi-cards.md)).
- **Soldes de trésorerie** — les liquidités détenues ici à la fin de la période, par devise.
- **Graphique de croissance** — les vues **Abs**, **%** et **P&L**, avec le P&L en **Ligne**, **Chandeliers** ou **Revenus** ([Graphique de croissance du portefeuille](../dashboard/charts.md#portfolio-growth-chart), [Mode P&L](../dashboard/charts.md#pnl-mode)). La vue que vous choisissez est partagée avec le Tableau de bord.
- **Allocation** — par type, secteur et zone géographique ([Panneau d'allocation](../dashboard/charts.md#allocation-panel)).

Le retour sur un courtier que vous avez déjà ouvert affiche immédiatement ses derniers chiffres, actualisés en arrière-plan si quelque chose a changé ([Revenir et actualiser](../dashboard/index.md#coming-back-and-refreshing)). **Actualiser** recalcule à la demande, y compris l'onglet **Risque** et le panneau des lots.

---

## 🔍 Onglet Positions

L'onglet **Positions** liste ce que vous détenez chez ce courtier, dans le même panneau que les [Positions du Tableau de bord](../dashboard/positions.md) :

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Portefeuille (Tableau)" alt="Vue tableau du portefeuille du courtier">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Portefeuille (Carte / Treemap)" alt="Vue carte du portefeuille du courtier">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Période (Tableau)" alt="Vue tableau de la période du courtier">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Période (Carte / Graphique)" alt="Vue carte de la période du courtier">
</div>

- **Portefeuille** affiche vos positions (quantité, valeur, poids) ; **Période** affiche les gains et pertes de chaque position sur les dates sélectionnées. Les deux se présentent sous forme de **Tableau** ou de **Carte**.
- La colonne **YOC** correspond au [Rendement sur coût](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) de chaque position chez ce courtier.
- **Analyser les lots** ouvre le panneau [Analyse FIFO des lots](../dashboard/positions.md#fifo-lots-analysis) sous la liste : trouvez-le dans le menu **⋮** d'une ligne, ou faites un clic droit sur l'actif dans le tableau ou la carte.

---

## 📑 Dans cette section

- 📥 **[Transactions du courtier](import.md)** — ajoutez des transactions à ce courtier, importez des relevés et gérez ses rapports téléversés.
- ⚙️ **[Configuration & Info](info.md)** — détails du compte, options de trading et panneau de partage.
- 🧠 **[Export IA du courtier](../ai-export/broker.md)** — ce que contient un export de courtier, et les analyses que vous pouvez demander à une IA.
- 🤝 **[Partage de courtier](sharing.md)** — les rôles (Propriétaire, Éditeur, Lecteur) et les parts de propriété.

La page Courtiers, le formulaire **Ajouter un courtier** et la page du courtier disposent chacun d'un court guide contextuel : relancez-les depuis [Paramètres → Préférences → Prise en main et guides](../settings/preferences.md#onboarding-and-guides).
