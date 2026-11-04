# 📐 Mesures

Le panneau Mesures vous indique comment le taux de change a évolué entre deux points du graphique : la
variation, la variation en % et le taux annuel.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Panneau des mesures FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Effectuer une mesure

### 📏 Étape 1 : Activer le mode de mesure

Cliquez sur 📏 (**Ajouter une mesure**) en haut à droite du graphique. Le panneau **Mesures** sous le
graphique s'ouvre et affiche **Active — cliquez sur le graphique**.

### 📍 Étape 2 : Cliquer sur le point de départ

Une infobulle indique la date et le taux que vous avez choisis ; une ligne en tirets suit le
pointeur.

### 🏁 Étape 3 : Cliquer sur le point d'arrivée

La mesure est ajoutée et le mode de mesure se désactive. Les deux dates sont automatiquement remises
dans l'ordre.

??? tip "➕ Toute la période en un clic — pratique sur un téléphone"

    Le bouton **+** de la barre **Mesures** mesure la période sélectionnée de son premier taux à son
    dernier, sans cliquer sur le graphique.

---

## 📊 Lire une mesure

Chaque mesure est une carte affichant ses dates, la variation en % et le nombre de jours
calendaires ; vous pouvez aussi définir la couleur et le style de sa ligne. Dépliez-la pour modifier
les dates et voir **Début**, **Fin**, **Δ Abs**, **Δ %** et **Δ%/an** pour la paire et pour chaque
superposition sur le même axe.

**Δ%/an** est le taux annuel (CAGR), où $d$ est le nombre de jours calendaires entre les deux
dates :

$$
\Delta\%_{yr} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Il apparaît à partir de 30 jours : un intervalle plus court affiche `—`, comme partout dans LibreFolio. Une
ligne qui part de 0 affiche `—` pour **Δ %** et **Δ%/an**.

Voir [Rendements et taux de croissance — Théorie financière](../../../financial-theory/fundamentals/returns.md)
pour les rendements logarithmiques et la capitalisation.

---

## 🔁 Plusieurs mesures

Chaque nouvelle mesure s'ajoute à côté des autres, avec sa propre couleur ; 🗑️ en supprime une.
Elles restent jusqu'à ce que vous quittiez la page.

---

## 💡 Astuces

- 🔍 **Zoomez** avant de cliquer, pour viser les points exacts.
- 📰 Comparez l'évolution **avant et après un événement**, comme l'annonce d'une banque centrale.
- ⚠️ **Δ%/an** attend 30 jours, car la capitalisation gonfle les mouvements courts : 1 % en 7 jours
  donnerait environ 68 % par an.
