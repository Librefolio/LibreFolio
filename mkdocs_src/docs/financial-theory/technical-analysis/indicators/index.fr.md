# 📉 Indicateurs techniques

LibreFolio expose **22 indicateurs techniques calculés côté backend**, regroupés selon la propriété de marché qu'ils mesurent. Les mêmes contrats mathématiques alimentent les graphiques d'actifs, les graphiques FX compatibles, les annotations et les consommateurs analytiques tels que l'export IA.

Les indicateurs comptent des **séances**, et non des jours calendaires : une séance est un jour où la série dispose d'une cotation propre — un prix pour un actif, un taux publié pour une paire FX. Un jour que la série remplit avec la dernière valeur connue — un week-end, un jour férié de marché, tout jour sans cotation — n'est pas une séance, et un prix stocké daté d'un week-end ou d'un jour férié de marché qui ne fait que répéter la clôture précédente ne l'est pas non plus (un [report stocké](../risk-metrics/data-quality.md#stored-carries)). Les périodes, la période d'initialisation et l'historique minimum sont tous comptés en séances, de sorte que l'indicateur SMA 200 calcule la moyenne des 200 dernières séances, soit environ 290 jours calendaires. Le graphique conserve ses dates calendaires : un indicateur n'a de valeurs que sur les séances, et sa ligne relie les jours de fermeture intermédiaires. La famille Risque compte ses fenêtres autrement. La Volatilité glissante, le Ratio de Sharpe glissant et le Bêta glissant comptent des **observations de rendement** de la série de rendements préparée pour l'actif : un rendement par séance, mesuré par rapport à la séance précédente — pour le Bêta glissant, pour chaque date du [calendrier commun](../risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs) aux deux actifs — de sorte qu'une fenêtre de $w$ exploite $w$ rendements calculés à partir de $w + 1$ prix. Le **Rendement glissant** compte en **jours calendaires** : il compare chaque date avec la clôture retenue exactement $N$ jours calendaires plus tôt ([Rendement glissant](../../fundamentals/returns.md#rolling-return-calendar)), le même calcul que le [mode Rendement glissant](../../../user/assets/detail/chart.md#primary-modes) du graphique.

!!! info "Les champs de prix ont leur importance"

    Les indicateurs ne peuvent pas tous s'exécuter sur toutes les séries. **9 des 22** sont des
    indicateurs en clôture seule et fonctionnent à la fois sur les actifs et les taux FX (EMA, SMA,
    KAMA, MACD, RSI, ROC, PPO, RSI stochastique, Bandes de Bollinger). Les indicateurs nécessitant
    le haut, le bas ou le volume sont réservés aux actifs et se déclarent indisponibles
    lorsque ces champs n'existent pas. La famille **Risque** est également réservée aux actifs : les
    mesures de risque glissantes ne sont pas produites pour les paires FX.

---

## 📈 Tendance

Les indicateurs de tendance lissent le prix ou mesurent si un mouvement directionnel est établi.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **EMA** | Où se situe la tendance pondérée récente ? | Clôture | [📖](ema.md) |
| **SMA** | Quel est le prix moyen à pondération égale ? | Clôture | [📖](sma.md) |
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
| **ROC** | À quelle vitesse le prix a-t-il changé ? | Clôture | [📖](roc.md) |
| **RSI stochastique** | Où se situe le RSI dans sa plage récente ? | Clôture | [📖](stochastic-rsi.md) |
| **PPO** | Quel est le momentum de la moyenne mobile en pourcentage ? | Clôture | [📖](ppo.md) |
| **CCI** | À quelle distance le prix se situe-t-il de sa moyenne statistique récente ? | Haut, Bas, Clôture | [📖](cci.md) |

➡️ [Vue d'ensemble du groupe Momentum](momentum.md)

---

## 🌊 Volatilité

Les indicateurs de volatilité mesurent l'amplitude, la dispersion et la largeur des canaux plutôt que la direction.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **Bandes de Bollinger** | Quelle est la largeur de l'enveloppe statistique du prix ? | Clôture | [📖](bollinger-bands.md) |
| **ATR** | Quelle est l'ampleur de la plage vraie typique ? | Haut, Bas, Clôture | [📖](atr.md) |
| **NATR** | Quelle est l'ampleur de la volatilité par rapport au prix ? | Haut, Bas, Clôture | [📖](natr.md) |
| **Canaux de Donchian** | Quels sont le plus haut et le plus bas de la période ? | Haut, Bas | [📖](donchian-channels.md) |

➡️ [Vue d'ensemble du groupe Volatilité](volatility.md)

---

## 📊 Volume

Les indicateurs de volume combinent la direction du prix avec l'activité de trading.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **OBV** | Le volume signé s'accumule-t-il ou se distribue-t-il ? | Clôture, Volume | [📖](obv.md) |
| **MFI** | Le flux monétaire est-il une pression d'achat ou de vente ? | Haut, Bas, Clôture, Volume | [📖](mfi.md) |

➡️ [Vue d'ensemble du groupe Volume](volume.md)

---

## ⚠️ Risque

Les indicateurs de risque transforment la série de prix elle-même en une lecture de risque glissante. Ils sont **réservés aux actifs** — les paires FX ne les produisent pas.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **Repli sous le sommet** | À quelle distance le prix se situe-t-il sous le sommet courant ? | Clôture | [📖](../risk-metrics/current-drawdown.md) |
| **Rendement glissant** | De combien le prix a-t-il évolué sur les $N$ derniers jours calendaires ? | Clôture | [📖](../../fundamentals/returns.md#rolling-return) |
| **Volatilité glissante** | Quelle est la dispersion des rendements récents ? | Clôture | [📖](../risk-metrics/volatility.md) |
| **Ratio de Sharpe glissant** | Le rendement excédentaire rémunère-t-il son risque ? | Clôture | [📖](../risk-metrics/sharpe-ratio.md) |
| **Bêta glissant** | Quelle est la sensibilité de l'actif à un actif de comparaison ? | Clôture + actif de comparaison | [📖](../risk-metrics/beta-active-return.md) |

➡️ [Vue d'ensemble des métriques de risque](../risk-metrics/index.md)

---

## 🔗 Voir aussi

- 🎯 **[Benchmarks synthétiques](../synthetic-benchmarks/index.md)** — Courbes de référence mathématiques
- 📈 **[Graphique interactif](../../../user/assets/detail/chart.md)** — Où les indicateurs sont affichés
- 📊 **[Signaux](../../../user/assets/detail/signals.md)** — Comment configurer les superpositions dans LibreFolio
