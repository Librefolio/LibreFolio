# ⚙️ Paramètres du graphique

La fenêtre **Paramètres du graphique** modifie l’apparence des graphiques et les superpositions qu’ils dessinent. Elle sert à la fois à la [liste FX](index.md) et à la [liste des actifs](../assets/index.md), et chaque liste conserve ses propres paramètres : modifier les graphiques FX ne touche jamais aux graphiques d’actifs.

---

## 🔓 Ouvrir les paramètres du graphique

- 🌐 **Pour tous les graphiques** — cliquez sur **Paramètres** (⚙️) dans la barre d’outils de la liste. La fenêtre s’intitule **Paramètres du graphique**. Son application remplace les paramètres personnalisés de chaque graphique de la liste, pages de détail incluses, et la fenêtre vous en avertit.
- 🎯 **Pour un graphique** — cliquez sur ⚙️ sur une carte. La fenêtre s’intitule **Paramètres du graphique (local)**, et ses paramètres ne s’appliquent qu’à ce graphique.

!!! note "Les pages de détail utilisent des panneaux intégrés"

    Sur une [page de détail de paire](detail/index.md) (et sur une page de détail d’actif), ⚙️ sur le graphique ouvre les mêmes paramètres d’apparence dans un panneau, et le panneau **Signaux** au-dessus du graphique contient les superpositions. Il s’agit des mêmes paramètres que les paramètres locaux de la carte.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Modale des paramètres du graphique" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Aperçu avant d’appliquer

La fenêtre affiche un graphique d’aperçu avec un sélecteur de vue. Il s’agit de la vue enregistrée du graphique, et **Appliquer** l’enregistre ; les options du sélecteur sont **Abs**, **%** ou **Rendement glissant**. C’est le même graphique que sur les pages de détail de la [paire](detail/index.md) et de l’[actif](../assets/detail/chart.md), mais plus haut que le graphique d’une carte : une ligne (pas de chandeliers), sans la barre d’outils, les marqueurs d’événements ni l’outil de mesure, et vous pouvez zoomer à la molette comme sur la page de détail. Il se dessine avec l’apparence et les plages d’axes que vous modifiez, et un signal de comparaison affiche l’icône et le type de son actif dans l’infobulle. Vos graphiques ne changent qu’après un clic sur **Appliquer** ; **Annuler** demande confirmation avant d’abandonner vos modifications.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Modale des paramètres du graphique avec l’aperçu en direct">
</div>

- 🌐 **Pour tous les graphiques**, l’aperçu dessine une courbe de démonstration. Le serveur calcule les indicateurs sur celle-ci, afin qu’ils apparaissent exactement comme sur vos graphiques réels.
- 🎯 **Pour un graphique**, l’aperçu utilise les données réelles de ce graphique. Les indicateurs affichent les derniers paramètres appliqués tant que vous n’avez pas cliqué sur **Appliquer**, et un bandeau vous le rappelle.

Un signal apparaît de la même manière dans l’aperçu que sur la carte ; ainsi, ce que vous voyez ici est ce que la carte dessine après **Appliquer**.

### 🔁 Vue Rendement glissant {: #rolling-return-view }

En mode **Rendement glissant**, l’aperçu dessine le rendement glissant du taux ou de l’actif, avec les rendements glissants de ses comparaisons. Pour un graphique, il utilise les données réelles de la carte et, sur un graphique FX, les paires FX qui y sont comparées ; pour tous les graphiques, il dessine une courbe de démonstration. Deux contrôles supplémentaires permettent de choisir la fenêtre : **1W**, **1M**, **3M**, **1Y** ou une durée personnalisée. Tant que vous n’en choisissez aucun, la fenêtre est automatique : le préréglage le plus grand qui s’inscrit dans la période affichée dans la liste. La liste des signaux ne montre que les comparaisons que cette vue dessine, à savoir une autre paire FX sur un graphique FX, et un autre actif sur un graphique d’actif ; les indicateurs techniques et les indices de référence restent enregistrés mais sont masqués jusqu’à ce que vous remettiez l’aperçu sur **Abs** ou **%**.

---

## 🎨 Apparence

| Paramètre | Effet |
|---------|--------------|
| **Couleurs de la ligne de base** | Vert au-dessus, rouge en dessous du début de la période, avec une ligne de base en pointillés. S’applique aux cartes des listes, aux pages de détail et à l’aperçu |
| **Remplissage de zone** | Dégradé sous la ligne |
| **Lignes de grille** | Grille horizontale en pointillés |
| **Dégradé des données obsolètes** | Estompe les jours sans nouvelle valeur, qui répètent une valeur antérieure |

### 📏 Plages d’axes

**Échelle de l’axe Y** comporte une ligne pour chaque axe du graphique : l’axe principal (le taux, ou le pourcentage en vue %) et une ligne pour chaque échelle d’indicateur, comme l’**axe RSI**. Les indicateurs qui partagent une échelle partagent une ligne.

- **Auto** adapte l’échelle aux données de cet axe.
- **Inclure 0** adapte l’échelle aux données et affiche aussi zéro.
- **Personnalisé** utilise les valeurs **Min** et **Max** que vous saisissez.

Les vues **Abs** et **%** conservent des plages distinctes : basculez l’aperçu sur **%** pour définir celle du pourcentage.

---

## 📈 Signaux de superposition

Ajoutez des superpositions depuis trois menus déroulants, comme dans le [panneau Signaux](detail/signals.md) de la page de détail :

- 🧮 **Indicateurs techniques** — 10 indicateurs s’appliquent aux taux FX (les graphiques d’actifs en proposent davantage), regroupés par famille avec une zone de recherche. Les calculs sont expliqués dans [Indicateurs techniques — Théorie financière](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Comparaison de données** — une autre paire FX ou un actif sur le même graphique. Sur une carte FX, la ligne d’un actif correspond à son prix dans la devise de l’actif, sans conversion, exactement comme la dessine la [page de détail de la paire](detail/index.md) : lisez-la en vue **%**, où elle part de sa propre première valeur comme le taux. En **Abs**, elle se trouve sur l’axe du taux. La liste charge les prix quotidiens des actifs comparés une seule fois pour toutes les cartes, et ne demande rien quand aucune carte ne compare d’actif. Dans la fenêtre ouverte pour **tous les graphiques**, une comparaison avec un actif n’est pas dessinée, car la courbe de démonstration n’a pas d’actif réel avec lequel la comparer (comme dans la [liste des actifs](../assets/index.md)). Un actif se choisit dans le même panneau que celui de la comparaison de risque : une zone de recherche, des filtres **Type** et **Devise**, chaque ligne affichant l’icône, le nom, le type et la devise de l’actif, et les indices de référence listés en premier ; un clic suffit pour choisir et fermer. L’actif propre au graphique est grisé, et un actif déjà utilisé par une autre comparaison porte une marque d’avertissement mais peut toujours être choisi.
- 📐 **Benchmarks synthétiques** — courbes de référence construites uniquement à partir de paramètres, et non de données de marché : [Linéaire](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Composé](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) et [Onde sinusoïdale](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

Chaque signal devient une carte avec ses paramètres, un lien 📖 vers sa page de théorie et, une fois calculé, une icône de diagnostic.

---

## 💾 Où les paramètres sont enregistrés

- Les paramètres des graphiques sont enregistrés dans **ce navigateur**, pour votre utilisateur, séparément pour les listes FX et d’actifs. Les paramètres propres à un graphique se superposent à ceux de sa liste.
- Ils ne sont pas stockés sur le serveur : un autre navigateur ou appareil part des valeurs par défaut, et l’effacement des données de navigation de ce site les réinitialise.
- La période sélectionnée n’est pas un paramètre de graphique : les pages d’un même onglet de navigateur la partagent.
