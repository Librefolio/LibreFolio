# 🧪 Onglet Corrélation

L'onglet **Corrélation** de la [page Actifs](index.md) pose les mêmes questions à une **sélection d'actifs** que vous composez — des actifs que vous détenez, des actifs simplement surveillés, ou les positions d'un courtier. Ouvrez-le depuis **Actifs** dans la barre latérale, puis l'onglet **Corrélation** dans la barre d'outils. Une sélection n'a pas de pondérations, donc l'onglet affiche des pourcentages et des ratios, jamais d'argent : pour votre propre argent, consultez l'[onglet Risque](../dashboard/risk.md) du Tableau de bord.

Chaque bloc ci-dessous suit un même schéma : ce à quoi il répond, une capture d'écran, ses outils et comment les lire.

- 🧺 **[Construire la sélection](#building-the-selection)** — quels actifs sont comparés
- 🕸️ **[Corrélation](#correlation)** — lesquels évoluent ensemble
- 📉 **[Combien chacun d'eux a-t-il fait mal ?](#how-much-did-each-hurt)** — les pertes de chacun
- ⚖️ **[Combien chacun d'eux a-t-il payé pour son risque ?](#what-did-each-pay)** — risque contre rendement
- ⏮️ **[Et si… ?](#what-if)** — un épisode passé, rejoué
- 🚩 **[Avertissements et données manquantes](#each-section-speaks-for-itself)** — ce qui manquait aux données

---

## 🧺 Construire la sélection {: #building-the-selection }

La carte en haut répond à *quels actifs sont comparés ?* Chaque puce correspond à un actif sélectionné, et l'onglet mémorise votre sélection dans ce navigateur.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-asset-picker" alt="Le panneau + ouvert par-dessus la carte de sélection : recherche, filtres Type et Devise, deux actifs cochés avec Ajouter 2, et, en lecture seule, les actifs qui ne peuvent pas être analysés sur la période, chacun avec sa raison" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils affichés**

- **Vérification d'éligibilité** — si un actif dispose d'assez de prix sur la période pour être analysé → [Qualité des données](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Comment le lire**

- **Ajoutez des actifs avec le +**, retirez-en un avec son **×**, ou modifiez-en plusieurs d'un coup avec **Tout sélectionner**, **Tout désélectionner**, **Inverser** et **Mes actifs** — jusqu'à **100 actifs**.
- **Le compteur** — *3 dans l'analyse, sur 42 analysables* — compte les actifs sélectionnés en cours d'analyse, parmi tous ceux qui pourraient l'être sur la période définie dans la barre d'outils.
- **Une puce en pointillés** ne peut pas être analysée sur cette période : elle reste sélectionnée, mais exclue des résultats. **Une puce ambre** est analysée, avec un avertissement. Survolez ou touchez une puce pour lire pourquoi.
- **Si la période laisse certains actifs sans prix**, un bandeau ambre propose **Utiliser la période durant laquelle tous ont des prix**, ce qui déplace les dates de la page pour tous les inclure.

---

## 🕸️ Corrélation {: #correlation }

Cette section répond à *lesquels évoluent ensemble ?* — pour repérer les actifs qui constituent en réalité le même pari, et ceux qui amortissent les autres.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-correlation" alt="La section Corrélation avec cinq actifs : la matrice triangulaire avec sa légende, les boutons d'ordre et les badges secteur et région ; Les paires les plus semblables RE Loan Roma avec RE Loan Milano à 0,94, quasi identiques, et la liste « Celles qui se compensent » est vide" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils affichés**

- **Coefficient de corrélation (ρ)** — à quel point deux actifs ont évolué ensemble, de −1 (toujours opposés) à +1 (toujours ensemble) → [Corrélation](../../financial-theory/technical-analysis/risk-metrics/correlation.md#interpretation)
- **Trier par similarité** — l'ordre par défaut : les actifs étroitement liés se retrouvent côte à côte, de sorte que les groupes redondants apparaissent sous forme de blocs → [Corrélation](../../financial-theory/technical-analysis/risk-metrics/correlation.md#why-the-matrix-answers-am-i-diversified)

**Comment le lire**

- **Un carré par paire** : bleu lorsque les deux actifs évoluent ensemble, rouge lorsqu'ils évoluent en sens opposés, pâle lorsqu'ils évoluent indépendamment. Survolez-le ou touchez-le pour obtenir la valeur en mots.
- **Partez des deux listes** : **Les plus semblables** nomme les paires qui constituent presque la même exposition, **Celles qui se compensent** les paires qui s'amortissent mutuellement. Une liste vide est un résultat. Cliquez sur une paire pour la retrouver dans la matrice.
- **Un tiret n'est pas un zéro** : la paire n'a pas pu être mesurée — historique trop court, ou prix qui n'a jamais bougé.
- **Les boutons d'ordre** réorganisent la matrice ; ils ne modifient jamais une valeur.

---

## 📉 Combien chacun d'eux a-t-il fait mal ? {: #how-much-did-each-hurt }

Cette section place chaque actif sur la même échelle de préjudice : ses pires pertes sur la période, et à quelle distance il se situe encore sous son sommet.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-hurt-table" alt="Le tableau Combien chacun d'eux a-t-il fait mal ? : une ligne par actif avec Mauvais jour, Mauvais mois, Pire chute et combien de temps elle a duré, Sous le sommet maintenant et Remontée vers le sommet" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils affichés**

- **Mauvais jour** — la perte moyenne sur les 5 % de jours les plus mauvais (CVaR à 95 %) → [VaR conditionnelle](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Mauvais mois** — la même chose sur de véritables périodes d'un mois → [VaR conditionnelle](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Pire chute** — la baisse la plus profonde depuis un sommet ; *durée N j* compte les jours jusqu'à ce que l'actif y revienne, ou jusqu'à la fin de la période → [Perte maximale](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Sous le sommet maintenant** — à quelle distance il se situe sous son plus haut niveau de la période → [Repli actuel](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **Remontée vers le sommet** — le gain nécessaire pour y revenir : 20 % en dessous nécessite +25 % → [Ce qu'il faut pour revenir](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md#what-it-takes-to-get-back)

**Comment le lire**

- **Chaque colonne a son propre horizon**, d'un jour à toute la période : comparez les actifs dans une colonne, n'additionnez jamais les colonnes.
- **Ce n'est pas un classement** : le tableau s'ouvre dans l'ordre de votre sélection. Cliquez sur un titre de colonne pour le trier, ou survolez-le pour savoir ce qu'il mesure.
- **Sur une période courte**, **Mauvais jour** et **Mauvais mois** peuvent rester vides tandis que les colonnes de repli sont remplies : ils nécessitent plus d'historique.

---

## ⚖️ Combien chacun d'eux a-t-il payé pour son risque ? {: #what-did-each-pay }

Cette section confronte le risque à la récompense — l'ampleur des variations de chaque actif et son rendement moyen annuel — dans un tableau et un graphique. Avec un indice de référence choisi sous *Comparé à*, elle montre aussi comment chaque actif a évolué avec lui.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-risk-return" alt="Combien chacun d'eux a-t-il payé pour son risque ? avec le S&P 500 comme indice de référence : sa ligne teintée ouvrant le tableau, la ligne de période et le graphique avec les cercles des actifs, le losange de l'indice de référence et la ligne en pointillés" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils affichés**

- **Volatilité** — l'ampleur des variations des rendements, sur une base annuelle → [Volatilité](../../financial-theory/technical-analysis/risk-metrics/volatility.md)
- **Rend. ann.** — le *rendement annuel moyen* : le rendement moyen de la période, ramené à une année → [Annualisation observée](../../financial-theory/technical-analysis/risk-metrics/observed-annualization.md)
- **Sortino** — le rendement obtenu par unité de variation à la baisse → [Ratio de Sortino](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md)
- **Sharpe** — le rendement obtenu par unité de volatilité → [Ratio de Sharpe](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Bêta** — avec un indice de référence : l'ampleur du mouvement de l'actif lorsque l'indice de référence bougeait → [Bêta et rendement actif](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md#interpretation)
- **Corrélation** — avec un indice de référence : à quel point les deux ont évolué ensemble → [Sélection de l'indice de référence](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#interpretation)
- **Droite risque/rendement** — avec un indice de référence : la ligne en pointillés tracée à travers lui sur le graphique → [La droite risque/rendement](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line)

**Comment le lire**

- **Ce n'est pas un classement** : le tableau s'ouvre avec la ligne de l'indice de référence, puis votre sélection dans son propre ordre. Cliquez sur un titre de colonne pour le trier.
- **La ligne sous le tableau** indique la période exacte derrière les chiffres, et précise lorsqu'elle est plus courte que la vôtre — généralement à cause d'un actif ayant un historique plus court.
- **Sur le graphique**, plus à droite signifie plus de variation et plus haut signifie plus de rendement moyen ; l'indice de référence est le losange. Un cercle au-dessus de la ligne en pointillés a été mieux rémunéré pour son risque que l'indice de référence. Cliquez sur une ligne ou un cercle pour mettre en évidence cet actif dans les deux.

!!! warning "Le rendement annuel moyen n'est pas le rendement que vous avez vécu"

    Sur un actif très volatil, le rendement réellement vécu est plus faible : ne lisez pas la hauteur d'un point comme ce que l'actif a rapporté. Il provient par ailleurs des seuls prix — les coupons et dividendes ne sont pas encore inclus.

### 🎯 Choisir l'indice de référence {: #choosing-the-benchmark }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-benchmark-picker" alt="Le sélecteur Comparé à ouvert : recherche, filtres Type et Devise, les actifs utilisables, puis, en lecture seule, ceux qui ne sont pas utilisables sur cette période, chacun avec sa raison" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Un seul indice de référence pour toutes les pages de risque** : votre choix sous *Comparé à* s'applique aussi aux pages de risque du Tableau de bord, du courtier et des actifs, afin qu'elles restent comparables.
- **Sa ligne ouvre le tableau**, avec un tiret sous **Bêta** et **Corrélation** : l'indice de référence n'est pas comparé à lui-même. Il peut aussi faire partie de vos actifs sélectionnés.
- **Les actifs qui ne peuvent pas être mesurés sur la période** sont listés à part dans le sélecteur, en lecture seule. Un indice de référence parmi eux reste choisi mais n'est pas utilisé tant que vous ne choisissez pas une période qui lui convient.

---

## ⏮️ Et si… ? {: #what-if }

Cette section répond à *comment chacun s'en est-il sorti lors d'un épisode passé réel ?* — une crise intégrée ou une période que vous choisissez, rejouée avec des rendements réels. Cliquez sur son titre pour l'ouvrir. Seul le rejeu historique est proposé : un choc hypothétique ou une simulation nécessiterait des pondérations.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-replay" alt="Et si… ? après Exécuter le rejeu : la boîte des actifs exclus, groupés par raison, avec le bouton qui rejoue la période plus courte, au-dessus du tableau avec Rendement et Effet" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils affichés**

- **Rejeu historique** — le rendement réel de chaque actif sur une période passée → [Rejeu historique](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)

**Comment le lire**

- **Choisissez un Préréglage**, tel que la *Crise financière mondiale*, ou définissez la **Période**, puis appuyez sur **Exécuter le rejeu**. Modifier la sélection ou les dates de la page efface le résultat.
- **Le tableau** affiche le **Rendement** de chaque actif, du pire au meilleur, avec une barre : rouge pour une perte, vert pour un gain. Il n'y a pas de total : une sélection n'a pas de pondérations à additionner.
- **Les actifs sans prix aux extrémités de la période** sont exclus et listés au-dessus du tableau, avec la raison. Lorsque c'est possible, un bouton rejoue la période plus courte durant laquelle ils ont tous des prix.

---

## 🚩 Avertissements et données manquantes {: #each-section-speaks-for-itself }

Lorsque quelque chose ne va pas avec les données, l'onglet le signale une fois, juste sous la carte de sélection, et nomme les résultats concernés.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-notice" alt="Haut de l'onglet Corrélation : la bannière repliée de qualité des données, l'avertissement Certains résultats sont partiels avec ses badges Mesures affectées, et la bannière ambre de la section Corrélation Indisponible pour les données sélectionnées" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Outils affichés**

- **Qualité des données** — prix et taux de change manquants ou obsolètes, et les résultats qu'ils rendent partiels → [Qualité des données](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Comment le lire**

- **La bannière de qualité des données** liste ce qu'il faut corriger, chaque problème avec son action, comme **Synchroniser les prix** ou **Synchroniser les taux**. Cliquez dessus pour ouvrir la liste.
- **L'avertissement** en dessous nomme les résultats **partiels** et leur cause. Un résultat partiel affiche tout de même ses chiffres : lisez-les en gardant cette cause à l'esprit.
- **La bannière ambre d'une section** signifie qu'un résultat n'a pas pu être obtenu du tout, souvent parce que la période est trop courte : choisissez-en une plus longue, ou synchronisez les prix.
- **Et si… ?** signale ses propres problèmes à l'intérieur de sa section.

---

## 🔎 Bon à savoir {: #reading-the-numbers }

- **Une période pour tous les actifs.** Chaque chiffre couvre les mêmes jours pour chaque actif sélectionné, de sorte que les lignes peuvent être comparées. Un actif ayant un historique plus court raccourcit cette période pour tous, et leurs chiffres changent : c'est attendu → [Qualité des données](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs)
- **Une seule devise.** Les rendements sont mesurés dans votre **Devise par défaut**, définie dans les [Préférences](../settings/preferences.md) (celle par défaut de l'instance si vous n'en avez jamais choisi), variations des taux de change incluses.
- **Un tiret n'est pas un zéro.** Le chiffre n'a pas pu être mesuré pour cet actif sur cette période ; survolez-le ou touchez-le pour lire pourquoi.
- **Une autre page, un autre chiffre.** Une autre page ou une autre sélection mesure sur des jours différents : ne comparez les chiffres que lorsqu'ils couvrent la même période.

---

## 🔗 Voir aussi {: #related }

- 📋 **[Liste des actifs](index.md)** — l'onglet Actifs, sa barre d'outils et sa plage de dates
- 🛡️ **[Onglet Risque du Tableau de bord](../dashboard/risk.md)** — les mêmes questions, pour votre propre portefeuille
- 📊 **[Mesures de risque](../../financial-theory/technical-analysis/risk-metrics/index.md)** — la théorie derrière chaque section de cet onglet
- 🛠️ **[Détails techniques](../../developer/frontend/components/features/risk-lab.md)** — pour les développeurs : comment cet onglet fonctionne à l'intérieur
