# 📈 Signaux

Le panneau Signaux vous permet de superposer des **indicateurs techniques** sur le graphique des changes. Ils sont calculés en temps réel à partir des données de taux de change et vous aident à identifier les tendances, les changements de dynamique et les modèles de volatilité.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Panneau des signaux de devises" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicateurs disponibles

### 📉 [EMA — Moyenne Mobile Exponentielle](../../../financial-theory/technical-analysis/indicators/ema.md)

Lisse le bruit des taux quotidiens pour révéler la **tendance sous-jacente**. En FX, une EMA croisant au-dessus de la ligne du taux suggère souvent un affaiblissement de la devise de base (ou un renforcement de la devise de cotation). Période configurable : plus courte = plus réactive, plus longue = plus lisse.

### 📊 [MACD — Convergence/Divergence des Moyennes Mobiles](../../../financial-theory/technical-analysis/indicators/macd.md)

Mesure la **dynamique** en calculant la différence entre une EMA rapide et une EMA lente. Un MACD positif signifie que l'EMA rapide est au-dessus de l'EMA lente (haussier), négatif signifie l'inverse (baissier). Utile en FX pour détecter les inversions de tendance et les changements de dynamique.

- 📈 **Ligne MACD** : Différence entre l'EMA rapide et l'EMA lente
- 〰️ **Ligne de signal** : EMA de la ligne MACD elle-même (dynamique lissée)
- 📊 **Histogramme** : Différence visuelle entre les lignes MACD et de signal

### 💪 [RSI — Indice de Force Relative](../../../financial-theory/technical-analysis/indicators/rsi.md)

Un **oscillateur** (0–100) qui mesure la vitesse et l'amplitude des changements de prix. Des valeurs au-dessus de 70 suggèrent un surachat et en dessous de 30 une survente.

### 📏 [Bandes de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

Une **enveloppe de volatilité** autour du prix. Les bandes s'élargissent pendant les périodes volatiles et se contractent pendant les périodes calmes.

- 〰️ **Bande médiane** : Moyenne Mobile Simple (SMA)
- 🔺 **Bande supérieure** : SMA + 2 écarts-types
- 🔻 **Bande inférieure** : SMA − 2 écarts-types

---

## 🛠️ Comment les utiliser

1. Cliquez sur le bouton bascule **Signaux** (📈) dans la barre d'outils du graphique
2. Le panneau des signaux s'ouvre sous le graphique
3. Ajoutez des indicateurs depuis les menus déroulants catégorisés (Indicateurs Techniques, Comparaison de Données, Benchmarks Synthétiques)
4. Les paramètres de chaque indicateur peuvent être ajustés directement en ligne
5. Les signaux s'affichent en superposition directement sur le graphique

---

## 📚 Approfondissement : Théorie financière

Pour un traitement mathématique complet de chaque indicateur — incluant les formules, les équivalents en traitement du signal et l'interprétation pratique :

:material-book-open-variant: **[Indicateurs techniques — Théorie financière](../../../financial-theory/technical-analysis/indicators/index.md)**

Cette page de référence couvre :

- 🔢 Les **formules mathématiques** derrière chaque indicateur
- 🎛️ Les **équivalents en traitement du signal** (EMA = filtre IIR, SMA = filtre FIR, etc.)
- ⚡ L'intuition **"rapide vs lent"** en termes de fréquences de coupure de filtre
- 📈 Des **exemples pratiques** de détection de croisement et d'identification de tendance
