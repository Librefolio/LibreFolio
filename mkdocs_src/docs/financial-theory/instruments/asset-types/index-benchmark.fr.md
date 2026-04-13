# ![](../../../static/icons/asset-types/other.png){: width="32" style="vertical-align: middle;" } Indice & Benchmark

Un **indice** est une mesure statistique d'une section du marché financier. Il suit la performance d'un groupe d'actifs et sert de **benchmark** par rapport auquel les investisseurs mesurent la performance de leur propre portefeuille.

---

## 🔑 Caractéristiques Clés

| Propriété | Détail |
|----------|--------|
| **Négociable ?** | Pas directement — mais les ETF et les contrats à terme suivent des indices |
| **Exemples** | S&P 500, MSCI World, FTSE 100, DAX, Nikkei 225 |
| **Utilisation dans LibreFolio** | Référence pour le signal [Comparaison d'actifs](../../../user/assets/detail/signals.md) |
| **Prix** | Calculé à partir de la pondération des composants, non négocié sur une place boursière |

---

## 📊 Comment sont construits les indices

### 📈 Méthodes de pondération

| Méthode | Formule | Exemple |
|--------|---------|---------|
| **Pondération par la capitalisation** | Pondération ∝ capitalisation boursière de l'entreprise | S&P 500, MSCI World |
| **Pondération par le prix** | Pondération ∝ cours de l'action | Dow Jones, Nikkei 225 |
| **Équipondérée** | Tous les composants ont la même pondération | S&P 500 Equal Weight |

### 🔄 Rééquilibrage

Les indices sont périodiquement rééquilibrés — des composants sont ajoutés, supprimés ou leur pondération est modifiée. Cela se produit généralement trimestriellement. Les ETF qui suivent l'indice doivent ajuster leurs positions en conséquence.

---

## 📐 Utilisation des benchmarks dans LibreFolio

LibreFolio propose deux types de benchmarks :

### 📊 Benchmarks réels (Comparaison d'actifs)

Comparez le graphique de votre actif avec un autre actif réel (par exemple, comparez votre action avec l'ETF S&P 500). Ceci utilise la superposition du signal **Comparaison d'actifs**.

### 🎯 Benchmarks synthétiques

Des courbes de référence mathématiques qui répondent à la question « et si mon actif avait progressé de X % par an ? » :

- **[Croissance linéaire](../../technical-analysis/synthetic-benchmarks/linear.md)** — Modèle d'intérêt simple
- **[Croissance composée](../../technical-analysis/synthetic-benchmarks/compound.md)** — Modèle d'intérêts composés
- **[Onde sinusoïdale](../../technical-analysis/synthetic-benchmarks/sine-wave.md)** — Référence cyclique pour la saisonnalité

---

## 🔗 Liens connexes

- 📊 **[ETF](etfs.md)** — Instruments qui suivent des indices
- 🎯 **[Benchmarks synthétiques](../../technical-analysis/synthetic-benchmarks/index.md)** — Courbes de référence mathématiques
- 📈 **[Rendements et taux de croissance](../../fundamentals/returns.md)** — Mesurer la performance par rapport au benchmark
