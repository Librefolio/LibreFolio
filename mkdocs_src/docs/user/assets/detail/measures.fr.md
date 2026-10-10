# 📐 Mesures

L'outil Mesure répond à la question *de combien cela a-t-il changé entre ces deux jours ?* Choisissez deux points sur le graphique et lisez la variation de l'actif, et des lignes qui y sont tracées, entre ces points.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-measures" alt="Panneau des mesures de l'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Prendre une mesure

1. Cliquez sur **📏 Ajouter une mesure** en haut à droite du graphique : le panneau **Mesures** s'ouvre en dessous.
2. Cliquez sur le point de **début** sur le graphique, puis sur le point de **fin**.
3. La nouvelle mesure s'ouvre avec son tableau, et le graphique la trace dans sa propre couleur.

**+ Ajouter une mesure** dans l'en-tête du panneau mesure l'ensemble du graphique à la place, de son premier à son dernier point : pratique sur mobile. L'en-tête de chaque mesure contient sa couleur et 🗑️ pour la supprimer ; développez la mesure pour modifier ses dates.

Les mesures ne sont pas sauvegardées : le rechargement de la page vide le panneau. **Prix** et **Rendement glissant** conservent des mesures distinctes.

---

## 💵 En mode Prix

Le tableau comporte une ligne pour l'actif (une seconde dans sa propre devise lorsque le graphique est converti) et une pour chaque ligne tracée sur l'axe des prix, comme un actif de comparaison ou une moyenne mobile. À côté des valeurs **Début** et **Fin** :

- **Δ Abs** — la différence $V_{end} - V_{start}$, dans l'unité de la ligne.
- **Δ %** — la variation $\frac{V_{end} - V_{start}}{V_{start}}$ → [Rendements et taux de croissance](../../../financial-theory/fundamentals/returns.md)
- **Δ%/an** — la même variation en taux annuel sur les $d$ jours calendaires entre les points, $(1 + \Delta\%)^{365/d} - 1$ → [Rendements et taux de croissance](../../../financial-theory/fundamentals/returns.md)

La ligne de résumé de la mesure ajoute le nombre de jours.

---

## 📈 En mode Rendement glissant

Les valeurs sont déjà des rendements, le tableau les compare donc :

- **Début**, **Fin** — le rendement glissant à chacune des deux dates.
- **Δ pp** — Fin moins Début, en points de pourcentage → [Rendement glissant sur les jours calendaires](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar)
- **Jours** — les jours calendaires entre les deux points.

---

## 🔗 Voir aussi

- 📈 **[Graphique interactif](chart.md)** — Commandes du graphique et filtrage par plage de dates
- 📊 **[Signaux](signals.md)** — Superpositions d'indicateurs techniques
