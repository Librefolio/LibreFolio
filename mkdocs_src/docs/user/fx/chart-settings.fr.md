# ⚙️ Paramètres des Graphiques

LibreFolio propose une fenêtre modale de **Paramètres des Graphiques** pour personnaliser l'apparence et le comportement des graphiques FX. Ces paramètres s'appliquent à la fois aux mini-graphiques de la [page Liste FX](index.md) et au graphique complet de la [page Détails de la Paire](detail/index.md).

---

## 🔓 Accéder aux Paramètres des Graphiques

Vous pouvez ouvrir la fenêtre des Paramètres des Graphiques depuis :

- 📋 La **page Liste FX** — via le bouton de paramètres (⚙️) dans la barre d'outils
- 📊 La **page Détails de la Paire** — via le bouton de paramètres du graphique

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Fenêtre Paramètres des Graphiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Paramètres Disponibles

### 🎨 Apparence

| Paramètre | Description |
|-----------|-------------|
| **Couleur de la ligne** | Couleur principale de la ligne du graphique |
| **Épaisseur de la ligne** | Épaisseur de la ligne du graphique (px) |
| **Remplissage de la zone** | Activer/désactiver le remplissage en dégradé sous la ligne |
| **Lignes de grille** | Afficher/masquer les lignes de grille horizontales et verticales |

### 🖱️ Infobulles et Interaction

| Paramètre | Description |
|-----------|-------------|
| **Format de l'infobulle** | Nombre de décimales affichées dans les infobulles |
| **Réticule** | Activer/désactiver le réticule au survol |
| **Zoom** | Paramètres de zoom via la molette de la souris et le pincement |

### 📈 Superposition de Signaux

Lors de l'utilisation du graphique de la page de détails, vous pouvez configurer les **indicateurs techniques** affichés en superposition :

#### 🧮 Signaux Calculés

Ceux-ci sont calculés à partir des données propres à la paire :

- 📉 **EMA** (Exponential Moving Average)
- 📊 **MACD** (Moving Average Convergence Divergence)
- 💪 **RSI** (Relative Strength Index)
- 📏 **Bandes de Bollinger**

Chaque signal peut être basculé via un interrupteur indépendamment depuis le [panneau des Signaux](detail/signals.md).

#### 🔍 Signaux Comparatifs et Benchmarks

Vous pouvez également superposer des **comparaisons de benchmarks** pour voir comment une paire performe par rapport à une référence :

- 📐 **Benchmarks Synthétiques** — Paniers personnalisés ou taux de référence calculés
- ↔️ **Superpositions de paires** — Comparer l'EUR/USD par rapport au GBP/USD sur le même graphique

Pour les fondements mathématiques, consultez [Indicateurs Techniques](../../financial-theory/technical-analysis/indicators/index.md) et [Benchmarks Synthétiques](../../financial-theory/technical-analysis/synthetic-benchmarks/index.md).

---

## 💾 Persistance

Les paramètres des graphiques sont stockés localement dans le `localStorage` de votre navigateur et s'appliquent à toutes les paires de devises. Ils sont conservés entre les sessions — même après avoir fermé et rouvert le navigateur — et ne seront perdus que si vous videz le cache/stockage de votre navigateur ou si le stockage expire (cela dépend du navigateur, généralement de quelques mois à plusieurs années).
