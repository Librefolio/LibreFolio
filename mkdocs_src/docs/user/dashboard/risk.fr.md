# 🛡️ Onglet Risque

L'onglet **Risque** du [Tableau de bord](index.md) montre à quel point votre portefeuille est risqué, à travers quatre questions simples — de ce qui s'est réellement produit à ce qui pourrait se produire. Il se situe entre **Positions & Analyse** et **Transactions**, et la page de chaque courtier possède le même onglet, mais pour ce courtier uniquement.

Chaque bloc ci-dessous suit un même schéma : ce à quoi il répond, une capture d'écran, ses outils et comment les lire.

- 📉 **[Combien cela peut-il faire mal ?](#how-much-can-it-hurt)** — les pertes que votre portefeuille a réellement subies
- 🧩 **[Suis-je aussi diversifié que je le pense ?](#diversification)** — quelles positions portent le risque, et lesquelles évoluent ensemble
- ⚖️ **[Suis-je rémunéré pour ce risque ?](#being-paid)** — le rendement face au risque, position par position et face à un indice de référence
- 🔮 **[Et si… ?](#what-if)** — une crise passée, un choc que vous choisissez, ou une simulation
- 🚩 **[Avis et données manquantes](#notices)** — ce qui manquait aux données, et quoi faire

---

## 📉 Combien cela peut-il faire mal ? {: #how-much-can-it-hurt }

Combien pourriez-vous perdre, et à quel point cela a-t-il déjà été grave ? Chaque chiffre ici correspond à quelque chose que votre portefeuille a réellement traversé durant la période ; les dépôts et les retraits ne comptent ni comme gains ni comme pertes.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-hurt" alt="Le bloc Combien cela peut-il faire mal ? : les cartes Un mauvais jour, Un mauvais mois et La pire chute, chacune avec son montant, et leurs lignes de détail (pire jour réellement observé, durée de la chute, récupération nécessaire, Repli à risque, Moyenne au-delà de ce seuil) ; puis le Temps passé sous le pic avec l'indice d'Ulcer, et la Distribution des rendements quotidiens avec le seuil de VaR" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils présentés**

- **Un mauvais jour**, **Un mauvais mois** — votre perte moyenne sur les 5 % de jours les plus mauvais, ou sur des périodes d'un mois → [VaR conditionnelle](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Seuil de VaR** — sur la *Distribution des rendements quotidiens* : la perte quotidienne que seuls les 5 % de jours les plus mauvais ont dépassée → [Valeur à risque](../../financial-theory/technical-analysis/risk-metrics/value-at-risk.md)
- **Pire jour réellement observé** — le seul pire jour de la période → [Pire réalisation](../../financial-theory/technical-analysis/risk-metrics/worst-realization.md)
- **La pire chute** — la baisse la plus profonde d'un sommet à un creux ultérieur → [Perte maximale](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Repli à risque** — à quelle distance sous son pic le portefeuille se trouvait, en excluant ses 5 % de jours les plus mauvais → [Repli à risque](../../financial-theory/technical-analysis/risk-metrics/drawdown-at-risk.md)
- **Moyenne au-delà de ce seuil** — à quelle distance sous son pic il se trouvait, en moyenne, lors de ces pires jours → [Repli à risque conditionnel](../../financial-theory/technical-analysis/risk-metrics/conditional-drawdown-at-risk.md)
- **Actuellement en baisse depuis le pic** — à quelle distance sous son dernier sommet le portefeuille se situe aujourd'hui → [Repli actuel](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **indice d'Ulcer** — sous *Temps passé sous le pic* : la profondeur et la durée des chutes ; plus il est bas, plus c'est calme → [indice d'Ulcer](../../financial-theory/technical-analysis/risk-metrics/ulcer-index.md)

**Comment le lire**

- **Des horizons différents** : les cartes vont d'un jour à un mois, puis à la pire chute, ne les additionnez donc jamais.
- **Le montant** sous chaque pourcentage correspond à cette perte appliquée à votre valeur nette.
- **Actuellement en baisse depuis le pic** n'apparaît que lorsque votre portefeuille est sous son dernier sommet.
- **Les icônes ? et ⓘ** à côté d'un chiffre ouvrent sa page théorique.

---

## 🧩 Suis-je aussi diversifié que je le pense ? {: #diversification }

Posséder de nombreuses positions n'est pas la même chose qu'être diversifié. Ce bloc montre quelles positions portent réellement votre risque, et lesquelles évoluent si étroitement ensemble qu'elles constituent le même pari.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-diversification" alt="Le bloc Suis-je aussi diversifié que je le pense ? : la phrase sous le titre ; les cartes Combien de paris indépendants détiens-je réellement ?, Le fait de répartir l'argent a-t-il apporté quelque chose ? et Quelle part de mon portefeuille n'est pas mesurée ici ? ; les positions avec leur poids, leur contribution au risque et la barre bidirectionnelle ; et Lesquelles d'entre elles sont le même pari ?, avec sa matrice, Les plus similaires et Celles qui se compensent" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils présentés**

- **Combien de paris indépendants détiens-je réellement ?** — à quel point votre argent est réparti uniformément → [Concentration](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **Le fait de répartir l'argent a-t-il apporté quelque chose ?** — à quel point vos positions s'amortissent mutuellement → [Concentration](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **Quelle part de mon portefeuille n'est pas mesurée ici ?** — les liquidités, plus les positions sans prix exploitables → [Qualité des données](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#excluded-weight)
- **Poids** et **contribution au risque** — la part de chaque position dans votre argent, et dans votre risque → [Contribution au risque](../../financial-theory/technical-analysis/risk-metrics/risk-contribution.md)
- **Lesquelles d'entre elles sont le même pari ?** — à quel point chaque paire de positions évolue ensemble → [Corrélation](../../financial-theory/technical-analysis/risk-metrics/correlation.md)

**Comment le lire**

- **Une longue barre rouge** à droite signale une position qui porte plus de votre risque que ne le suggère son poids ; lorsqu'une se distingue, la phrase sous le titre la nomme.
- **Dans la matrice**, les paires bleues évoluent ensemble, donc détenir les deux apporte peu ; les paires rouges évoluent en sens opposé et se compensent.
- **Survolez un carré** pour obtenir sa valeur en mots. Les listes *Les plus similaires* et *Celles qui se compensent* font ressortir les paires qui méritent un coup d'œil.

---

## ⚖️ Suis-je rémunéré pour ce risque ? {: #being-paid }

Le risque ne vaut la peine d'être pris que s'il est rémunéré. Ce bloc confronte le rendement de votre portefeuille et de chaque position à ses variations — dans un tableau et dans un graphique — et, si vous en choisissez un, à un indice de référence.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-paid" alt="Le bloc Suis-je rémunéré pour ce risque ?, comparé à l'indice MSCI World : le tableau ouvert par les lignes Portefeuille et indice de référence, avec Poids, Volatilité, Rendement ann., Sortino, Sharpe, Bêta et Corrélation ; le graphique risque/rendement avec les points des positions et du portefeuille dimensionnés par le poids, le losange de l'indice de référence et la ligne pointillée depuis le taux sans risque ; et les notes sous le graphique" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils présentés**

- **Volatilité** — l'ampleur des variations des rendements sur une année → [Volatilité](../../financial-theory/technical-analysis/risk-metrics/volatility.md)
- **Rendement ann.** — le rendement moyen, ramené à une année → [Annualisation observée](../../financial-theory/technical-analysis/risk-metrics/observed-annualization.md)
- **Sortino** — le rendement obtenu pour chaque unité de variation à la baisse → [Ratio de Sortino](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md)
- **Sharpe** — le rendement obtenu pour chaque unité de variation, à la hausse comme à la baisse → [Ratio de Sharpe](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Bêta** — l'ampleur du mouvement d'une position lorsque l'indice de référence bouge → [Bêta et rendement actif](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md)
- **Corrélation** — à quel point une position évolue avec l'indice de référence → [Corrélation](../../financial-theory/technical-analysis/risk-metrics/correlation.md)
- **Comparé à** et la ligne pointillée — votre indice de référence, et la ligne séparant les risques les mieux rémunérés des moins bien rémunérés → [Sélection de l'indice de référence](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line)

**Comment le lire**

- **Choisissez un indice de référence** dans **Comparé à** — un tracker d'un vaste indice mondial est le plus pertinent. Il s'applique à toutes les pages Risque, et ajoute les colonnes **Bêta** et **Corrélation**.
- **Au-dessus de la ligne pointillée**, un point a été mieux rémunéré pour son risque que l'indice de référence — ou, sans indice de référence, que votre portefeuille.
- **Cliquez** sur le titre d'une colonne pour trier le tableau, ou sur une ligne pour trouver son point dans le graphique.
- **La ligne Portefeuille** rejoue les positions d'aujourd'hui, aux poids d'aujourd'hui, sur la période — le titre indique *sur la composition actuelle* — ce n'est donc pas l'historique de vos transactions. Les rendements proviennent uniquement des prix, sans dividendes ni coupons pour l'instant.

---

## 🔮 Et si… ? {: #what-if }

Quel effet une crise passée, ou un choc que vous imaginez, aurait-il sur le portefeuille que vous détenez aujourd'hui — et que pourrait-il se passer à l'avenir ? Le bloc est fermé au départ : cliquez sur son titre pour l'ouvrir.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-whatif" alt="Le bloc Et si… ? ouvert : le Rejeu historique : avis Partiel, Ajouter : Choc hypothétique et Simulation, et la boîte Rejeu historique après Lancer le rejeu, avec le préréglage Crise financière mondiale et sa période, la boîte de l'actif exclu, la phrase du total, et le tableau avec Poids, Rendement, Contribution, Impact et Effet" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils présentés**

- **Rejeu historique** — une période passée réelle, appliquée à votre portefeuille tel qu'il est aujourd'hui → [Rejeu historique](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)
- **Choc hypothétique** — une baisse ou une hausse que vous supposez pour chaque classe d'actifs, secteur ou région → [Choc hypothétique](../../financial-theory/technical-analysis/risk-metrics/hypothetical-shock.md)
- **Simulation** — un éventail de futurs possibles, construit à partir de votre propre historique → [Modes de simulation](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md)

**Comment le lire**

- **Ajoutez un outil** avec les boutons **Ajouter :** ; son **×** le ferme et supprime son résultat. Les outils que vous laissez ouverts réapparaîtront la prochaine fois, dans ce navigateur.
- **Rejeu historique** : choisissez une crise dans **Préréglage**, ou votre propre **Période**, puis **Lancer le rejeu**. Les positions sans prix pour cette période sont exclues, et un bouton peut proposer une période durant laquelle elles ont toutes des prix.
- **Choc hypothétique** : cliquez sur un scénario, comme *Krach boursier*, pour le lancer ; **Afficher le choc par catégorie d'exposition** vous permet de modifier ses hypothèses.
- **Simulation** : choisissez un mode — *Historique remélangé* est recommandé — et un horizon, puis **Simuler**. Lisez le cône comme un éventail de possibilités, pas comme une prévision.

!!! note "La simulation est encore en bêta"

    Son résultat dépend fortement de la quantité d'historique que contient la période par rapport à l'horizon — voir [Pourquoi la simulation est encore en bêta](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="whatif-simulation" alt="La boîte Et si… ? Simulation : l'avis bêta et l'avertissement du modèle, les cinq modes avec Historique remélangé recommandé, l'horizon, les trajectoires et la graine, et après Simuler les chiffres terminaux, le cône et Ce que cette simulation a supposé" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚩 Avis et données manquantes {: #notices }

Un chiffre de risque ne vaut pas mieux que les prix qui le sous-tendent. Lorsque des données sont manquantes ou obsolètes, l'onglet le signale, ainsi que ce que cela a changé.

**Outils présentés**

- **Qualité des données** — les prix et taux de change manquants ou obsolètes, et les positions qu'ils excluent → [Qualité des données](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Comment le lire**

- **La bannière en haut** liste les prix et taux de change manquants ou obsolètes : corrigez-les avec ses boutons, ou avec **Synchroniser** en haut à droite.
- **L'avis au-dessus des blocs** indique quels résultats sont partiels, et pourquoi.
- **Une bannière à l'intérieur d'un bloc** nomme un chiffre qui n'a pas pu être calculé, avec la raison.
- **Un tiret (—)** signifie qu'un chiffre n'a pas pu être mesuré : il ne signifie jamais zéro.
- **Pour réessayer**, appuyez sur **Actualiser**, ou relancez l'outil Et si… ?

---

## 🔎 Bon à savoir {: #good-to-know }

- **L'onglet du tableau de bord couvre l'ensemble de votre portefeuille** — chaque courtier que vous détenez avec une part supérieure à 0 % — sur la plage de dates et la devise du tableau de bord. Il ignore le filtre de courtier : un sous-titre le précise, et les montants sous les pourcentages sont masqués tant qu'un filtre est actif.
- **Sur la page d'un courtier**, l'onglet affiche les mêmes blocs pour ce courtier uniquement.
- **Changer la période ou la devise** recalcule chaque bloc et efface les résultats de l'outil Et si… ? : relancez-les.
- **Détails du calcul**, repliés au bas de chaque bloc, montrent sur combien de données reposent les chiffres.

---

## 🔗 Voir aussi {: #related }

- 🧪 **[Onglet Corrélation](../assets/correlation.md)** — les mêmes questions, posées à une sélection d'actifs que vous choisissez
- 📚 **[Métriques de risque](../../financial-theory/technical-analysis/risk-metrics/index.md)** — la théorie derrière chaque chiffre ; l'icône de livre de chaque bloc l'ouvre
- 📊 **[Tableau de bord](index.md)** — les autres onglets, la plage de dates, la devise et le filtre de courtier
- 🏦 **[Courtiers](../brokers/index.md)** — la page de chaque courtier, avec son propre onglet Risque
- 🛠️ **[Détails techniques](../../developer/frontend/components/features/risk-lab.md#dashboard-risk-tab)** — pour les développeurs : comment cet onglet fonctionne à l'intérieur
