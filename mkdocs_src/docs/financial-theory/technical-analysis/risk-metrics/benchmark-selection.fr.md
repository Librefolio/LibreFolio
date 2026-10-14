# 🎯 Sélection de l'indice de référence

Chaque chiffre relatif transporte un passager invisible : la chose par rapport à laquelle il a été mesuré. « Le portefeuille a battu le marché de trois points » n'est pas une affirmation sur le portefeuille — c'est une affirmation sur le portefeuille **et** sur ce qui a été appelé « le marché ». Changez le second terme et le verdict change avec lui, sans qu'aucune position n'ait bougé.

Cette page traite de ce second terme. Le choix de la comparaison n'est pas une préférence d'affichage appliquée après l'analyse : il fait partie du résultat.

---

## 🔢 Ce que signifie « relatif » {: #what-relative-means }

Étant donné une série de rendements primaire $r_p$ et une série de comparaison $r_b$ observées aux mêmes dates, LibreFolio dérive les chiffres relatifs de ce couple.

**Le rendement actif** est la différence entre les deux rendements de période de détention, chacun composé sur la fenêtre partagée :

$$\text{Active} = \left[ \prod_{t=1}^{N} (1 + r_{p,t}) - 1 \right] - \left[ \prod_{t=1}^{N} (1 + r_{b,t}) - 1 \right]$$

C'est une différence de rendements composés sur la fenêtre effectivement partagée par les deux séries — pas un chiffre annualisé, et pas un ratio.

**Le bêta** mesure la force avec laquelle la série primaire a répondu à la série de comparaison :

$$\beta = \frac{\mathrm{Cov}(r_p, r_b)}{\mathrm{Var}(r_b)}$$

Le dénominateur est la clé de toute cette page : le bêta est la covariance **divisée par la variance de l'indice de référence**. Tout ce que l'indice de référence fait — ou ne fait pas — se propage dans le chiffre.

**La corrélation** est calculée avec le même estimateur que la [matrice de corrélation](correlation.md), et répond à la question de savoir si la comparaison est même pertinente : un bêta mesuré par rapport à quelque chose que le portefeuille ne suit pas décrit une relation qui n'existe pas.

---

## 💡 Interprétation {: #interpretation }

Les trois chiffres répondent à des questions différentes et sont censés être lus ensemble.

| Chiffre | Question à laquelle il répond |
|---|---|
| Rendement actif | Le portefeuille a-t-il terminé la fenêtre partagée devant ou derrière la comparaison ? |
| Bêta | Dans quelle mesure la réponse du portefeuille aux mouvements de la comparaison a-t-elle été amplifiée ? |
| Corrélation | La comparaison était-elle une référence pertinente ? |

La corrélation vient en premier en pratique. Le rendement actif et le bêta restent arithmétiquement bien définis par rapport à une comparaison que le portefeuille ignore complètement, et ils n'ont aucun sens dans ce cas — une faible corrélation est le signal que l'indice de référence était la mauvaise question, pas que le portefeuille était la mauvaise réponse.

### 🧭 Pourquoi le choix est déjà la moitié du verdict {: #why-the-choice-is-already-half-the-verdict }

Un seul portefeuille d'actions mondial comparé à un vaste indice mondial, à un indice domestique et à un fonds obligataire produira trois rendements actifs différents, trois bêtas différents et trois impressions différentes — à partir des mêmes positions sur les mêmes dates. Aucun des trois n'est une erreur de mesure. Ils répondent à trois questions différentes, et la question a été choisie lorsque l'indice de référence a été choisi.

La conséquence pratique est une règle de comparabilité : **deux chiffres relatifs ne peuvent être comparés entre eux que s'ils ont été mesurés par rapport au même indice de référence**. Un bêta n'est pas une propriété d'un portefeuille ; c'est une propriété d'un portefeuille *et* d'une référence. LibreFolio enregistre l'actif de comparaison dans les métadonnées du résultat lui-même précisément pour qu'un chiffre ne puisse jamais être séparé de la référence qui l'a produit.

---

## 🧮 Ce qui peut servir d'indice de référence {: #what-can-serve-as-a-benchmark }

La comparaison n'est pas arbitraire. L'analyse prend un **actif réel qui existe dans vos données** comme référence, identifié explicitement, et trois choses en découlent.

**Il doit exister.** Une comparaison avec un actif inconnu n'est pas silencieusement abandonnée ou remplacée par une valeur par défaut : l'analyse ne retourne aucune valeur, signale des paramètres invalides et nomme l'actif demandé.

**Il doit avoir un historique de prix utilisable.** La série de l'indice de référence est préparée exactement comme les positions analysées, sur le même calendrier partagé et dans la même devise cible. Si aucune série utilisable ne peut être construite pour lui, le résultat est indisponible plutôt qu'approximatif.

Le sélecteur d'indice de référence demande au moteur quels actifs ont un historique de prix utilisable qui leur est propre sur la période d'analyse et dans la devise cible, et liste les autres à part, en lecture seule, chacun avec les raisons du moteur. Un indice de référence choisi précédemment qui ne passe pas ce contrôle reste choisi et affiché dans le sélecteur, mais rien n'est mesuré par rapport à lui. Si le contrôle ne peut pas être effectué, rien n'est verrouillé.

**Il doit bouger.** Le bêta divise par la variance de la série de comparaison, donc une référence qui ne bouge jamais n'a pas de variance par laquelle diviser : le bêta et la corrélation reviennent indéfinis, et les deux déclenchent un avertissement explicite plutôt qu'un nombre. C'est pourquoi une référence plate — une constante, un taux de rendement fixe hypothétique — ne peut pas fonctionner comme indice de référence ici. La contrainte n'est pas une politique qui pourrait être levée ; c'est l'arithmétique du ratio.

!!! info "Un indice de référence n'est pas un seuil"

    La comparaison répond à « par rapport à quoi ? », pas à « est-ce bon ? ». Un portefeuille qui est en retard sur un indice de référence en hausse et un portefeuille qui baisse moins qu'un indice de référence en chute produisent tous deux un chiffre ; aucun des deux chiffres ne sait si l'investisseur devrait être satisfait. Ce jugement nécessite l'objectif, qui vit en dehors de la métrique.

---

## 📏 La fenêtre partagée {: #the-shared-window }

Deux séries couvrent rarement exactement les mêmes dates, donc la comparaison est calculée sur l'**intersection** des deux calendriers : à chaque date partagée, chaque série contribue ses rendements depuis la date partagée précédente — pour la première date partagée, depuis la date précédente de la série primaire — composés en un seul. Un indice de référence coté les jours où la série primaire ne l'est pas — un crypto-actif le week-end, à côté d'un portefeuille lu sur ses [jours d'observation](data-quality.md#coverage) — conserve ces mouvements.

Trois conséquences sont publiées avec le résultat.

**Un minimum s'applique.** En dessous de 20 observations partagées, la comparaison n'est pas calculée du tout : le résultat est indisponible avec un motif d'historique insuffisant portant à la fois le nombre d'observations partagées trouvées et le nombre requis. Un indice de référence qui chevauche à peine votre historique ne produit aucun chiffre au lieu d'un chiffre fragile.

**La couverture est rapportée.** Le résultat enregistre quelle fraction des dates propres à la série primaire a survécu à l'intersection — c'est-à-dire sur combien de vos dates la référence choisie avait un rendement qui lui est propre. Un indice de référence lancé à la moitié de votre période de détention ne compare pas silencieusement une demi-période ; il le dit.

**Le facteur d'annualisation est remesuré sur la fenêtre partagée.** Parce que l'intersection est généralement plus courte et plus clairsemée que la fenêtre d'analyse complète, toute quantité annualisée dans la comparaison est mise à l'échelle par un facteur mesuré sur l'échantillon commun plutôt qu'hérité de l'analyse plus large — la même logique de facteur observé décrite dans [Annualisation observée](observed-annualization.md), appliquée au chevauchement.

---

## 📈 La droite risque/rendement {: #the-risk-return-line }

Dans l'onglet **Risque** du tableau de bord et de la page d'un courtier, le niveau **Suis-je payé pour ce risque ?** dessine un graphique du risque en fonction du rendement — volatilité annualisée en abscisse, rendement annuel moyen en ordonnée. Il montre un point par position, dimensionné par son poids dans le portefeuille ; un pour le portefeuille lui-même, tel que composé aujourd'hui et rejoué sur la fenêtre ; un pour l'indice de référence, dessiné comme un losange ; et une droite en pointillés.

La droite part de l'axe vertical au **taux sans risque utilisé par la page** — le même taux que ses chiffres de Sharpe et de Sortino, qui est aujourd'hui de 0 sur le tableau de bord et sur la page d'un courtier — et passe **par l'indice de référence**. En théorie, c'est la droite du marché des capitaux, qui passe par le *portefeuille de marché* ; ici, l'indice de référence est ce qui représente le marché :

$$R = R_f + \frac{R_b - R_f}{\sigma_b}\,\sigma$$

où :

- $\sigma$ est une volatilité annualisée, et $R$ le rendement annuel moyen atteint par la droite à cette volatilité ;
- $R_f$ est le taux sans risque utilisé par la page ;
- $R_b$ et $\sigma_b$ sont le rendement annuel moyen de l'indice de référence — son rendement moyen par période, mis à l'échelle sur un an — et sa volatilité annualisée.

**Lecture.** La pente, $(R_b - R_f)/\sigma_b$, est le [ratio de Sharpe](sharpe-ratio.md) de l'indice de référence : son rendement moyen au-dessus du taux sans risque par unité de volatilité. Un point au-dessus de la droite a été mieux payé pour son risque que l'indice de référence — plus de rendement moyen au-dessus du taux sans risque par unité de volatilité, un ratio de Sharpe plus élevé. Un point en dessous a été moins bien payé. Comme tout chiffre relatif sur cette page, c'est une comparaison avec la référence, pas une note.

**Choisir l'indice de référence pour cela.** Parce que l'indice de référence représente « le marché », un **vaste indice mondial** — un tracker d'un indice d'actions mondial, par exemple — est le substitut le plus pertinent. Un indice domestique, un indice sectoriel ou un fonds obligataire dessinent encore une droite, mais la transforment en une comparaison avec cette référence plus étroite : voir [Pourquoi le choix est déjà la moitié du verdict](#why-the-choice-is-already-half-the-verdict).

**Sans indice de référence choisi** — ou avec un indice de référence qui n'a pas pu être mesuré sur la fenêtre — la droite passe par **votre propre portefeuille** à la place. Au-dessus signifie alors mieux payé que le portefeuille dans son ensemble, et la pente est le ratio de Sharpe du portefeuille.

**Un indice de référence que vous détenez** est dessiné une seule fois, pas comme deux points : c'est le point de votre position lui-même, à son poids, dans le style de l'indice de référence, et la droite passe par lui.

**Sur la page Actifs.** Son [onglet Corrélation](../../../user/assets/correlation.md#what-did-each-pay), qui compare une sélection d'actifs que vous avez constituée, dessine la même droite lorsqu'un indice de référence est choisi et mesuré sur la fenêtre : elle part du taux sans risque utilisé par la page — 0 aujourd'hui, comme sur le tableau de bord — et passe par le losange de l'indice de référence, donc sa pente est le ratio de Sharpe de l'indice de référence et un point au-dessus a été mieux payé pour son risque que l'indice de référence. Un indice de référence qui fait partie des actifs sélectionnés est dessiné une seule fois, comme le point de cet actif dans le style de l'indice de référence, et la droite passe par lui. Sans indice de référence, ou avec un indice de référence qui n'a pas pu être mesuré sur la fenêtre, aucune droite n'est dessinée, car aucun portefeuille ne peut prendre la place de l'indice de référence — une sélection n'a pas de poids et donc pas d'ensemble propre à travers lequel faire passer une droite — et le graphique montre le compromis et vous laisse le jugement.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-risk-return" alt="Qu'est-ce que chacun d'entre eux a payé pour son risque ? sur l'onglet Corrélation, avec le S&P 500 comme indice de référence : le tableau ouvert par sa ligne teintée, et le graphique avec les cercles des actifs, le losange de l'indice de référence et la ligne pointillée du taux sans risque la traversant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Prix uniquement, pour l'instant"

    Les rendements sur ce graphique proviennent uniquement des séries de prix : les coupons et les dividendes ne sont pas encore inclus. Une position qui verse une grande part de son rendement sous forme de revenu se situe donc plus bas que ne le ferait son rendement total — et lorsque l'indice de référence fait de même, la droite s'incline avec lui.

---

## ⚠️ Limitations {: #limitations }

!!! warning "L'indice de référence est un choix, et le choix n'est pas neutre"

    Parce que le bêta et le signe du rendement actif dépendent tous deux de la référence, une comparaison choisie après avoir vu les résultats n'est pas une mesure — c'est un récit. La séquence honnête consiste à décider ce que le portefeuille cherche à suivre *avant* de demander comment il s'est comporté par rapport à lui.

!!! warning "Les chiffres relatifs ne s'empilent pas"

    Les bêtas et les rendements actifs mesurés par rapport à des références différentes appartiennent à des échelles différentes. Comparer le bêta d'un actif par rapport à un indice domestique avec le bêta d'un autre actif par rapport à un indice mondial produit une comparaison de deux nombres sans rapport qui se trouvent partager un nom.

!!! warning "Les deux côtés ne sont pas toujours du même type de rendement"

    L'actif de comparaison apporte toujours le rendement de sa propre série de prix, tandis que le côté primaire conserve la base de rendement de ce qui est analysé — un actif ou un portefeuille entier. Le résultat enregistre quelle base a été utilisée du côté primaire, et il vaut la peine de vérifier avant d'interpréter un petit rendement actif comme significatif.

!!! warning "Un calendrier partagé cache ce qu'il écarte"

    Seules les dates présentes dans les deux séries sont comparées. Si la référence manque précisément pendant la période turbulente qui compte le plus, la comparaison voit cette période comme une seule étape composée — ou pas du tout, avant la première date partagée de la référence — plutôt que comme elle s'est déroulée. Le chiffre de couverture est ce qui rend cette perte visible — lisez-le avant de lire le bêta.

---

## 🔗 Voir aussi {: #related }

- 📈 **[Bêta et rendement actif](beta-active-return.md)** — les deux chiffres que ce choix détermine
- 🔗 **[Corrélation](correlation.md)** — si la référence choisie est pertinente ou non
- 📅 **[Annualisation observée](observed-annualization.md)** — pourquoi le facteur est remesuré sur le chevauchement
- 🧪 **[Qualité des données](data-quality.md)** — ce que le calendrier partagé écarte, et comment il est rapporté
- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — la pente de la droite risque/rendement
