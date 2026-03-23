# 📉 Graphique interactif

Le cœur de la page détail de la paire — un graphique complet **alimenté par ECharts** qui vous permet de visualiser l'historique des taux de change avec des outils interactifs puissants.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Graphique détaillé FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Modes d'affichage

Basculer entre deux modes via la barre d'outils :

- 📈 **Absolu** — Affiche les valeurs brutes du taux de change (ex. 1 EUR = 1,0845 USD). Idéal pour voir les niveaux réels du taux.
- 📊 **Pourcentage (%)** — Affiche la variation en pourcentage depuis le premier point de données visible. Idéal pour comparer les mouvements relatifs et superposer plusieurs signaux.

En passant en mode %, tous les signaux superposés sont également recalculés en pourcentage depuis leur point de départ respectif.

---

## 🔍 Navigation et zoom

| Action | Ordinateur | Mobile |
|--------|------------|--------|
| **Balayer** | Clic + glisser | Toucher + glisser |
| **Zoom avant** | Molette de souris vers le haut | Pincement écarter |
| **Zoom arrière** | Molette de souris vers le bas | Pincement rapprocher |
| **Réinitialiser le zoom** | Double-clic | Double-appui |

Vous pouvez également utiliser les **préréglages temporels** (1S, 1M, 3M, 6M, 1A, 2A) ou sélectionner une plage **Personnalisée** pour accéder rapidement à des périodes spécifiques.

!!! info "Disponibilité des données"

    Si la plage sélectionnée dépasse les données disponibles, LibreFolio affiche ce qui est disponible. Utilisez **Synchroniser** pour essayer de télécharger des données plus anciennes — mais notez que certains fournisseurs ont une couverture historique limitée.

---

## 💬 Infobulle

Survolez n'importe quel point du graphique pour voir :

- 📅 La **date**
- 💱 Le **taux de change** avec une précision complète
- 📊 Le **pourcentage de variation** par rapport au point de données précédent

---

## 🧰 Barre d'outils

La barre d'outils du graphique donne un accès rapide à :

- 📊 **Mode d'affichage** — Absolu / Pourcentage
- ⏱️ **Plage temporelle** — 1S, 1M, 3M, 6M, 1A, 2A, Personnalisée
- 📈 **[Signaux](signals.md)** — Activer les superpositions d'indicateurs techniques
- 📏 **[Mesures](measures.md)** — Outil de mesure clic à clic
- ✏️ **[Éditeur de données](data-editor.md)** — Modifier des points de données individuels
- ⚙️ **[Paramètres du graphique](../chart-settings.md)** — Personnalisation visuelle

---

## 🔗 Connexes

- ⚙️ **[Paramètres du graphique](../chart-settings.md)** — Personnaliser les couleurs, l'épaisseur de ligne, le remplissage de zone, la grille
- 📈 **[Signaux](signals.md)** — Superposer des indicateurs techniques sur le graphique
