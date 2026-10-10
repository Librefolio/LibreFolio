# 📉 Indicateurs techniques

LibreFolio expose **22 indicateurs techniques calculés côté backend**, groupés par la caractéristique de marché qu'ils mesurent. Les mêmes formules mathématiques alimentent les graphiques d'actifs, les graphiques FX compatibles, les annotations et les consommateurs analytiques tels que l'export IA.

Les indicateurs comptent des **séances**, pas des jours calendaires : une séance est un jour où la série a sa propre cotation — un prix pour un actif, un taux publié pour une paire FX. Un jour que la série comble avec la dernière valeur connue — un week-end, un jour férié de marché, tout jour sans cotation — n'est pas une séance, pas plus qu'un prix stocké daté d'un week-end ou d'un jour férié de marché qui ne fait que répéter la clôture précédente (un [report stocké](../risk-metrics/data-quality.md#stored-carries)). Les périodes, le préchauffage et l'historique minimum se comptent tous en séances : la SMA 200 fait donc la moyenne des 200 dernières séances, soit environ 290 jours calendaires. Le graphique conserve ses dates calendaires : un indicateur n'a de valeurs que les jours de séance, et sa ligne enjambe les jours de fermeture intermédiaires. La seule exception à fenêtre calendaire est le rendement glissant calendaire derrière le [mode Rendement glissant](../../../user/assets/detail/chart.md#primary-modes) du graphique, qui compare chaque date à la clôture résolue exactement $N$ jours calendaires plus tôt.

!!! info "Les champs de prix comptent"

    Tous les indicateurs ne peuvent pas s'exécuter sur toutes les séries. **9 des 22**
    sont des indicateurs basés uniquement sur le cours de clôture et fonctionnent à la
    fois sur les actifs et les taux de change (EMA, SMA, KAMA, MACD, RSI, ROC, PPO,
    RSI stochastique, bandes de Bollinger). Les indicateurs qui nécessitent les champs
    Haut, Bas ou Volume sont réservés aux actifs et se déclarent indisponibles lorsque
    ces champs n'existent pas. La famille **Risque** est également réservée aux actifs :
    aucune mesure de risque glissante n'est produite pour les paires FX.

---

## 📈 Tendance

Les indicateurs de tendance lissent le cours ou déterminent si un mouvement directionnel est établi.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **EMA** | Où se situe la tendance récente pondérée ? | Clôture | [📖](ema.md) |
| **SMA** | Quel est le prix moyen équipondéré ? | Clôture | [📖](sma.md) |
| **KAMA** | Comment le lissage doit-il s'adapter au bruit ? | Clôture | [📖](kama.md) |
| **ADX** | Quelle est la force de la tendance ? | Haut, Bas, Clôture | [📖](adx.md) |
| **Aroon** | À quand remontent les nouveaux extrêmes ? | Haut, Bas | [📖](aroon.md) |

➡️ [Vue d'ensemble du groupe Tendance](trend.md)

---

## ⚡ Momentum

Les indicateurs de momentum mesurent la vitesse, la pression directionnelle et l'accélération.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **RSI** | Les acheteurs ou les vendeurs dominent-ils ? | Clôture | [📖](rsi.md) |
| **MACD** | Le momentum de la tendance s'accélère-t-il ? | Clôture | [📖](macd.md) |
| **ROC** | À quelle vitesse le prix a-t-il varié ? | Clôture | [📖](roc.md) |
| **RSI stochastique** | Où se situe le RSI dans sa fourchette récente ? | Clôture | [📖](stochastic-rsi.md) |
| **PPO** | Quel est le momentum des moyennes mobiles en pourcentage ? | Clôture | [📖](ppo.md) |
| **CCI** | À quelle distance le prix se situe-t-il de sa moyenne statistique récente ? | Haut, Bas, Clôture | [📖](cci.md) |

➡️ [Vue d'ensemble du groupe Momentum](momentum.md)

---

## 🌊 Volatilité

Les indicateurs de volatilité mesurent l'amplitude, la dispersion et la largeur des canaux plutôt que la direction.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **Bandes de Bollinger** | Quelle est la largeur de l'enveloppe statistique des prix ? | Clôture | [📖](bollinger-bands.md) |
| **ATR** | Quelle est l'amplitude réelle typique ? | Haut, Bas, Clôture | [📖](atr.md) |
| **NATR** | Quelle est l'ampleur de la volatilité par rapport au prix ? | Haut, Bas, Clôture | [📖](natr.md) |
| **Canaux de Donchian** | Quels sont le plus haut et le plus bas de la période ? | Haut, Bas | [📖](donchian-channels.md) |

➡️ [Vue d'ensemble du groupe Volatilité](volatility.md)

---

## 📊 Volume

Les indicateurs de volume combinent la direction du prix avec l'activité de négociation.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **OBV** | Le volume signé indique-t-il une accumulation ou une distribution ? | Clôture, Volume | [📖](obv.md) |
| **MFI** | Le flux monétaire indique-t-il une pression acheteuse ou vendeuse ? | Haut, Bas, Clôture, Volume | [📖](mfi.md) |

➡️ [Vue d'ensemble du groupe Volume](volume.md)

---

## ⚠️ Risque

Les indicateurs de risque transforment la série de prix elle-même en une mesure de risque glissante. Ils sont **réservés aux actifs** — les paires FX n'en produisent pas.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **Drawdown depuis le sommet** | De combien le prix est-il inférieur à son plus haut cumulé ? | Clôture | [📖](../risk-metrics/max-drawdown.md) |
| **Rendement glissant** | À combien s'élève le rendement composé de la dernière fenêtre ? | Clôture | [📖](../../fundamentals/returns.md) |
| **Volatilité glissante** | Quelle est la dispersion des rendements récents ? | Clôture | [📖](../risk-metrics/volatility.md) |
| **Ratio de Sharpe glissant** | Le rendement excédentaire compense-t-il le risque pris ? | Clôture | [📖](../risk-metrics/sharpe-ratio.md) |
| **Bêta glissant** | Quelle est la sensibilité de l'actif à un actif de comparaison ? | Clôture + actif de comparaison | — |

➡️ [Vue d'ensemble des métriques de risque](../risk-metrics/index.md)

---

## 🔗 Liens connexes

- 🎯 **[Benchmarks synthétiques](../synthetic-benchmarks/index.md)** — Courbes de référence mathématiques
- 📈 **[Graphique interactif](../../../user/assets/detail/chart.md)** — Où les indicateurs sont affichés
- 📊 **[Signaux](../../../user/assets/detail/signals.md)** — Comment configurer les superpositions dans LibreFolio
