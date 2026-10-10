# 🔍 Positions et analyse

L'onglet **Positions** montre ce que vous détenez, ce que chaque position a rapporté au cours de la période et, à un clic, les lots FIFO derrière chaque position. La page de chaque courtier possède le même onglet pour ce courtier uniquement, avec les mêmes paramètres de tableau.

- 📋 **[Positions](#holdings)** — ce que vous possédez à la date de fin
- 📈 **[Performance](#performance)** — ce que chaque position a rapporté au cours de la période
- 🔬 **[Analyse des lots FIFO](#fifo-lots-analysis)** — les lots derrière une position

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Positions (Tableau)" alt="Vue tableau des positions">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Positions (Carte / Treemap)" alt="Vue carte / treemap des positions">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Performance (Tableau)" alt="Vue tableau de la performance">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Performance (Carte / Graphique)" alt="Vue carte / graphique de la performance">
</div>

---

## 🎛️ Choisir une vue

- **Portefeuille / Période** bascule entre [Positions](#holdings) et [Performance](#performance) ; **Tableau / Carte** (les deux icônes) entre un tableau et un graphique.
- **L'icône en forme d'œil** (dans Tableau) affiche, masque ou réordonne les colonnes ; **Réinitialiser la disposition** les restaure. **Voir tout →** ouvre la page des actifs.
- **Pour approfondir une position**, ouvrez son menu **⋮** dans un tableau, ou faites un clic droit dessus dans n'importe quelle vue : **Analyser les lots** ouvre l'[Analyse des lots FIFO](#fifo-lots-analysis) ci-dessous, **Voir l'actif** la page de l'actif.

LibreFolio se souvient de vos choix.

---

## 📋 Positions — ce que vous détenez {: #holdings }

Que possédez-vous à la date de fin, et comment se porte chaque position ? **Portefeuille** liste une ligne par actif et par courtier, la valeur la plus élevée en premier.

**Colonnes affichées**

| Colonne | Ce qu'elle affiche |
|:---|:---|
| **Actif** | L'actif, avec son icône de type |
| **Δ1** / **Δ1%** | Variation du jour du P&L latent à la quantité du jour, en montant et en % de la valeur de la veille |
| **P&L latent** / **P&L %** | Valeur actuelle moins ce qu'a coûté la position ouverte, en montant et en % de ce coût → [Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) |
| **Annualisé** | Rendement composé annuel depuis la première transaction, revenus et frais inclus → [Rendement annualisé net](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md) |
| **YOC** | Les dividendes et intérêts de la dernière année par unité, rapportés à son prix moyen → [Rendement sur coût](#yield-on-cost-yoc) |
| **Valeur** / **Poids** | Ce que vaut la position, et sa part de votre valeur nette, liquidités incluses |
| **Qté** | Actions, unités ou pièces détenues |
| **Prix** *(masqué)* | Le prix unitaire utilisé : le prix de marché, ou le prix de la dernière transaction lorsqu'il n'y a pas de cotation → [Résolution des prix](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/price-resolution.md) |
| **PRU** *(masqué)* | Prix de revient unitaire, chaque achat au taux de change de sa propre date → [Prix de revient unitaire (PRU)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) |
| **Plus ancien lot ouvert** *(masqué)* | Date d'ouverture du plus ancien lot encore ouvert |
| **Courtiers** | Le courtier détenant la position |

**Comment l'interpréter**

- **Le poids inclut les liquidités**, donc les lignes totalisent moins de 100 % lorsque vous détenez des liquidités.
- **Le PRU conserve le taux de change de chaque achat**, tandis que la valeur utilise celui de la date de fin : le P&L latent inclut l'évolution du taux depuis.
- **Dans la carte**, les tuiles sont regroupées par courtier et par type d'actif ; la taille représente la valeur, la couleur le P&L %. Faites défiler pour zoomer, faites glisser pour déplacer, et **Réinitialiser le zoom** (↺) réaffiche tout.

??? info "➖ Cellules vides — quand une valeur manque"

    - **`—` dans P&L latent, P&L % ou PRU** : l'actif n'a aucun prix, ou une partie de ce que vous avez payé est inconnue — un taux de change manquant à une date d'achat, ou un transfert ou ajustement sans coût de base. La [bannière de qualité des données](index.md#data-quality-banner) indique ce qu'il faut corriger.
    - **Δ1** et **Δ1%** nécessitent un prix de marché ; **Annualisé** nécessite une position suffisamment ancienne pour qu'un taux annuel ait un sens.

### 💸 Rendement sur coût (YOC) {: #yield-on-cost-yoc }

Combien de revenu chaque unité vous verse-t-elle, par rapport à ce qu'elle a coûté ? Le **YOC** compare les dividendes et intérêts reçus par chaque unité sur les **365 derniers jours** à son prix d'achat moyen.

**Comment l'interpréter**

- **Une valeur par actif et par courtier**, sur l'année qui se termine à la date de fin : déplacer la date de début ne la change pas.
- **Brut, pas après impôt** : les transactions distinctes d'impôts et de frais ne sont pas soustraites.
- **Survolez une valeur** pour voir le revenu par unité, la période et les taux de change utilisés — chaque paiement au taux de sa propre date.
- **`0.00%`** signifie un revenu enregistré à zéro ; un simple **`-`** signifie aucun revenu au cours de la dernière année.

🔗 **Théorie** : [Rendement sur coût](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) — les règles exactes, et en quoi le YOC diffère du rendement du dividende ou du CAGR

??? info "🚦 Un tiret avec une icône ⓘ — quand le YOC n'est pas disponible"

    LibreFolio n'affiche aucun YOC partiel. Lorsqu'une entrée échoue, survolez l'icône ⓘ ambre pour en connaître la raison : moins d'un an d'historique chez ce courtier et aucun revenu encore, un paiement sans unités détenues la veille, un historique d'achat, de vente, de transfert ou de division qui ne s'additionne pas, un taux de change manquant, ou un prix moyen inconnu. Une fois cela corrigé, le YOC est recalculé.

---

## 📈 Performance — ce que chaque position a rapporté {: #performance }

Quelles positions ont gagné ou perdu de l'argent au cours de la période, et comment ? **Période** liste chaque position de la période, ouverte ou fermée depuis, les plus fortes variations en premier. LibreFolio le calcule la première fois que vous l'ouvrez, cela peut donc prendre un moment.

**Métriques affichées**

- **P&L période**, décomposé comme sur la [carte P&L période](kpi-cards.md#card-1-period-pl) en **Variation latente**, **Ventes**, **Dividendes et intérêts** et **Coûts** → [P&L période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Annualisé** — le résultat de la période en taux annuel, sur la durée pendant laquelle la position a été détenue dans la période → [Rendement annualisé net](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md)
- **Δ1** / **Δ1%** pour les positions ouvertes et, masqués par défaut, **Valeur de début**, **Valeur de fin**, **Plus ancien lot ouvert** et **Statut**
- **Autres effets de la période** — ce qui n'appartient à aucune position : **Revenus non alloués** et **Coûts non alloués**, enregistrés sans actif, et le **Résidu autre / de rapprochement**

**Comment l'interpréter**

- **Les positions fermées** sont en italique, ou portent un badge **Fermé** dans le graphique ; pour n'en lister qu'un type, affichez **Statut** et filtrez-le.
- **Dans la carte**, les gains s'empilent à droite de zéro et les pertes à gauche, le résultat net fermant la ligne ; chaque pourcentage se compare à la valeur de début de la position.
- **Le P&L période d'une position** peut différer de son gain depuis l'origine : seule la période compte.

??? tip "🙈 Masquer les montants — ce que le graphique affiche encore"

    Avec **Masquer les montants** activé (le bouton en forme d'œil dans la barre supérieure), les montants et l'axe du graphique deviennent `•••`, comme dans `+€•••`. Les signes, les devises, les pourcentages, les longueurs de barres et les couleurs restent, vous voyez donc toujours qui a gagné ou perdu, et combien par rapport aux autres. Voir le [mode confidentialité](../settings/preferences.md#privacy-mode).

---

## 🔬 Analyse des lots FIFO {: #fifo-lots-analysis }

Quels achats composent une position, où sont-ils détenus, et comment chacun s'est-il comporté ? L'**Analyse des lots FIFO** répond lot par lot : chaque achat ouvre un *lot*, et chaque vente ferme d'abord les lots ouverts les **plus anciens** — Premier entré, premier sorti.

Choisissez **Analyser les lots** sur une position et le panneau s'ouvre en dessous, pour les courtiers de la page : votre filtre de courtier sur le tableau de bord, le courtier lui-même sur sa propre page. **Voir l'actif** (↗) ouvre l'actif, **✕** ferme le panneau.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Vue d'ensemble" alt="Vue d'ensemble de l'analyse des lots FIFO">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 PRU / Prix de marché" alt="Graphique PRU et prix de marché">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Durée de vie et conservation des lots" alt="Diagramme de Gantt de la durée de vie et de la conservation des lots">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Tableau unifié des lots" alt="Tableau unifié des lots">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Comparaison de valeur" alt="Graphique de comparaison de valeur">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Comparaison de rendement" alt="Graphique de comparaison de rendement">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Modale de détail du lot" alt="Modale de détail du lot">
</div>

**Comment les blocs fonctionnent ensemble**

- **Une seule sélection** : cliquez sur les bulles, les barres ou les lignes du tableau pour choisir des lots ; si aucun n'est choisi, chaque lot visible compte. **Ouvert / Fermé**, sur la chronologie, filtre chaque bloc.
- **Double-cliquez pour naviguer** : d'un marqueur de graphique vers les lots de cette transaction, d'une barre de chronologie vers sa ligne de tableau, et inversement.
- **Montants complets du courtier** : chez un courtier que vous codétenez, votre part n'est pas appliquée ici, contrairement aux cartes KPI et aux Positions.

🔗 **Théorie** : [Moteur FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md) · [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md) · [Appariement FIFO](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching) · [Fiscalité](../../financial-theory/fundamentals/taxation.md)

### 💹 1. PRU / Prix de marché

Comment le prix se compare-t-il à ce que vous avez payé, et où en est chaque lot ?

**Métriques affichées**

- **Prix de marché** — en pointillés lorsque LibreFolio l'estime à partir de votre dernière transaction → [Chaîne de prix d'évaluation](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)
- **PRU** — une ligne par courtier, et une ligne **Combiné** en pointillés lorsque l'actif est détenu chez plusieurs → [Prix de revient unitaire (PRU)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Bulles** — une par lot long, à son rendement total, parmi les marqueurs de vos transactions et paiements → [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)

**Comment l'interpréter**

- **Abs / %** affiche les prix ou leur variation depuis le premier point ; **Auto / Depuis 0** définit le point de départ de l'axe.
- **La couleur de la bulle** est le courtier d'ouverture, sa **taille** la quantité du lot (**Abs**) ou sa valeur d'ouverture (**%**) ; une **bordure en pointillés** signifie une évaluation au coût.
- **Un trou dans une ligne de PRU** est un jour dont le PRU est inconnu : aucune moyenne erronée n'est tracée.

### 🕒 2. Durée de vie et conservation des lots

Quand chaque lot a-t-il été ouvert, et quel courtier le détenait ?

**Métriques affichées**

- **Barres** — une par lot, chacune colorée selon le courtier qui le détient et aussi épaisse que la quantité détenue ; violette en pointillés en transit, avec une voie par courtier après un transfert → [Moteur FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)

**Comment l'interpréter**

- **Ouvert / Fermé** ne conserve que les lots ouverts, uniquement les fermés, ou les deux.
- **Une barre plus fine** a perdu une partie de sa quantité, par exemple à cause d'une vente partielle.
- **Cliquez** sur une barre pour sélectionner son lot, **double-cliquez** dessus pour trouver sa ligne dans le tableau.

### 📋 3. Tableau des lots

Chaque lot avec ses chiffres, selon le filtre et la sélection du panneau.

**Métriques affichées**

- **Date d'ouverture**, **P&L total**, **Rendement total**, **Annualisé**, **Valeur actuelle**, **Quantité ouverte** et **Conservation**, avec une ligne **Totaux** → [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Revenus** lorsqu'un lot en a reçu, et **Frais**, **Impôts**, **P&L net** et **Rendement net** lorsqu'un lot supporte des coûts → [Coûts et métriques nettes](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)

**Comment l'interpréter**

- **Cliquez** sur une ligne pour la sélectionner, **double-cliquez** pour la retrouver dans la chronologie ; la couleur de la ligne est celle du courtier d'ouverture.
- **Le menu ⋮** propose **Voir le détail du lot**, **Aller au lot dans le Gantt**, **Aller à la transaction d'ouverture** et **Copier l'identifiant du lot** — une référence stable, pratique pour le support.
- **D'autres colonnes**, comme **Valeur d'ouverture**, se cachent derrière l'icône en forme d'œil.

### 💰 4. Comparaison valeur / rendement

Que valent les lots sélectionnés, et qu'ont-ils rapporté depuis leur ouverture ? Si aucun n'est sélectionné, le graphique couvre chaque lot visible.

**Métriques affichées**

- **Valeur** — **Valeur résiduelle**, **Produit de cession** et **Revenus cumulés** empilés jusqu'à la **Valeur globale**, par rapport à la **Valeur d'ouverture** → [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Rendement** — le résultat depuis l'ouverture, en montant (**Abs**) ou en pourcentage (**%**) : un **Rendement agrégé**, plus une ligne par lot lorsque vous en comparez plusieurs

**Comment l'interpréter**

- **Valeur globale supérieure à la valeur d'ouverture** : les lots ont gagné, ventes et revenus inclus.
- **Une ligne en pointillés** dans **Valeur** est une valeur estimée au coût, sans prix de marché.

### 🧾 5. Détail du lot

Toute l'histoire d'un lot. Ouvrez-le avec **Voir le détail du lot** (⋮) ou en cliquant sur sa cellule **Conservation**.

**Métriques affichées**

- **Résumé** — valeur d'ouverture et valeur actuelle, produit de cession, **P&L FIFO**, **P&L total**, **Rendement total**, et **Rendement en liquidités** lorsque le lot a reçu des revenus → [Analyse des lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Décomposition nette** — le P&L total moins les frais et impôts alloués au lot → [Coûts et métriques nettes](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)
- **Conservation actuelle** et **Historique** — où se trouve le lot maintenant, et chaque événement depuis son ouverture

**Comment l'interpréter**

- **Les quantités correspondent aux positions complètes du courtier**, comme l'indique l'icône ⓘ à côté.
- **Aller à la transaction** ouvre la transaction de la ligne d'historique que vous avez choisie — par défaut, celle d'ouverture.

??? warning "⚠️ Quand le panneau vous avertit"

    - **Une bannière repliée** liste ce qui manque — un taux, un prix, un coût d'achat — avec une puce par lot concerné qui retrouve sa bulle. Corrigez-la comme pour la [bannière de qualité des données](index.md#data-quality-banner).
    - **Un message rouge** signifie que les quantités ou les transferts ne s'additionnent pas : les chiffres peuvent être incomplets, vérifiez donc les transactions de l'actif.
    - **Un lot évalué au coût** n'a pas de prix de marché : bordure de bulle en pointillés, aucune plus-value ou moins-value de marché.

---

## 🔗 Voir aussi

- 💰 **[Cartes KPI](kpi-cards.md)** — les mêmes résultats pour l'ensemble du portefeuille
- 💸 **[Transactions](../transactions/index.md)** — l'onglet **Transactions** du tableau de bord liste les opérations de la plage et des courtiers sélectionnés
- 🛠️ **[Détails techniques](../../developer/frontend/pages/index.md#dashboard)** — pour les développeurs : comment fonctionnent en interne l'onglet Positions et le panneau des lots

---

*[⬅️ Retour à la vue d'ensemble du tableau de bord](index.md)*
