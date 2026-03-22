# ⚙️ Paramètres du graphique

LibreFolio propose une fenêtre modale **Paramètres du graphique** pour personnaliser l'apparence et le comportement des graphiques FX. Ces paramètres s'appliquent à la fois aux mini-graphiques de la [page Liste FX](index.md) et au graphique complet de la [page de détail de la paire](detail/index.md).

---

## 🔓 Accéder aux paramètres du graphique

Vous pouvez ouvrir la fenêtre modale des paramètres du graphique depuis :

- 📋 La **page Liste FX** — via le bouton des paramètres (⚙️) dans la barre d'outils
- 📊 La **page de détail de la paire** — via le bouton des paramètres du graphique

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Fenêtre modale Paramètres du graphique" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Paramètres disponibles

### 🎨 Apparence

| Paramètre | Description |
|-----------|-------------|
| **Couleur de la ligne** | Couleur principale de la ligne du graphique |
| **Épaisseur de la ligne** | Épaisseur de la ligne du graphique (px) |
| **Remplissage dégradé sous la ligne** | Active/désactive le remplissage dégradé sous la ligne |
| **Lignes de grille** | Afficher/masquer les lignes de grille horizontales et verticales |

### 🖱️ Info-bulle & Interaction

| Paramètre | Description |
|-----------|-------------|
| **Format de l'info-bulle** | Nombre de décimales affichées dans les info-bulles |
| **Réticule** | Active/désactive le réticule au survol |
| **Zoom** | Paramètres de zoom avec la molette de la souris et le pincement |

### 📈 Superposition des signaux

Lorsque vous utilisez le graphique de la page de détail, vous pouvez configurer les **indicateurs techniques** affichés en superposition :

#### 🧮 Signaux calculés

Ces signaux sont calculés à partir des données propres à la paire :

- 📉 **EMA** (Moyenne Mobile Exponentielle)
- 📊 **MACD** (Convergence/Divergence de Moyennes Mobiles)
- 💪 **RSI** (Indice de Force Relative)
- 📏 **Bandes de Bollinger**

Chaque signal peut être activé/désactivé indépendamment depuis le [panneau Signaux](detail/signals.md).

#### 🔍 Signaux comparatifs & Références

Vous pouvez également superposer des **comparaisons avec des références** pour voir comment une paire se comporte par rapport à une référence :

- 📐 **Références synthétiques** — Paniers personnalisés ou taux de référence calculés
- ↔️ **Superpositions de paires croisées** — Comparez EUR/USD avec GBP/USD sur le même graphique

Pour les fondements mathématiques, consultez [Indicateurs techniques](../../financial-theory/technical-indicators.md) et [Références synthétiques](../../financial-theory/synthetic-benchmarks.md).

---

## 💾 Persistance

Les paramètres du graphique sont stockés localement dans votre navigateur et s'appliquent à toutes les paires de devises. Ils sont conservés entre les sessions.
