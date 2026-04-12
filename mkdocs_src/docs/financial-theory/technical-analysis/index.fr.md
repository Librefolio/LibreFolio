# 📊 Analyse Technique

L'analyse technique étudie les **schémas de prix et la dynamique du marché** pour identifier les tendances, l'élan (momentum) et la volatilité. Contrairement à l'analyse fondamentale (qui évalue la valeur intrinsèque d'une entreprise), l'analyse technique se concentre uniquement sur les données historiques de prix et de volume.

---

## 📖 Sommaire

### 📉 [Indicateurs](indicators/index.md)

Superpositions de graphiques qui extraient des informations de tendance, de momentum ou de volatilité à partir des données de prix. LibreFolio implémente quatre indicateurs principaux, chacun expliqué sous un angle **financier** et un angle de **traitement du signal** :

- **[EMA](indicators/ema.md)** — Moyenne Mobile Exponentielle (suivi de tendance)
- **[MACD](indicators/macd.md)** — Convergence et Divergence des Moyennes Mobiles (momentum)
- **[RSI](indicators/rsi.md)** — Indice de Force Relative (surachat/survente)
- **[Bandes de Bollinger](indicators/bollinger-bands.md)** — Enveloppe de volatilité adaptative

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
