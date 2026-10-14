# 🔗 Corrélation

La corrélation mesure **comment deux positions évoluent l'une par rapport à l'autre**. C'est la métrique qui détermine si un portefeuille est véritablement diversifié ou simplement long : posséder beaucoup de choses n'est pas de la diversification si ces choses montent et descendent ensemble.

---

## 🔢 Formule {: #formula }

Pour deux séries de rendements $r_i$ et $r_j$ observées sur les mêmes $N$ périodes, le coefficient de corrélation de Pearson est leur covariance normalisée par leurs écarts-types :

$$\rho_{i,j} = \frac{\mathrm{Cov}(r_i, r_j)}{\sigma_i \, \sigma_j}$$

avec les estimateurs d'échantillon non biaisés ($N-1$) :

$$\mathrm{Cov}(r_i, r_j) = \frac{1}{N-1} \sum_{t=1}^{N} (r_{i,t} - \bar{r_i})(r_{j,t} - \bar{r_j}) \qquad \sigma_i = \sqrt{\frac{1}{N-1} \sum_{t=1}^{N} (r_{i,t} - \bar{r_i})^2}$$

C'est la division par les deux écarts-types qui rend le résultat comparable : la covariance s'exprime en unités de rendement au carré et croît avec la volatilité de ses entrées, tandis que $\rho$ est un nombre pur borné par $-1$ et $+1$, quels que soient les actifs.

!!! info "La corrélation est calculée après conversion de devise"

    Les rendements entrent dans le calcul déjà convertis dans la devise cible demandée pour l'analyse — la même règle pour un portefeuille et pour un ensemble d'actifs. Le chiffre décrit donc ce qu'a vécu un détenteur mesurant dans cette devise, mouvements de change inclus — et non ce que l'instrument a fait dans sa devise d'origine. Deux actifs cotés dans des devises différentes sont comparés sur la même base convertie.

---

## 💡 Interprétation {: #interpretation }

Le coefficient possède trois points de référence, et seulement trois qui ne nécessitent aucune convention :

| Valeur | Signification |
|---|---|
| $\rho = +1$ | Les deux séries évoluent en parfaite synchronie : l'une est une fonction linéaire positive exacte de l'autre |
| $\rho = 0$ | Aucune relation **linéaire** entre les deux séries sur la fenêtre observée |
| $\rho = -1$ | Opposition parfaite : une série est une fonction linéaire négative exacte de l'autre |

Tout ce qui se situe entre ces pôles est une question de degré. Pour rendre la matrice lisible, LibreFolio lit chaque coefficient dans l'une de quatre bandes, partout où elle dessine une matrice de corrélation — dans l'onglet Risque du Tableau de bord et de la page d'un courtier, et dans l'[onglet Corrélation](../../../user/assets/correlation.md#correlation) de la page Actifs — dans l'infobulle de chaque cellule et dans les deux listes de paires à côté de la matrice :

| Bande | Plage | Lecture affichée |
|---|---|---|
| Élevée | $\rho > 0.7$ | elles évoluent ensemble |
| Modérée | $0.3 \le \rho \le 0.7$ | elles évoluent en partie ensemble |
| Faible | $-0.3 < \rho < 0.3$ | elles évoluent indépendamment |
| Inverse | $\rho \le -0.3$ | elles évoluent en sens opposés |

Les seuils sont symétriques autour de zéro, de sorte qu'un coefficient faible se lit comme une indépendance quel que soit son signe : $\rho = -0.01$ ne prouve nullement que deux actifs se compensent. Les deux listes ne conservent que les cas manifestes — *les plus similaires* pour la bande élevée, *ceux qui s'opposent* pour la bande inverse — et une paire avec $\rho \ge 0.9$ est en outre signalée comme *quasi identique* : deux instruments qui constituent, en pratique, une seule exposition. Une cellule sans coefficient n'appartient à aucune bande : une corrélation inconnue n'est jamais lue comme faible.

Les bandes sont des aides à la lecture, non des verdicts. Il n'existe aucun niveau à partir duquel une paire devient « trop corrélée », car la réponse dépend de la part du portefeuille que représentent ces deux positions — une question à laquelle la matrice de corrélation seule ne peut répondre.

### 🧩 Pourquoi la matrice répond-elle à « Suis-je diversifié ? » {: #why-the-matrix-answers-am-i-diversified }

Le nombre de positions est un décompte ; la diversification est un comportement. Dix positions qui répondent toutes au même facteur se comportent, lors d'un mauvais mois, comme une seule position détenue dix fois. La matrice de corrélation est ce qui rend cela visible : c'est la carte des relations, non un verdict à leur sujet.

Lisez-la pour sa structure plutôt que pour ses valeurs individuelles — les groupes de positions qui évoluent ensemble, les paires qui ne le font vraiment pas, et si un prétendu diversifiant se comporte réellement comme tel. La diagonale ne porte aucune information : partout où elle contient une valeur, cette valeur est $+1$ par construction — mais la cellule diagonale d'une série plate est `undefined`, et une matrice en dessous du seuil d'observation ne contient aucune valeur du tout (voir [Comment chaque cellule est calculée](#how-each-cell-is-computed)).

L'ordre par défaut de la matrice sert cette lecture. Il range les actifs par classification agglomérative avec liaison moyenne sur la distance

$$d_{ij} = 1 - |\rho_{ij}|$$

de sorte que les paires fortement liées — dans le même sens ou en sens opposés — se retrouvent côte à côte, et que les groupes apparaissent sous forme de blocs. Liaison moyenne plutôt que liaison simple, car la liaison simple enchaîne : deux groupes sans lien réunis par un unique actif intermédiaire seraient dessinés comme un seul bloc. Une paire sans coefficient est placée à la distance maximale, $d_{ij} = 1$, afin qu'une valeur manquante ne puisse jamais rapprocher deux actifs dans le même bloc ; les égalités sont départagées par la position, de sorte que la même matrice produit toujours le même ordre.

La corrélation répond à *comment* les positions évoluent ensemble. Elle ne dit rien sur **quelle part** du portefeuille chacune représente, raison pour laquelle elle se lit aux côtés de la [Concentration](concentration.md) et de la [Contribution au risque](risk-contribution.md) : une corrélation forte entre deux positions marginales importe bien moins qu'une corrélation modérée entre les deux plus importantes.

---

## 🧮 Comment chaque cellule est calculée {: #how-each-cell-is-computed }

Chaque cellule de la matrice revient dans l'un de trois états, et chaque cellule porte le nombre d'observations sur lequel elle a été jugée.

| État de la cellule | Quand | Ce qui est publié |
|---|---|---|
| `ok` | Le calendrier partagé contient suffisamment d'observations et aucune des deux séries n'est plate | Le coefficient, borné à $[-1, +1]$ |
| `insufficient` | Le calendrier partagé contient moins d'observations que le minimum requis — chaque cellule de la matrice est alors dans cet état | Aucune valeur — le nombre d'observations est publié sans coefficient |
| `undefined` | Au moins une des deux séries a une variance (numériquement) nulle | Aucune valeur — une série qui ne bouge jamais n'a aucune direction à partager |

Le minimum est appliqué à la **matrice dans son ensemble**, et non paire par paire. Comme chaque série se trouve sur le même calendrier partagé (voir ci-dessous), chaque paire est calculée exactement sur les mêmes dates, de sorte qu'il existe un unique nombre d'observations pour toute la matrice : soit il franchit le seuil, soit il ne le franchit pas, et lorsqu'il ne le franchit pas, chaque cellule est signalée comme insuffisante. Un historique court ne laisse donc jamais certaines paires calculées et d'autres vides — il raccourcit le calendrier, et avec lui l'échantillon, pour toutes les paires à la fois. Le seuil par défaut est de 20 observations, et il s'agit d'un paramètre ajustable de l'analyse plutôt que d'une règle codée en dur.

Chaque état autre que `ok` qui se produit au moins une fois déclenche également un avertissement sur le résultat — `insufficient_pair_history` et `flat_series` respectivement — afin qu'une matrice totalement ou partiellement inutilisable le signale explicitement au lieu de laisser des cellules vides à interpréter. Malgré son nom, `insufficient_pair_history` concerne toujours la matrice entière. Une série plate, en revanche, ne vide que sa propre ligne et sa propre colonne et laisse toutes les autres corrélations intactes.

!!! info "Toutes les séries partagent un même calendrier"

    Avant tout calcul de corrélation, chaque série de la portée est alignée sur un unique calendrier partagé : une date n'entre dans l'analyse que si **chaque** position peut être valorisée ce jour-là dans la devise cible. Les paires ne sont donc jamais calculées sur des dates discordantes ou interpolées — mais le coût est collectif, car une date qui échoue pour une position est écartée pour toutes. Une position avec un historique court — qui ne peut pas être valorisée avant le début demandé — raccourcit la fenêtre pour toute la matrice : le calendrier commence à la première date à laquelle chaque position peut être valorisée, et le rapport de qualité des données nomme les positions concernées plutôt que de lister les dates ignorées. Un trou à l'intérieur d'un historique ne supprime aucune date : un cours manquant, comme un taux de change manquant, est remplacé par le dernier connu, reporté sans limite d'ancienneté, et le rapport ne compte comme points reportés que ceux maintenus au-delà du [seuil d'obsolescence](data-quality.md#staleness-threshold). Une fois le calendrier démarré, une date n'est écartée que si une position n'a toujours aucune valeur dans la devise cible ce jour-là, et ces dates sont listées dans le rapport comme incomplètes. Voir [Qualité des données](data-quality.md).

    Lorsque la matrice est construite sur un ensemble d'actifs choisis directement, sans portefeuille derrière eux, un actif avec **aucune série de cours du tout** n'est pas un historique court mais un historique absent : il est exclu de la portée avant la construction du calendrier. Le résultat le liste comme exclu — avec la raison `no_price_source` lorsqu'aucune source de cours ne lui est assignée et qu'aucun cours n'a jamais été enregistré pour lui, `missing_price` sinon — déclenche un avertissement `assets_excluded` et est marqué `partial`. L'actif n'apparaît pas comme une ligne plate, et il ne raccourcit pas la fenêtre pour les autres actifs. Voir [Exclusions](data-quality.md#exclusions).

---

## ⚠️ Limitations {: #limitations }

!!! warning "La corrélation ne voit que la partie linéaire d'une relation"

    $\rho$ mesure à quel point la relation entre deux séries est décrite par une droite. Une dépendance réelle mais courbe — un actif ne réagissant qu'aux grands mouvements d'un autre, par exemple — peut produire un coefficient proche de zéro. Une corrélation faible signifie « aucun lien linéaire n'a été détecté dans cette fenêtre », jamais « ces positions sont sans rapport ».

!!! warning "Un seul nombre pour toute la fenêtre"

    Une corrélation est une moyenne sur la période demandée. Une paire qui est restée sans lien pendant la majeure partie de la fenêtre et a évolué ensemble au pire moment produit une moyenne rassurante. C'est l'asymétrie bien documentée de la diversification : les corrélations observées dans des conditions calmes ne sont pas une promesse quant au comportement en période de stress, où des positions qui semblaient indépendantes cessent fréquemment de l'être. La matrice décrit la fenêtre sur laquelle elle a été mesurée, et rien d'autre.

!!! warning "Corrélation n'est pas causalité, ni ampleur"

    Deux actifs peuvent être fortement corrélés par un facteur commun sans aucun lien entre eux. Et la corrélation ne dit rien sur la taille : une paire corrélée à $+1$ où un actif bouge violemment et l'autre à peine partage une direction, pas un risque. L'ampleur appartient à la [Volatilité](volatility.md), le poids appartient à la [Contribution au risque](risk-contribution.md).

---

## 🔗 Voir aussi {: #related }

- 🧩 **[Concentration](concentration.md)** — quelle part du portefeuille chaque position représente réellement
- ⚖️ **[Contribution au risque](risk-contribution.md)** — quelles positions portent le risque du portefeuille une fois corrélation et poids combinés
- 📊 **[Volatilité](volatility.md)** — l'ampleur que la corrélation normalise délibérément
- 🧪 **[Qualité des données](data-quality.md)** — le calendrier partagé, et ce qu'une date manquante coûte à toute la matrice
