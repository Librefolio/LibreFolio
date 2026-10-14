# 📈 Signaux

Le panneau **Signaux** trace des indicateurs techniques, des séries de comparaison et des courbes de référence sur le graphique FX. LibreFolio calcule les indicateurs à partir des taux stockés de la paire.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Panneau des signaux FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Ajouter un signal

1. Cliquez sur la barre **Signaux** au-dessus du graphique pour déplier le panneau.
2. Choisissez un signal dans l'un des trois menus déroulants : **Indicateurs techniques**, **Comparaison de données** ou **Benchmarks synthétiques**.
3. Ajustez ses paramètres sur sa carte : le graphique suit.
4. Faites glisser les cartes pour les réorganiser ; 🗑️ en supprime une.

Les signaux que vous ajoutez sont conservés avec les [paramètres du graphique](../chart-settings.md) de cette paire.

---

## 🧮 Indicateurs techniques — 9 pour le FX

Neuf indicateurs fonctionnent sur les taux FX. Suivez les liens ci-dessous, ou cliquez sur 📖 sur une carte, pour les formules mathématiques de chacun d'eux.

| Famille | Indicateurs |
|---|---|
| 📈 **Tendance** (3) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) |
| ⚡ **Momentum** (5) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [RSI stochastique](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) |
| 🌊 **Volatilité** (1) | [Bandes de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) |

??? info "🤔 Pourquoi seulement 9 ? — les autres indicateurs ont besoin de plus qu'un taux quotidien"

    Les taux FX ont une seule valeur par jour, sans plus haut, plus bas ni volume. Les autres indicateurs ont besoin de ces champs, ou mesurent un risque de type portefeuille, et ne sont donc disponibles que sur les [graphiques d'actifs](../../assets/detail/signals.md). La liste complète se trouve dans [Indicateurs techniques — Théorie financière](../../../financial-theory/technical-analysis/indicators/index.md).

### 🔍 Trouver un indicateur

Le menu déroulant **Indicateurs techniques** est une arborescence groupée par famille (tendance, momentum, volatilité), avec un champ de recherche en haut : tapez pour filtrer toutes les familles à la fois. Les touches fléchées et `Enter` fonctionnent aussi.

*Capture d'écran à venir : l'arborescence des indicateurs groupés ouverte dans le panneau Signaux FX.*

---

## 💱 Comparaison de données

- 💱 **Paire FX** — une autre de vos paires, par ex. GBP/USD à côté d'EUR/USD. Dans la liste, 👑 marque la paire de cette page et 📌 une paire déjà utilisée par un autre signal.
- ↔️ **Comparaison d'actif** — le prix d'un actif à côté du taux.

Une carte de comparaison comporte des boutons pour synchroniser la paire ou l'actif comparé et pour ouvrir sa page. En vue %, les deux courbes démarrent à 0 %, ce qui permet de comparer directement leurs évolutions.

## 📐 Benchmarks synthétiques

Courbes de référence construites uniquement à partir de paramètres, sans données de marché :
[Croissance linéaire](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
[Croissance composée](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) et
[Onde sinusoïdale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🎛️ Lire une carte de signal

- 📖 ouvre la page théorique de l'indicateur ; survolez un paramètre pour obtenir de l'aide.
- Un badge compte les points de données chargés pour le signal.
- Un indicateur de chargement tourne pendant que le signal est calculé. Ensuite, une icône peut signaler un problème — survolez-la pour les détails :
    - gris ℹ️ — une petite mise en garde ;
    - orange ⚠️ — calculé avec des réserves, comme des lacunes, une courte période d'initialisation ou des données qui commencent après la période ;
    - rouge ⚠️ — non calculé, par exemple parce que l'historique est trop court.

Si une carte signale des données manquantes, la synchronisation de la paire comble généralement la lacune.

---

## 📚 Approfondissement : théorie financière

La formule de chaque indicateur, sa vision en traitement du signal (l'EMA comme filtre IIR, la SMA comme filtre FIR) et la façon de lire ses croisements :

:material-book-open-variant: **[Indicateurs techniques — Théorie financière](../../../financial-theory/technical-analysis/indicators/index.md)**
