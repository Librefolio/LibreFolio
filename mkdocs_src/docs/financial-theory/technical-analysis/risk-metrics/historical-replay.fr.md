# ⏮️ Rejeu historique

Le rejeu historique applique les mouvements d'un épisode passé réel au portefeuille tel qu'il est composé aujourd'hui, en demandant ce que ce même épisode produirait maintenant.

C'est la question *que me ferait 2008 ?* à laquelle on répond par l'arithmétique plutôt que par le souvenir — et la valeur de la réponse dépend entièrement de la compréhension de quel portefeuille est soumis à cet épisode.

---

## 🔢 Comment le rejeu est calculé {: #how-the-replay-is-computed }

Vous choisissez un épisode — une plage de dates — et l'analyse utilise les rendements réels de chaque position sur cette plage. Chaque actif reçoit une unité de richesse au départ et se capitalise de manière autonome :

$$
W_i(t) = W_i(t-1) \cdot \left(1 + r_i(t)\right), \qquad W_i(0) = 1
$$

La richesse du portefeuille à chaque étape est la somme pondérée de ces indices de richesse des actifs, plus la part de liquidités :

$$
W_p(t) = c + \sum_i w_i \, W_i(t)
$$

et le rendement du portefeuille pour la période est la variation de cette richesse :

$$
r_p(t) = \frac{W_p(t)}{W_p(t-1)} - 1
$$

La part de liquidités $c$ vaut par défaut ce que les pondérations des actifs laissent de reste, $c = 1 - \sum_i w_i$, et les pondérations plus les liquidités doivent totaliser $1$. Toutes les séries doivent être établies sur un calendrier commun ; tout rendement inférieur à $-100\%$ et toute pondération négative sont refusés.

---

## 🧭 Rien n'est rééquilibré {: #nothing-is-rebalanced }

Les pondérations $w_i$ multiplient des indices de richesse des actifs qui divergent. Seules les pondérations **initiales** sont imposées : à partir de la deuxième période, la composition effective est celle qu'a produite la capitalisation.

C'est délibéré, et c'est le sens de *buy and hold*. Lors d'un krach, les actifs qui chutent le plus se réduisent d'eux-mêmes en proportion du portefeuille — aucune règle ne les vend, et aucune règle ne les reconstitue. Un rejeu avec rééquilibrage serait un exercice différent, car le rééquilibrage achète ce qui a chuté et rapporterait un résultat différent pour le même épisode.

!!! info "Les liquidités rapportent exactement zéro"

    La part de liquidités apporte une constante à la richesse du portefeuille à chaque période. Ce n'est pas un choix neutre, c'est un choix spécifique avec des conséquences dans les deux sens : pendant un krach, les liquidités sont la partie du portefeuille qui conserve sa valeur, et elles rendront la perte rejouée plus faible que ne le suggéreraient les seules positions investies. Sur une longue période ou une période inflationniste, un rendement nominal nul est une perte réelle que le rejeu ne montre pas, car le rejeu est exprimé en termes nominaux.

---

## ❓ Quel portefeuille est rejoué {: #whose-portfolio-is-being-replayed }

C'est le point sur lequel le résultat est le plus souvent mal interprété.

!!! warning "Ce n'est pas la performance qu'a réalisée votre portefeuille"

    Le rejeu projette les positions **d'aujourd'hui** vers le passé. Il répond à *comment le portefeuille que je détiens aujourd'hui se serait-il comporté dans cet épisode ?* — et non à *comment me suis-je comporté ?* Les deux ne coïncident que si la composition n'a jamais changé, et ils divergent chaque fois qu'une position a été achetée, vendue ou redimensionnée. La performance passée réelle est un fait établi et est rapportée ailleurs ; ce chiffre est une hypothèse sur une composition qui, dans de nombreux cas, n'existait pas à ces dates.

Il existe une seconde conséquence, plus discrète. Le portefeuille détenu aujourd'hui est celui qui a **survécu** à toutes les décisions prises depuis : les positions qui ont été vendues, y compris celles vendues parce qu'elles se portaient mal, n'y figurent pas. Le projeter vers le passé transporte cette sélection avec lui, de sorte qu'un rejeu d'un épisode défavorable peut paraître plus confortable que l'épisode ne l'était réellement — non pas parce que l'arithmétique est fausse, mais parce que l'arithmétique est appliquée à un ensemble de positions choisi avec le bénéfice de tout ce qui s'est produit par la suite.

---

## 🧩 Positions sans historique suffisant {: #holdings-without-enough-history }

Un épisode de 2008 ne peut pas être rejoué sur un fonds lancé en 2019 : il n'y a pas de rendements à appliquer. L'analyse ne comble pas la lacune par une hypothèse et ne s'arrête pas : elle **exclut la position** et rejoue les autres.

Chaque position est jugée sur ses propres cotations, et non sur le calendrier partagé. Elle ne participe que si elle est cotée aux deux extrémités de la fenêtre, à sept jours calendaires près du [seuil d'obsolescence](data-quality.md#staleness-threshold) : au début, une cotation dans les sept jours précédant le début de la fenêtre — ou, pour un historique qui commence à l'intérieur de la fenêtre, une première cotation au plus tard sept jours après le début de la fenêtre ; à la fin, une dernière cotation au plus tard sept jours avant la fin de la fenêtre. Le test est exécuté avant la préparation des séries de rendements, et l'ordre importe. Les séries rejouées partagent un seul calendrier (voir [Limitations](#limitations)) : une position qui commence tard, si elle était conservée, déplacerait le début de ce calendrier et raccourcirait le rejeu de toutes les autres positions pour s'y adapter.

### 🏷️ Pourquoi une position est exclue {: #why-a-holding-is-left-out }

Chaque position exclue porte exactement une raison :

| Raison | Ce que montrent les cotations de la position |
|---|---|
| Aucun prix dans la période | Aucune cotation à l'intérieur de la fenêtre, et aucune dans les sept jours précédant son début. |
| Première cotation après le début de la période | Son historique commence à l'intérieur de la fenêtre, plus de sept jours après le début. |
| Aucun prix récent au début de la période | Elle était cotée avant la fenêtre, mais pas dans les sept jours précédant son début — une lacune dans un historique plus ancien, ou un rythme clairsemé comme une NAV mensuelle. |
| Aucun prix récent à la fin de la période | Aucun prix dans les sept derniers jours de la fenêtre. Les cotations ne sont lues que jusqu'à la fin de la fenêtre, de sorte qu'une lacune et une radiation y sont indiscernables et partagent cette raison. |
| Aucun taux de change vers votre devise | Aucun taux de change de sa devise vers la devise dans laquelle l'analyse est exprimée. |
| Exclue par vous | Le lecteur l'a exclue manuellement, là où c'est possible — voir [Proxies](#proxies). |

### ⚖️ Ce qui la remplace {: #what-takes-its-place }

Ce qu'il advient d'une position exclue dépend de si le rejeu comporte des pondérations.

**Sur un portefeuille** — l'onglet Risque du Tableau de bord ou de la page d'un courtier — la position quitte le rejeu, mais sa pondération non. La pondération exclue est ajoutée à la part de liquidités $c$, ce qui signifie qu'elle est rejouée comme **rapportant exactement zéro** pour tout l'épisode. Ce zéro appartient au total, et non à la position : la position ne reçoit aucun rendement propre, et la liste des rendements par position ne mentionne que les positions qui ont été rejouées — un zéro parmi elles indiquerait un rendement que personne n'a mesuré.

Ce traitement mérite un instant d'attention, car il n'est pas neutre. Exclure une position ne rend pas le portefeuille plus petit ; elle rend cette fraction du portefeuille plate. Dans un épisode où tout a chuté, une position de 10 % maintenue plate est une affirmation implicite qu'elle aurait été ce que vous possédiez de mieux. Personne ne fait cette affirmation intentionnellement — le moteur l'applique de lui-même — c'est pourquoi le résultat nomme chaque position qu'il a exclue, avec sa raison et sa part de la valeur.

**Sur une sélection d'actifs sans pondérations** — l'onglet [Corrélation](../../../user/assets/correlation.md) de la page Actifs — il n'y a pas de part de liquidités pour maintenir quoi que ce soit. L'actif est simplement omis : il ne reçoit aucun rendement du tout, pas un rendement nul, et les chiffres parlent pour les actifs qui ont été rejoués. Une sélection n'a pas de composition à additionner, de sorte que ces rendements par actif constituent la réponse entière.

### 🔎 Ce que montre le résultat {: #what-the-result-shows }

Sur ces trois onglets, le rejeu dit ce qu'il a exclu avant les chiffres qu'il rapporte :

- un avertissement **au-dessus de tout le reste** lorsque plus de la moitié de la valeur du portefeuille est exclue, indiquant la part que le résultat couvre encore : au-delà de ce point, le total parle pour une minorité du portefeuille, le reste étant maintenu plat à côté ;
- dès qu'une position est exclue, un encadré **au-dessus du total, là où il y en a un, et du tableau** liste les positions exclues, **regroupées par raison**, chacune sous forme de badge avec son icône et son nom — sur un portefeuille avec sa part de la valeur également, sous une ligne indiquant quelle part de la valeur compte comme liquidités à rendement nul. La [période commune](#the-common-period), lorsqu'il y en a une, est proposée dans le même encadré ;
- le tableau ne liste que les positions qui ont été **rejouées**, de la pire à la meilleure — un clic sur un titre de colonne trie selon cette colonne — chacune sur une ligne : sa **Pondération** ; son **Rendement**, le sien sur la période ; sa **Contribution**, la pondération multipliée par ce rendement, de sorte que les contributions s'additionnent au total ; son **Impact**, le montant gagné ou perdu ; et son **Effet**, une barre dans une colonne que vous pouvez élargir en faisant glisser le bord de son titre. La barre montre la contribution sur un portefeuille et le rendement sur une sélection. Elle part d'une ligne de zéro au milieu de la colonne — les pertes à gauche en rouge, les gains à droite en vert — sur une échelle unique partagée par toutes les lignes, la plus grande amplitude atteignant le bord. Une position exclue n'a [aucun rendement propre](#what-takes-its-place), donc elle n'obtient pas de ligne, et non une ligne à zéro ;
- une colonne sans rien à montrer est omise, et non remplie de tirets : une sélection d'actifs n'a pas de pondérations, pas de contributions et pas d'argent, donc son tableau ne montre que le **Rendement** et l'**Effet** ;
- lorsque toutes les positions sont exclues, aucun chiffre : le résultat indique qu'il n'y a **rien à rejouer**, et liste les raisons.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-replay" alt="Que se passerait-il… ? sur l'onglet Corrélation après Exécuter le rejeu : l'encadré des actifs exclus, sous forme de badges regroupés par raison, avec le bouton de période commune, au-dessus du tableau des actifs rejoués, avec Rendement et Effet" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📆 La période commune {: #the-common-period }

Lorsque ce sont les extrémités de la fenêtre qui ont exclu des positions — un début tardif, une lacune avant la fenêtre, aucun prix récent à sa fin — l'analyse propose la partie de la fenêtre dans laquelle elles sont également cotées. Cette partie commence le lendemain de la dernière première cotation, à l'intérieur de la fenêtre, d'une position sans prix au début, de sorte que cette cotation devienne son prix de départ ; elle se termine à la plus ancienne des dernières cotations d'une position sans prix récent à la fin. Avant d'être proposée, une seconde lecture des cotations sur cette fenêtre plus courte la confirme : chaque position qu'elle ramène, et chaque position que la fenêtre couvrait déjà, doit être cotée aux deux extrémités, sinon rien n'est proposé. Une position exclue pour n'avoir aucun prix dans la fenêtre, ou aucun taux de change, n'en fait jamais partie : aucune fenêtre plus courte ne la ramènerait.

Sur ces onglets, la proposition est un bouton à l'intérieur de l'encadré qui liste ce qui a été exclu : il montre ses dates et combien de positions il ramène, et un clic le rejoue — y compris lorsque rien du tout n'a pu être rejoué sur la fenêtre d'origine. Lorsque le rejeu a porté sur l'une des crises prédéfinies — encore choisie dans le menu, aux dates propres à la crise — et que la proposition est plus courte, elle est marquée comme ne couvrant qu'une partie de la crise. C'est le compromis : vous récupérez les positions, mais vous rejouez un segment plus court que l'épisode, et tout ce que le marché a fait en dehors de ce segment ne figure plus dans la réponse. Choisir **Aucun préréglage**, une plage rapide ou une date de votre choix met la crise de côté : le rejeu suivant porte sur une période, et non plus sur la crise, et ne porte pas une telle marque.

### 🎭 Proxies {: #proxies }

Un proxy permet à la série de rendements d'un autre actif de remplacer une position dépourvue d'historique. Il n'existe qu'à un seul endroit : l'onglet **Risque & Scénarios** de la page de détail d'un actif, pour cet actif seul, où le lecteur peut lui choisir un proxy ou l'exclure à la place. Une position couverte par un proxy est rejouée sur les rendements de son proxy au lieu d'être exclue, et un proxy sans rendements utilisables sur la fenêtre est refusé comme un choix invalide, jamais discrètement écarté. Le rejeu sur les trois onglets ci-dessus n'offre ni proxy ni exclusion manuelle.

!!! warning "Un proxy est un choix, pas un fait"

    Remplacer une position par un proxy change ce que le résultat signifie. Il ne dit plus ce qui serait arrivé à cette position ; il dit ce qui serait arrivé **si cette position s'était comportée comme son substitut** sur cet épisode. Cette condition fait partie de la réponse, et non une note de bas de page — un indice large servant de proxy à une position concentrée sous-estimera comment cette position aurait évolué, et aucune partie de l'arithmétique ne peut détecter l'inadéquation. Le résultat enregistre quelles positions ont été couvertes par un proxy.

---

## 💡 Interprétation {: #interpretation }

Le rejeu produit un rendement composé pour l'épisode, et en dessous, un rendement pour chaque position qu'il a rejouée. Lisez-les comme un **énoncé conditionnel** : *cette composition, sur ces dates précises, sans rééquilibrage, avec des liquidités plates — et plates avec elles chaque position que le moteur a exclue — et un proxy uniquement là où il a été choisi*. Sur une sélection d'actifs, il n'y a pas de composition à capitaliser et rien n'est maintenu plat : les rendements par actif sont autonomes, pour les actifs qui ont pu être rejoués.

Sa force est que chaque chiffre qu'il contient s'est produit. La séquence des rendements est celle que le marché a délivrée — la trajectoire de repli, le regroupement des mauvais jours, la vitesse de la reprise sont tous réels, ce qu'un résumé distributionnel ne peut précisément pas reproduire. Sa faiblesse en est l'image inversée : c'est **un** épisode. Il s'est produit une fois, et le prochain stress ne sera pas une copie de celui-ci.

Un rejeu n'est donc ni une prévision ni une probabilité. C'est une mesure d'exposition à un événement connu — utile parce que l'événement est connu, et limitée pour la même raison.

---

## ⚠️ Limitations {: #limitations }

!!! warning "Un épisode est un échantillon"

    Rejouer un seul segment historique dit ce que ce segment produirait. Cela ne borne pas ce qu'un futur segment pourrait produire, et choisir le pire épisode du registre ne fait pas du résultat un pire cas — cela en fait le pire cas *du registre*.

!!! warning "La composition est figée à celle d'aujourd'hui"

    Les positions ouvertes après l'épisode, les positions depuis clôturées, et toute variation de taille entre-temps sont absentes par construction. Plus la plage de rejeu est éloignée d'aujourd'hui, plus le portefeuille rejoué est une construction plutôt qu'un historique.

!!! warning "Les rendements sont pris tels qu'ils sont mesurés"

    Le rejeu prépare ses séries de rendements comme le reste de l'analyse, mais sur la fenêtre de son épisode et pour les actifs qu'il rejoue, chaque proxy à la place de la position qu'il représente. Ces séries partagent un calendrier, construit comme décrit sous [Qualité des données](data-quality.md#alignment-what-missing-data-actually-costs) : chaque date de la fenêtre à laquelle au moins un de ces actifs a une cotation propre, conservée partout où chacun d'eux peut être valorisé, au besoin à un prix reporté d'une date antérieure. Les lacunes, les prix reportés et la conversion de devise atteignent tous le rejeu par ces séries. Voir [Qualité des données](data-quality.md) pour ce que l'analyse rapporte sur les séries qu'elle a utilisées.

---

## 🔗 Connexes {: #related }

- ⚡ **[Choc hypothétique](hypothetical-shock.md)** — la même question avec un scénario choisi au lieu d'un scénario historique
- 📉 **[Perte maximale](max-drawdown.md)** — la pire baisse le long d'une trajectoire, et [combien de temps a pris la reprise](max-drawdown.md#recovery-time)
- 📍 **[Repli actuel](current-drawdown.md)** — où en est le portefeuille aujourd'hui, avant d'appliquer un quelconque scénario
- 🧩 **[Contribution au risque](risk-contribution.md)** — quelles positions portent le risque sur lequel un épisode agirait
- 🧪 **[Qualité des données](data-quality.md)** — les séries sur lesquelles le rejeu a été exécuté
