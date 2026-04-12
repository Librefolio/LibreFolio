# 📚 Théorie Financière

Cette section documente les modèles financiers, les conventions et les définitions utilisés tout au long de LibreFolio.

## 📖 Aperçu

Des calculs financiers précis sont essentiels pour un suivi de portefeuille. LibreFolio implémente des conventions financières standards pour garantir la cohérence avec les rapports des courtiers et les données réelles. Cette section est organisée en quatre domaines thématiques.

## 🗺️ Carte Conceptuelle

### 🏦 [Instruments](instruments/index.md)

Les éléments constitutifs de tout portefeuille :

- **[Types d'actifs](instruments/asset-types/index.md)** — Actions, ETF, Obligations, Crypto, Immobilier, Indices
- **[Types de transactions](instruments/transaction-types/index.md)** — Achat/Vente, Dépôt/Retrait, Dividende, Frais, Intérêts, Transfert
- **[Événements d'actifs](instruments/asset-events/index.md)** — Dividende, Intérêts, Division d'actions, Ajustement de prix, Règlement à l'échéance

### 📊 [Analyse Technique](technical-analysis/index.md)

Superpositions de graphiques basées sur les données et courbes de référence mathématiques :

- **[Indicateurs](technical-analysis/indicators/index.md)** — EMA, MACD, RSI, Bandes de Bollinger
- **[Benchmarks synthétiques](technical-analysis/synthetic-benchmarks/index.md)** — Croissance Linéaire, Croissance Composée, Onde Sinusoïdale

### 📐 [Fondamentaux](fundamentals/index.md)

Concepts financiers de base :

- **[Conventions de décompte des jours](fundamentals/day-count.md)** — ACT/365, ACT/360, 30/360, ACT/ACT
- **[Rendements & Taux de croissance](fundamentals/returns.md)** — Rendements simples vs log, CAGR, annualisation
- **[Fiscalité](fundamentals/taxation.md)** — Plus-values, report d'impôt, Capitalisation vs Distribution

### 📈 [Théorie du Portefeuille](portfolio-theory/index.md)

Théorie Moderne du Portefeuille et gestion des risques :

- **[Diversification](portfolio-theory/diversification.md)** — Corrélation, risque systématique vs idiosyncrasique
- **[Allocation d'actifs](portfolio-theory/asset-allocation.md)** — Stratégique, tactique, trajectoires de glissement, rééquilibrage
- **[Métriques de risque](portfolio-theory/risk-metrics/index.md)** — Sharpe, Sortino, Perte maximale (Max Drawdown), Volatilité
