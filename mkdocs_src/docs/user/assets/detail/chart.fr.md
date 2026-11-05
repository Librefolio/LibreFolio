# 📈 Graphique interactif

Le graphique est le cœur de la page d'un actif : l'historique des prix, ou l'ampleur de la variation du prix sur une fenêtre glissante. Faites défiler pour zoomer, glissez pour déplacer la vue et survolez un point pour afficher ses valeurs.

_Dernière mise à jour : 2026-10-22_

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Graphique des prix de l'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Prix ou rendement glissant {: #primary-modes }

Les deux boutons au-dessus du graphique déterminent ce qu'il dessine :

- **Prix** — l'historique des prix, avec les [événements](events.md) de l'actif comme marqueurs.
- **Rendement glissant** — pour chaque date, la variation du prix sur une fenêtre que vous choisissez ([ci-dessous](#rolling-return)).

La page s'ouvre dans la vue que présente la carte de cet actif sur la [page Actifs](../index.md) : **Abs** ou **%** ouvrent le mode **Prix** dans cette vue, **Rendement glissant** ouvre le mode **Rendement glissant**. Changez le mode ici, ou cliquez sur **Abs** ou **%** sous **Prix**, et cela devient la vue de l'actif : sa carte et votre prochaine visite s'ouvriront dans cette vue. Ce choix est mémorisé dans ce navigateur, pour votre compte utilisateur, en même temps que les paramètres du graphique ; l'interrupteur de la liste réinitialise chaque carte, et donc chaque page de détail, à la vue de la liste.

### 🗓️ Fenêtre de rendement glissant {: #rolling-return }

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart-rolling-return" alt="Graphique d'un actif en mode Rendement glissant avec la fenêtre 1Y et un actif de comparaison" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Cette vue répond à la question : *de combien le prix a-t-il varié sur la fenêtre, à chaque date ?* Chaque point compare la clôture de ce jour avec la clôture exactement $N$ jours calendaires plus tôt :

$$
R(d) = \frac{P(d)}{P(d-N)} - 1
$$

où $P$ est la dernière clôture connue ce jour-là, dans la devise du graphique → [Rendement glissant sur jours calendaires](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar).

Choisissez $N$ avec le contrôle **Fenêtre** à côté des deux boutons :

- **1W**, **1M**, **3M**, **1Y** — 7, 30, 90 et 365 jours.
- **Personnalisé** — un nombre entier suivi de **W**, **M** ou **Y**, comptés comme 7, 30 et 365 jours : `3M` correspond à 90 jours.
- **?** ouvre cette section du manuel.

La fenêtre peut dépasser la plage de dates affichée : LibreFolio lit les prix plus anciens dont il a besoin. Elle est identique à celle de la carte de l'actif : celle choisie pour cet actif ou, tant que vous n'en choisissez pas, une fenêtre automatique — le plus grand préréglage adapté à la plage affichée (environ 3 mois → 3M, un an ou plus → 1Y, moins d'une semaine → 1W). Une fenêtre choisie ici est conservée pour cet actif, dans ce navigateur.

Comment le lire :

- **Au-dessus de zéro**, le prix est plus élevé que $N$ jours auparavant ; **en dessous de zéro**, plus bas.
- **Survolez un point** : ↩ indique la date à laquelle il est comparé ; 📅 et 💱 donnent les dates du prix et des taux de change réellement utilisés, lorsque l'un d'eux est plus ancien.
- Les **[comparaisons d'actifs](signals.md#data-comparison)** deviennent aussi des rendements glissants, avec la même fenêtre et la même devise.
- **Prix uniquement** : les dividendes, les intérêts et vos transactions ne sont pas inclus.

??? note "🧩 Trous et lignes courtes — quand l'historique est incomplet"

    Un point reste vide, jamais estimé, lorsque l'un de ses deux prix est manquant ou non positif. Chaque ligne commence à la première date où elle peut être calculée ; ainsi, un actif récent ou un taux de change manquant ne raccourcit que sa propre ligne, et un prix qui manque par la suite laisse un trou. Lorsque seule une partie de la plage peut être calculée, une note sous le graphique l'indique ; lorsque rien ne peut l'être, un message remplace le graphique.

---

## 🎛️ Choisir ce que le graphique affiche

### 📅 Plage de dates

La plage de dates de la barre d'outils de la page définit les dates affichées : **1W**, **1M**, **3M**, **6M**, **1Y**, **2Y**, **YTD**, **Tout** ou **Personnalisé**, un nombre de jours, de semaines, de mois ou d'années en remontant à partir d'aujourd'hui ; cliquez sur une date pour choisir les deux bornes sur un calendrier. Les deux bornes doivent être des jours différents : le jour que vous cliquez en premier ne peut pas être cliqué à nouveau, et une date saisie égale à l'autre borne devient rouge. S'il reste de la place sur la barre, d'autres préréglages apparaissent (3Y, 5Y, 10Y, WTD, MTD, QTD). La plage que vous choisissez vous suit sur les pages du tableau de bord, du courtier, de l'actif et des FX du même onglet de navigateur.

Sur une plage longue, le graphique peut regrouper les jours en semaines ou en mois pour rester lisible : un badge **Hebdomadaire** ou **Mensuel** en haut à gauche l'indique.

### 💱 Convertir vers une autre devise

**Convertir vers**, à côté du prix, affiche le graphique dans une autre devise, avec une ligne 💱 en pointillés pour le prix dans la devise propre de l'actif. Le menu liste les devises que vos paires FX peuvent atteindre ; **Créer une paire FX…** en bas du menu ajoute une paire manquante. Les rendements glissants sont eux aussi calculés dans la devise choisie.

??? note "💱 Quand un taux de change est manquant"

    Une bannière au-dessus du graphique nomme la paire, avec un raccourci pour la créer ou l'ouvrir. Le bouton **Sync** de la page télécharge les taux des paires qui existent ; il ne crée jamais de paire.

### 📊 Ligne ou chandeliers, Abs ou %

En mode **Prix**, les boutons en haut à gauche du graphique permettent de basculer :

- entre une **ligne** et des **chandeliers**, qui nécessitent les prix d'ouverture, de plus haut et de plus bas ;
- entre **Abs**, les prix, et **%**, la variation depuis le premier jour de la plage.

---

## 🧰 Outils du graphique

Les trois boutons en haut à droite du graphique :

- **📏 Ajouter une mesure** — comparez deux points : voir [Mesures](measures.md). **Prix** et **Rendement glissant** conservent des mesures séparées.
- **✏️ Modifier les prix et les événements** — ouvre l'[Éditeur de données](data-editor.md), en mode **Prix** uniquement.
- **⚙️ Esthétique** — **Remplissage de la zone**, **Couleurs de la ligne de base** (vert au-dessus de la valeur de départ, ou au-dessus de zéro en %, rouge en dessous), **Lignes de grille**, **Dégradé des données obsolètes** (atténue les points dont le prix ou le taux de change est reporté depuis un jour antérieur) et **Échelle de l'axe Y** (**Auto**, **Inclure 0** ou limites **Personnalisées**). Les chandeliers désactivent le remplissage de la zone, les couleurs de la ligne de base et le dégradé des données obsolètes.

Ces paramètres et vos signaux sont mémorisés pour cet actif, dans ce navigateur. Pour les modifier pour tous les actifs à la fois, utilisez **Paramètres** sur la [page Actifs](../index.md) : voir [Paramètres du graphique](../../fx/chart-settings.md).

---

## 🔗 Voir aussi

- 📊 **[Signaux](signals.md)** — Superposer des indicateurs techniques
- 📐 **[Mesures](measures.md)** — Mesurer les écarts de prix
- 📅 **[Événements](events.md)** — Comprendre les marqueurs d'événements
- 📚 **[Rendements et taux de croissance](../../../financial-theory/fundamentals/returns.md)** — Comment sont calculés les rendements simples, annualisés et glissants
- 🛠️ **[Fonctionnement interne du graphique](../../../developer/frontend/components/charts.md)** — Pour les développeurs : les deux modes, où réside l'état du graphique et comment la page se synchronise
