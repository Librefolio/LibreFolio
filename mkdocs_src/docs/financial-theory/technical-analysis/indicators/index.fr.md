# 📉 Indicateurs techniques

LibreFolio expose **17 indicateurs techniques calculés côté serveur**, regroupés par la propriété de marché qu'ils mesurent. Les mêmes contrats mathématiques alimentent les graphiques d'actifs, les graphiques FX compatibles, les annotations et les futurs consommateurs analytiques.

!!! info "Les champs de prix sont importants"

    Tous les indicateurs ne peuvent pas fonctionner sur toutes les séries. Les indicateurs basés uniquement sur le prix de clôture fonctionnent sur les actifs et les taux de change ; les indicateurs nécessitant le plus haut, le plus bas ou le volume sont réservés aux actifs et se signalent comme indisponibles lorsque ces champs n'existent pas.

---

## 📈 Tendance

Les indicateurs de tendance lissent le prix ou mesurent si un mouvement directionnel est établi.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **EMA** | Où se situe la tendance pondérée récente ? | Clôture | [📖](ema.md) |
| **SMA** | Quel est le prix moyen à pondération égale ? | Clôture | [📖](sma.md) |
| **KAMA** | Comment le lissage doit-il s'adapter au bruit ? | Clôture | [📖](kama.md) |
| **ADX** | Quelle est la force de la tendance ? | Plus haut, Plus bas, Clôture | [📖](adx.md) |
| **Aroon** | À quel moment les nouveaux extrêmes sont-ils apparus ? | Plus haut, Plus bas | [📖](aroon.md) |

➡️ [Aperçu du groupe Tendance](trend.md)

---

## ⚡ Momentum

Les indicateurs de momentum mesurent la vitesse, la pression directionnelle et l'accélération.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **RSI** | Les acheteurs ou les vendeurs dominent-ils ? | Clôture | [📖](rsi.md) |
| **MACD** | Le momentum de la tendance s'accélère-t-il ? | Clôture | [📖](macd.md) |
| **ROC** | À quelle vitesse le prix a-t-il changé ? | Clôture | [📖](roc.md) |
| **Stochastic RSI** | Où se situe le RSI dans sa plage récente ? | Clôture | [📖](stochastic-rsi.md) |
| **PPO** | Quel est le momentum de la moyenne mobile en pourcentage ? | Clôture | [📖](ppo.md) |
| **CCI** | À quelle distance le prix est-il de sa moyenne statistique récente ? | Plus haut, Plus bas, Clôture | [📖](cci.md) |

➡️ [Aperçu du groupe Momentum](momentum.md)

---

## 🌊 Volatilité

Les indicateurs de volatilité mesurent l'étendue, la dispersion et la largeur du canal plutôt que la direction.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **Bollinger Bands** | Quelle est la largeur de l'enveloppe statistique du prix ? | Clôture | [📖](bollinger-bands.md) |
| **ATR** | Quelle est la taille du vrai range typique ? | Plus haut, Plus bas, Clôture | [📖](atr.md) |
| **NATR** | Quelle est la volatilité par rapport au prix ? | Plus haut, Plus bas, Clôture | [📖](natr.md) |
| **Donchian Channels** | Quels sont le plus haut et le plus bas de la période ? | Plus haut, Plus bas | [📖](donchian-channels.md) |

➡️ [Aperçu du groupe Volatilité](volatility.md)

---

## 📊 Volume

Les indicateurs de volume combinent la direction du prix avec l'activité de trading.

| Indicateur | Question principale | Données | Détails |
|---|---|---|---|
| **OBV** | Le volume signé est-il en accumulation ou en distribution ? | Clôture, Volume | [📖](obv.md) |
| **MFI** | Le flux monétaire est-il une pression d'achat ou de vente ? | Plus haut, Plus bas, Clôture, Volume | [📖](mfi.md) |

➡️ [Aperçu du groupe Volume](volume.md)

---

## 🔗 Liés

- 🎯 **[Repères synthétiques](../synthetic-benchmarks/index.md)** — Courbes de référence mathématiques
- 📈 **[Graphique interactif](../../../user/assets/detail/chart.md)** — Où les indicateurs sont affichés
- 📊 **[Signaux](../../../user/assets/detail/signals.md)** — Comment configurer les superpositions dans LibreFolio
