# 💼 Actifs

Les actifs sont les instruments que vous détenez ou que vous suivez : actions, ETF, obligations, crypto, ou un compte d'épargne avec intérêts programmés. La page **Actifs** les liste tous, chacun avec un petit graphique de cours, et ouvre la page de détail de n'importe lequel d'entre eux.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vue en grille de cartes" alt="Page de liste des actifs (grille)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vue en tableau de données" alt="Page de liste des actifs (tableau)">
</div>

## 📌 Qu'est-ce qu'un actif ?

Chaque actif possède :

- **un nom et des identifiants** — ISIN, ticker ou autres codes ;
- **un type** — action, ETF, obligation, crypto, matière première… ([types d'actifs](../../financial-theory/instruments/asset-types/index.md)) ;
- **une devise** — celle dans laquelle ses cours sont cotés ;
- **un fournisseur de cours**, facultatif — il télécharge le cours actuel et l'historique à votre place ([Fournisseurs](providers/index.md)) ;
- **une distribution sectorielle et géographique**, facultative ;
- **des événements** — dividendes, divisions, intérêts… ([Événements d'un actif](detail/events.md)).

Les actifs sont partagés par tous les utilisateurs de ce LibreFolio : ce sont vos transactions qui décident lesquels sont les vôtres.

## 📋 Parcourir la liste

Ouvrez **Actifs** dans la barre latérale, puis :

- **Choisissez une disposition** — les deux boutons à côté de **Ajouter un actif** basculent entre des cartes avec un petit graphique (**Vue en grille**) et un tableau triable (**Vue en tableau**). Votre choix est mémorisé dans ce navigateur.
- **Choisissez la période** — la plage de dates définit la période des graphiques des cartes et de la variation qu'ils affichent. Lorsque le graphique d'une carte regroupe les jours en semaines ou en mois parce que la zone de tracé est trop étroite pour autant de jours, un petit badge **Hebdomadaire** ou **Mensuel** en haut à gauche l'indique, comme sur le [graphique de la page de détail](detail/chart.md). Dans le tableau, les colonnes **Δ** donnent la variation sur un jour et sur chaque période, de 1W à 5Y, qui tient dans la plage.
- **Filtrez** — saisissez dans **Rechercher des actifs...** pour filtrer par nom, et choisissez une ou plusieurs devises et types dans les deux menus ; le ✕ efface la recherche et les deux menus.
- **Afficher les actifs archivés** — la liste n'affiche au départ que les actifs **Actifs** : activez **Inactifs** pour y ajouter les archivés, ou désactivez **Actifs** pour ne voir que ceux-là.

Cliquez sur une carte ou sur une ligne pour ouvrir la **[page de détail](detail/index.md)** de l'actif. Là, les flèches **‹ ›** parcourent les actifs dans l'ordre où cette liste les affiche, filtres et tri compris.

??? note "📉 Abs, % ou Rolling Return sur les cartes — vue en grille uniquement"

    Le sélecteur de la barre d'outils propose trois options : l'icône de courbe, la même que sur les cartes, pour les cours absolus (son infobulle indique **Afficher en absolu**), **%** (la variation sur la période) et l'icône de calendrier pour le **Rolling Return**. Votre choix s'applique à toutes les cartes, à leur graphique et à leur variation, et il est mémorisé dans ce navigateur, pour votre utilisateur, avec les paramètres du graphique.

    Le bouton de vue d'une carte passe à la vue suivante, **%** → **Rolling Return** → **Abs** → **%**, et affiche la vue vers laquelle il va basculer. Une carte conserve son propre choix, même après un rechargement, jusqu'à ce que vous changiez à nouveau la barre d'outils : cela réinitialise toutes les cartes sur la vue de la barre d'outils.

    En **Rolling Return**, une carte trace le rendement glissant de l'actif, le même rendement sur fenêtre calendaire que le mode **Rolling Return** de la [page de détail de l'actif](detail/index.md), et par-dessus, les rendements glissants des comparaisons d'actifs enregistrées sur cette carte. Les autres indicateurs restent enregistrés, simplement masqués dans cette vue. Le cours et la variation en haut de la carte ne changent pas. Si l'actif a moins d'historique que la fenêtre, la carte affiche un court message à la place du graphique.

    La fenêtre se choisit dans les [Paramètres du graphique](../fx/chart-settings.md) : 1W, 1M, 3M, 1Y ou une fenêtre personnalisée. Tant que vous n'en choisissez pas, elle est automatique : le plus grand préréglage qui tient dans la période affichée dans la liste ; ainsi, une plage de 3 mois utilise 3M et une plage d'un an ou plus utilise 1Y.

    La [page de détail](detail/index.md) de l'actif s'ouvre dans la vue de sa carte, et avec la fenêtre Rolling Return de la carte. Une vue choisie à cet endroit devient celle de la carte.

??? note "⚙️ L'apparence des graphiques des cartes"

    **Paramètres** dans la barre d'outils définit l'apparence et les superpositions de tous les graphiques d'actifs d'un coup, et son application remplace les paramètres propres à chaque actif, pages de détail comprises. Le ⚙️ d'une carte ne modifie que cette carte. Voir [Paramètres du graphique](../fx/chart-settings.md).

### 🗂️ Vos actifs, les actifs des autres utilisateurs, les actifs suivis

Les deux dispositions répartissent la liste en trois panneaux au maximum, chacun avec son nombre ; un panneau vide n'est pas affiché.

| Panneau | Ce qu'il contient |
|---|---|
| **Vos actifs** | Actifs détenus aujourd'hui dans un courtier que vous possédez |
| **Actifs des autres utilisateurs** | Actifs détenus aujourd'hui uniquement par d'autres utilisateurs — dans des courtiers que vous ne possédez pas |
| **Suivis** | Actifs que personne ne détient actuellement — jamais achetés ou déjà vendus, gardés sous surveillance |

Ce qui compte, c'est la position **aujourd'hui** : lorsque vous vendez toute votre position, l'actif passe dans *Actifs des autres utilisateurs* si quelqu'un d'autre le détient encore, et dans *Suivis* sinon. Les courtiers partagés avec vous en tant qu'**Éditeur** ou **Lecteur** comptent comme des courtiers d'autres utilisateurs, et une position ramenée à un reliquat négligeable compte comme non détenue.

Dans la vue en tableau, chaque panneau est un tableau avec ses propres pages ; redimensionner, déplacer ou masquer une colonne s'applique aux trois.

## 🔄 Garder les cours à jour

- **Tout synchroniser** ouvre une fenêtre où **Démarrer la synchronisation** télécharge les derniers cours de chaque actif disposant d'un fournisseur ; **Tout recharger** recharge la liste à partir de ce que LibreFolio a enregistré. Survolez **Paramètres**, **Tout synchroniser** ou **Tout recharger** pendant une demi-seconde pour lire ce que fait le bouton. Lorsque la période contient déjà des cours enregistrés pour certains actifs, la fenêtre vous le signale avant de démarrer : la synchronisation les remplace par les valeurs du fournisseur, vos modifications manuelles comprises. Dans l'onglet **[Corrélation](correlation.md)**, ces boutons deviennent **Synchroniser la sélection**, qui télécharge aussi les taux de change servant à convertir les actifs sélectionnés, et **Tout recharger**, qui recalcule toutes les analyses.
- **Prix live** — tant que la plage de dates se termine aujourd'hui, les prix se rafraîchissent d'eux-mêmes : chaque minute sur cette page, toutes les 30 secondes sur la page d'un actif. Un prix passe au vert lorsqu'il a augmenté depuis le rafraîchissement précédent, au rouge lorsqu'il a baissé ; quand le marché est fermé, vous voyez la dernière clôture, sans couleur. Pour épargner le serveur et les fournisseurs de cours, le rafraîchissement se met en pause lorsque l'onglet du navigateur est en arrière-plan, et après deux minutes sans utiliser la page : une petite étiquette **Mises à jour en pause** s'affiche alors en haut de la page. Il n'y a rien à cliquer : dès que vous revenez sur l'onglet, que vous bougez la souris ou que vous appuyez sur une touche, les prix se rafraîchissent à nouveau d'eux-mêmes.
- **En arrière-plan**, le serveur rafraîchit les cours selon un calendrier défini par votre administrateur ([Planificateur de données de marché](../../admin/settings.md#market-data-scheduler)). Le tableau de bord affiche les cours enregistrés.

## 🖱️ Agir sur un actif

Chaque carte a ses propres boutons ; dans le tableau, le **⋮** en fin de ligne, ou un clic droit, ouvre les mêmes actions :

- **Synchroniser** — télécharge les cours de l'actif pour la période sélectionnée. Cela nécessite un fournisseur, et le tableau le bloque aussi pour un actif archivé.
- **Recharger** — recharge ses cours à partir de ce que LibreFolio a enregistré.
- **Fusionner avec…** — intègre un doublon à un autre actif, qui conserve tout ([Créer et modifier](create-edit.md)).
- **Supprimer** — supprime un actif qu'aucune transaction n'utilise, avec son fournisseur, ses cours et ses événements (dividendes, divisions…).

Dans le tableau, cochez plusieurs lignes pour **Synchroniser**, **Recharger** ou **Supprimer** ces lignes ensemble.

??? warning "🗑️ Quand un actif ne peut pas être supprimé"

    Un actif n'est pas supprimé tant qu'**une** transaction l'utilise, même une transaction dans un courtier que vous ne pouvez pas voir. Le résultat indique combien de transactions l'utilisent, avec un lien **Transactions** filtré sur cet actif. Cette page n'affiche que les courtiers auxquels vous avez accès ; elle peut donc lister moins de transactions que le décompte.

    Lorsque la liste compte déjà des transactions pour l'actif, sa confirmation s'ouvre directement sur ce résultat, sans bouton **Supprimer** : il n'y a rien à confirmer. Sinon, le résultat apparaît après votre confirmation, et LibreFolio vérifie encore avant de supprimer.

## 🧭 Fonctionnalités

### ➕ [Créer et modifier](create-edit.md)

Créez un actif, connectez-le à un fournisseur de cours et tenez ses informations à jour.

### 🧪 [Onglet Corrélation](correlation.md)

Comparez une sélection d'actifs côte à côte — matrice de corrélation, pertes, risque face au rendement et rejeu historique, en pourcentages uniquement.

### 📊 [Page de détail d'un actif](detail/index.md)

Le graphique de cours avec ses signaux, ses mesures et ses événements, l'éditeur de données et la classification.

### 🔌 [Fournisseurs](providers/index.md)

Des cours automatiques depuis Yahoo Finance, justETF, Borsa Italiana, le CSS Scraper ou le moteur d'investissement programmé.

---

## 🔗 Voir aussi

- 📚 **[Théorie financière — Types d'actifs](../../financial-theory/instruments/asset-types/index.md)** — Action, ETF, Obligation, Crypto, etc.
- 💱 **[Taux de change](../fx/index.md)** — Taux de change des devises utilisés pour la conversion entre devises
- 🛠️ **[Prix live](../../developer/frontend/components/features/live-ticker.md)** — Pour les développeurs : comment les pages interrogent les prix live
