# 📉 Graphique interactif

Le cœur de la page de détail d'une paire : l'historique du taux de la paire sur la période sélectionnée.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Graphique de détail FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Vue Abs ou en %

Basculez avec **Abs** / **%** dans le coin supérieur gauche du graphique ; la page s'ouvre en vue %.

- 📊 **%** — la variation depuis le premier jour de la période. Les superpositions partent elles aussi
  de 0 %, ce qui permet de comparer leurs évolutions d'un coup d'œil.
- 📈 **Abs** — le taux lui-même, par ex. 1 EUR = 1.0845 USD.

---

## 🔍 Zoom, déplacement et période

| Action | Ordinateur | Mobile |
|--------|---------|--------|
| **Zoom** | Molette de la souris | Pincement |
| **Déplacement** | Cliquer et glisser | Glisser avec deux doigts (un doigt fait défiler la page) |

- **Période** : les préréglages **1W** à **2Y**, **YTD** et **Tout**, ou **Personnalisé** (un nombre
  de jours, de semaines, de mois ou d'années en arrière à partir d'aujourd'hui) ; cliquez sur les dates pour
  les choisir dans un calendrier. D'autres préréglages apparaissent lorsque la barre d'outils dispose
  de suffisamment de place. Les pages d'un même onglet de navigateur partagent la période.
- Sur une période longue, le graphique regroupe les taux par semaine ou par mois et affiche un badge
  **Hebdomadaire** ou **Mensuel** : zoomez pour obtenir les taux quotidiens.
- Sur un écran étroit, l'axe affiche moins de dates, et des dates plus courtes ; la première et la dernière
  restent toujours visibles.

??? info "📅 Historique plus court que la période — quand le graphique commence plus tard"

    Une bannière indique la date à partir de laquelle les données sont disponibles. **Sync** peut
    récupérer des taux plus anciens, si le fournisseur les publie ; sinon, saisissez-les dans
    l'[éditeur de données](data-editor.md).

---

## 💬 Infobulle

Survolez le graphique, ou touchez-le sur mobile, pour voir :

- 📅 la **date** (ou la semaine ou le mois, lorsque le graphique regroupe les taux) ;
- 💱 le **taux** et la valeur de chaque superposition ;
- 📊 la **variation depuis le début de la période** : Δ et % en vue Abs, % en vue % ;
- ⚠️ **Obsolète : N jour(s) d'ancienneté** les jours sans nouveau taux, comme les week-ends et les jours fériés.

---

## 🧰 Boutons du graphique

- 📏 **Mesure** — voir [Mesures](measures.md).
- ✏️ **Modifier les taux** — voir [éditeur de données](data-editor.md).
- ⚙️ **Esthétique** — couleurs, remplissage, grille et plages d'axes, comme dans [paramètres du graphique](../chart-settings.md).
- 📊 Le panneau **Signaux** au-dessus du graphique — voir [Signaux](signals.md).

---

## 🔗 Voir aussi

- ⚙️ **[paramètres du graphique](../chart-settings.md)** — Apparence du graphique et signaux de superposition
- 📈 **[Signaux](signals.md)** — Indicateurs techniques sur le graphique
