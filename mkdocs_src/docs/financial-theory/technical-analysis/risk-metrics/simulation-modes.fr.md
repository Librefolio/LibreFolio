# 🎲 Modes de simulation

La simulation projette un portefeuille vers l'avant en générant un grand nombre de futurs possibles et en lisant la distribution de leur point d'arrivée. C'est le seul endroit de cette section où **rien dans le résultat ne s'est produit** : chaque trajectoire est fabriquée, et la façon dont elle est fabriquée décide de ce que les résultats peuvent contenir et de ce qu'ils ne peuvent pas.

Il y a cinq façons de les fabriquer. Le résultat nomme celle des cinq qu'il a utilisée, avec ses paramètres, dans un court bloc — *Ce que cette simulation a supposé* — mais pas ce que ces paramètres impliquent. Cette page le dit.

---

## 🧭 Les cinq modes {: #the-five-modes }

Sur l'onglet **Risque** du Tableau de bord et de la page d'un courtier, la simulation est le troisième outil de **Et si… ?**, après le rejeu historique et le choc hypothétique. Elle propose cinq modes, chacun avec son hypothèse écrite sous son nom :

| Mode | Comment les trajectoires sont fabriquées | Hypothèse ajoutée à l'historique |
|---|---|---|
| **Historique remélangé** — *Recommandé*, le mode par défaut | [Bootstrap par blocs conjoints](#block-bootstrap) | Aucune : vos propres rendements, réordonnés en blocs |
| **Marché calme** | Bootstrap par blocs conjoints avec un [régime](#prescribed-regimes) | Amplitude réduite de 30 % sur tout l'horizon |
| **Crise prolongée** | Bootstrap par blocs conjoints avec un régime | Amplitudes ×2,5 et un niveau baissant de 20 % par an, pendant 14 mois |
| **Choc et reprise** | Bootstrap par blocs conjoints avec un régime | Une baisse de 35 % sur les deux premiers mois, puis l'historique tel quel |
| **Courbe normale (MBG)** — *Avancé* | [Mouvement brownien géométrique](#the-process) | Rendements gaussiens avec une dérive, une volatilité et une corrélation constantes |

Les quatre premiers tirent des rendements réels de la fenêtre analysée et ne diffèrent que par le régime qu'ils déclarent par-dessus ; le dernier tire d'un modèle ajusté à cette fenêtre. Un régime ne peut pas être combiné avec la courbe normale, et la liste ne propose pas une telle paire.

À côté du mode, l'étape demande un **Horizon (jours)** — 365 par défaut, au plus 3 650 — et un nombre de **Trajectoires de simulation** — 8 192 par défaut, de 256 à 100 000 — et, pour la courbe normale uniquement, une **Stratégie d'échantillonnage**. Une **Graine aléatoire** fixe les tirages — le quasi-Monte Carlo n'en a pas besoin — de sorte que les mêmes entrées donnent toujours le même résultat. **Simuler** l'exécute. La réponse donne le **Rendement moyen terminal**, la **Probabilité de perte** — la part des trajectoires qui se terminent en dessous de leur point de départ — et l'intervalle du 5e au 95e centile le dernier jour, au-dessus d'un cône qui dessine les 5e, 50e et 95e centiles jour par jour.

L'onglet **Risque & Scénarios** de la page de détail d'un actif exécute toujours la courbe normale seule, avec un échantillonnage Monte Carlo ou quasi-Monte Carlo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="whatif-simulation" alt="La boîte Et si… ? Simulation du Tableau de bord : l'avis de bêta et l'avertissement sur le modèle, les cinq modes avec Historique remélangé recommandé, l'horizon, les trajectoires et la graine, et après Simuler les chiffres terminaux, le cône et Ce que cette simulation a supposé" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧪 Pourquoi la simulation est encore en bêta {: #why-beta }

Toutes les autres parties de l'analyse des risques sont sorties de bêta. Seule l'étape de simulation s'ouvre avec un avis : *La simulation est encore en bêta. Son résultat dépend fortement de la quantité d'historique demandée par rapport à l'horizon : une fenêtre courte avec un horizon long peut produire des chiffres invraisemblables.* En dessous, un second avertissement reste définitivement, car un modèle reste un modèle : *C'est le seul barreau qui est un modèle plutôt qu'une mesure. Lisez-le comme une plage de possibilités, non comme une prévision.*

Le défaut derrière le premier avis est le rapport entre l'horizon $H$, compté en pas, et les $n$ observations de la fenêtre. Une trajectoire rééchantillonnée de $H$ pas réutilise chaque observation $H/n$ fois en moyenne : à partir d'un quart d'historique, un horizon d'un an correspond à ce quart, remélangé et répété environ quatre fois, et quoi que ce quart ait fait — un rally, une période calme, une baisse — devient l'année. La courbe normale n'y échappe pas, car sa dérive et sa volatilité sont celles de la fenêtre, reportées telles quelles quelle que soit la longueur de l'horizon. Demander plus d'historique ne guérit pas toujours non plus : une position avec un historique court raccourcit la fenêtre partagée pour toutes (voir [Qualité des données](data-quality.md#alignment-what-missing-data-actually-costs)). Aucun garde-fou sur ce rapport n'est encore appliqué, et tant qu'il n'y en a pas, l'étape reste en bêta. L'[incertitude de la dérive](#the-drift-is-an-estimate), affichée à côté de chaque résultat, est ce rapport à l'œuvre.

---

## 🔁 Historique remélangé : le bootstrap par blocs conjoints {: #block-bootstrap }

Le mode par défaut n'estime rien. Il prend les rendements simples des positions sur la fenêtre analysée, alignés sur un calendrier partagé — une ligne par date d'observation, une colonne par position — les transforme en rendements logarithmiques $x_{s,i} = \ln(1 + r_{s,i})$, et construit chaque futur à partir de **blocs** de lignes consécutives de cette matrice.

Avec $n$ observations dans la fenêtre et des blocs de $b$ observations, une trajectoire de $H$ pas est assemblée à partir de $\lceil H/b \rceil$ blocs. Chaque bloc commence à une ligne tirée uniformément au hasard parmi les $n$ et prend les $b$ lignes à partir de là, en bouclant de la dernière ligne à la première ; les blocs sont mis bout à bout et coupés à $H$ pas. La position $i$ croît le long de la trajectoire par la somme composée de ses rendements logarithmiques tirés, et le portefeuille est la composition d'aujourd'hui conservée sans rééquilibrage, sa part de liquidités $c$ ne rapportant rien :

$$
G_i(s) = \exp\Big(\sum_{u=1}^{s} x_{u,i}\Big), \qquad R(s) = c + \sum_i w_i \, G_i(s) - 1
$$

où $w_i$ sont les poids d'aujourd'hui et $R(s)$ est le rendement du portefeuille après $s$ pas. Trois propriétés découlent de la construction :

- **Des lignes entières sont tirées.** Le rendement d'une position à une date voyage avec le rendement de chaque autre position à la même date, si bien que leur co-mouvement est porté par construction : aucune covariance n'est estimée, inversée ou vérifiée, et aucune ne peut échouer.
- **Les rendements consécutifs restent ensemble à l'intérieur d'un bloc.** La dépendance à courte portée — une semaine turbulente, une série de jours calmes — survit dans chaque bloc, et n'est rompue qu'aux jointures.
- **Sans régime, chaque pas s'est produit.** Les queues sont celles de la fenêtre elle-même, pas celles d'une courbe en cloche : un pas isolé ne peut pas bouger plus que le plus grand mouvement enregistré par la fenêtre, et une trajectoire ne contient rien que la fenêtre ne contenait pas.

### 📏 Jours calendaires et pas {: #calendar-days-and-steps }

L'horizon est exprimé en jours calendaires, mais l'historique est une séquence d'observations : une série cotée en jours de bourse en contient environ 252 par an, pas 365. Un horizon de $D$ jours calendaires est donc converti à la fréquence observée $f$ de la fenêtre, le nombre d'observations qu'elle contient par an (voir [Annualisation observée](observed-annualization.md)) :

$$
H = \max\Big(1,\ \operatorname{round}\Big(\frac{D \, f}{365}\Big)\Big)
$$

Les $H$ pas sont simulés puis relus à raison d'un point par jour calendaire : le jour $d$ montre le pas $\lfloor d \, H / D \rfloor$, si bien qu'un jour tombant entre deux pas répète le précédent — pas de cotation, pas de mouvement.

### 🧱 La longueur de bloc {: #block-length }

Sauf si une longueur de bloc est demandée, elle suit la règle empirique du bootstrap à blocs mobiles, proportionnelle à la racine cubique de l'échantillon :

$$
b = \min\big(n,\ \max(2,\ \operatorname{round}(n^{1/3}))\big)
$$

Cela donne 6 observations pour un an de jours de bourse, et 9 pour trois ans : assez long pour porter le regroupement de volatilité sur quelques jours consécutifs, assez court pour laisser de nombreux blocs distincts à tirer. Le résultat rapporte la longueur utilisée, reconvertie en jours calendaires, sous *Longueur de bloc*.

L'analyse accepte aussi une longueur demandée, `block_length_days`, de 1 à 5 000 jours calendaires, convertie en observations à la même fréquence $f$. L'étape **Et si… ?** ne l'offre pas et utilise toujours la règle ci-dessus, donc seule une requête envoyée directement à l'analyse peut la définir — et seule une telle requête peut rencontrer le refus décrit dans [Limites](#limits).

---

## 🌦️ Régimes prescrits {: #prescribed-regimes }

*Marché calme*, *Crise prolongée* et *Choc et reprise* rééchantillonnent exactement comme ci-dessus, puis transforment chaque rendement logarithmique tiré pendant la durée du régime :

$$
\tilde{x}_{s,i} = \bar{x}_i + k_s \, (x_{s,i} - \bar{x}_i) + \delta_s
$$

où $\bar{x}_i$ est le rendement logarithmique moyen de la position $i$ sur la fenêtre, $k_s$ met à l'échelle les amplitudes autour de cette moyenne et $\delta_s$ décale leur niveau. En dehors de la durée, $k_s = 1$ et $\delta_s = 0$ : l'historique est tiré tel quel.

| Mode | Durée | $k_s$ | $\delta_s$, par pas |
|---|---|---|---|
| Marché calme | tout l'horizon | $0.7$ | $0$ |
| Crise prolongée | les 426 premiers jours calendaires (14 mois) | $2.5$ | $\ln(0.8)/f$ |
| Choc et reprise | les 61 premiers jours calendaires (2 mois) | $1$ | $\ln(0.65)/m$ |

avec $f$ la fréquence observée de la fenêtre et $m$ le nombre de pas couverts par le choc. Sur un an de pas, le décalage de crise se compose en un facteur de $0.8$ — un niveau inférieur de 20 % chaque année à ce que l'historique seul donnerait — en plus d'amplitudes deux fois et demie plus larges. Le choc se compose en $0.65$, une baisse de 35 % en plus de l'historique, sur sa durée, et toujours intégralement : sur un horizon plus court que deux mois, toute la baisse tombe dans l'horizon. Les durées sont converties en pas de la même manière que l'horizon.

Un régime est **déclaré, jamais estimé** : ces nombres sont l'hypothèse, écrite, pas quelque chose de mesuré à partir de vos données. Chaque pas applique le même $k_s$ et le même $\delta_s$ à chaque position, ce qui laisse les corrélations entre elles celles de l'historique.

Lorsque l'horizon est plus court que la durée d'un régime, le régime ne couvre que l'horizon, et le résultat le dit — pour une crise sur un horizon d'un an : *Déclaré sur 426 jours, appliqué sur 365 : le cône répond à la question plus courte.*

---

## 📈 La courbe normale : mouvement brownien géométrique {: #the-process }

Dans le mode *Courbe normale (MBG)*, chaque trajectoire provient d'un **mouvement brownien géométrique**. Pour un actif unique, la valeur $S_t$ évolue selon

$$
dS_t = \mu S_t \, dt + \sigma S_t \, dW_t
$$

où $\mu$ est la dérive, $\sigma$ la volatilité et $W_t$ un mouvement brownien, par lequel le hasard entre. Chaque actif simulé part de 1.0, donc sa trajectoire est un facteur de croissance plutôt qu'un prix, et il est avancé jour après jour jusqu'à atteindre l'horizon.

Les actifs ne sont pas simulés séparément puis additionnés. Ils sont assemblés en un processus unique dont les chocs sont liés par **une seule matrice de corrélation**, de sorte qu'un mouvement d'un actif arrive accompagné des mouvements qu'implique son co-mouvement mesuré.

L'intégration de l'équation donne la trajectoire sous forme close :

$$
S_t = S_0 \exp\left(\left(\mu - \frac{\sigma^{2}}{2}\right) t + \sigma W_t\right)
$$

Deux propriétés de ce modèle font l'essentiel du travail, et toutes deux sont des restrictions :

- **$\mu$ et $\sigma$ sont des constantes.** Chacune prend une valeur et la garde pour tout l'horizon, et il en va de même pour chaque entrée de la matrice de corrélation. Rien dans la simulation ne modifie sa propre volatilité, ni ses propres corrélations, en cours d'exécution.
- **Le hasard n'entre que par $W_t$**, donc sur tout intervalle le rendement logarithmique est distribué normalement. La forme des rendements simulés est fixée avant que la première trajectoire ne soit tirée, et cette forme est la courbe en cloche.

La seconde propriété est celle à emporter dans tout ce qui suit : la distribution normale est **plus mince dans les queues** que les rendements que les marchés produisent réellement, et les queues sont ce pour quoi on lit une simulation de risque.

---

## 🎲 Deux façons de tirer le même modèle {: #sampling-strategies }

La **Stratégie d'échantillonnage** offerte avec la courbe normale — et uniquement avec elle — se choisit entre **Monte Carlo** et **quasi-Monte Carlo**. C'est un choix sur la façon dont les nombres aléatoires sont produits, et sur rien d'autre. Le bootstrap n'a pas un tel choix : il tire toujours les débuts de ses blocs à partir d'un générateur pseudo-aléatoire amorcé.

!!! warning "Deux entrées ne sont pas deux modèles"

    Un menu à deux entrées invite à lire qu'il y a deux modèles disponibles, et que l'un d'eux pourrait mieux convenir à un portefeuille que l'autre. Il n'y en a pas deux. Les deux entrées pilotent le même mouvement brownien géométrique, avec la même dérive, la même volatilité et la même matrice de corrélation, et toutes deux tirent des nombres **gaussiens** pour ce faire.

    Le quasi-Monte Carlo achète la **convergence**, pas le réalisme. Sa suite à faible discrépance couvre l'espace d'échantillonnage plus uniformément que des tirages pseudo-aléatoires, de sorte que l'estimation se stabilise avec moins de trajectoires. Il ne simule pas un marché différent, et il ne répare aucune des hypothèses de cette page.

Ce qui diffère, c'est ce dont chacune a besoin pour être reproductible, et ce que chacune exige du nombre de trajectoires :

| | Monte Carlo | Quasi-Monte Carlo |
|---|---|---|
| Source des nombres | générateur pseudo-aléatoire | une suite de Sobol à faible discrépance |
| Reproduite par | une graine aléatoire | un index de départ dans la suite |
| Nombre de trajectoires | aucune autre exigence | doit être une **puissance de deux** |
| Limite supplémentaire | — | positions × jours d'horizon au plus 21 201 — voir [Limites](#limits) |

Les deux sont entièrement reproductibles : la même graine, ou le même index de départ, régénère les mêmes trajectoires. Ni l'une ni l'autre n'accepte le paramètre de l'autre — une graine et un index de départ Sobol sont mutuellement exclusifs. Le Tableau de bord n'affiche pas d'index de départ : il entre toujours dans la suite à 0. L'onglet **Risque & Scénarios** de la page d'un actif permet de le définir.

---

## 📐 D'où viennent les paramètres {: #parameters }

Dans la courbe normale, le modèle est fourni par la mesure plutôt que par le choix. Les rendements de la fenêtre analysée sont convertis en rendements logarithmiques, et à partir de ceux-ci :

- la **covariance** est la covariance d'échantillon, symétrisée et mise à l'échelle en termes annuels. Chaque observation de la fenêtre porte le même poids — un rendement du premier jour compte exactement autant qu'un rendement du dernier ;
- les **volatilités** sont les racines carrées de sa diagonale, et la **matrice de corrélation** est ce qui reste une fois cette échelle divisée ;
- la mise à l'échelle en termes annuels utilise le facteur de durée observée mesuré décrit dans [Annualisation observée](observed-annualization.md), pas une convention fixe.

La dérive est le seul paramètre qui n'est pas simplement la moyenne mesurée :

$$
\mu = \bar{r}_{\log} \cdot f + \frac{\sigma^{2}}{2}
$$

avec $\bar{r}_{\log}$ le rendement logarithmique moyen par observation, $f$ le facteur d'annualisation et $\sigma^{2}$ la variance annuelle. Le terme de demi-variance est la correction de convexité d'Itô. Le paramètre de dérive du processus est un taux de croissance *simple* attendu, tandis que ce qui a été mesuré est un rendement *logarithmique* moyen, et les deux diffèrent exactement de la moitié de la variance ; l'ajouter rend la croissance logarithmique attendue des trajectoires simulées égale au rendement logarithmique moyen de la fenêtre. Sans cela, les trajectoires croîtraient plus lentement que les données dont elles proviennent.

Les liquidités sont traitées différemment des positions, dans tous les modes. Elles entrent dans la trajectoire du portefeuille à leur poids et y restent : la poche de liquidités **rapporte exactement zéro** sur tout l'horizon et n'apporte aucune variation propre.

---

## 🧮 La dérive est une estimation {: #the-drift-is-an-estimate }

Quel que soit le mode, le centre du cône repose sur la croissance moyenne de la fenêtre — le bootstrap tire chaque ligne avec la même probabilité, la courbe normale fixe sa dérive à partir de la même moyenne — et cette moyenne est une estimation d'échantillon, avec son propre écart-type. Le cône ne contient pas cette erreur : il est la dispersion des trajectoires *étant donné* la dérive. Ainsi, à côté du résultat, une ligne indique de combien cette erreur seule déplace la médiane.

Avec $\hat{\sigma}$ l'écart-type du rendement logarithmique du portefeuille par observation sur les $n$ observations de la fenêtre — liquidités comptées à leur poids, ne rapportant rien — et $H$ l'horizon en pas, le facteur à 95 % est

$$
\varphi = \exp\left(z_{0.975} \, \frac{H \, \hat{\sigma}}{\sqrt{n}}\right), \qquad z_{0.975} \approx 1.96
$$

et la médiane $M$ du dernier jour reçoit l'intervalle $\big[(1 + M)/\varphi - 1,\ (1 + M)\,\varphi - 1\big]$ : *La dérive provient de … observations : cela seul place cette médiane entre … et ….* Lorsque $\varphi$ dépasse la dispersion du cône lui-même, $(1 + P_{95})/(1 + P_{5})$, la ligne devient un avertissement ambre : l'incertitude sur la dérive seule est alors plus large que la bande tracée par la simulation.

L'exposant croît avec $H$ et ne diminue qu'avec $\sqrt{n}$ : doubler l'horizon le double, tandis que le diviser par deux exige quatre fois plus d'historique. C'est le [rapport derrière l'avis de bêta](#why-beta), écrit sous forme de nombre.

---

## 🚧 Limites {: #limits }

Une simulation est refusée, plutôt que mal exécutée, dans les cas ci-dessous. Le refus est lui-même le résultat — la simulation revient indisponible — et la bannière de **Et si… ?** en dit la raison :

| Refus | Quand | À l'écran | Que changer |
|---|---|---|---|
| Historique trop court | Moins de 30 observations dans la fenêtre | *Historique insuffisant pour ce calcul.* | Une plage de dates plus longue |
| Bloc plus long que l'historique | Une longueur de bloc demandée couvre plus d'observations que la fenêtre n'en contient | *Paramètres de calcul invalides.* | Un bloc plus court, ou une fenêtre plus longue |
| Nombre de trajectoires | Quasi-Monte Carlo avec un nombre de trajectoires qui n'est pas une puissance de deux | *Paramètres de calcul invalides.* | Une puissance de deux : 4 096, 8 192, 16 384… |
| Budgets de trajectoires | Tout mode, lorsque trajectoires × (jours d'horizon + 1) dépasse 20 000 000, ou trajectoires × jours d'horizon × positions dépasse 200 000 000 | *Cette simulation est trop grande pour être exécutée. Utilisez moins de trajectoires de simulation ou un horizon plus court.* | Moins de trajectoires, ou un horizon plus court |
| Séquence trop grande | Courbe normale avec quasi-Monte Carlo, lorsque positions × jours d'horizon dépasse 21 201 | *Cette simulation quasi-Monte Carlo est trop grande pour être exécutée. Raccourcissez l'horizon ou choisissez l'échantillonnage Monte Carlo.* | Un horizon plus court, ou l'échantillonnage Monte Carlo |
| Historique trop long | Historique remélangé ou un régime, lorsque la fenêtre contient plus de 5 000 observations, ou observations de la fenêtre × positions dépasse 250 000 | *Cette simulation est trop grande pour être exécutée : la période contient trop d'historique. Choisissez une période plus courte.* | Une plage de dates plus courte |
| Trop de positions | Tout mode, lorsque plus de 100 positions participent | *Une simulation peut inclure au plus 100 positions, et ce portefeuille en a plus. Simulez plutôt un courtier avec moins de positions.* | Aucun paramètre : un courtier avec moins de positions, simulé depuis sa propre page |

Chaque limite de taille répond `resource_limit` — trop grand pour être exécuté, ce qui n'est ni un échec ni un défaut des paramètres. Ses détails nomment la limite atteinte, la valeur atteinte et le plafond, et un `remedy` nomme ce qui ramène la requête à portée. Le remède choisit la phrase à l'écran, donc chacune dit quoi changer ; un refus de taille qui ne nomme aucun remède, ou pour lequel la bannière n'a pas de phrase, est affiché avec le message général *Ce calcul est trop grand pour être exécuté.* Le refus de longueur de bloc est plutôt un refus d'un paramètre, et son code le dit — paramètres invalides plutôt qu'historique insuffisant. Il indique la longueur demandée, les observations qu'elle couvre et les observations que la fenêtre contient : le remède est un bloc plus court, car plus d'historique n'est souvent pas disponible. Le refus de Sobol indique le nombre de dimensions de séquence nécessaires — une par position et par jour de l'horizon — et la limite. À l'horizon par défaut de 365 jours, la limite admet 58 positions ; à l'horizon le plus long, 3 650 jours, elle tombe entre cinq et six : cinq positions nécessitent 18 250 dimensions, six en nécessitent 21 900. Le nombre de trajectoires n'y joue aucun rôle, et l'échantillonnage Monte Carlo n'a pas une telle limite.

Les limites de taille mordent plus tôt qu'elles n'en ont l'air. Aux 8 192 trajectoires par défaut, tout horizon au-delà de 2 440 jours dépasse le premier budget de trajectoires — à 2 441 jours, 8 192 × 2 442 = 20 004 864. Aux 365 jours et 8 192 trajectoires par défaut, une portée de 67 positions ou plus dépasse le second : 8 192 × 365 × 67 = 200 335 360. Le budget d'historique se resserre à mesure que la portée grandit : la fenêtre peut contenir au plus 5 000 observations — près de vingt ans de jours de bourse — et au plus 250 000 divisé par le nombre de positions, donc la première borne gouverne jusqu'à 50 positions et la seconde au-delà, jusqu'à 2 500 observations, environ dix ans, à 100. Au-delà de 100 positions, aucun paramètre n'aide : la portée est refusée avant que quoi que ce soit ne soit rééchantillonné ou estimé, quels que soient les paramètres, et il ne reste qu'à simuler un courtier unique avec moins de positions. Dans chaque décompte, les positions sont celles que la simulation lit, donc une position [exclue](data-quality.md#exclusions) ne compte dans aucun d'eux. Une requête au-delà de plusieurs limites les rencontre une à la fois : chaque refus en nomme une, et le suivant apparaît une fois celle-ci corrigée.

---

## 💡 Interprétation {: #interpretation }

Lisez le résultat comme ce qu'implique le mode, jamais comme ce qui est censé se produire :

- **Rien dedans n'est une preuve.** Une trajectoire rééchantillonnée réarrange ce que la fenêtre contenait ; une trajectoire de modèle est une conséquence de la dérive, de la volatilité et des corrélations fournies. Ni l'une ni l'autre ne porte d'information que la fenêtre ne contenait pas déjà, et un régime n'ajoute que l'hypothèse qu'il déclare.
- **Plus de trajectoires réduit l'erreur d'échantillonnage, pas l'erreur de modèle.** Augmenter le nombre de trajectoires fait converger le résultat — vers la réponse que *ce mode* donne. Aucun nombre de trajectoires n'ajoute un krach que la fenêtre ne contenait pas, n'épaissit une queue gaussienne ou ne fait bouger une corrélation fixe.
- **Le centre de la distribution est une extrapolation.** C'est la croissance moyenne de la fenêtre reportée telle quelle — décalée, sous une crise ou un choc, du montant que le régime déclare. Une fenêtre qui a monté produit des futurs qui montent, tant que l'horizon dure, et la précision avec laquelle cette moyenne est connue est l'[incertitude de la dérive](#the-drift-is-an-estimate).
- **La dispersion est aussi large que la fenêtre l'était, et pas plus** — sauf le facteur qu'un régime déclare. Une période d'estimation calme fournit des amplitudes calmes et un co-mouvement confortable, et la simulation produit alors un futur calme en toute bonne foi.

Les chiffres qui lisent ce qui s'est réellement produit — [Valeur à risque](value-at-risk.md), [Pire réalisation](worst-realization.md), [Perte maximale](max-drawdown.md) — sont au moins bornés par un historique qui a eu lieu. Une simulation n'est bornée que par ses propres hypothèses. La courbe normale peut montrer une perte pire que tout ce qui est enregistré, dont la forme est celle du modèle plutôt que du marché ; une longue trajectoire rééchantillonnée peut enfiler des blocs défavorables en une baisse que le marché n'a jamais livrée d'un seul tenant.

---

## ⚠️ Limitations {: #limitations }

!!! warning "La fenêtre est la seule source"

    Chaque mode lit une seule fenêtre : le bootstrap réutilise ses lignes, la courbe normale ajuste ses moyennes, et les deux pondèrent chaque observation également, sans poids supplémentaire sur les plus récentes. Une fenêtre sans krach n'en contient aucun à tirer, et une fenêtre qui a monté est projetée en hausse, quelle que soit la longueur de l'horizon. La fenêtre sur laquelle chaque résultat a été calculé est publiée avec lui — voir [Qualité des données](data-quality.md).

!!! warning "La courbe normale sous-estime les queues"

    Les rendements réels des marchés produisent des mouvements extrêmes plus souvent, et plus grands, qu'une distribution normale ne le permet. Le mode *Courbe normale (MBG)*, construit sur des incréments gaussiens, rapporte donc les issues rares comme plus rares et plus modérées qu'elles ne l'ont été historiquement, et il le fait avec le plus d'assurance à l'extrémité de la distribution — la partie qu'une simulation de risque existe pour décrire. [Valeur à risque](value-at-risk.md) couvre la même défaillance sous sa forme paramétrique. Le bootstrap conserve les queues propres à la fenêtre : ni plus minces, ni plus épaisses.

!!! warning "La volatilité ne se regroupe que jusqu'à un bloc"

    Dans la courbe normale, la volatilité est un nombre unique pour tout l'horizon, donc un mauvais jour ne rend pas le jour suivant plus susceptible d'être mauvais. Le bootstrap conserve le regroupement de la fenêtre à l'intérieur de chaque bloc, long de quelques jours, et le perd aux jointures : une période turbulente rééchantillonnée dure à peu près aussi longtemps qu'un bloc, pas aussi longtemps que celle dont elle provient, sauf si une *Crise prolongée* en déclare une. Les marchés réels se comportent autrement : les périodes turbulentes arrivent par séries, et les crises persistent. Une pire séquence simulée n'est pas le même objet qu'une crise historique et ne doit pas être comparée à une telle crise.

!!! warning "Les corrélations ne se brisent jamais"

    La courbe normale applique une seule matrice de corrélation à chaque futur ; le bootstrap porte le co-mouvement propre à la fenêtre, et les régimes le laissent inchangé par construction. Ni l'un ni l'autre ne peut produire, sauf si la fenêtre le contient, l'événement qui endommage le plus un portefeuille diversifié : des corrélations montant vers un exactement quand les marchés chutent, laissant des positions qui se compensaient auparavant tomber ensemble. [Corrélation](correlation.md) couvre la version mesurée, et combien elle dépend de la fenêtre dont elle a été tirée.

!!! warning "Les liquidités restent immobiles, et rien d'autre ne se produit"

    La part de liquidités du portefeuille ne croît ni ne varie sur l'horizon, quoi qu'elle puisse rapporter en réalité, et la composition est conservée sans rééquilibrage. Les coûts, les flux de trésorerie et l'inflation sont aussi laissés de côté : le résultat les liste sous *Exclus du cône*. Plus l'horizon est long, plus ces simplifications comptent.

---

## 🔗 Voir aussi {: #related }

- 📊 **[Volatilité](volatility.md)** — la mesure de dispersion que la courbe normale prend comme l'un de ses deux paramètres
- 🔗 **[Corrélation](correlation.md)** — la structure de co-mouvement que la simulation maintient fixe sur chaque trajectoire
- 📅 **[Annualisation observée](observed-annualization.md)** — la fréquence mesurée qui transforme les jours calendaires en pas, et les statistiques de la fenêtre en statistiques annuelles
- 📉 **[Valeur à risque](value-at-risk.md)** — la même question de queue, répondue à partir de rendements observés plutôt que générés
- ⏮️ **[Rejeu historique](historical-replay.md)** — un épisode réel appliqué au portefeuille actuel, où rien n'est généré
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre et le nombre d'observations à partir desquels les paramètres ont été estimés
