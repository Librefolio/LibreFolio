# 💵 MWRR (Money-Weighted Rate of Return) / XIRR

*[⬅️ Retour à l'aperçu des indicateurs de performance](index.md)*

## 💡 Qu'est-ce que c'est ?
Le MWRR (également connu sous le nom de Taux de Rendement Interne) mesure *votre performance personnelle*. Il pondère fortement les périodes où vous aviez le plus d'argent investi.

## 🧮 Comment ça fonctionne
Il examine les dates exactes et les montants de tous vos flux de trésorerie (dépôts et retraits) ainsi que la valeur finale du portefeuille, en calculant le taux d'intérêt constant qu'une banque aurait dû vous offrir pour atteindre exactement le même résultat final.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

Où $CF_i$ est chaque flux de trésorerie (dépôts positifs, retraits négatifs, valeur finale du portefeuille positive).

## 🎯 Quand l'utiliser
- Pour juger **votre timing personnel**.
- Pour voir la réalité concrète de la croissance de votre capital.

## 📈 Comment la série cumulative (graphique) est calculée
Pour afficher le MWRR sous forme de graphique historique dans le temps, le calcul est effectué de manière **cumulative** depuis le début pour chaque jour de la série.

Pour chaque point de données tracé au jour $t_N$ :

1. Le calcul considère toute la fenêtre temporelle de $t_0$ à $t_N$.
2. Il établit l'équation de la Valeur Actuelle Nette (VAN) où le flux de trésorerie initial à $t_0$ est la valeur de départ du portefeuille (représentée comme un flux de trésorerie négatif : un « investissement »).
3. Tous les flux de trésorerie intermédiaires entre $t_0$ et $t_N$ sont placés sur la chronologie.
4. Le flux de trésorerie final à $t_N$ représente la liquidation hypothétique du portefeuille, qui est la VNI à $t_N$ (représentée comme un flux de trésorerie positif).

**Cas particulier mathématique important :**
Si un flux de trésorerie externe survient exactement le jour final $t_N$ de la période évaluée, la VNI à $t_N$ incorpore déjà ce flux. Dans l'équation VAN pour ce jour spécifique, le flux de trésorerie net final doit tenir compte à la fois de la VNI finale et du flux réalisé ce même jour.

**Exemple :**
Imaginez que vous commencez à $t_0$ avec un portefeuille de 1 000 \$.
- Le flux de trésorerie à $t_0$ est de -1 000 \$.
- Au jour $t_{31}$, vous déposez 100 \$ supplémentaires.
- La VNI de votre portefeuille passe immédiatement à 1 100 \$ (en supposant aucune croissance du marché).

Si l'algorithme utilise la VNI finale de +1 100 \$ comme flux final sans compenser le dépôt effectué ce jour exact, le calcul suppose qu'un investissement de 1 000 \$ a atteint 1 100 \$ uniquement grâce à la performance du marché (un gain erroné de 10 %). En incluant correctement le dépôt de -100 \$ à $t_{31}$ aux côtés de la VNI terminale, le flux net final devient +1 000 \$ (1 100 \$ - 100 \$), prouvant correctement que le rendement réel était de 0 %.

Cette logique garantit également qu'au tout premier jour ($t_0$), la VNI de départ et l'investissement initial s'annulent parfaitement, ancrant le début du graphique à exactement 0 %.
