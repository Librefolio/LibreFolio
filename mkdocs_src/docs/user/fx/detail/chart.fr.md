# 📉 Graphique Interactif

Le cœur de la page Détails de la Paire — un graphique complet **propulsé par ECharts** qui vous permet de visualiser l'historique des taux de change grâce à de puissants outils interactifs.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Graphique Détails FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Modes d'Affichage

Basculez entre deux modes d'affichage à l'aide de la barre d'outils :

- 📈 **Absolu** — Affiche les valeurs brutes du taux de change (ex: 1 EUR = 1,0845 USD). Idéal pour voir les niveaux de taux réels.
- 📊 **Pourcentage (%)** — Affiche la variation en pourcentage depuis le premier point de données visible. Idéal pour comparer les mouvements relatifs et superposer plusieurs signaux.

Lors du passage au mode %, tous les signaux superposés sont également recalculés en pourcentages à partir de leurs points de départ respectifs.

---

## 🔍 Navigation & Zoom

| Action | Bureau | Mobile |
|--------|---------|--------|
| **Déplacement** | Clic + glisser | Toucher + glisser |
| **Zoom avant** | Molette haut | Pincer vers l'extérieur |
| **Zoom arrière** | Molette bas | Pincer vers l'intérieur |
| **Réinitialiser le zoom** | Double-clic | Double-appui |

Vous pouvez également utiliser les **préréglages de plage temporelle** (1W, 1M, 3M, 6M, 1Y, 2Y) ou sélectionner une plage de dates **Personnalisée** pour accéder rapidement à des périodes spécifiques.

!!! info "Disponibilité des données"

    Si la plage temporelle sélectionnée dépasse les données disponibles, LibreFolio affiche tout ce qui est accessible. Utilisez **Sync** pour tenter de récupérer des données plus anciennes auprès du fournisseur — mais notez que certains fournisseurs ont une couverture historique limitée.

---

## 💬 Infobulle

Survolez n'importe quel point du graphique pour voir :

- 📅 La **date**
- 💱 Le **taux de change** avec une précision complète
- 📊 La **variation en pourcentage** par rapport au point de données précédent

---

## 🧰 Barre d'Outils

La barre d'outils du graphique permet un accès rapide à :

- 📊 **Interrupteur du mode d'affichage** — Absolu / Pourcentage
- ⏱️ **Plage temporelle** — 1W, 1M, 3M, 6M, 1Y, 2Y, Personnalisée
- 📈 **[Signaux](signals.md)** — Activer/désactiver les superpositions d'indicateurs techniques
- 📏 **[Mesures](measures.md)** — Outil de mesure par clics successifs
- ✏️ **[Éditeur de données](data-editor.md)** — Modifier des points de données individuels
- ⚙️ **[Paramètres du graphique](../chart-settings.md)** — Personnalisation visuelle

---

## 🔗 Liens connexes

- ⚙️ **[Paramètres du graphique](../chart-settings.md)** — Personnaliser les couleurs, la largeur des lignes, le remplissage de zone, la grille
- 📈 **[Signaux](signals.md)** — Superposer des indicateurs techniques sur le graphique
