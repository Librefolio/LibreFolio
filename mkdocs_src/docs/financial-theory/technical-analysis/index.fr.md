# 📊 Analyse Technique

L'analyse technique étudie les **schémas de prix et la dynamique du marché** pour identifier les tendances, l'élan (momentum) et la volatilité. Contrairement à l'analyse fondamentale (qui évalue la valeur intrinsèque d'une entreprise), l'analyse technique se concentre uniquement sur les données historiques de prix et de volume.

---

## 📖 Sommaire

### 📉 [Indicateurs](indicators/index.md)

Superpositions de graphiques qui extraient des informations de tendance, de momentum, de volatilité ou de volume à partir des données de marché. LibreFolio implémente **17 indicateurs backend**, chacun expliqué sous un angle **financier** et un angle de **traitement du signal** :

- 📈 **[Tendance](indicators/trend.md)** — EMA, SMA, KAMA, ADX, Aroon
- ⚡ **[Momentum](indicators/momentum.md)** — RSI, MACD, ROC, Stochastic RSI, PPO, CCI
- 🌊 **[Volatilité](indicators/volatility.md)** — Bandes de Bollinger, ATR, NATR, Canaux de Donchian
- 📊 **[Volume](indicators/volume.md)** — OBV, MFI

### 🎯 [Benchmarks Synthétiques](synthetic-benchmarks/index.md)

Courbes de référence mathématiques superposées aux graphiques pour comparaison. Contrairement aux indicateurs (calculés *à partir* des données de marché), les benchmarks sont générés purement à partir de paramètres :

- **[Croissance Linéaire](synthetic-benchmarks/linear.md)** — Modèle d'intérêt simple
- **[Croissance Composée](synthetic-benchmarks/compound.md)** — Modèle d'intérêts composés
- **[Onde Sinusoïdale](synthetic-benchmarks/sine-wave.md)** — Référence cyclique pour la saisonnalité

---

## ⚡ L'intuition "Rapide" vs "Lente"

En finance, les termes *rapide* et *lent* font référence à la **constante de temps** ($\tau$) du filtre sous-jacent.

| Propriété | Rapide (petit $N$) | Lent (grand $N$) |
|---|---|---|
| Fréquence de coupure $f_c$ | Plus élevée | Plus basse |
| Rejet du bruit | Faible — laisse passer les hautes fréquences (HF) | Bon — lissage important |
| Déphasage | Faible — réagit rapidement | Élevé — retard significatif |
| $N$ typique | 9, 12, 14 | 26, 50, 200 |

---

## 🔗 Sections Connexes

- 🏦 **[Instruments](../instruments/index.md)** — Les actifs analysés par ces indicateurs
- 📐 **[Fondamentaux](../fundamentals/index.md)** — Rendements, conventions de comptage des jours
- 📈 **[Théorie du Portefeuille](../portfolio-theory/index.md)** — Métriques de risque et allocation
