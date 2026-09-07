# 📊 Signaux

Le panneau Signaux permet de superposer des **indicateurs techniques**, des **séries de comparaison** et des **courbes de benchmark** sur le graphique de prix. Les indicateurs sont calculés côté serveur par la **plateforme de plugins de signaux** du backend de LibreFolio à partir de l'historique de prix stocké de l'actif — le navigateur ne fait que restituer les résultats, si bien que le graphique, les diagnostics et les instantanés de l'export IA affichent tous les mêmes chiffres.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Panneau de signaux d'un actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 Signaux disponibles

Les signaux sont organisés en **trois catégories**, chacune avec son propre menu déroulant en haut du panneau.

### 📉 Indicateurs techniques — 22 plugins backend

Les graphiques d'actifs peuvent exécuter **22 plugins d'indicateurs**, regroupés par la propriété de marché qu'ils mesurent. Les mathématiques de chaque indicateur figurent dans la section Théorie financière — suivez les liens ci-dessous, ou cliquez sur l'icône 📖 de n'importe quelle carte de signal pour accéder directement à sa page de théorie.

| Famille | Indicateurs |
|---|---|
| 📈 **Tendance** (5) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) · [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) · [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) |
| ⚡ **Momentum** (6) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [RSI stochastique](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) · [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) |
| 🌊 **Volatilité** (4) | [Bandes de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) · [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) · [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) · [Canaux de Donchian](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) |
| 📊 **Volume** (2) | [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) · [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) |
| ⚠️ **Risque** (5) | Drawdown sous-marin · Rendement glissant · Volatilité glissante · Ratio de Sharpe glissant · Bêta glissant |

Pour les concepts de la famille Risque, voir les pages de théorie [Métriques de risque](../../../financial-theory/technical-analysis/risk-metrics/index.md) ([Drawdown maximal](../../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md), [Volatilité](../../../financial-theory/technical-analysis/risk-metrics/volatility.md), [Ratio de Sharpe](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)).

!!! info "Tous les indicateurs ne peuvent pas s'exécuter sur tous les actifs"

    Les indicateurs qui nécessitent des prix **haut/bas** (ADX, Aroon, ATR, NATR, CCI,
    canaux de Donchian) ou du **volume** (OBV, MFI) ne deviennent disponibles que
    lorsque votre historique de prix inclut ces champs — la carte de signal vous
    indique quel champ manque. **Bêta glissant** vous demande en outre de choisir
    un actif de comparaison.

### 💱 Comparaison de données

Des superpositions calculées par le navigateur qui normalisent une autre série sur le même graphique :

- ↔️ **Comparaison d'actifs** — superpose la performance d'un autre actif, normalisée à la même échelle (par exemple, une action par rapport à son benchmark)
- 💱 **Paire de devises** — superpose le taux d'une paire de devises configurée

### 📐 Benchmarks synthétiques

Des **courbes de référence mathématiques** calculées par le navigateur, générées uniquement à partir de paramètres — aucune donnée de marché nécessaire : [Croissance linéaire](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Croissance composée](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md), et [Onde sinusoïdale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🔍 Trouver un indicateur

Le menu déroulant des indicateurs est une **arborescence repliable regroupée par famille** (tendance, momentum, volatilité, volume, risque), avec une zone de recherche en haut :

- ⌨️ Tapez pour filtrer dans toutes les familles — la recherche correspond aux noms, aux descriptions et même aux champs de données qu'utilise un indicateur
- 📁 Chaque famille affiche un badge de compteur et se déplie et se replie indépendamment
- 🖱️ Prise en charge complète du clavier : les flèches déplacent le curseur, `→`/`←` déplient et replient une famille, `Entrée` sélectionne

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Recherche groupée d'indicateurs dans le panneau de signaux d'un actif">
</div>

---

## 🎛️ Cartes de signal

Chaque signal ajouté devient une carte affichant :

- 📖 Une **icône de documentation** renvoyant à la page de théorie financière de l'indicateur
- 🎚️ **Paramètres en ligne** (nombres, menus déroulants, cases à cocher) — certaines infobulles contiennent des formules LaTeX rendues avec KaTeX
- 🏷️ Un **badge de données** avec le nombre de points de prix (📈) chargés
- 🗑️ Bouton de suppression ; faites glisser les cartes pour réorganiser les superpositions

### ⏳ Pendant que le backend calcule

Un petit **spinner** apparaît sur chaque carte pendant que la requête backend est en cours. Cet état transitoire est délibéré : les cartes n'affichent jamais d'erreur rouge « pas de données » simplement parce que la réponse n'est pas encore arrivée.

### 🩺 Diagnostics par signal

Après le chargement, une icône colorée indique comment le calcul s'est déroulé — survolez-la pour l'explication complète :

- ℹ️ **Avis** (gris) / ⚠️ **Avertissement** (ambre) — le signal a été calculé mais avec des réserves : des lacunes dans les données, une période de chauffe incomplète ou une plage qui commence avant vos données
- 🔴 **Erreur** (rouge) — le signal n'a pas pu être calculé : champs OHLCV manquants, historique insuffisant pour les paramètres choisis ou échec du calcul

---

## 🧩 Données incomplètes : segments partiels

Les indicateurs qui tolèrent les lacunes (ADX, Aroon, ATR, NATR, CCI, Donchian, MFI, OBV) n'échouent pas sur un historique de prix lacunaire : le backend sélectionne le **segment contigu complet** le plus récent, y calcule l'indicateur, et signale le résultat comme *partiel* — l'infobulle vous indique quel segment a été utilisé et combien de points ont été exclus. Tous les autres indicateurs exigent des données sans lacune et expliquent pourquoi ils ne peuvent pas s'exécuter au lieu de tracer une ligne trompeuse.

---

## 📉 Drawdown : interrupteur d'historique complet

La carte **Drawdown sous-marin** comporte une case à cocher **Historique complet** (activée par défaut) : la baisse est mesurée par rapport au pic courant de la *totalité* de l'historique disponible, puis découpée à la fenêtre visible — un pic datant de plusieurs années compte toujours. Désactivez-la pour une vue plus rapide, relative à la fenêtre. Les instantanés de l'export IA utilisent toujours le comportement sur tout l'historique, indépendamment de ce paramètre du graphique.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Carte de signal de drawdown avec l'interrupteur d'historique complet">
</div>

---

## 🛠️ Mode d'emploi

1. Cliquez sur l'interrupteur **Signaux** (📈) dans la barre d'outils
2. Le panneau Signaux s'ouvre sous la barre d'outils
3. Ajoutez des signaux à partir des trois menus déroulants de catégories (**Indicateurs techniques**, **Comparaison de données**, **Benchmarks synthétiques**)
4. Ajustez les paramètres de chaque signal en ligne sur sa carte
5. Les signaux sont affichés sous forme de superpositions directement sur le graphique

---

## 🧠 Export IA

Le bouton **Export IA** (:material-brain:) de la barre d'outils de la page propose deux
tâches liées à l'actif :

- **Revue de position**
- **Analyse de marché de l'actif**

Le backend construit l'instantané à partir de l'identité et de la valorisation de l'actif,
de l'historique de prix normalisé, du contexte de la position de portefeuille et des
résultats techniques issus du service de signaux partagé. Le navigateur ne recalcule pas
les indicateurs. Les tâches n'apparaissent que lorsqu'elles s'appliquent à l'actif et aux
données disponibles — par exemple, la Revue de position nécessite une position ouverte.
Voir [Export IA de l'actif](../../ai-export/asset.md) ou l'[aperçu de l'export IA](../../ai-export/index.md).

---

## 📚 Pour aller plus loin : Théorie financière

Pour un traitement mathématique complet de chaque indicateur — formules, équivalents en traitement du signal et interprétation pratique :

:material-book-open-variant: **[Indicateurs techniques — Théorie financière](../../../financial-theory/technical-analysis/indicators/index.md)**

Cette page de référence couvre :

- 🔢 Les **formules mathématiques** derrière chaque indicateur
- 🎛️ Les équivalents en **traitement du signal** (EMA = filtre IIR, SMA = filtre FIR, etc.)
- ⚡ L'intuition **« rapide vs lent »** en termes de fréquences de coupure des filtres
- 📈 Des **exemples pratiques** de détection de croisement et d'identification de tendance
