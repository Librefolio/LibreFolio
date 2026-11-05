# 📊 Signaux

Les signaux sont des lignes tracées sur le graphique des prix : des **indicateurs techniques** que LibreFolio calcule à partir des prix enregistrés, **un autre actif ou une paire de devises** auxquels se comparer, et des **courbes de référence** telles qu'une croissance régulière. Utilisez-les pour lire la tendance, le momentum, la volatilité et le risque en un coup d'œil.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Panneau des signaux de l'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Ajouter un signal

1. Ouvrez le panneau **Signaux** au-dessus du graphique.
2. Choisissez un signal dans l'un des trois menus du panneau : **Indicateurs techniques**, **Comparaison de données** ou **Benchmarks synthétiques**. Dans le menu des indicateurs, tapez pour rechercher par nom, par description ou par les données qu'utilise un indicateur.
3. Réglez ses paramètres sur la carte qui apparaît ; le graphique suit.
4. Faites glisser une carte par sa poignée (les flèches sur téléphone) pour changer l'ordre, ou supprimez-la avec 🗑️.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Recherche groupée d'indicateurs dans le panneau des signaux de l'actif">
</div>

Chaque ligne d'une carte, et chaque zone d'indicateurs tels que le RSI, possède sa propre couleur et son propre style de ligne. Vos signaux sont mémorisés pour cet actif, dans ce navigateur.

---

## 📉 Indicateurs techniques {: #technical-indicators }

**22 indicateurs**, regroupés selon ce qu'ils mesurent. Chaque nom renvoie à sa page théorique ; le **?** sur une carte ouvre la même page.

### 📈 Tendance

- [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) — moyenne simple des cours de clôture
- [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) — moyenne qui accorde plus de poids aux prix récents
- [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) — moyenne qui s'adapte au bruit du marché
- [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) — force de la tendance, avec +DI et −DI pour sa direction
- [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) — à quel point les derniers plus hauts et plus bas sont récents

### ⚡ Momentum

- [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) — pression à l'achat et à la vente, avec des zones de surachat et de survente
- [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) — momentum entre deux moyennes mobiles, avec une ligne de signal et un histogramme
- [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) — le même momentum, en pourcentage
- [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) — vitesse de variation du prix
- [Stochastic RSI](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) — position du RSI dans sa plage récente
- [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) — écart par rapport au prix moyen

### 🌊 Volatilité

- [Bandes de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) — une bande autour d'une moyenne mobile qui s'élargit avec la volatilité
- [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) — volatilité en unités de prix
- [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) — volatilité en pourcentage du prix
- [Canaux de Donchian](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) — le plus haut et le plus bas de la période

### 📊 Volume

- [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) — pression du volume derrière les mouvements de prix
- [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) — momentum pondéré par le volume

### ⚠️ Risque

- [Repli sous le sommet](../../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md) — de combien le prix se situe sous son plus haut cumulé ([historique complet](#drawdown-full-history))
- [Rendement glissant](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar) — rendement fondé uniquement sur le prix, comparé à la clôture d'un nombre choisi de jours calendaires auparavant, la même mesure que le mode [Rendement glissant](chart.md#rolling-return) du graphique
- [Volatilité glissante](../../../financial-theory/technical-analysis/risk-metrics/volatility.md) — volatilité annualisée sur une fenêtre glissante
- [Ratio de Sharpe glissant](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md) — rendement excédentaire par unité de volatilité sur une fenêtre glissante
- [Bêta glissant](../../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md) — à quel point l'actif suit l'actif de comparaison que vous choisissez

Les périodes se comptent en **séances**, les jours où l'actif a été coté : une SMA 200 couvre 200 séances, soit environ 290 jours calendaires ([pourquoi](../../../financial-theory/technical-analysis/indicators/index.md)). La **Fenêtre** de la Volatilité glissante, du Ratio de Sharpe glissant et du Bêta glissant compte des **observations** : un rendement pour chaque jour où l'actif a été coté — pour le Bêta glissant, pour chaque jour où l'un ou l'autre des deux actifs a été coté, l'autre étant compté à son dernier prix. La **Fenêtre** du Rendement glissant compte des **jours calendaires**, comme dans le mode [Rendement glissant](chart.md#rolling-return) du graphique.

!!! info "Certains indicateurs ne peuvent pas être calculés sur tous les actifs"

    ADX, Aroon, ATR, NATR, CCI, Canaux de Donchian et MFI ont besoin des prix **haut** et **bas** ; OBV et MFI ont besoin du **volume**. Sans ces données, la carte vous indique quelles données manquent.

### 📉 Repli sur l'historique complet {: #drawdown-full-history }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Carte du signal de repli avec la case à cocher Historique complet">
</div>

La carte **Repli sous le sommet** dispose d'une case à cocher **Historique complet**, activée par défaut : la baisse est mesurée depuis le prix le plus haut de tout l'historique de l'actif, même des années avant les dates affichées. Décochez-la pour une vue plus rapide, mesurée depuis le prix le plus haut parmi les dates affichées.

---

## 💱 Comparer avec un actif ou une paire de devises {: #data-comparison }

Le menu **Comparaison de données** ajoute :

- **Comparaison d'actifs** — un autre actif sur le même graphique, par exemple une action face à son ETF indiciel. En vue **%**, les deux lignes partent de 0 %. L'actif se choisit dans le même panneau que celui de la comparaison de risque : une zone de recherche, des filtres **Type** et **Devise**, les indices de référence listés en premier, un clic pour choisir. L'actif propre au graphique est grisé ; un actif déjà utilisé par une autre comparaison porte une marque d'avertissement mais reste sélectionnable.
- **Paire FX** — le taux de l'une de vos paires de devises.

Avec **Tout** sélectionné, le graphique démarre sur la plus ancienne des deux séries. Si l'actif comparé possède des prix depuis 1985 et l'actif propre au graphique depuis 2010, le graphique est tracé à partir de 1985, la ligne de l'actif du graphique restant vide jusqu'en 2010, et la date **Depuis** affiche 1985. En vue **%**, chaque ligne part de 0 % sur son propre premier prix. Si l'actif comparé commence plus tard que celui du graphique, le graphique reste tel quel et la ligne de comparaison débute à son propre premier jour. Les autres signaux (indicateurs et benchmarks synthétiques) suivent les jours de l'actif du graphique et sont donc vides avant son premier jour.

**Sync** (🔄) sur une carte de Comparaison d'actifs télécharge les prix de cet actif pour les dates du graphique, ainsi que les taux de change qui le convertissent, pour les paires qui existent. Lorsque la paire est absente, un ⚠️ orange ambré sur la carte la crée ; lorsque ses taux sont absents, un 🔄 orange ambré les synchronise.

En mode [Rendement glissant](chart.md#rolling-return), seule la Comparaison d'actifs subsiste : chaque actif comparé devient un rendement glissant, avec la même fenêtre et la même devise. Les autres signaux sont masqués, non supprimés, et réapparaissent en mode **Prix**.

---

## 📐 Benchmarks synthétiques

Des courbes de référence tracées à partir de leurs seuls paramètres, sans données de marché :

- [Croissance linéaire](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md) — $y(t) = y_0\,(1 + r\,t)$
- [Croissance composée](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) — $y(t) = y_0\,(1 + r)^t$
- [Onde sinusoïdale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md) — $y(t) = A \sin(2\pi t / T) + y_0$

---

## 🩺 Lire une carte de signal

- Un **indicateur de chargement** tourne pendant le calcul du signal.
- **📈 N** est le nombre de points de prix chargés.
- Un **ℹ** gris — calculé, avec une petite réserve : une courte lacune ou une période d'initialisation presque complète. Survolez l'icône pour les détails.
- Un **⚠** orange ambré — calculé, avec une réserve qui mérite un coup d'œil : des lacunes plus importantes, une période d'initialisation incomplète, ou des données qui commencent après la première date affichée. La carte prend elle aussi une teinte ambrée.
- Un **⚠** rouge — non calculé : un champ de prix manquant, un historique trop court pour les paramètres, aucune donnée du tout, ou une erreur de calcul. La carte devient rouge.

??? note "🧩 Historique de prix lacunaire — quand un signal est partiel"

    ADX, Aroon, ATR, NATR, CCI, Canaux de Donchian, MFI et OBV peuvent fonctionner sur un historique lacunaire : ils utilisent la portion récente sans lacunes qui est suffisamment longue, et l'infobulle indique cette portion et le nombre de points écartés. Les autres indicateurs ont besoin d'un historique sans lacunes, et expliquent pourquoi ils ne peuvent pas fonctionner plutôt que de tracer une ligne trompeuse. Un week-end ou un jour férié boursier ne constitue pas une lacune.

---

## 🔗 Voir aussi

- 📚 **[Indicateurs techniques](../../../financial-theory/technical-analysis/indicators/index.md)** — La formule de chaque indicateur et comment l'interpréter
- ⚠️ **[Métriques de risque](../../../financial-theory/technical-analysis/risk-metrics/index.md)** — Les métriques derrière les signaux de risque
- 🧠 **[Export IA d'un actif](../../ai-export/asset.md)** — Les indicateurs techniques calculés par le même backend, exportés pour un assistant IA
- 🛠️ **[Guide des plugins de signaux](../../../developer/architecture/patterns/signal_plugin_guide.md)** — Pour les développeurs : comment les indicateurs sont calculés, vérifiés et ajoutés
