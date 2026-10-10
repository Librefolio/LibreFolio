# 🧪 Qualité des données

Un chiffre de risque n'est digne de confiance qu'à la mesure des observations qui le sous-tendent ; la quantité et la fraîcheur des données sous-jacentes font donc partie intégrante de la lecture du résultat. LibreFolio ne garde pas cette couche cachée : chaque résultat de risque s'accompagne d'un rapport sur les données sources, d'un statut qui en découle et — lorsqu'il manquait quelque chose — de la liste de ce qui manquait.

---

## 🚦 Statut des données sources {: #source-data-status }

Les données sources sont classées en trois niveaux :

| Statut | Signification |
|---|---|
| `ok` | Rien ne manque, et rien n'a été reporté au-delà du [seuil d'obsolescence](#staleness-threshold). La série est ce qu'elle prétend être. |
| `carried_forward` | Rien ne manque franchement, mais certains prix ou taux de change ont été reportés d'une date antérieure au-delà du seuil d'obsolescence — cotations obsolètes, points de prix reportés, points FX reportés. |
| `partial` | Quelque chose manque franchement : des prix, des paires FX, des dates à l'intérieur de la fenêtre analysée pour lesquelles tous les actifs n'ont pas pu être valorisés, des paires FX non résolues, ou des actifs qui n'ont pas pu participer du tout. |

Deux propriétés de cette échelle importent davantage que les étiquettes.

**Elle est dérivée, non déclarée.** Le statut est une propriété calculée à partir du contenu même du rapport : un producteur ne peut pas prétendre à `ok` tout en signalant des prix manquants, car le statut est recalculé à partir de ce que contient le rapport. Tout ce qui manque franchement donne `partial` ; si rien ne manque mais que quelque chose a été reporté au-delà du seuil d'obsolescence, `carried_forward` ; sinon `ok`. `partial` prévaut sur `carried_forward`.

**Elle est catégorielle, non numérique.** Le statut répond à la question *quel type d'imperfection est présente*, jamais *combien est tolérable*. Il n'existe aucun niveau de complétude en dessous duquel le système déclare un chiffre non fiable — ce jugement est laissé au lecteur, délibérément et explicitement.

### ⏳ Le seuil d'obsolescence {: #staleness-threshold }

Un prix ou un taux de change reporté d'une date antérieure est chose ordinaire en soi : les week-ends, les jours fériés et les instruments cotés selon leur propre calendrier de marché laissent constamment des lacunes — et un prix stocké un week-end ou un jour férié de marché qui ne fait que répéter la clôture précédente est lui aussi reporté, non coté (voir [Reports stockés](#stored-carries)). Une valeur reportée ne devient **obsolète** qu'une fois qu'elle a plus de **sept jours calendaires** de retard sur la date qu'elle représente, et seule une valeur obsolète compte à l'encontre de la série par actif d'une analyse : elle est enregistrée comme un point de prix ou FX reporté, et un seul suffit pour `carried_forward`. Une valeur plus récente ne dégrade rien, mais elle n'est pas invisible : un prix reporté donne toujours un rendement de période nul, et ce rendement entre dans l'échantillon (voir [Limites](#limitations)). Le seuil décide de ce qui compte comme une imperfection, non du nombre d'imperfections tolérables.

Sept jours calendaires est l'unique seuil d'obsolescence du projet, non une convention de cette page : le [laboratoire de corrélation](../../../user/assets/correlation.md) de la page Actifs et le rejeu historique jugent l'âge d'un prix selon ces mêmes sept jours, et les avertissements qui signalent des prix ou des taux de change obsolètes le citent.

### 🔁 Reports stockés {: #stored-carries }

Tous les prix reportés n'arrivent pas sous forme de lacune. Certaines sources livrent une ligne pour chaque jour calendaire, en répétant la dernière clôture les jours où leur marché est fermé : justETF, par exemple, répète la clôture du vendredi le samedi et le dimanche. Lus comme des cotations, ces lignes introduiraient dans chaque série construite à partir d'elles un rendement nul, dans la devise propre de l'actif, qu'aucun marché n'a produit. Ainsi un prix stocké est-il un **report**, et non une cotation, lorsque ces deux conditions sont réunies :

- il est daté d'un samedi ou d'un dimanche, ou d'un jour de semaine férié sur au moins l'une des principales places — l'union des calendriers que fournit QuantLib pour TARGET, Borsa Italiana, Xetra, Euronext Paris, London Stock Exchange, Switzerland et le NYSE ;
- sa clôture, dans la devise propre de l'actif, est **exactement** celle de la ligne précédente, sans tolérance.

Trois types de lignes restent des cotations : le premier prix d'une série, qui n'a pas de ligne précédente ; un prix inchangé un jour de semaine ordinaire, car une journée plate d'une obligation ou d'un fonds monétaire est réelle ; et un prix qui a bougé un week-end ou un jour férié, comme celui d'un crypto-actif. L'union des places est sûre parce que la règle exige aussi la répétition exacte : un instrument qui a coté pendant qu'une autre place était fermée a presque toujours bougé, et un prix qui a bougé reste une cotation — au pire, une journée réellement plate à une telle date est lue comme un report. La table des jours fériés est construite au démarrage du serveur ; si elle n'a pas pu être construite, seuls les week-ends s'appliquent jusqu'à ce qu'une tentative ultérieure réussisse.

Un report est la dernière cotation authentique reportée, et il est daté de cette cotation ; sur un week-end ordinaire, il a donc un ou deux jours — bien à l'intérieur du seuil d'obsolescence. Sa date n'est pas une date de cotation de l'actif. Il n'ajoute aucun candidat au [calendrier partagé](#alignment-what-missing-data-actually-costs), aucun jour d'observation à la série de rendements d'un portefeuille (voir [Couverture](#coverage)), et rien aux cotations qui décident si un actif peut participer à une analyse d'un ensemble d'actifs — au moins 20 sur la période, le minimum que les analyses statistiques acceptent — ou à un [rejeu historique](historical-replay.md), qui exige que l'actif soit valorisé aux deux extrémités de sa fenêtre. Là où la cotation d'un autre actif inscrit malgré tout la date sur un calendrier partagé, l'actif y est valorisé à sa dernière cotation authentique, et ce point compte comme reporté dans la mesure de fraîcheur décrite sous [Couverture](#coverage).

---

## 📋 Ce que le rapport consigne {: #what-the-report-records }

Le rapport est un inventaire, non un score :

| Signal | Ce qu'il saisit |
|---|---|
| Actifs à prix manquant | Positions pour lesquelles aucun prix utilisable n'a pu être obtenu |
| Paires FX manquantes / non résolues | Conversions de devise qui n'ont pas pu être résolues |
| Prix obsolètes | Positions dont le dernier prix est plus ancien que le [seuil d'obsolescence](#staleness-threshold) |
| Points de prix reportés | Combien de points de prix ont été reportés au-delà du seuil d'obsolescence, et pour quels actifs |
| Points FX reportés | Combien de points de conversion ont été reportés au-delà du seuil d'obsolescence, et pour quelles paires |
| Dates incomplètes | Dates auxquelles la valorisation, la NAV, la valeur comptable ou l'allocation n'ont pas pu être complétées pour chaque position |
| Actifs inutilisables | Actifs exclus avant toute tentative de calcul, chacun avec une raison |
| Avertissements | Notes libres attachées par l'étape de production |

Chaque entrée nomme l'objet qu'elle concerne — l'actif, la paire FX, la date. Un lecteur peut demander *quel* actif, quelle paire FX ou quelle date a dégradé le chiffre, et non seulement *si* quelque chose l'a fait.

---

## 🧮 Alignement : ce que coûtent réellement les données manquantes {: #alignment-what-missing-data-actually-costs }

Lorsqu'une analyse couvre plusieurs positions — une matrice de corrélation, une décomposition de contribution au risque —, elle est calculée sur un **calendrier partagé unique**, et c'est dans la construction de ce calendrier que les données manquantes se traduisent par un coût visible.

1. Une date est candidate si au moins une position y avait une cotation fraîche, un [report stocké](#stored-carries) ne comptant pas comme telle : les candidates sont l'union des calendriers de cotation des positions sur la fenêtre demandée.
2. Une date candidate n'entre dans l'analyse que si **chaque** position a pu y être valorisée. Ici, *valorisée* inclut un prix ou un taux de change reporté d'une date antérieure, sans limite d'âge ; en pratique, le test n'échoue donc qu'avant le premier prix utilisable d'une position, ou lorsque sa conversion dans la devise cible n'a pas pu être résolue. Les dates qui échouent à ce test sont écartées pour toutes les positions, mais elles ne sont enregistrées comme dates de valorisation incomplètes qu'une fois le calendrier amorcé — c'est-à-dire après la ligne de base.
3. La ligne de base est la dernière date avant le début demandé à laquelle toutes les positions étaient valorisables ; s'il n'y en a aucune, l'analyse commence à l'intérieur de la fenêtre demandée, à la première date à laquelle chaque position peut être valorisée, et les positions responsables de ce départ tardif sont nommées.

La conséquence mérite d'être énoncée clairement : **une position qui commence en retard raccourcit la fenêtre pour tout le monde**. Une lacune à l'intérieur d'un historique ne raccourcit rien, car le prix ou le taux de change manquant est reporté. Rien n'est interpolé : un prix ou un taux reporté est le dernier connu. Une fois qu'il a été reporté au-delà du [seuil d'obsolescence](#staleness-threshold), il est compté comme un point reporté — une affaire relevant du statut `carried_forward`, non de la longueur de la fenêtre. Une valeur plus récente ne dégrade pas le statut, bien qu'un prix reporté, quel que soit son âge, compte toujours à l'encontre de la mesure de fraîcheur décrite sous [Couverture](#coverage). Une position n'est jamais partiellement incluse dans un calcul conjoint — soit la date convient à toutes, soit ce n'est pas une observation. Un départ tardif seul ne rend pas le résultat `partial` : les dates qu'il coûte ne sont pas listées comme incomplètes, le rapport nomme les positions responsables dans ses entrées `short_history`, et la perte se reflète dans le nombre d'observations et dans la couverture du calendrier partagé ci-dessous. Une date perdue après l'amorçage du calendrier est différente : elle est listée comme incomplète, et elle rend le résultat `partial`.

---

## 📏 Couverture {: #coverage }

La couverture est normalement le compagnon de densité du statut : elle répond à la question *quelle part de ce qui aurait pu être observé l'a réellement été*. Plusieurs ratios différents portent ce nom. Ils ne partagent aucun dénominateur, et ils ne mesurent pas tous le même type de chose : deux comptent des observations, un troisième compte des positions et ne contient aucune observation.

**Combien le calendrier partagé a-t-il coûté ?** Parmi les dates auxquelles au moins une position avait une cotation fraîche, c'est la part qui a survécu à l'exigence que chaque position soit valorisable. Un chiffre nettement inférieur à 1 signifie que, sur nombre des dates où une position était cotée, une autre n'a pas pu être valorisée — et comme les lacunes sont reportées, cela pointe en général vers une position dont l'historique débute bien après le début demandé, ou vers des conversions qui n'ont pas pu être résolues, plutôt que vers des lacunes.

**Quelle part des données est réellement fraîche ?** Sur la grille positions × observations, c'est la part des points dont le prix a été coté à cette date plutôt que reporté d'une date antérieure. Elle mesure le même type d'imperfection que le statut `carried_forward`, mais sur les seules observations et avec un critère plus strict : tout prix reporté compte à son encontre, aussi récent soit-il, tandis que le statut ne compte que ceux reportés au-delà du seuil d'obsolescence. Elle ne compte aussi que les prix : une cotation fraîche mais qui a dû être convertie avec un taux de change reporté reste comptée comme fraîche, car les conversions reportées sont suivies comme un signal distinct à part entière. Une part inférieure à 100 % ne signifie donc pas en soi `carried_forward`, et une part de 100 % n'exclut pas en soi ce statut — ni, par conséquent, un résultat `partial`.

**Quelle part du portefeuille a pu être classée ?** Parmi les positions du périmètre, c'est la part dont les métadonnées de secteur ou de géographie étaient disponibles, plutôt que manquantes et reléguant la position dans le compartiment fourre-tout `Other` à 100 %. Celle-ci est un constat sur les métadonnées : aucun prix, aucune date et aucune observation n'y entre. Un [choc hypothétique](hypothetical-shock.md) rapporte ce ratio.

!!! warning "Un nom partagé, deux types de grandeur"

    Lorsque le chiffre est une mesure de densité, son dénominateur dépend du chemin. Pour une analyse construite à partir de cotations d'instruments, ce sont les dates de cotation candidates. Pour une série de portefeuille, ce sont les **jours d'observation** du portefeuille : l'analyse lit la série de rendements propre au portefeuille, son [rendement pondéré par le temps](../performance-metrics/portfolio-engine/twrr.md), uniquement les jours où au moins une position du périmètre avait une cotation qui lui était propre, et enchaîne le rendement de chaque autre jour dans le suivant ; le dénominateur compte ces jours sur toute l'étendue — ou chaque jour calendaire couvert, si aucune position n'avait de cotation qui lui soit propre dans la fenêtre. Sur une série de portefeuille, ce chiffre est élevé par construction — l'historique du portefeuille possède un point pour chaque jour calendaire, reportant la dernière valeur connue là où rien n'était coté, de sorte que chaque jour d'observation en a un — et il ne certifie donc rien quant aux prix qui le sous-tendent. Sur une grille d'instruments, un chiffre plus bas indique des dates que le calendrier partagé a réellement perdues — un départ tardif, ou une conversion qui n'a pas pu être résolue — jamais un marché fermé : une date à laquelle rien n'a été coté, ou à laquelle les seuls prix stockés étaient des reports, n'est pas candidate, et à une date où seules certaines positions étaient cotées, les autres sont reportées et toujours valorisées, de sorte que la fermeture apparaît plutôt dans la mesure de fraîcheur.

    La question *ces prix ont-ils été cotés, ou reportés ?* a bien une réponse dans le système, mais c'est la mesure de fraîcheur ci-dessus, non celle qu'un résultat porte sous le nom de *couverture*. Quelle mesure parvient à tel ou tel écran dépasse ce que décrit cette page.

    Un seul discriminant permet de trancher sans aucune connaissance des rouages internes. **Lorsqu'un résultat rapporte `n_observations = 0` et `calendar_days = 0` à côté d'une couverture non nulle, cette couverture n'est pas un constat sur la densité des données.** Elle ne peut pas l'être : rien n'a été observé. Elle indique quelle part du portefeuille a été classée.

    La distinction change ce qu'il convient de faire du chiffre. Une couverture de 80 %, lue selon les deux premières acceptions, dit *un cinquième des prix manque*. Sur un ratio de classification, elle dit qu'un cinquième des étiquettes de secteur ou de géographie manque. L'un est une lacune dans les données de marché, l'autre une lacune dans les métadonnées d'actif, et les deux appellent des actions totalement différentes. Voir [Annualisation observée](observed-annualization.md) pour la manière dont l'étendue et le nombre d'observations produisent aussi le facteur d'annualisation.

---

## 🚫 Exclusions {: #exclusions }

Un actif peut quitter l'analyse à deux moments différents, et la distinction est consignée.

**Avant toute tentative de calcul**, lorsque ses données sources ne peuvent en soutenir aucun : pas de prix utilisable, pas de conversion de devise utilisable, devise invalide. Ceux-ci sont signalés comme actifs inutilisables, chacun avec sa raison.

**Lors de la résolution du périmètre**, si l'actif n'a aucune série de rendements préparée utilisable. Le périmètre demandé est alors réduit aux actifs qui subsistent, chaque exclusion conserve sa raison, et un avertissement par raison nomme précisément les actifs écartés.

Dans aucun des deux cas l'analyse ne refuse de s'exécuter : elle s'exécute sur ce qui reste et le signale. Un actif exclu est un changement dans *ce qui a été mesuré*, ce qui explique pourquoi il fait sortir de l'état propre tout résultat dont il a changé la mesure — et seulement ceux-là.

### 🎯 Quels résultats portent une exclusion {: #which-results-carry-an-exclusion }

Une exclusion est un trou dans la série par actif du périmètre : la série de rendements de chaque position, alignée sur le [calendrier partagé](#alignment-what-missing-data-actually-costs). Tout résultat construit à partir de ces séries en hérite — l'actif est listé comme exclu, l'avertissement qui le nomme accompagne le résultat, et le résultat est `partial`. Cela couvre la corrélation, la contribution au risque, le risque/rendement et la simulation ; les KPI, la valeur à risque et la comparaison rejoués sur la composition actuelle, c'est-à-dire les poids du jour appliqués à ces séries ; les analyses d'un ensemble d'actifs choisis directement ; et les analyses d'une *tranche* d'un portefeuille, une sélection de ses positions. Une tranche ne peut pas être découpée dans l'historique propre du portefeuille, de sorte que même en mode historique elle est rejouée à partir des séries des positions sélectionnées.

L'exception est le mode historique d'un portefeuille dans son ensemble — tous ses courtiers ou une sélection de ceux-ci, mais non une tranche de ses positions. Là, quatre analyses lisent l'historique de rendements propre au portefeuille, son [rendement pondéré par le temps](../performance-metrics/portfolio-engine/twrr.md) (TWRR), sur ses [jours d'observation](#coverage), au lieu des séries par actif : les KPI (volatilité, Sharpe, Sortino, …), la [Valeur à risque](value-at-risk.md) et la [VaR conditionnelle](conditional-value-at-risk.md) historiques, le repli, et la comparaison à un indice de référence, qui n'ajoute que la série propre de l'indice de référence. Cet historique valorise déjà chaque position — une position sans cotation de marché au prix de sa dernière transaction — de sorte qu'un actif manquant dans la série par actif ne leur coûte rien en valeur : au plus, les jours où seul cet actif était coté cessent d'être des jours d'observation, et leurs rendements sont enchaînés dans le suivant. Ils n'héritent ni de l'exclusion ni de l'avertissement qui la nomme, ni de l'avertissement selon lequel la part de la composition actuelle comptée à rendement nul inclut de la valeur en transit, un constat sur une composition qu'ils n'utilisent jamais. La même requête rapporte toujours l'exclusion sur chaque résultat qui lit les séries par actif. Ce qui peut encore rendre ces quatre `partial`, ce sont les données derrière l'historique du portefeuille lui-même, et pour la comparaison la préparation de son indice de référence — voir [Interprétation](#interpretation).

Les tests de stress appliquent leurs propres règles. Un [rejeu historique](historical-replay.md) prépare ses propres séries sur la fenêtre de son épisode, et laisse de côté — pour ses propres raisons, nommées dans ses propres avertissements — les actifs qu'elle ne peut pas valoriser aux deux extrémités de cette fenêtre. Un [choc hypothétique](hypothetical-shock.md) ne lit aucune série de rendements : il applique ses chocs à chaque position par le biais de la classification de la position, de sorte qu'une exclusion de la série par actif ne lui coûte rien, et il n'hérite ni de l'exclusion ni de son avertissement.

### 🏷️ Raisons d'exclusion {: #exclusion-reasons }

Chaque actif exclu porte une raison, et chaque raison a sa propre phrase dans l'avertissement :

| Raison | Pourquoi l'actif a été laissé de côté |
|---|---|
| `no_price_source` | Aucune source de prix ne lui est assignée et aucun prix n'a jamais été enregistré pour lui. Rien n'est mis en place pour le valoriser, ce qui en fait un état permanent plutôt qu'une lacune dans les données — typiquement un investissement privé, tel qu'un prêt de crowdfunding, qu'aucun marché ne cote. |
| `missing_price` | Il a une source de prix, ou des prix enregistrés, mais aucun prix utilisable pour la période : la source n'a rien renvoyé pour lui, ou tous les prix enregistrés tombent après la période. |
| `missing_fx` | Ses prix n'ont pas pu être convertis dans la devise cible. |
| `invalid_currency` | Ses prix ne portent aucune devise valide. |
| `insufficient_history` | L'historique dans la période est insuffisant pour lui donner une série de rendements utilisable. |

Les prix enregistrés uniquement *avant* la période ne causent jamais d'exclusion : le dernier d'entre eux est reporté dans la période, comme décrit sous [Alignement](#alignment-what-missing-data-actually-costs). Seul le résultat distingue les deux premières raisons : dans son rapport sur les données sources, un actif que rien ne valorise reste listé parmi les actifs inutilisables comme `missing_price`.

### ⚖️ Le poids exclu {: #excluded-weight }

Les analyses de la composition actuelle qui indiquent des poids — contribution au risque et risque/rendement — gardent une position exclue à son poids et la comptent à rendement nul : les chiffres qu'elles calculent sont exactement ceux que donnerait le même argent détenu en liquidités. Le résultat nomme cette part séparément. `excluded_weight` est la somme des poids des positions du périmètre laissées sans série, et elle est indiquée à côté de `cash_weight`, le résidu à rendement nul : la part de la valeur du périmètre détenue en dehors des positions qui ont une série — liquidités, toute valeur en transit et les positions exclues. Dans chaque résultat que produisent ces deux analyses, le poids exclu fait partie de ce résidu. Les deux ne pourraient ne pas s'imbriquer que si les positions valaient plus que la valeur nette — un solde de trésorerie négatif non compensé par de la valeur en transit — et dans ce cas aucune des deux analyses ne produit de résultat : il revient `unavailable`. Les sélections sans poids, telles qu'un ensemble d'actifs choisis directement, ne portent ni l'un ni l'autre.

---

## 💡 Interprétation {: #interpretation }

Chaque résultat analytique porte un statut qui lui est propre, distinct de celui des données sources :

| Statut du résultat | Signification |
|---|---|
| `ok` | Calculé sans rien de manquant ni d'obsolète dans ses données sources, rien d'exclu de ce qu'il lit et aucun avertissement dégradant |
| `partial` | Calculé, mais avec des données sources manquantes ou obsolètes, quelque chose d'exclu de ce qu'il lit, ou un avertissement dégradant |
| `unavailable` | Non calculé ; un code de raison stable explique pourquoi (historique insuffisant, données indisponibles, paramètres invalides, un calcul trop volumineux pour être exécuté, périmètre ou mode incompatible, …) |
| `failed` | Le calcul s'est interrompu sur une erreur que l'analyse ne déclare pas — une défaillance du calcul, jamais un verdict sur les données. Il porte le code `execution_failed` (*Le calcul backend a échoué.*), le serveur le journalise, et l'écran affiche **Calculation failed** |

Un échec n'est pas une valeur indéfinie. Une métrique qui n'a véritablement pas de valeur pour des données bien formées — la corrélation d'une série qui n'a jamais bougé, un ratio de Sharpe sur une volatilité nulle — n'échoue pas : cette valeur revient vide, signalée `undefined` dans une cellule de corrélation ou expliquée par un avertissement tel que `sharpe_undefined`, et le reste du résultat demeure utilisable. À l'inverse, une erreur que l'analyse n'a pas anticipée n'est jamais rapportée comme une métrique indéfinie : cela transformerait une défaillance du calcul en un constat sur vos données.

Un résultat est `partial` lorsque **l'une** des conditions suivantes est remplie : un avertissement qui dégrade le résultat est présent ; un actif du périmètre que le résultat lit a été [exclu](#which-results-carry-an-exclusion) ; l'analyse elle-même a exclu quelque chose ; ou le statut du rapport sur les données sources sur lequel le résultat est jugé est autre que `ok`. Dans ce dernier cas, un avertissement explicite est également attaché, de sorte que la dégradation n'est jamais déduite du seul statut.

Ce rapport est celui de la série que le résultat a consommée :

- un résultat construit à partir des séries par actif du périmètre — y compris les KPI, les chiffres de valeur à risque, le repli et la comparaison lorsqu'ils sont rejoués à partir de ces séries, sur la composition actuelle ou sur une tranche — est jugé sur le rapport de leur préparation, fusionné, lorsque le périmètre est un portefeuille, avec le rapport propre du portefeuille ;
- sur le TWRR d'un portefeuille, les KPI, les chiffres de valeur à risque et le repli sont jugés sur le rapport sur les données sources propre au portefeuille : si l'historique du portefeuille lui-même est incomplet — une position qui n'a pas pu être valorisée, un taux de change manquant, un jour où la valeur nette n'a pas pu être valorisée intégralement —, ils restent `partial`, avec l'avertissement. Ce rapport suit ce qui n'a pas pu être valorisé, non l'ancienneté d'une valorisation, de sorte qu'un prix reporté au-delà du seuil d'obsolescence à l'intérieur de l'historique du portefeuille ne les dégrade pas ;
- la comparaison à un indice de référence sur le TWRR est jugée sur le rapport du portefeuille plus la préparation de son indice de référence, qui est alignée sur le calendrier partagé du périmètre : un prix ou un taux de change sur ce calendrier reporté au-delà du [seuil d'obsolescence](#staleness-threshold) — celui de l'indice de référence ou d'une position —, ou une date perdue du calendrier, la rend encore `partial` ; les positions exclues du périmètre n'ont jamais intégré ce calendrier, de sorte que leur exclusion ne la rend pas `partial`.

!!! info "Comment lire un résultat partial"

    `partial` ne signifie pas *faux*. Cela signifie que le chiffre porte une imperfection connue : il peut reposer sur des prix ou des taux de change reportés au-delà du seuil d'obsolescence — même fenêtre, mêmes positions —, ou répondre à une question légèrement différente de celle posée, sur un calendrier aux dates incomplètes ou sur un nombre réduit de positions. Le chiffre et la raison voyagent ensemble dans la même charge utile, et ils sont faits pour être lus ensemble : une contribution au risque calculée avec deux positions exclues décrit un portefeuille dans lequel ces deux sont restées immobiles, comme des liquidités — non le portefeuille tel qu'il est.

Les analyses refusent aussi de répondre plutôt que de mal répondre. Chacune déclare le nombre minimal d'observations dont elle a besoin, et en dessous de ce plancher elle n'est pas calculée du tout : le résultat revient `unavailable` avec une raison `insufficient_history` portant à la fois les observations disponibles et le nombre requis. La contribution au risque et la comparaison à un indice de référence, par exemple, nécessitent toutes deux au moins 20. Les chiffres de valeur à risque comptent leurs fenêtres composées selon l'horizon plutôt que leurs rendements, de sorte qu'un horizon plus long nécessite une fenêtre plus longue — voir [Valeur à risque](value-at-risk.md#the-observation-count-is-not-the-history-length). La [Corrélation](correlation.md#how-each-cell-is-computed) est une exception : elle n'est jamais refusée pour un historique court. Son plancher — un paramètre ajustable de l'analyse, 20 observations par défaut — s'applique à la matrice dans son ensemble : chaque série partage un même calendrier, donc chaque paire a le même nombre d'observations, et sous le plancher chaque cellule revient `insufficient` sans coefficient, dans un résultat marqué `partial` plutôt que `unavailable`.

---

## ⚠️ Limites {: #limitations }

!!! warning "Un statut décrit les entrées, non le modèle"

    `ok` dit que la série était complète, non que la métrique est appropriée, que la fenêtre est suffisamment longue, ou que le passé ressemble à l'avenir. Toutes les mises en garde des pages de métriques s'appliquent encore à un chiffre construit sur des données impeccables.

!!! warning "Les données reportées flattent un chiffre de risque"

    Un prix reporté d'une date antérieure produit un rendement de période exactement nul dans la devise propre de l'instrument ; après conversion dans la devise cible, seul le taux de change le fait bouger. Tout prix reporté fait cela, aussi récent soit-il, et ces rendements entrent dans l'échantillon comme toute autre observation. À l'intérieur du [seuil d'obsolescence](#staleness-threshold), c'est ordinaire : sur un week-end, un jour férié ou un jour où un seul autre marché a coté, l'instrument n'a pas eu de nouvelle cotation, et sa cotation suivante rattrape. Un prix reporté plus longtemps représente des jours où l'instrument a fort bien pu bouger, de sorte qu'une série riche en tels points rapporte **moins** de mouvement que l'instrument n'en a réellement connu. Ce sont ces points que compte le statut `carried_forward`, et ce statut est l'avertissement qu'un chiffre d'apparence calme peut l'être pour la mauvaise raison.

!!! warning "Une position valorisée d'après ses transactions reste immobile"

    Sur le TWRR d'un portefeuille, une position qu'aucun marché ne valorise est valorisée [au prix de sa dernière transaction](../performance-metrics/portfolio-engine/price-resolution.md), de sorte que, dans sa propre devise, elle reste immobile d'une transaction à la suivante. Pour un prêt détenu à sa valeur nominale — un investissement de crowdfunding typique —, c'est la vérité. Pour une position dont la valeur bouge réellement, cela aplatit chaque chiffre lu sur le TWRR, tout comme le fait un prix reporté. Aucun statut ne le signale : le rapport du portefeuille ne compte pas une valorisation issue de transactions à l'encontre de son statut, et pour une position sans source de prix il traite cette valorisation comme l'état voulu, permanent.

!!! warning "Aucun seuil de qualité n'écarte un chiffre"

    Hormis les nombres minimaux d'observations décrits ci-dessus, en dessous desquels une analyse n'est pas calculée du tout ou chaque cellule de corrélation revient `insufficient`, rien dans le système ne déclare un niveau de couverture ou une part reportée au-delà duquel un chiffre doit être écarté. Cette absence est délibérée — le chiffre honnête est celui qui vient avec sa propre provenance —, mais elle signifie que le jugement final vous appartient, et qu'il ne peut pas être délégué à l'étiquette de statut.

---

## 🔗 Voir aussi {: #related }

- 📅 **[Annualisation observée](observed-annualization.md)** — le facteur d'annualisation compté à partir des mêmes observations, et pourquoi une série clairsemée n'est pas nécessairement une série cassée
- 🔗 **[Corrélation](correlation.md)** — rapporte le nombre d'observations derrière chaque cellule individuelle
- 📊 **[Volatilité](volatility.md)** — le chiffre le plus directement aplati par les prix reportés
