# 📈 Signaux

Le panneau Signaux vous permet de superposer des **indicateurs techniques**, des **séries de comparaison** et des **courbes benchmark** sur le graphique FX. Les indicateurs sont calculés côté serveur par la **plateforme de plugins de signaux** du backend de LibreFolio à partir de l'historique des taux enregistré pour la paire — le navigateur ne fait que restituer les résultats.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Panneau Signaux FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 Signaux disponibles

Les signaux sont organisés en **trois catégories**, chacune avec son propre menu déroulant en haut du panneau : **Indicateurs techniques**, **Comparaison de données** et **Benchmarks synthétiques**.

### 📉 Indicateurs techniques — 9 plugins compatibles FX

Parmi les 22 plugins d'indicateurs du backend, **9 fonctionnent sur les taux de clôture FX**. Les mathématiques de chaque indicateur figurent dans la section Théorie financière — suivez les liens ci-dessous, ou cliquez sur l'icône 📖 de n'importe quelle carte de signal pour accéder directement à sa page de théorie.

| Famille | Indicateurs |
|---|---|
| 📈 **Tendance** (3) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) |
| ⚡ **Momentum** (5) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [RSI stochastique](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) |
| 🌊 **Volatilité** (1) | [Bandes de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) |

!!! info "Pourquoi seulement 9 ?"

    Les taux FX n'ont qu'une seule valeur par jour — il n'y a ni haut, ni bas, ni
    volume. Les 13 plugins restants nécessitent ces champs supplémentaires (ou
    calculent des métriques de risque de type portefeuille) et sont en revanche
    disponibles sur les [graphiques d'actifs](../../assets/detail/signals.md).
    L'inventaire complet se trouve dans
    [Indicateurs techniques — Théorie financière](../../../financial-theory/technical-analysis/indicators/index.md).

### 💱 Comparaison de données

Superpositions calculées par le navigateur qui normalisent une autre série sur le même graphique :

- 💱 **Paire FX** — superposer une autre paire configurée (par exemple comparer EUR/USD à GBP/USD) ; les paires déjà sélectionnées par un autre signal sont marquées 📌, et la paire de la page actuelle porte un 👑
- ↔️ **Comparaison d'actifs** — superposer la performance d'un actif à côté du taux de change

### 📐 Benchmarks synthétiques

Des **courbes de référence mathématiques** calculées par le navigateur, générées purement à partir de paramètres — aucune donnée de marché n'est nécessaire : [Croissance linéaire](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Croissance composée](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) et [Onde sinusoïdale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🔍 Trouver un indicateur

Le menu déroulant des indicateurs est une **arborescence repliable regroupée par famille** (tendance, momentum, volatilité), avec une zone de recherche en haut — tapez pour filtrer toutes les familles à la fois ; les flèches, `→`/`←` et `Enter` permettent de naviguer dans l'arborescence.

*Capture d'écran à venir : l'arborescence groupée des indicateurs ouverte sur le panneau Signaux FX.*

---

## 🎛️ Cartes de signaux

Chaque signal ajouté devient une carte affichant :

- 📖 Une **icône de documentation** renvoyant à la page de Théorie financière de l'indicateur
- 🎚️ **Paramètres en ligne** (période, période de signal, …) — certaines infobulles contiennent des formules LaTeX rendues avec KaTeX
- 🏷️ Un **badge de données** avec le nombre de points de taux (📈) chargés
- 🗑️ Bouton de suppression ; faites glisser les cartes pour réorganiser les superpositions

Un petit **spinner** apparaît sur chaque carte pendant que la requête backend est en cours. Après le chargement, une icône colorée affiche les **diagnostics** par signal — survolez-la pour plus de détails : ℹ️ avis (gris) et ⚠️ avertissement (ambre) lorsque le signal a été calculé avec des réserves (données manquantes, échauffement incomplet, données commençant après la plage du graphique), 🔴 erreur (rouge) lorsqu'il n'a pas pu être calculé du tout (historique insuffisant, champs manquants). Si une carte signale des données manquantes, la synchronisation de la paire comble généralement la lacune.

---

## 🛠️ Comment utiliser

1. Cliquez sur l'interrupteur **Signaux** (📈) dans la barre d'outils du graphique
2. Le panneau des signaux s'ouvre sous le graphique
3. Ajoutez des signaux depuis les trois menus déroulants de catégories (Indicateurs techniques, Comparaison de données, Benchmarks synthétiques)
4. Ajustez les paramètres de chaque signal en ligne sur sa carte
5. Les signaux sont rendus sous forme de superpositions directement sur le graphique

---

## 🧠 Export IA

Le bouton **Export IA** (:material-brain:) de la barre d'outils de la page propose deux tâches FX :

- **Analyse de paire FX**
- **Impact de l'exposition FX**

L'instantané du backend utilise la paire de devises canonique de la page, la plage sélectionnée, la devise cible, l'historique des taux et les résultats partagés des signaux techniques. Pour l'impact de l'exposition FX, l'exposition est limitée aux devises cash et aux devises de négociation ou de valorisation des positions directement liables à la paire ; il ne **remonte pas** jusqu'aux fonds ou émetteurs pour déduire une exposition de change cachée. Voir [Export IA FX](../../ai-export/fx.md) ou l'[aperçu de l'Export IA](../../ai-export/index.md).

---

## 📚 Approfondissement : Théorie financière

Pour un traitement mathématique complet de chaque indicateur — y compris les formules, les équivalents en traitement du signal et l'interprétation pratique :

:material-book-open-variant: **[Indicateurs techniques — Théorie financière](../../../financial-theory/technical-analysis/indicators/index.md)**

Cette page de référence couvre :

- 🔢 Les **formules mathématiques** derrière chaque indicateur
- 🎛️ Les équivalents en **traitement du signal** (EMA = filtre IIR, SMA = filtre FIR, etc.)
- ⚡ L'intuition **« rapide vs lent »** en termes de fréquences de coupure des filtres
- 📈 Des **exemples pratiques** de détection de croisement et d'identification de tendance
