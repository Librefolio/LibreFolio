# 📉 Graphique interactif

Le cœur de la page de détail de la paire : l'historique des taux de la paire sur la période sélectionnée.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Graphique de détail FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Vue Abs ou %

Basculez avec **Abs** / **%** dans le coin supérieur gauche du graphique ; la page s'ouvre en vue %.

- 📊 **%** — la variation depuis le premier jour de la période. Les courbes superposées partent
  elles aussi de 0 %, ce qui permet de comparer leurs évolutions d'un coup d'œil.
- 📈 **Abs** — le taux lui-même, par ex. 1 EUR = 1,0845 USD.

---

## 🔍 Zoom, panoramique et période

| Action | Ordinateur | Mobile |
|--------|---------|--------|
| **Zoom** | Molette de la souris | Pincer |
| **Panoramique** | Cliquer et faire glisser | Faire glisser avec deux doigts (un doigt fait défiler la page) |

- **Période** : les préréglages **1W** à **2Y**, **YTD** et **Tout**, ou **Personnalisé** (un nombre de jours,
  de semaines, de mois ou d'années en remontant à partir d'aujourd'hui) ; cliquez sur les dates pour les choisir dans un calendrier. Les deux bornes
  doivent être des jours différents : le jour cliqué en premier ne peut pas être cliqué à nouveau, et une date saisie égale à
  l'autre borne devient rouge. D'autres préréglages apparaissent lorsque la barre d'outils dispose d'assez de place. Les pages du même
  onglet de navigateur partagent la période.
- Sur une période longue, le graphique regroupe les taux par semaine ou par mois et affiche un badge **Hebdomadaire** ou
  **Mensuel** : zoomez pour obtenir les taux quotidiens.
- Sur un écran étroit, l'axe affiche moins de dates et des dates plus courtes ; la première et la dernière restent toujours visibles.

??? info "📅 Historique plus court que la période — lorsque le graphique commence plus tard"

    Une bannière indique la date à partir de laquelle les données sont disponibles. **Synchroniser** peut récupérer des taux plus anciens, si le
    fournisseur les publie ; sinon, saisissez-les dans l'[Éditeur de données](data-editor.md).

---

## 💬 Infobulle

Survolez le graphique, ou touchez-le sur mobile, pour voir :

- 📅 la **date** (ou la semaine ou le mois, lorsque le graphique regroupe les taux) ;
- 💱 le **taux** et la valeur de chaque courbe superposée ;
- 📊 la **variation depuis le début de la période** : Δ et % en vue Abs, % en vue % ;
- ⚠️ **Obsolète depuis N jour(s)** les jours sans nouveau taux, comme les week-ends et les jours fériés.

---

## 🔁 Rendement glissant {: #rolling-return }

Deux boutons au-dessus du graphique permettent de choisir ce qu'il dessine : **Cours** (l'historique des taux, comme ci-dessus) et
**Rendement glissant**.

En **Rendement glissant**, chaque point répond à la question *de combien le taux a-t-il varié au cours des N derniers jours ?* Il
compare le taux de ce jour-là avec le taux N jours calendaires plus tôt. Exemple : sur EUR → USD avec la fenêtre **3M**
(90 jours), si le taux est de 1,0845 aujourd'hui et était de 1,0500 il y a quatre-vingt-dix jours, le point affiche
**+3,3 %**. Au-dessus de zéro, la première devise a acheté davantage de la seconde que N jours auparavant ; en dessous de zéro, moins.

- 🗓️ **Fenêtre** — à côté des deux boutons : **1W**, **1M**, **3M**, **1Y**, ou **Personnalisé** (un nombre
  entier de semaines, de mois ou d'années). Tant que vous n'en choisissez pas une, la fenêtre est automatique : le plus grand préréglage
  qui tient dans la période affichée. La fenêtre peut être plus longue que la période : LibreFolio lit les taux plus anciens
  dont il a besoin. Le bouton **?** ouvre la [même explication](../../assets/detail/chart.md#rolling-return)
  donnée pour les actifs, et l'aperçu des [Paramètres du graphique](../chart-settings.md#rolling-return-view) dessine
  aussi cette vue.
- 💱 **Comparer avec une autre paire** — ajoutez une **paire FX** dans le panneau [Signaux](signals.md#data-comparison) :
  chaque paire comparée dessine son propre rendement glissant, avec la même fenêtre. Dans ce mode, le panneau
  ne propose que ces comparaisons ; vos autres signaux restent enregistrés et reviennent avec **Cours**.
- 🔄 **Direction** — le rendement suit la direction affichée par la page, EUR → USD ou USD → EUR.
- 📏 ✏️ **Mesure** et **Modifier les taux** sont masqués : ils agissent sur les taux, ils appartiennent donc à **Cours**.
- 💾 **Mémorisé** — le mode et la fenêtre sont enregistrés avec les paramètres du graphique de cette paire, dans ce
  navigateur. La carte de la paire dans la liste FX les partage : une carte en **Rendement glissant** ouvre la page dans
  ce mode, et la page se rouvre dans le mode dans lequel vous l'avez laissée. Le retour à **Cours** est immédiat.

Changer la période, la fenêtre, la direction ou les paires comparées, ou cliquer sur **Actualiser**,
recalcule le rendement, et un indicateur de chargement s'affiche jusqu'à l'arrivée du résultat. Si aucun rendement ne peut être
calculé, le graphique affiche la raison au lieu d'une courbe.

---

## 🧰 Boutons du graphique

- 📏 **Mesure** — voir [Mesures](measures.md). **Cours** uniquement.
- ✏️ **Modifier les taux** — voir [Éditeur de données](data-editor.md). **Cours** uniquement.
- ⚙️ **Esthétique** — couleurs, remplissage, grille et plages d'axes, comme dans les [Paramètres du graphique](../chart-settings.md).
- 📊 Le panneau **Signaux** au-dessus du graphique — voir [Signaux](signals.md).

---

## 🔗 Voir aussi

- ⚙️ **[Paramètres du graphique](../chart-settings.md)** — Apparence du graphique et signaux superposés
- 📈 **[Signaux](signals.md)** — Indicateurs techniques sur le graphique
