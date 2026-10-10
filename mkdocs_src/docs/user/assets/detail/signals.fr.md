# 📊 Signaux

Les signaux sont des lignes tracées sur le graphique des prix : **indicateurs techniques** que LibreFolio calcule à partir des prix stockés, **un autre actif ou une paire de devises** avec lequel comparer, et **courbes de référence** telles qu'une croissance régulière. Utilisez-les pour lire la tendance, le momentum, la volatilité et le risque en un coup d'œil.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Panneau des signaux d'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Ajouter un signal

1. Ouvrez le panneau **Signaux** au-dessus du graphique.
2. Choisissez un signal dans l'un de ses trois menus : **Indicateurs techniques**, **Comparaison de données** ou **Benchmarks synthétiques**. Dans le menu des indicateurs, tapez pour rechercher par nom, description ou les données utilisées par un indicateur.
3. Définissez ses paramètres sur la carte qui apparaît ; le graphique suit.
4. Faites glisser une carte par sa poignée (flèches sur téléphone) pour changer l'ordre, ou supprimez-la avec 🗑️.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Recherche d'indicateurs groupés sur le panneau des signaux d'actif">
</div>

Chaque ligne d'une carte, et chaque zone d'indicateurs tels que le RSI, a sa propre couleur et son propre style de ligne. Vos signaux sont mémorisés pour cet actif, dans ce navigateur.

---

## 📉 Indicateurs techniques {: #technical-indicators }

**22 indicateurs**, regroupés selon ce qu'ils mesurent. Chaque nom renvoie à sa page théorique ; le **?** sur une carte ouvre la même page.

### 📈 Tendance

- [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) — moyenne simple des prix de clôture
- [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) — moyenne qui accorde plus de poids aux prix récents
- [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) — moyenne qui s'adapte au bruit du marché
- [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) — force de la tendance, avec +DI et −DI pour sa direction
- [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) — à quel point les derniers sommets et creux sont récents

### ⚡ Momentum

- [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) — pression d'achat et de vente, avec zones de surachat et de survente
- [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) — momentum entre deux moyennes mobiles, avec une ligne de signal et un histogramme
- [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) — le même momentum, en pourcentage
- [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) — vitesse de variation du prix
- [RSI stochastique](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) — position du RSI dans sa plage récente
- [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) — distance par rapport au prix moyen

### 🌊 Volatilité

- [Bandes de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) — une bande autour d'une moyenne mobile qui s'élargit avec la volatilité
- [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) — volatilité en unités de prix
- [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) — volatilité en pourcentage du prix
- [Canaux de Donchian](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) — le plus haut des hauts et le plus bas des bas de la période

### 📊 Volume

- [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) — pression du volume derrière les mouvements de prix
- [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) — momentum pondéré par le volume

### ⚠️ Risque

- [Repli sous le sommet](../../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md) — l'écart du prix sous son plus haut courant ([historique complet](#drawdown-full-history))
- [Rendement glissant](../../../financial-theory/fundamentals/returns.md#rolling-return-sessions) — rendement basé uniquement sur le prix, sur une fenêtre glissante
- [Volatilité glissante](../../../financial-theory/technical-analysis/risk-metrics/volatility.md) — volatilité annualisée sur une fenêtre glissante
- [Ratio de Sharpe glissant](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md) — rendement excédentaire par unité de volatilité sur une fenêtre glissante
- [Bêta glissant](../../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md) — la force avec laquelle l'actif suit un actif de comparaison de votre choix

Les périodes comptent des **séances**, les jours où l'actif a été coté : une SMA 200 couvre 200 séances, environ 290 jours calendaires ([pourquoi](../../../financial-theory/technical-analysis/indicators/index.md)). La **Fenêtre** des quatre signaux de risque glissants compte aussi les jours avec une cotation ; pour le Bêta glissant, les jours où les deux actifs ont été cotés.

!!! info "Tous les indicateurs ne peuvent pas s'exécuter sur tous les actifs"

    ADX, Aroon, ATR, NATR, CCI, canaux de Donchian et MFI ont besoin des prix **haut** et **bas** ; OBV et MFI ont besoin du **volume**. Sans eux, la carte vous indique quelles données manquent.

### 📉 Repli sur l'historique complet {: #drawdown-full-history }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Carte de signal Repli avec l'interrupteur d'historique complet">
</div>

La carte **Repli sous le sommet** a une case à cocher **Historique complet**, activée par défaut : la baisse est mesurée depuis le prix le plus haut de tout l'historique de l'actif, même des années avant les dates affichées. Décochez-la pour une vue plus rapide, mesurée depuis le prix le plus haut dans les dates affichées.

---

## 💱 Comparer avec un actif ou une paire de devises {: #data-comparison }

Le menu **Comparaison de données** ajoute :

- **Comparaison d'actif** — un autre actif sur le même graphique, comme une action face à son ETF indiciel. En vue **%**, les deux lignes commencent à 0 %.
- **Paire FX** — le taux de l'une de vos paires de devises.

**Synchroniser** (🔄) sur une carte de comparaison d'actif télécharge les prix de cet actif pour les dates du graphique, ainsi que les taux de change qui le convertissent, pour les paires qui existent. Lorsque la paire est manquante, un ⚠️ orange sur la carte la crée ; lorsque ses taux sont manquants, un 🔄 orange les synchronise.

En mode [Rendement glissant](chart.md#rolling-return), seule la comparaison d'actif reste : chaque actif comparé devient un rendement glissant, avec la même fenêtre et la même devise. Les autres signaux sont masqués, non supprimés, et réapparaissent en mode **Prix**.

---

## 📐 Benchmarks synthétiques

Courbes de référence tracées à partir de leurs seuls paramètres, sans données de marché :

- [Croissance linéaire](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md) — $y(t) = y_0\,(1 + r\,t)$
- [Croissance composée](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) — $y(t) = y_0\,(1 + r)^t$
- [Onde sinusoïdale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md) — $y(t) = A \sin(2\pi t / T) + y_0$

---

## 🩺 Lire une carte de signal

- Un **spinner** tourne pendant que le signal est calculé.
- **📈 N** est le nombre de points de prix chargés.
- Un **ℹ** gris — calculé, avec une petite réserve : un court écart ou un préchauffage presque terminé. Survolez l'icône pour les détails.
- Un **⚠** orange — calculé, avec une réserve à examiner : des écarts plus importants, un préchauffage incomplet ou des données qui commencent après la première date affichée. La carte devient orange elle aussi.
- Un **⚠** rouge — non calculé : un champ de prix manquant, un historique trop court pour les paramètres, aucune donnée, ou une erreur de calcul. La carte devient rouge.

??? note "🧩 Historique de prix discontinu — lorsqu'un signal est partiel"

    ADX, Aroon, ATR, NATR, CCI, canaux de Donchian, MFI et OBV peuvent s'exécuter sur un historique discontinu : ils utilisent la portion la plus récente sans écarts qui soit suffisamment longue, et l'infobulle nomme cette portion et le nombre de points omis. Les autres indicateurs nécessitent un historique sans écarts, et expliquent pourquoi ils ne peuvent pas s'exécuter plutôt que de tracer une ligne trompeuse. Un week-end ou un jour férié de marché ne constitue pas un écart.

---

## 🔗 Voir aussi

- 📚 **[Indicateurs techniques](../../../financial-theory/technical-analysis/indicators/index.md)** — La formule de chaque indicateur et comment le lire
- ⚠️ **[Métriques de risque](../../../financial-theory/technical-analysis/risk-metrics/index.md)** — Les métriques derrière les signaux de risque
- 🧠 **[Export IA d'actif](../../ai-export/asset.md)** — Indicateurs techniques calculés par le même backend, exportés pour un assistant IA
- 🛠️ **[Guide des plugins de signaux](../../../developer/architecture/patterns/signal_plugin_guide.md)** — Pour les développeurs : comment les indicateurs sont calculés, vérifiés et ajoutés
