# 📈 Signaux

Le panneau Signaux vous permet de superposer des **indicateurs techniques** sur le graphique FX. Ceux-ci sont calculés en temps réel à partir des données de taux de change et vous aident à identifier les tendances, les changements de momentum et les schémas de volatilité.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Panneau des signaux FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicateurs disponibles

### 📉 [EMA — Moyenne Mobile Exponentielle](../../../financial-theory/technical-analysis/indicators/ema.md)

Lisse le bruit des taux quotidiens pour révéler la **tendance sous-jacente**. En FX, lorsqu'une EMA croise la ligne de taux vers le haut, cela suggère souvent un affaiblissement de la devise de base (ou un renforcement de la devise de contrepartie). Période configurable : plus elle est courte, plus l'indicateur est réactif ; plus elle est longue, plus la courbe est lisse.

### 📊 [MACD — Convergence et Divergence des Moyennes Mobiles](../../../financial-theory/technical-analysis/indicators/macd.md)

Mesure le **momentum** en calculant la différence entre une EMA rapide et une EMA lente. Un MACD positif signifie que l'EMA rapide est au-dessus de l'EMA lente (haussier), un MACD négatif signifie l'inverse (baissier). Utile en FX pour détecter les retournements de tendance et les changements de momentum.

- 📈 **Ligne MACD** : Différence entre l'EMA rapide et l'EMA lente
- 〰️ **Ligne de Signal** : EMA de la ligne MACD elle-même (momentum lissé)
- 📊 **Histogramme** : Différence visuelle entre les lignes MACD et de Signal

### 💪 [RSI — Indice de Force Relative](../../../financial-theory/technical-analysis/indicators/rsi.md)

Un **oscillateur** (0–100) qui mesure la vitesse et l'ampleur des variations de prix. En FX, des valeurs supérieures à 70 peuvent suggérer que la paire de devises est surachetée, et des valeurs inférieures à 30 suggèrent qu'elle est survendue. Utile pour repérer les retournements potentiels.

### 📏 [Bandes de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

Une **enveloppe de volatilité** autour du prix. Les bandes s'élargissent pendant les périodes volatiles et se contractent pendant les périodes calmes. En FX, un taux touchant la bande supérieure peut signaler des conditions de surachat, tandis qu'un contact avec la bande inférieure peut signaler une survente.

- 〰️ **Bande centrale** : Moyenne Mobile Simple (SMA)
- 🔺 **Bande supérieure** : SMA + 2 écarts-types
- 🔻 **Bande inférieure** : SMA − 2 écarts-types

---

## 🛠️ Mode d'emploi

1. Cliquez sur l'interrupteur **Signaux** (📈) dans la barre d'outils du graphique
2. Le panneau des signaux s'ouvre sous le graphique
3. Ajoutez des indicateurs via les menus déroulants catégorisés (Indicateurs techniques, Comparaison de données, Benchmarks synthétiques)
4. Les paramètres de chaque indicateur peuvent être ajustés en ligne
5. Les signaux sont rendus sous forme de superpositions directement sur le graphique

---

## 📚 Approfondissement : Théorie Financière

Pour un traitement mathématique complet de chaque indicateur — incluant les formules, les équivalents en traitement du signal et l'interprétation pratique :

:material-book-open-variant: **[Indicateurs Techniques — Théorie Financière](../../../financial-theory/technical-analysis/indicators/index.md)**

Cette page de référence couvre :

- 🔢 Les **formules mathématiques** derrière chaque indicateur
- 🎛️ Les équivalents en **traitement du signal** (EMA = filtre IIR, SMA = filtre FIR, etc.)
- ⚡ L'intuition **"rapide vs lent"** en termes de fréquences de coupure des filtres
- 📈 Des **exemples pratiques** de détection de croisement et d'identification de tendance
