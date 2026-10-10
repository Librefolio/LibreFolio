# 💼 Actifs

Les actifs sont les instruments que vous détenez ou que vous suivez : actions, ETF, obligations, crypto, ou un compte d’épargne à intérêts programmés. La page **Actifs** les liste tous, chacun avec un petit graphique de prix, et ouvre la page de détail de n’importe lequel d’entre eux.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vue grille" alt="Page de la liste des actifs (grille)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vue tableau" alt="Page de la liste des actifs (tableau)">
</div>

## 📌 Qu’est-ce qu’un actif ?

Chaque actif possède :

- **un nom et des identifiants** — ISIN, ticker ou autres codes ;
- **un type** — action, ETF, obligation, crypto, matière première… ([types d’actifs](../../financial-theory/instruments/asset-types/index.md)) ;
- **une devise** — celle dans laquelle ses prix sont cotés ;
- **un fournisseur de prix**, facultatif — il télécharge pour vous le prix actuel et l’historique ([Fournisseurs](providers/index.md)) ;
- **une distribution sectorielle et géographique**, facultative ;
- **des événements** — dividendes, divisions, intérêts… ([Événements d’un actif](detail/events.md)).

Les actifs sont partagés par toutes les personnes de ce LibreFolio : vos transactions déterminent lesquels sont les vôtres.

## 📋 Parcourir la liste

Ouvrez **Actifs** dans la barre latérale, puis :

- **Choisissez une disposition** — les deux boutons à côté de **Ajouter un actif** basculent entre des cartes avec un petit graphique (**Vue grille**) et un tableau triable (**Vue tableau**). Votre choix est mémorisé dans ce navigateur.
- **Choisissez la période** — la plage de dates définit la période des graphiques des cartes et de la variation qu’elles affichent. Dans le tableau, les colonnes **Δ** donnent la variation sur un jour et sur chaque période, de 1W à 5Y, qui tient dans la plage.
- **Filtrer** — saisissez dans **Rechercher des actifs...** pour filtrer par nom, et choisissez une ou plusieurs devises et types dans les deux menus ; le ✕ efface la recherche et les deux menus.
- **Afficher les actifs archivés** — au départ, la liste n’affiche que les actifs **Actif** : activez **Inactif** pour ajouter les archivés, ou désactivez **Actif** pour ne voir que ceux-là.

Cliquez sur une carte ou une ligne pour ouvrir la **[page de détail](detail/index.md)** de l’actif. Là, les flèches **‹ ›** parcourent les actifs dans l’ordre où cette liste les affiche, filtres et tri compris.

??? note "📉 Abs ou % sur les cartes — vue grille uniquement"

    **Abs / %** dans la barre d’outils fait basculer chaque carte, son graphique et sa variation, entre prix et pourcentages ; le bouton **%** d’une carte ne change que cette carte, jusqu’à ce que vous modifiiez à nouveau la barre d’outils. La page s’ouvre toujours sur **%**.

??? note "⚙️ L’apparence des graphiques des cartes"

    **Paramètres** dans la barre d’outils définit en une fois l’apparence et les superpositions de tous les graphiques des actifs, et son application remplace les paramètres propres à chaque actif, pages de détail incluses. Le ⚙️ d’une carte ne modifie que cette carte. Voir [Paramètres du graphique](../fx/chart-settings.md).

### 🗂️ Vos actifs, les actifs des autres utilisateurs, suivis

Les deux dispositions divisent la liste en trois panneaux au maximum, chacun avec son nombre ; un panneau vide n’est pas affiché.

| Panneau | Ce qu’il contient |
|---|---|
| **Vos actifs** | Actifs détenus actuellement dans un courtier que vous possédez |
| **Actifs des autres utilisateurs** | Actifs détenus actuellement uniquement par d’autres utilisateurs — dans des courtiers que vous ne possédez pas |
| **Suivis** | Actifs que personne ne détient actuellement — jamais achetés ou déjà vendus, gardés à l’œil |

Ce qui compte, c’est la position **aujourd’hui** : lorsque vous vendez toute votre position, l’actif passe dans *Actifs des autres utilisateurs* si quelqu’un d’autre le détient encore, et dans *Suivis* sinon. Les courtiers partagés avec vous en tant qu’**Éditeur** ou **Lecteur** comptent comme des courtiers d’autres utilisateurs, et une position réduite à un reliquat négligeable compte comme non détenue.

Dans la vue tableau, chaque panneau est un tableau avec ses propres pages ; redimensionner, déplacer ou masquer une colonne : ces opérations s’appliquent aux trois.

## 🔄 Garder les prix à jour

- **Tout synchroniser** ouvre une fenêtre où **Démarrer la synchronisation** télécharge les derniers prix de chaque actif doté d’un fournisseur ; **Tout recharger** recharge la liste à partir de ce que LibreFolio a stocké. Dans l’onglet **[Corrélation](correlation.md)**, ils deviennent **Synchroniser la sélection**, qui télécharge aussi les taux de change servant à convertir les actifs sélectionnés, et **Tout recharger**, qui recalcule toutes les analyses.
- **Prix live** — tant que cette page ou la page d’un actif est ouverte et que la plage de dates se termine aujourd’hui, les prix se rafraîchissent d’eux-mêmes de temps à autre. Un prix passe au vert lorsqu’il a augmenté depuis le rafraîchissement précédent, au rouge lorsqu’il a baissé ; quand le marché est fermé, vous voyez la dernière clôture, sans couleur.
- **En arrière-plan**, le serveur rafraîchit les prix selon un calendrier défini par votre administrateur ([Planificateur de données de marché](../../admin/settings.md#market-data-scheduler)). Le tableau de bord affiche les prix stockés.

## 🖱️ Agir sur un actif

Chaque carte a ses propres boutons ; dans le tableau, le **⋮** en fin de ligne, ou un clic droit, ouvre les mêmes actions :

- **Synchroniser** — télécharge les prix de l’actif pour la période sélectionnée. Cela nécessite un fournisseur, et le tableau bloque également cette action pour un actif archivé.
- **Recharger** — recharge ses prix à partir de ce que LibreFolio a stocké.
- **Fusionner avec…** — fusionne un doublon dans un autre actif, qui conserve tout ([Créer et modifier](create-edit.md)).
- **Supprimer** — supprime un actif qu’aucune transaction n’utilise.

Dans le tableau, cochez plusieurs lignes pour les **Synchroniser**, les **Recharger** ou les **Supprimer** ensemble.

??? warning "🗑️ Quand un actif ne peut pas être supprimé"

    Un actif n’est pas supprimé tant que **la moindre** transaction l’utilise, même une transaction dans un courtier que vous ne pouvez pas voir. Le résultat indique combien de transactions l’utilisent, avec un lien **Transactions** filtré sur cet actif. Cette page n’affiche que les courtiers auxquels vous avez accès, elle peut donc lister moins de transactions que le nombre affiché.

## 🧭 Fonctionnalités

### ➕ [Créer et modifier](create-edit.md)

Créez un actif, connectez-le à un fournisseur de prix et gardez ses détails exacts.

### 🧪 [Onglet Corrélation](correlation.md)

Comparez une sélection d’actifs côte à côte — matrice de corrélation, pertes, risque par rapport au rendement, et rejeu historique, en pourcentages uniquement.

### 📊 [Page de détail d’un actif](detail/index.md)

Le graphique de prix avec ses signaux, ses mesures et ses événements, l’éditeur de données, et la classification.

### 🔌 [Fournisseurs](providers/index.md)

Des prix automatiques depuis Yahoo Finance, justETF, Borsa Italiana, le CSS Scraper, ou le moteur d’investissement programmé.

---

## 🔗 Voir aussi

- 📚 **[Théorie financière — Types d’actifs](../../financial-theory/instruments/asset-types/index.md)** — Action, ETF, Obligation, Crypto, etc.
- 💱 **[Taux de change](../fx/index.md)** — Taux utilisés pour la conversion entre devises
- 🛠️ **[Prix live](../../developer/frontend/components/features/live-ticker.md)** — Pour les développeurs : comment les pages interrogent les prix live
