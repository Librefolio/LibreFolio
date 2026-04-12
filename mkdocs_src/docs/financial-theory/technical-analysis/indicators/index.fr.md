# 📉 Indicateurs Techniques

LibreFolio propose quatre indicateurs techniques sous forme de superpositions de graphiques. Chaque indicateur est expliqué selon deux perspectives complémentaires : l'interprétation **financière** utilisée quotidiennement par les traders, et l'équivalent en **traitement du signal** que les ingénieurs reconnaîtront instantanément.

!!! info "Pourquoi deux perspectives ?"

    Les marchés financiers ne sont **pas** des systèmes LTI (Linéaires et Invariants dans le Temps) stationnaires — ils
    sont bruités, chaotiques, et leur contenu spectral évolue avec le temps. Pourtant, les outils mathématiques
    que nous appliquons pour extraire la tendance, le momentum ou la volatilité sont *exactement* les mêmes
    filtres à temps discret enseignés dans tout cours de traitement du signal.

---

## 📋 Aperçu des Indicateurs

| Indicateur | Ce qu'il mesure | Utilisation clé | Détails |
|-----------|-----------------|---------|---------|
| **EMA** | Direction de la tendance | Détection de croisement doré/de la mort | [📖](ema.md) |
| **MACD** | Momentum / accélération de la tendance | Croisements haussiers/baissiers | [📖](macd.md) |
| **RSI** | Surachat / survente | Configurations de retour à la moyenne | [📖](rsi.md) |
| **Bandes de Bollinger** | Enveloppe de volatilité | Détection de compression (squeeze) → cassure (breakout) | [📖](bollinger-bands.md) |

---

## 🔗 Liens connexes

- 🎯 **[Benchmarks Synthétiques](../synthetic-benchmarks/index.md)** — Courbes de référence mathématiques
- 📈 **[Graphique Interactif](../../../user/assets/detail/chart.md)** — Affichage des indicateurs
- 📊 **[Signaux](../../../user/assets/detail/signals.md)** — Comment configurer les superpositions dans LibreFolio
