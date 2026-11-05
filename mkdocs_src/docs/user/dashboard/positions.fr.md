# 🔍 Positions et analyse

L'onglet **Positions** montre ce que vous détenez, ce que chaque position a rapporté sur la période et, à un clic, les lots FIFO derrière n'importe quelle position. La page de chaque courtier possède le même onglet, pour ce courtier seul, avec les mêmes paramètres de tableau.

- 📋 **[Positions](#holdings)** — ce que vous détenez à la date de fin
- 📈 **[Période](#performance)** — ce que chaque position a rapporté sur la période
- 🔬 **[Analyse des lots FIFO](#fifo-lots-analysis)** — les lots derrière une position

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Portefeuille (Tableau)" alt="Vue tableau du portefeuille">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Portefeuille (Carte / Treemap)" alt="Vue carte du portefeuille">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Période (Tableau)" alt="Vue tableau de la période">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Période (Carte / Graphique)" alt="Vue carte de la période">
</div>

---

## 🎛️ Choisir une vue

- **[Portefeuille](#holdings) / [Période](#performance)** bascule entre ce que vous détenez et ce que chaque position a rapporté ; **Tableau / Carte** (les deux icônes) entre un tableau et un graphique.
- **L'icône en forme d'œil** (en mode Tableau) affiche, masque ou réordonne les colonnes ; **Réinitialiser la mise en page** les rétablit. **Voir tout →** ouvre la page Actifs.
- **Pour creuser une position**, ouvrez son menu **⋮** dans un tableau, ou faites un clic droit dessus dans n'importe quelle vue : **Analyser les lots** ouvre l'[Analyse des lots FIFO](#fifo-lots-analysis) sous les positions (sur le tableau de bord comme sur la page d'un courtier), **Voir l'actif** la page de l'actif.

LibreFolio se souvient de vos choix.

---

## 📋 Positions — ce que vous détenez {: #holdings }

Que détenez-vous à la date de fin, et comment se porte chaque position ? **Portefeuille** liste une ligne par actif et par courtier, la valeur la plus élevée en premier. En bas, en italique, viennent les positions que vous avez **entièrement vendues au cours de la période** : elles n'ont ni valeur, ni poids, ni rendement, mais vous pouvez les cocher pour tracer leur courbe dans le [graphique](#return-of-the-positions), et elles disposent des actions de ligne habituelles.

**Colonnes affichées**

| Colonne | Ce qu'elle montre |
|:---|:---|
| **Actif** | L'actif, avec son icône de type |
| **Δ1** / **Δ1%** | Variation du jour du P&L latent à la quantité du jour, en argent et en % de la valeur d'hier |
| **P&L latent** / **P&L %** | Valeur actuelle moins ce que la position ouverte a coûté, en argent et en % de ce coût → [Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) |
| **Annualisé** | Rendement composé annuel depuis la première transaction, revenus et frais inclus → [Rendement annualisé net](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md) |
| **YOC** | Les dividendes et intérêts de la dernière année par unité, rapportés à son prix moyen → [Rendement sur coût](#yield-on-cost-yoc) |
| **Valeur** / **Poids** | Ce que vaut la position, et sa part de votre valeur nette, liquidités incluses |
| **Qté** | Actions, parts ou cryptomonnaies détenues |
| **Prix** *(masqué)* | Le prix unitaire utilisé : le prix de marché, ou le prix de votre dernier achat ou de votre dernière vente lorsqu'il n'y a pas de cotation ; `—` pour un actif valorisé à ce qu'il vous a coûté, qui n'a aucun prix → [Résolution du prix](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/price-resolution.md) |
| **Coût moyen** *(masqué)* | Prix d'achat moyen par unité, chaque achat au taux de change de sa propre date → [Prix de revient unitaire (PRU)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) |
| **Plus ancien lot ouvert** *(masqué)* | Date d'ouverture du plus ancien lot encore ouvert chez ce courtier ; une division d'actions conserve les dates |
| **Courtiers** | Le courtier qui détient la position |

**Comment le lire**

- **Le poids tient compte des liquidités**, donc les lignes totalisent moins de 100 % lorsque vous détenez des liquidités.
- **Le poids affiche `—` lorsque votre valeur nette est nulle ou négative**, par exemple lorsque vous avez emprunté plus de liquidités que vos positions ne valent : une part de celle-ci n'aurait aucun sens.
- **Le coût moyen conserve le taux de change de chaque achat**, tandis que la valeur utilise celui de la date de fin : le P&L latent inclut l'évolution du taux depuis.
- **Δ1 compare deux prix à deux taux de change** : le prix du jour, celui auquel la position est valorisée, au taux du jour, face au dernier prix de marché jusqu'à hier au taux d'hier. Pour un actif coté dans une autre devise dont le prix n'a pas bougé, Δ1 ne reflète que la variation du taux de change sur la journée, et `0` lorsque le taux n'a pas varié non plus.
- **Dans la Carte**, les tuiles sont groupées par courtier et par type d'actif ; la taille est la valeur, la couleur le P&L %. Faites défiler pour zoomer, glissez pour déplacer, et **Réinitialiser le zoom** (↺) réaffiche le tout.

??? info "➖ Cellules vides — quand une valeur manque"

    - **`—` dans le P&L latent, le P&L % ou le coût moyen** : une partie de ce que vous avez payé est inconnue — un taux de change manquant à une date d'achat, ou un transfert ou un ajustement sans coût de base —, ou, pour le P&L latent et le P&L % uniquement, le prix ne peut pas être converti car le taux de change de la date de fin manque. La [bannière de qualité des données](index.md#data-quality-banner) indique ce qu'il faut corriger.
    - **`—` dans le prix, avec un P&L latent de `0`** : l'actif n'a aucun prix — ni prix de marché, ni achat ni vente, comme lorsque vous l'avez reçu via un ajustement ou un transfert —, sa valeur est donc ce qu'il vous a coûté.
    - **Δ1** et **Δ1%** nécessitent un prix de marché aujourd'hui et un prix daté d'hier ou avant ; le premier jour de votre portefeuille, il n'y a pas de veille, ils restent donc vides. **L'annualisé** nécessite une position suffisamment ancienne pour qu'un taux annuel ait un sens.

### 📉 Rendement des positions {: #return-of-the-positions }

Laquelle de vos positions a fait mieux que le portefeuille, et laquelle moins bien ? Sur le tableau de bord, la vue **Tableau** de **Portefeuille** comme de **Période** place une case à cocher sur chaque ligne et, sous le tableau, un graphique **Rendement des positions**. Il se trouve à côté de l'allocation par actif — le camembert du jour et la zone d'historique, avec deux boutons — à environ 3/5 et 2/5 de la ligne, comme le graphique de croissance et l'allocation de la vue d'ensemble. La vue **Carte** n'a pas de graphique.

- **Rien de coché** : le graphique n'affiche que la courbe du portefeuille. **Cochez une ligne**, dans l'un ou l'autre tableau, pour ajouter une courbe pour cette position, et cochez-en d'autres pour les comparer.
- **La légende** sous le titre a un bouton par courbe : cliquez dessus pour masquer ou afficher la courbe. Un **drapeau** marque une position clôturée, et un **sigle d'avertissement** une position dont un prix ou un taux de change manque, dont la courbe omet ces jours-là.
- **Abs / % / Glissant** changent la vue ; les boutons sont sur le graphique, en haut à droite. **Abs** est le gain ou la perte de la position en argent, depuis le début de la période. **%** est son rendement en *base 100* : chaque courbe part de 100 le premier jour de la période, donc 112 signifie +12 %. **Glissant** est décrit ci-dessous. LibreFolio se souvient de la vue.
- **La courbe d'une position clôturée s'arrête le jour de sa clôture** ; survolez le bouton de la légende pour voir la date.
- **Jusqu'à 50 positions** peuvent être tracées en même temps.

**Glissant — comparer les actifs entre eux.** Pour chaque position cochée, la courbe montre le pourcentage de variation du **prix** de l'actif sur une fenêtre qui glisse le long de la période, afin que des actifs achetés à des jours différents puissent être comparés sur un pied d'égalité. La fenêtre est la plus longue parmi 1 semaine, 1 mois, 3 mois et 1 an qui tient dans la période. Elle est **par actif** : deux courtiers détenant le même actif partagent une seule courbe. Il n'y a **aucune courbe de portefeuille** dans cette vue, puisque le portefeuille n'a pas de prix.

??? info "📐 Pourquoi la courbe du portefeuille peut différer des positions"

    La courbe du portefeuille est le rendement que mesure le tableau de bord, le [rendement pondéré dans le temps](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md), et non le gain de vos positions sur le capital qu'elles ont mobilisé. Les deux peuvent donc différer, même lorsque toutes les positions sont cochées ; une phrase sous le graphique le précise. Les jours où votre portefeuille vaut zéro ou moins, il n'y a pas de rendement pondéré dans le temps, la courbe du portefeuille présente donc une lacune en **%** ([Quand aucun TWRR n'est affiché](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr)).

### 💸 Rendement sur coût (YOC) {: #yield-on-cost-yoc }

Combien chaque unité vous rapporte-t-elle, comparé à ce qu'elle a coûté ? **YOC** compare les dividendes et intérêts reçus par unité sur les **365 derniers jours** avec son prix d'achat moyen.

**Comment le lire**

- **Une valeur par actif et par courtier**, sur l'année qui se termine à la date de fin : déplacer la date de début ne la change pas.
- **Brut, et non net d'impôt** : les transactions distinctes d'impôt et de frais ne sont pas soustraites.
- **Survolez une valeur** pour voir le revenu par unité, la période et les taux de change utilisés — chaque paiement au taux de sa propre date.
- **`0.00%`** signifie un revenu enregistré à zéro, ou des corrections qui l'annulent exactement ; un simple **`-`** signifie aucun revenu sur la dernière année.

🔗 **Théorie** : [Rendement sur coût](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) — les règles exactes, et en quoi le YOC diffère du rendement du dividende ou du CAGR

??? info "🚦 Un tiret avec une icône ⓘ — quand le YOC n'est pas disponible"

    LibreFolio n'affiche pas de YOC partiel. Lorsqu'une donnée d'entrée fait défaut, survolez l'ⓘ ambre pour en connaître la raison : moins d'un an d'historique chez ce courtier et encore aucun revenu, un paiement alors qu'aucune unité n'était détenue la veille, un historique d'achats, de ventes, de transferts ou de divisions qui ne s'additionne pas, un taux de change manquant, ou un prix moyen inconnu. Une fois cela corrigé, le YOC est recalculé. Un tiret apparaît aussi lorsque les corrections enregistrées sur la dernière année — des lignes plus anciennes de dividendes ou d'intérêts négatifs — totalisent plus que le revenu lui-même : l'ⓘ indique alors *Les corrections dépassent le revenu de la dernière année.*

---

## 📈 Période — ce que chaque position a rapporté {: #performance }

Quelles positions ont gagné ou perdu de l'argent sur la période, et comment ? **Période** liste toutes les positions de la période, ouvertes ou clôturées depuis, les plus fortes variations en premier. LibreFolio la calcule la première fois que vous l'ouvrez, cela peut donc prendre un instant.

**Indicateurs affichés**

- **P&L période**, décomposé comme sur la [carte P&L période](kpi-cards.md#card-1-period-pl) en **Variation non réalisée**, **Ventes**, **Dividendes et intérêts** et **Coûts** → [P&L période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Annualisé** — le résultat de la période en taux annuel, sur la durée pendant laquelle la position a été détenue dans la période ; `—` pour une position clôturée dans la période après moins de 30 jours de détention, trop court pour qu'un taux annuel ait un sens → [Rendement annualisé net](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md)
- **Δ1** / **Δ1%** pour les positions ouvertes et, masqués par défaut, **Valeur de début**, **Valeur de fin**, **Plus ancien lot ouvert** et **Statut**
- **Autres effets de la période** — ce qui n'appartient à aucune position : les **revenus non alloués** et les **coûts non alloués**, enregistrés sans actif ; l'**effet de change sur les liquidités**, ce que les taux de change ont fait pendant la période sur les liquidités que vous détenez dans une autre devise, avec une ligne uniquement pour un courtier dont les liquidités ont varié sous l'effet des taux ; les **transferts à la valeur de marché**, lorsque vous ne regardez qu'une partie de vos courtiers, le gain que des titres transférés depuis ou vers un courtier hors de votre sélection ont réalisé avant de franchir la frontière, une ligne par courtier ([Transferts à la valeur de marché](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#transfers-at-market-value)) ; et le **résidu Autres / réconciliation**, ce qui reste — une devise échangée avec un coût, la variation de change des liquidités en route entre deux de vos courtiers, des titres en route entre eux le premier ou le dernier jour de la période, une vente laissée hors des **Ventes** parce qu'un taux ou un coût d'achat manque, ou le coût d'achat d'un minuscule reliquat — 0,00001 unité ou moins, qu'une vente de presque toutes les unités peut laisser et qui ne compte pas comme une position → [Effet de change sur les liquidités](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#fx-on-cash)

**Comment le lire**

- **Les positions clôturées** sont en italique, ou portent un badge **Clôturée** dans le graphique ; pour n'en lister qu'un seul type, affichez **Statut** et filtrez dessus.
- **Dans la Carte**, les gains s'empilent à droite de zéro et les pertes à gauche, le résultat net fermant la ligne ; chaque pourcentage se compare à la valeur de début de la position.
- **Le P&L période d'une position** peut différer de son gain depuis l'origine : seule la période compte.
- **La valeur de début** et **la valeur de fin** sont calculées comme la **Valeur** dans **Portefeuille** — mêmes prix, un actif sans prix valorisé à ce qu'il vous a coûté, le taux de change de chaque jour —, de sorte que les lignes plus les **Autres effets de la période** totalisent la [carte P&L période](kpi-cards.md#card-1-period-pl). Un **`—`** dans **Variation non réalisée** signifie qu'une valeur n'a pas pu être calculée, par exemple un taux de change ou un coût d'achat manquant : ce n'est pas un zéro.
- **Des titres déplacés entre deux de vos courtiers** pendant la période scindent leur résultat : la ligne du courtier émetteur conserve ce qu'ils ont fait jusqu'à leur arrivée, celle du courtier récepteur ce qu'ils ont fait ensuite ; le total ne change pas.

??? tip "🙈 Masquer les montants — ce que le graphique montre encore"

    Lorsque **Masquer les montants** est activé (le bouton en forme d'œil dans la barre supérieure), les montants et l'axe du graphique deviennent `•••`, comme dans `+€•••`. Les signes, les devises, les pourcentages, la longueur des barres et les couleurs restent, vous voyez donc toujours qui a gagné ou perdu, et combien par rapport aux autres. Voir le [Mode confidentialité](../settings/preferences.md#privacy-mode).

---

## 🔬 Analyse des lots FIFO {: #fifo-lots-analysis }

Quels achats composent une position, où sont-ils détenus, et comment chacun s'en est-il sorti ? L'**Analyse des lots FIFO** répond lot par lot : chaque achat ouvre un *lot*, et chaque vente clôture d'abord les lots ouverts les **plus anciens** — premier entré, premier sorti.

Choisissez **Analyser les lots** sur une position et le panneau s'ouvre, pour les courtiers de la page : votre filtre de courtiers sur le tableau de bord, le courtier lui-même sur sa propre page. Sur le tableau de bord, comme sur la page d'un courtier, il s'ouvre **sous les positions** : le tableau des positions et le graphique de rendement restent à l'écran. **Voir l'actif** (↗) ouvre l'actif ; **✕** ferme le panneau, tout comme le bouton Retour du navigateur.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Vue d'ensemble" alt="Vue d'ensemble de l'analyse des lots FIFO">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 PRU / Prix de marché" alt="Graphique du PRU et du prix de marché">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Vie et conservation du lot" alt="Diagramme de Gantt de la vie et de la conservation des lots">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Tableau unifié des lots" alt="Tableau unifié des lots">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Comparaison des valeurs" alt="Graphique de comparaison des valeurs">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Comparaison des rendements" alt="Graphique de comparaison des rendements">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Modale de détail du lot" alt="Modale de détail du lot">
</div>

**Comment les blocs fonctionnent ensemble**

- **Une seule sélection** : cliquez sur les bulles, les barres ou les lignes du tableau pour choisir des lots ; sans sélection, tous les lots visibles comptent. **Ouverts / Clôturés**, sur la chronologie, filtre tous les blocs.
- **Double-clic pour naviguer** : d'un repère du graphique vers les lots de cette transaction, d'une barre de la chronologie vers sa ligne de tableau, et inversement.
- **Montants complets du courtier** : sur un compte de courtier détenu en copropriété, votre quote-part n'est pas appliquée ici, contrairement aux cartes KPI et aux Positions.

🔗 **Théorie** : [Moteur FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md) · [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md) · [Appariement FIFO](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching) · [Fiscalité](../../financial-theory/fundamentals/taxation.md)

### 💹 1. Coût moyen / Prix de marché

Comment le prix se compare-t-il à ce que vous avez payé, et où en est chaque lot ?

**Indicateurs affichés**

- **Prix de marché** — en pointillés là où LibreFolio l'estime à partir de votre dernière transaction → [Chaîne de prix de valorisation](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)
- **Coût moyen** — une ligne par courtier, et une ligne **Combinée** en pointillés lorsque l'actif est logé chez plusieurs → [Prix de revient unitaire (PRU)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Bulles** — une par lot long, à son rendement total, parmi les repères de vos transactions et paiements → [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)

**Comment le lire**

- **Abs / %** affiche les prix ou leur variation depuis le premier point ; **Auto / Depuis 0** définit le point de départ de l'axe.
- **La couleur d'une bulle** est le courtier d'ouverture, sa **taille** la quantité du lot (**Abs**) ou sa valeur d'ouverture (**%**) ; une **bordure en pointillés** signifie une valorisation au coût.
- **Une lacune dans une ligne de coût moyen** correspond à un jour dont le coût moyen est inconnu : aucune moyenne erronée n'est tracée.
- **La ligne du prix de marché** couvre toute la période, y compris les jours sans lot ouvert : après avoir tout vendu, elle continue jusqu'à la date de fin.

### 🕒 2. Vie et conservation du lot

Quand chaque lot a-t-il été ouvert, et quel courtier le détenait ?

**Indicateurs affichés**

- **Barres** — une par lot, colorée selon le courtier qui le détient et aussi épaisse que la quantité détenue ; violette en pointillés pendant le transit, avec une voie par courtier après un transfert → [Moteur FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)

**Comment le lire**

- **Ouverts / Clôturés** ne conserve que les lots ouverts, que les lots clôturés, ou les deux.
- **Une barre plus fine** a perdu une partie de sa quantité, par exemple lors d'une vente partielle.
- **Cliquez** sur une barre pour sélectionner son lot, **double-cliquez** pour trouver sa ligne dans le tableau.
- **Les repères sur une barre** sont les événements du lot : ▲ achat, ▼ vente, ◆ transfert, **+** ajustement entrant, **×** ajustement sortant et │ division. Survolez un repère, touchez-le ou atteignez-le au clavier pour voir ce qui s'est passé, la date, la quantité (masquée par ••• en mode confidentialité) et le courtier : un transfert entre vos courtiers indique **De** et **Vers**, un transfert avec un courtier hors du panneau ne nomme que le courtier que vous consultez, et un point où plusieurs événements tombent le même jour les liste tous. Cliquez ou double-cliquez sur un repère comme sur sa barre.

### 📋 3. Tableau des lots

Chaque lot avec ses chiffres, selon le filtre et la sélection du panneau.

**Indicateurs affichés**

- **Date d'ouverture**, **P&L total**, **Rendement total**, **Annualisé**, **Valeur actuelle**, **Quantité ouverte** et **Conservation**, avec une ligne **Totaux** → [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Revenus** lorsqu'un lot en a reçu, et **Frais**, **Impôts**, **P&L net** et **Rendement net** lorsqu'un lot supporte des coûts → [Coûts et indicateurs nets](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)

**Comment le lire**

- **Cliquez** sur une ligne pour la sélectionner, **double-cliquez** pour la retrouver dans la chronologie ; la couleur de la ligne est le courtier d'ouverture.
- **Le menu ⋮** propose **Voir le détail du lot**, **Aller au lot dans le Gantt**, **Aller à la transaction d'ouverture** et **Copier l'identifiant du lot** — une référence stable, pratique pour le support.
- **D'autres colonnes**, comme **Valeur d'ouverture**, attendent derrière l'icône en forme d'œil.

### 💰 4. Comparaison des valeurs / rendements

Que valent les lots sélectionnés, et qu'ont-ils gagné depuis leur ouverture ? Sans sélection, le graphique couvre tous les lots visibles.

**Indicateurs affichés**

- **Valeur** — **Valeur résiduelle**, **Produit des ventes** et **Revenus cumulés** empilés jusqu'à la **Valeur globale**, face à la **Valeur d'ouverture** → [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Rendement** — le résultat depuis l'ouverture, en argent (**Abs**) ou en pourcentage (**%**) : un **Rendement agrégé**, plus une ligne par lot lorsque vous en comparez plusieurs

**Comment le lire**

- **Valeur globale supérieure à la valeur d'ouverture** : les lots ont gagné, ventes et revenus inclus.
- **Une ligne en pointillés** dans **Valeur** signifie que la valeur actuelle d'un lot est estimée au coût : son actif n'a aucun prix — ni prix de marché, ni achat ni vente, ni transfert dont le coût compte comme son prix jusqu'à la date de fin.
- **Un début plat** : jusqu'au premier prix de l'actif — prix de marché, achat ou vente, ou coût d'un transfert qui l'a apporté avant tout le reste —, un lot, par exemple celui que vous avez reçu via un ajustement, est valorisé à ce qu'il vous a coûté, sans gain ni perte. Un jour dont le prix n'a pas de taux de change est quant à lui écarté.

### 🧾 5. Détail du lot

Toute l'histoire d'un lot. Ouvrez-la avec **Voir le détail du lot** (⋮) ou en cliquant sur sa cellule **Conservation**.

**Indicateurs affichés**

- **Résumé** — valeur d'ouverture et valeur actuelle, produit, **P&L FIFO**, **P&L total**, **Rendement total**, et **Rendement en liquidités** lorsque le lot a reçu des revenus → [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Détail net** — le P&L total moins les frais et impôts alloués au lot → [Coûts et indicateurs nets](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)
- **Conservation actuelle** et **Historique** — où se trouve le lot maintenant, et chaque événement depuis son ouverture. Un transfert entre deux de vos courtiers se lit en deux lignes, *A → En transit* et *En transit → B*, même lorsque les unités partent et arrivent le même jour

**Comment le lire**

- **Les quantités correspondent à l'ensemble des positions du courtier**, comme l'indique l'ⓘ à côté.
- **Un transfert avec un courtier hors du panneau** compte comme des unités entrantes ou sortantes. Les unités reçues ouvrent un nouveau lot le jour de leur arrivée, au coût que porte le transfert. Les unités envoyées clôturent leurs lots le jour de leur départ, au prix de marché de ce jour, de sorte que le gain qu'elles ont réalisé chez ce courtier compte comme réalisé ici. L'historique du lot étiquette ces mouvements **TRANSFER+** et **TRANSFER-**, et les graphiques les marquent comme des transferts — ◆ sur Vie et conservation du lot, **Transfert entrant** et **Transfert sortant** sur les repères de Coût moyen / Prix de marché — sans nommer l'autre courtier. Pour suivre les lots d'origine au fil du mouvement, ouvrez le panneau avec les deux courtiers (aucun filtre de courtier sur le tableau de bord). Un transfert encore en route le dernier jour du panneau affiche ses unités comme en transit.
- **Aller à la transaction** ouvre la transaction de la ligne d'historique que vous avez choisie — par défaut, celle d'ouverture.

??? warning "⚠️ Quand le panneau vous avertit"

    - **Une bannière repliée** liste ce qui manque — un taux, un prix, un coût d'achat — avec une puce par lot concerné qui retrouve sa bulle. Corrigez-le comme pour la [bannière de qualité des données](index.md#data-quality-banner). La bannière repliée liste aussi les revenus et les coûts qu'aucun lot n'a pu prendre en charge — un dividende versé après la vente de tous les lots, par exemple —, chacun avec son propre montant et sa date.
    - **Un message rouge** signifie que les quantités ou les transferts de certaines transactions de l'actif ne s'additionnent pas, si bien que ses lots ne peuvent pas être reconstruits. Il liste chaque transaction à corriger avec son jour, son courtier, ce qui ne va pas et un bouton **Aller à la transaction**. Pendant ce temps, le panneau masque les lots, leur chronologie et la comparaison, et le premier graphique ne conserve que ses lignes de **Coût moyen** et le **Prix de marché**. Corrigez ces transactions et les lots réapparaissent.
    - **Valorisé au coût** : les jours précédant le premier prix de l'actif — aucun prix de marché, aucun achat ni vente, aucun transfert dont le coût compte comme son prix —, ses lots sont valorisés à ce qu'ils ont coûté, sans gain ni perte de marché, et la bannière nomme ces jours. Sans aucun prix jusqu'à la date de fin, la bulle du lot a une bordure en pointillés.

---

## 🔗 Voir aussi

- 💰 **[Cartes KPI](kpi-cards.md)** — les mêmes résultats pour l'ensemble du portefeuille
- 💸 **[Transactions](../transactions/index.md)** — l'onglet **Transactions** du tableau de bord liste les opérations de la plage et des courtiers sélectionnés
- 🛠️ **[Détails techniques](../../developer/frontend/pages/index.md#dashboard)** — pour les développeurs : le fonctionnement interne de l'onglet Positions et du panneau des lots

---

*[⬅️ Retour à la vue d'ensemble du tableau de bord](index.md)*
