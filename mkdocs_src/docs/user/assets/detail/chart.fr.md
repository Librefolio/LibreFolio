# 📈 Graphique interactif

Le graphique est le cœur de la page d'un actif : l'historique des prix, ou l'ampleur de la variation du prix sur une fenêtre glissante. Faites défiler pour zoomer, glissez pour vous déplacer et survolez un point pour afficher ses valeurs.

_Dernière mise à jour : 2026-10-08_

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Graphique des prix de l'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Prix ou rendement glissant {: #primary-modes }

Les deux boutons au-dessus du graphique déterminent ce qu'il trace :

- **Prix** — l'historique des prix, avec les [événements](events.md) de l'actif comme marqueurs.
- **Rendement glissant** — pour chaque date, la variation du prix sur une fenêtre que vous choisissez ([ci-dessous](#rolling-return)).

La page s'ouvre toujours sur **Prix**.

### 🗓️ Fenêtre du rendement glissant {: #rolling-return }

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart-rolling-return" alt="Graphique de l'actif en mode Rendement glissant, avec la fenêtre 1Y et un actif de comparaison" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Cette vue répond à la question : *de combien le prix a varié sur la fenêtre, à chaque date ?* Chaque point compare la clôture de ce jour avec la clôture exactement $N$ jours calendaires plus tôt :

$$
R(d) = \frac{P(d)}{P(d-N)} - 1
$$

où $P$ est la dernière clôture connue ce jour-là, dans la devise du graphique → [Rendement glissant sur jours calendaires](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar).

Choisissez $N$ avec le contrôle **Fenêtre** à côté des deux boutons :

- **1W**, **1M**, **3M**, **1Y** — 7, 30, 90 et 365 jours.
- **Personnalisé** — un nombre entier avec **W**, **M** ou **Y**, compté comme 7, 30 et 365 jours : `3M` correspond à 90 jours.
- **?** ouvre cette section du manuel.

La fenêtre peut être plus longue que les dates affichées à l'écran : LibreFolio va chercher les prix plus anciens dont il a besoin. Elle est mémorisée pour cet actif, dans ce navigateur.

Comment l'interpréter :

- **Au-dessus de zéro**, le prix est plus élevé qu'il y a $N$ jours ; **en dessous de zéro**, plus bas.
- **Survolez un point** : ↩ donne la date avec laquelle il est comparé ; 📅 et 💱 donnent les dates du prix et des taux de change réellement utilisés, lorsque l'un d'eux est plus ancien.
- Les **[comparaisons d'actifs](signals.md#data-comparison)** deviennent elles aussi des rendements glissants, avec la même fenêtre et la même devise.
- **Prix uniquement** : les dividendes, les intérêts et vos transactions ne sont pas inclus.

??? note "🧩 Lacunes et lignes courtes — quand l'historique est incomplet"

    Un point reste vide, jamais estimé, lorsque l'un de ses deux prix est manquant ou n'est pas positif. Chaque ligne commence à la première date où elle peut être calculée : un actif récent ou un taux de change manquant ne raccourcit donc que sa propre ligne, et un prix manquant plus tard laisse une lacune. Lorsque seule une partie de la plage peut être calculée, une note sous le graphique le signale ; lorsque rien ne peut l'être, un message remplace le graphique.

---

## 🎛️ Choisir ce que le graphique affiche

### 📅 Plage de dates

La plage de dates dans la barre d'outils de la page définit les dates affichées à l'écran : **1W**, **1M**, **3M**, **6M**, **1Y**, **2Y**, **YTD**, **MAX**, ou **Personnalisé** avec un calendrier. S'il reste de la place sur la barre, d'autres préréglages apparaissent (3Y, 5Y, 10Y, WTD, MTD, QTD). La plage que vous choisissez vous suit sur les pages Tableau de bord, courtier, actif et FX du même onglet de navigateur.

Sur une plage longue, le graphique peut regrouper les jours en semaines ou en mois pour rester lisible : un badge **Hebdomadaire** ou **Mensuel** en haut à gauche l'indique.

### 💱 Convertir dans une autre devise

**Convertir en**, à côté du prix, affiche le graphique dans une autre devise, avec une ligne 💱 en pointillés pour le prix dans la devise propre à l'actif. Le menu liste les devises que vos paires FX permettent d'atteindre ; **Créer un forex…** en bas de celui-ci permet d'ajouter une paire manquante. Les rendements glissants sont eux aussi calculés dans la devise choisie.

??? note "💱 Quand un taux de change est manquant"

    Une bannière au-dessus du graphique nomme la paire, avec un raccourci pour la créer ou l'ouvrir. Le bouton **Synchroniser** de la page télécharge les taux des paires qui existent ; il n'en crée jamais.

### 📊 Ligne ou chandeliers, Abs ou %

En mode **Prix**, les boutons en haut à gauche du graphique permettent de basculer :

- entre une **ligne** et des **chandeliers**, qui nécessitent les prix d'ouverture, haut et bas ;
- entre **Abs**, les prix, et **%**, la variation depuis le premier jour de la plage.

---

## 🧰 Outils sur le graphique

Les trois boutons en haut à droite du graphique :

- **📏 Ajouter une mesure** — comparez deux points : voir [Mesures](measures.md). **Prix** et **Rendement glissant** conservent des mesures distinctes.
- **✏️ Modifier les prix et événements** — ouvre l'[Éditeur de données](data-editor.md), en mode **Prix** uniquement.
- **⚙️ Esthétique** — **Remplissage d'aire**, **Couleurs de référence** (vert au-dessus de la valeur de départ, ou au-dessus de zéro en %, rouge en dessous), **Lignes de grille**, **Dégradé des valeurs obsolètes** (atténue les points dont le prix ou le taux de change est reporté depuis un jour antérieur) et **Échelle de l'axe Y** (**Auto**, **Inclure 0** ou limites **Personnalisées**). Les chandeliers désactivent le remplissage d'aire, les couleurs de référence et le dégradé des valeurs obsolètes.

Ces paramètres et vos signaux sont mémorisés pour cet actif, dans ce navigateur. Pour les modifier pour tous les actifs à la fois, utilisez **Paramètres** sur la [page Actifs](../index.md) : voir [Paramètres du graphique](../../fx/chart-settings.md).

---

## 🔗 Voir aussi

- 📊 **[Signaux](signals.md)** — Superposer des indicateurs techniques
- 📐 **[Mesures](measures.md)** — Mesurer les écarts de prix
- 📅 **[Événements](events.md)** — Comprendre les marqueurs d'événements
- 📚 **[Rendements et taux de croissance](../../../financial-theory/fundamentals/returns.md)** — Comment sont calculés les rendements simples, annualisés et glissants
- 🛠️ **[Fonctionnement interne du graphique](../../../developer/frontend/components/charts.md)** — Pour les développeurs : les deux modes, où réside l'état du graphique et comment la page se synchronise
