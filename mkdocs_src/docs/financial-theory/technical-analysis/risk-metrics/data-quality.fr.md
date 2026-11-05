# 🧪 Qualité des données

Un chiffre de risque n’est digne de confiance qu’à la mesure des observations qui le sous-tendent ; la quantité et la fraîcheur des données sous-jacentes font donc partie de la lecture du résultat. LibreFolio ne cache pas cette couche : chaque résultat de risque est accompagné d’un rapport sur les données sources, d’un statut qui en découle et — lorsqu’il manquait quelque chose — de la liste de ce qui manquait.

---

## 🚦 Statut des données sources {: #source-data-status }

Les données sources sont classées sur trois niveaux :

| Statut | Ce que cela signifie |
|---|---|
| `ok` | Rien ne manque, et rien n’est reporté au-delà du [seuil d’obsolescence](#staleness-threshold). La série est bien ce qu’elle prétend être. |
| `carried_forward` | Rien ne manque à proprement parler, mais certains prix ou taux de change ont été reportés depuis une date antérieure au-delà du seuil d’obsolescence — cotations obsolètes, points de prix reportés, points FX reportés. |
| `partial` | Quelque chose manque à proprement parler : prix, paires FX, dates dans la fenêtre analysée pour lesquelles certaines positions n’ont pas pu être valorisées, paires de devises non résolues, ou actifs qui n’ont pas pu participer du tout. |

Deux propriétés de cette échelle importent davantage que les libellés.

**Il est déduit, non déclaré.** Le statut est une propriété calculée à partir du contenu même du rapport : un producteur ne peut pas revendiquer `ok` tout en signalant des prix manquants, car le statut est recalculé à partir de ce que contient le rapport. Tout ce qui manque à proprement parler donne `partial` ; si rien ne manque mais que quelque chose a été reporté au-delà du seuil d’obsolescence, `carried_forward` ; sinon `ok`. `partial` prime sur `carried_forward`.

**Il est catégoriel, non numérique.** Le statut répond à *quel type d’imperfection est présent*, jamais à *quelle quantité est tolérable*. Il n’existe aucun niveau de complétude en dessous duquel le système déclare un chiffre non fiable — ce jugement est laissé au lecteur, délibérément et explicitement.

### ⏳ Le seuil d’obsolescence {: #staleness-threshold }

Un prix ou un taux de change reporté depuis une date antérieure est ordinaire en soi : les week-ends, les jours fériés et les instruments cotés selon leurs propres calendriers de marché laissent constamment des lacunes — et un prix stocké un week-end ou un jour férié de marché qui ne fait que répéter la clôture précédente est lui aussi reporté, et non coté (voir [Reports stockés](#stored-carries)). Une valeur reportée ne devient **obsolète** qu’une fois que son ancienneté par rapport à la date qu’elle représente dépasse **sept jours calendaires**, et seule une valeur obsolète est comptée au débit de la série par actif d’une analyse : elle est enregistrée comme point de prix ou de FX reporté, et un seul suffit pour `carried_forward`. Une valeur plus récente ne dégrade rien, mais elle n’est pas invisible : un prix reporté produit toujours un rendement de période nul, et ce rendement entre dans l’échantillon (voir [Limites](#limitations)). Le seuil détermine ce qui compte comme une imperfection, non combien d’imperfections sont tolérables.

Sept jours calendaires constituent l’unique seuil d’obsolescence du projet, et non une convention propre à cette page : le [laboratoire de corrélation](../../../user/assets/correlation.md) de la page Actifs et le rejeu historique jugent l’âge d’un prix selon ces mêmes sept jours, et les avertissements qui signalent des prix ou des taux de change obsolètes le citent.

### 🔁 Reports stockés {: #stored-carries }

Certains prix reportés ne se présentent pas sous forme de lacune. Certaines sources fournissent une ligne pour chaque jour calendaire, en répétant la dernière clôture les jours où leur marché est fermé : justETF, par exemple, répète la clôture du vendredi le samedi et le dimanche. Lues comme des cotations, ces lignes introduiraient dans chaque série construite à partir d’elles un rendement nul, dans la devise propre à l’actif, qu’aucun marché n’a produit. Ainsi, un prix stocké est un **report**, et non une cotation, lorsque les deux conditions suivantes sont réunies :

- il est daté d’un samedi ou d’un dimanche, ou d’un jour de semaine qui est férié sur au moins l’une des principales places boursières — l’union des calendriers que QuantLib fournit pour TARGET, Borsa Italiana, Xetra, Euronext Paris, la London Stock Exchange, la Suisse et le NYSE ;
- sa clôture, dans la devise propre à l’actif, est **exactement** la clôture de la ligne précédente, sans tolérance.

Trois types de ligne restent des cotations : le premier prix d’une série, qui n’a pas de ligne précédente ; un prix inchangé un jour de semaine ordinaire, car une journée plate pour une obligation ou un fonds monétaire est réelle ; et un prix qui a bougé un week-end ou un jour férié, comme celui d’un crypto-actif. L’union des places boursières est sûre parce que la règle exige aussi la répétition exacte : un instrument qui s’est négocié pendant qu’une autre place était fermée a presque toujours bougé, et un prix qui a bougé reste une cotation — au pire, une journée réellement plate à une telle date est lue comme un report. La table des jours fériés est construite au démarrage du serveur ; si elle n’a pas pu l’être, seuls les week-ends s’appliquent jusqu’à ce qu’une tentative ultérieure réussisse.

Un report est la dernière cotation authentique reportée, et il est daté à partir de cette cotation ; sur un week-end ordinaire, il a donc un ou deux jours d’ancienneté — bien en deçà du seuil d’obsolescence. Sa date n’est pas une date de cotation de l’actif. Il n’ajoute aucun candidat au [calendrier partagé](#alignment-what-missing-data-actually-costs), aucun jour d’observation à la série de rendements d’un portefeuille (voir [Couverture](#coverage)) et rien aux cotations qui décident si un actif peut participer à une analyse d’un ensemble d’actifs — au moins 20 sur la période, le minimum accepté par les analyses statistiques — ou à un [rejeu historique](historical-replay.md), qui exige que l’actif soit valorisé aux deux extrémités de sa fenêtre. Lorsque la cotation d’un autre actif fait malgré tout figurer la date sur un calendrier partagé, l’actif y est valorisé à sa dernière cotation authentique, et ce point compte comme reporté dans la mesure de fraîcheur décrite sous [Couverture](#coverage).

---

## 📋 Ce que le rapport enregistre {: #what-the-report-records }

Le rapport est un inventaire, pas un score :

| Signal | Ce qu’il capte |
|---|---|
| Actifs à prix manquant | Positions pour lesquelles aucun prix exploitable n’a pu être obtenu |
| Paires FX manquantes / non résolues | Conversions de devises qui n’ont pas pu être résolues |
| Prix obsolètes | Positions dont le dernier prix est plus ancien que le [seuil d’obsolescence](#staleness-threshold) |
| Points de prix reportés | Combien de points de prix ont été reportés au-delà du seuil d’obsolescence, et pour quels actifs |
| Points FX reportés | Combien de points de conversion ont été reportés au-delà du seuil d’obsolescence, et pour quelles paires |
| Dates incomplètes | Dates auxquelles la valorisation, la NAV, la valeur comptable ou l’allocation n’a pas pu être achevée pour chaque position |
| Actifs inutilisables | Actifs exclus avant toute tentative de calcul de métrique, chacun avec un motif |
| Avertissements | Notes libres ajoutées par l’étape de production |

Chaque entrée nomme l’objet concerné — l’actif, la paire de devises, la date. Le lecteur peut demander *quel* actif, *quelle* paire de devises ou *quelle* date a dégradé le chiffre, et pas seulement *si* quelque chose l’a dégradé.

---

## 🧮 Alignement : ce que coûtent réellement les données manquantes {: #alignment-what-missing-data-actually-costs }

Lorsqu’une analyse porte sur plusieurs positions — une matrice de corrélation, une décomposition de la contribution au risque —, elle est calculée sur un **calendrier partagé unique**, et c’est dans la construction de ce calendrier que les données manquantes se traduisent par un coût visible.

1. Une date est candidate si au moins une position y disposait d’une cotation fraîche, un [report stocké](#stored-carries) ne comptant pas comme telle : les candidates sont l’union des calendriers de cotation des positions sur la fenêtre demandée.
2. Une date candidate n’entre dans l’analyse que si **chaque** position a pu y être valorisée. Ici, *valorisé* inclut un prix ou un taux de change reporté depuis une date antérieure, sans limite d’ancienneté ; en pratique, le test n’échoue donc qu’avant le premier prix exploitable d’une position, ou lorsque sa conversion dans la devise cible n’a pas pu être résolue. Les dates qui échouent à ce test sont écartées pour toutes les positions, mais elles ne sont enregistrées comme dates de valorisation incomplètes qu’une fois le calendrier commencé — c’est-à-dire après la ligne de base.
3. La ligne de base est la dernière date avant le début demandé à laquelle toutes les positions étaient valorisables ; s’il n’en existe aucune, l’analyse commence à l’intérieur de la fenêtre demandée, à la première date à laquelle chaque position peut être valorisée, et les positions responsables de ce démarrage tardif sont nommées.

La conséquence mérite d’être énoncée clairement : **une position qui démarre tard raccourcit la fenêtre pour tout le monde**. Une lacune à l’intérieur d’un historique ne raccourcit rien, car le prix ou le taux de change manquant est reporté. Rien n’est interpolé : un prix ou un taux reporté est le dernier connu. Une fois qu’il a été reporté au-delà du [seuil d’obsolescence](#staleness-threshold), il est compté comme point reporté — ce qui relève du statut `carried_forward`, non de la longueur de la fenêtre. Une valeur plus récente ne dégrade pas le statut, bien qu’un prix reporté, quel que soit son âge, compte toujours au débit de la mesure de fraîcheur décrite sous [Couverture](#coverage). Une position n’est jamais partiellement incluse dans un calcul conjoint — soit la date convient à toutes, soit ce n’est pas une observation. Un démarrage tardif ne suffit pas à rendre le résultat `partial` : les dates qu’il fait perdre ne sont pas listées comme incomplètes, le rapport nomme les positions responsables dans ses entrées `short_history`, et la perte apparaît dans le nombre d’observations et dans la couverture du calendrier partagé ci-dessous. Une date perdue après le démarrage du calendrier est différente : elle est listée comme incomplète et rend le résultat `partial`.

---

## 📏 Couverture {: #coverage }

La couverture est normalement le pendant du statut en matière de densité : elle répond à *quelle part de ce qui aurait pu être observé l’a effectivement été*. Plusieurs ratios différents portent ce nom. Ils ne partagent aucun dénominateur et ne mesurent pas tous le même type de chose : deux d’entre eux comptent des observations, un troisième compte des positions et ne contient aucune observation.

**Combien le calendrier partagé a-t-il coûté ?** Parmi les dates auxquelles au moins une position disposait d’une cotation fraîche, c’est la part qui a survécu à l’exigence que chaque position soit valorisable. Un chiffre nettement inférieur à 1 signifie que, à beaucoup des dates où une position était cotée, une autre ne pouvait pas être valorisée — et comme les lacunes sont reportées, cela indique généralement une position dont l’historique commence bien après le début demandé, ou des conversions qui n’ont pas pu être résolues, plutôt que des lacunes.

**Quelle part des données est réellement fraîche ?** Sur la grille positions × observations, c’est la part des points dont le prix a été coté à cette date plutôt que reporté depuis une date antérieure. Elle mesure le même type d’imperfection que le statut `carried_forward`, mais sur les seules observations et avec un critère plus strict : tout prix reporté compte au débit, si récent soit-il, alors que le statut ne compte que ceux reportés au-delà du seuil d’obsolescence. Elle ne compte en outre que les prix : une cotation fraîche mais qui a dû être convertie avec un taux de change reporté compte toujours comme fraîche, car les conversions reportées sont suivies comme un signal distinct. Ainsi, une part inférieure à 100 % ne signifie pas en soi `carried_forward`, et une part de 100 % ne l’exclut pas en soi — ni, par conséquent, un résultat `partial`.

**Quelle part du portefeuille a pu être classée ?** Parmi les positions du périmètre, c’est la part dont les métadonnées de secteur ou de zone géographique étaient disponibles, au lieu d’être manquantes et d’envoyer la position dans le compartiment fourre-tout `Other` à 100 %. Celle-ci est une affirmation sur les métadonnées : aucun prix, aucune date et aucune observation n’y entrent. Un [choc hypothétique](hypothetical-shock.md) rapporte ce ratio.

!!! warning "Un nom partagé, deux types de grandeur"

    Lorsque le chiffre est une mesure de densité, son dénominateur dépend du chemin. Pour une analyse construite à partir des cotations d’instruments, ce sont les dates de cotation candidates. Pour une série de portefeuille, ce sont les **jours d’observation** du portefeuille : l’analyse lit la série de rendements du portefeuille lui-même, son [rendement pondéré par le temps](../performance-metrics/portfolio-engine/twrr.md), uniquement les jours où au moins une position du périmètre disposait d’une cotation propre, et enchaîne le rendement de chaque autre jour dans le suivant ; le dénominateur compte ces jours sur l’étendue — ou chaque jour calendaire de l’étendue, si aucune position ne disposait d’une cotation propre dans la fenêtre. Sur une série de portefeuille, ce chiffre est élevé par construction — l’historique du portefeuille possède un point pour chaque jour calendaire, en reportant la dernière valeur connue là où rien n’était coté, de sorte que chaque jour d’observation en possède un — et il ne certifie donc rien sur les prix qui le sous-tendent. Sur une grille d’instruments, un chiffre plus bas indique des dates que le calendrier partagé a réellement perdues — un démarrage tardif, ou une conversion qui n’a pas pu être résolue — jamais un marché fermé : une date à laquelle rien n’était coté, ou à laquelle les seuls prix stockés étaient des reports, n’est pas candidate, et à une date où seules certaines positions étaient cotées, les autres sont reportées et toujours valorisées, de sorte que la fermeture apparaît plutôt dans la mesure de fraîcheur.

    La question *ces prix ont-ils été cotés, ou reportés ?* a bien une réponse dans le système, mais c’est la mesure de fraîcheur ci-dessus, non celle qu’un résultat porte sous le nom de *couverture*. Quelle mesure parvient à tel ou tel écran dépasse ce que décrit cette page.

    Un discriminateur tranche sans aucune connaissance des rouages internes. **Lorsqu’un résultat rapporte `n_observations = 0` et `calendar_days = 0` à côté d’une couverture non nulle, cette couverture n’est pas une affirmation sur la densité des données.** Elle ne peut pas l’être : rien n’a été observé. Elle indique quelle part du portefeuille a été classée.

    La distinction change ce qu’il convient de faire du nombre. Une couverture de 80 %, lue avec les deux premières significations en tête, dit *un cinquième des prix manque*. Sur un ratio de classification, elle dit qu’un cinquième des libellés de secteur ou de zone géographique manque. L’un est une lacune dans les données de marché, l’autre une lacune dans les métadonnées d’actif, et les deux appellent des actions complètement différentes. Voir [Annualisation observée](observed-annualization.md) pour la manière dont l’étendue et le nombre d’observations produisent aussi le facteur d’annualisation.

---

## 🚫 Exclusions {: #exclusions }

Un actif peut sortir de l’analyse à deux moments différents, et la distinction est enregistrée.

**Avant toute tentative de calcul de métrique**, lorsque ses données sources ne peuvent pas en soutenir une : aucun prix exploitable, aucune conversion de devise exploitable, une devise invalide. Ces actifs sont signalés comme actifs inutilisables, chacun portant son motif.

**Lorsque le périmètre est résolu**, si l’actif ne dispose d’aucune série de rendements préparée exploitable. Le périmètre demandé est alors réduit aux actifs qui subsistent, chaque exclusion conserve son motif, et un avertissement par motif nomme exactement les actifs écartés.

Dans aucun des deux cas l’analyse ne refuse de s’exécuter : elle s’exécute sur ce qui reste et le dit. Un actif exclu constitue un changement dans *ce qui a été mesuré*, et c’est pourquoi il fait sortir de l’état propre tout résultat dont il a changé la mesure — et seulement ceux-là.

### 🎯 Quels résultats portent une exclusion {: #which-results-carry-an-exclusion }

Une exclusion est un trou dans les séries par actif du périmètre : les séries de rendements de chaque position, alignées sur le [calendrier partagé](#alignment-what-missing-data-actually-costs). Tout résultat construit à partir de ces séries en hérite — l’actif est listé comme exclu, l’avertissement qui le nomme accompagne le résultat, et le résultat est `partial`. Cela couvre la corrélation, la contribution au risque, le risque/rendement et la simulation ; les KPI, la valeur à risque et la comparaison rejouées sur la composition actuelle, c’est-à-dire les pondérations d’aujourd’hui appliquées à ces séries ; les analyses d’un ensemble d’actifs choisis directement ; et les analyses d’une *tranche* d’un portefeuille, une sélection de ses positions. Une tranche ne peut pas être découpée dans l’historique propre du portefeuille ; même en mode historique, elle est donc rejouée à partir des séries des positions sélectionnées.

L’exception est le mode historique d’un portefeuille dans son ensemble — tous ses courtiers ou une sélection de ceux-ci, mais pas une tranche de ses positions. Là, quatre analyses lisent l’historique de rendements du portefeuille lui-même, son [rendement pondéré par le temps](../performance-metrics/portfolio-engine/twrr.md) (TWRR), sur ses [jours d’observation](#coverage), au lieu des séries par actif : les KPI (volatilité, Sharpe, Sortino, …), la [valeur à risque](value-at-risk.md) historique et la [VaR conditionnelle](conditional-value-at-risk.md), le repli et la comparaison à un indice de référence, qui n’ajoute que la série propre de l’indice de référence. Cet historique valorise déjà chaque position — une position sans cotation de marché à la valeur de son dernier achat ou de sa dernière vente, ou à son coût lorsqu’elle n’a connu ni achat ni vente —, de sorte qu’un actif absent des séries par actif ne coûte rien en valeur à ces quatre analyses : au plus, les jours où seul cet actif était coté cessent d’être des jours d’observation, et leurs rendements sont enchaînés dans le suivant. Elles n’héritent ni de l’exclusion ni de l’avertissement qui la nomme, ni de l’avertissement selon lequel la part de la composition actuelle comptée à rendement nul inclut de la valeur en transit, une affirmation sur une composition qu’elles n’utilisent jamais. La même requête signale toujours l’exclusion sur chaque résultat qui lit les séries par actif. Ce qui peut encore rendre ces quatre analyses `partial`, ce sont les données derrière l’historique du portefeuille lui-même et, pour la comparaison, la préparation de son indice de référence — voir [Interprétation](#interpretation).

Les tests de résistance appliquent leurs propres règles. Un [rejeu historique](historical-replay.md) prépare ses propres séries sur la fenêtre de son épisode et laisse de côté — pour ses propres raisons, nommées dans ses propres avertissements — les actifs qu’il ne peut pas valoriser aux deux extrémités de cette fenêtre. Un [choc hypothétique](hypothetical-shock.md) ne lit aucune série de rendements du tout : il applique ses chocs à chaque position via la classification de la position ; une exclusion des séries par actif ne lui coûte donc rien, et il n’hérite ni de l’exclusion ni de son avertissement.

### 🏷️ Motifs d’exclusion {: #exclusion-reasons }

Chaque actif exclu porte un motif, et chaque motif dispose de sa propre phrase dans l’avertissement :

| Motif | Pourquoi l’actif a été écarté |
|---|---|
| `no_price_source` | Aucune source de prix ne lui est affectée et aucun prix n’a jamais été enregistré pour lui. Rien n’est configuré pour le valoriser ; il s’agit donc d’un état permanent plutôt que d’une lacune dans les données — typiquement un investissement privé, comme un prêt de crowdfunding, qu’aucun marché ne cote. |
| `missing_price` | Il possède une source de prix, ou des prix enregistrés, mais aucun prix exploitable pour la période : la source n’a rien renvoyé pour lui, ou tous les prix enregistrés tombent après la période. |
| `missing_fx` | Ses prix n’ont pas pu être convertis dans la devise cible. |
| `invalid_currency` | Ses prix ne portent aucune devise valide. |
| `insufficient_history` | L’historique de la période est insuffisant pour lui fournir une série de rendements exploitable. |

Des prix enregistrés uniquement *avant* la période ne provoquent jamais d’exclusion : le dernier d’entre eux est reporté dans la période, comme décrit sous [Alignement](#alignment-what-missing-data-actually-costs). Seul le résultat permet de distinguer les deux premiers motifs : dans son rapport sur les données sources, un actif que rien ne valorise est toujours listé parmi les actifs inutilisables comme `missing_price`.

### ⚖️ Le poids exclu {: #excluded-weight }

Les analyses de la composition actuelle qui indiquent des pondérations — la contribution au risque et le risque/rendement — conservent une position exclue à sa pondération et la comptent à rendement nul : les chiffres qu’elles calculent sont exactement ceux que donnerait le même argent détenu en liquidités. Le résultat nomme cette part séparément. `excluded_weight` est la somme des pondérations des positions du périmètre laissées sans série, et il est indiqué à côté de `cash_weight`, le résidu à rendement nul : la part de la valeur du périmètre détenue en dehors des positions qui ont une série — liquidités, toute valeur en transit et les positions exclues. Dans chaque résultat que produisent ces deux analyses, le poids exclu fait partie de ce résidu. Les deux ne pourraient manquer de s’emboîter que si les positions valaient plus que la valeur nette — un solde de trésorerie négatif non compensé par de la valeur en transit — et, dans ce cas, aucune des deux analyses ne produit de résultat : il revient `unavailable`. Les sélections sans pondérations, comme un ensemble d’actifs choisis directement, ne portent ni l’un ni l’autre.

---

## 💡 Interprétation {: #interpretation }

Chaque résultat analytique porte son propre statut, distinct de celui des données sources :

| Statut du résultat | Signification |
|---|---|
| `ok` | Calculé sans rien de manquant ou d’obsolète dans ses données sources, sans rien d’exclu de ce qu’il lit et sans avertissement dégradant |
| `partial` | Calculé, mais avec des données sources manquantes ou obsolètes, quelque chose d’exclu de ce qu’il lit, ou un avertissement dégradant |
| `unavailable` | Non calculé ; un code de motif stable explique pourquoi (historique insuffisant, données indisponibles, paramètres invalides, calcul trop volumineux pour être exécuté, périmètre ou mode incompatible, …) |
| `failed` | Le calcul s’est interrompu sur une erreur que l’analyse ne déclare pas — une défaillance du calcul, jamais un verdict sur les données. Il porte le code `execution_failed` (*Le calcul backend a échoué.*), le serveur le journalise, et l’écran affiche **Échec du calcul** |

Une défaillance n’est pas une valeur indéfinie. Une métrique qui n’a réellement aucune valeur pour des données bien formées — la corrélation d’une série qui n’a jamais bougé, un ratio de Sharpe sur une volatilité nulle — n’échoue pas : cette valeur revient vide, signalée `undefined` dans une cellule de corrélation ou expliquée par un avertissement tel que `sharpe_undefined`, et le reste du résultat demeure exploitable. À l’inverse, une erreur que l’analyse n’a pas anticipée n’est jamais rapportée comme une métrique indéfinie : cela transformerait une défaillance du calcul en affirmation sur vos données.

Un résultat est `partial` lorsque **l’une** des conditions suivantes est remplie : un avertissement qui dégrade le résultat est présent ; un actif du périmètre que le résultat lit a été [exclu](#which-results-carry-an-exclusion) ; l’analyse elle-même a exclu quelque chose ; ou le statut du rapport sur les données sources sur lequel le résultat est jugé est différent de `ok`. Dans ce dernier cas, un avertissement explicite est également joint, de sorte que la dégradation n’est jamais déduite du seul statut.

Ce rapport est celui des séries que le résultat a consommées :

- un résultat construit à partir des séries par actif du périmètre — y compris les KPI, les chiffres de valeur à risque, le repli et la comparaison lorsqu’ils sont rejoués à partir de ces séries, sur la composition actuelle ou sur une tranche — est jugé sur le rapport de leur préparation, fusionné, lorsque le périmètre est un portefeuille, avec le rapport propre au portefeuille ;
- sur le TWRR d’un portefeuille, les KPI, les chiffres de valeur à risque et le repli sont jugés sur le rapport sur les données sources propre au portefeuille : si l’historique du portefeuille lui-même est incomplet — une position qui n’a pas pu être valorisée, un taux de change manquant, un jour où la valeur nette n’a pas pu être valorisée intégralement —, ils restent `partial`, avec l’avertissement. Ce rapport suit ce qui n’a pas pu être valorisé, et non l’ancienneté d’une valorisation ; un prix reporté au-delà du seuil d’obsolescence dans l’historique du portefeuille ne les dégrade donc pas ;
- la comparaison à un indice de référence sur le TWRR est jugée sur le rapport du portefeuille plus la préparation de son indice de référence, qui est aligné sur le calendrier partagé du périmètre : un prix ou un taux de change de ce calendrier reporté au-delà du [seuil d’obsolescence](#staleness-threshold) — celui de l’indice de référence ou d’une position —, ou une date perdue de ce calendrier, rend encore cette comparaison `partial` ; les positions exclues du périmètre ne sont jamais entrées dans ce calendrier, leur exclusion ne le fait donc pas.

!!! info "Comment lire un résultat partiel"

    `partial` ne signifie pas *faux*. Cela signifie que le chiffre porte une imperfection connue : il peut reposer sur des prix ou des taux de change reportés au-delà du seuil d’obsolescence — même fenêtre, mêmes positions — ou répondre à une question légèrement différente de celle posée, sur un calendrier aux dates incomplètes ou sur moins de positions. Le chiffre et le motif voyagent ensemble dans la même charge utile, et ils sont faits pour être lus ensemble : une contribution au risque calculée avec deux positions exclues décrit un portefeuille dans lequel ces deux positions sont restées immobiles, comme des liquidités — et non le portefeuille tel qu’il est.

Les analyses préfèrent également refuser de répondre plutôt que de mal répondre. Chacune déclare le nombre minimal d’observations dont elle a besoin, et en dessous de ce plancher elle n’est pas calculée du tout : le résultat revient `unavailable` avec un motif `insufficient_history` portant à la fois les observations disponibles et le nombre requis. La contribution au risque et la comparaison à un indice de référence, par exemple, exigent toutes deux au moins 20. Les chiffres de valeur à risque comptent leurs fenêtres composées sur l’horizon plutôt que leurs rendements ; un horizon plus long nécessite donc une fenêtre plus longue — voir [valeur à risque](value-at-risk.md#the-observation-count-is-not-the-history-length). La [corrélation](correlation.md#how-each-cell-is-computed) fait exception : elle n’est jamais refusée pour un historique court. Son plancher — un paramètre ajustable de l’analyse, 20 observations par défaut — s’applique à la matrice dans son ensemble : chaque série partage un même calendrier, donc chaque paire a le même nombre d’observations, et sous le plancher chaque cellule revient `insufficient` sans coefficient, dans un résultat marqué `partial` plutôt que `unavailable`.

---

## ⚠️ Limites {: #limitations }

!!! warning "Un statut décrit les entrées, pas le modèle"

    `ok` dit que la série était complète, non que la métrique est appropriée, que la fenêtre est suffisamment longue ou que le passé ressemble à l’avenir. Toutes les réserves des pages de métriques s’appliquent toujours à un chiffre construit sur des données impeccables.

!!! warning "Les données reportées flattent un chiffre de risque"

    Un prix reporté depuis une date antérieure produit un rendement de période exactement nul dans la devise propre à l’instrument ; après conversion dans la devise cible, seul le taux de change le fait bouger. Tout prix reporté fait cela, si récent soit-il, et ces rendements entrent dans l’échantillon comme n’importe quelle autre observation. En deçà du [seuil d’obsolescence](#staleness-threshold), cela est ordinaire : pendant un week-end, un jour férié ou un jour où seul un autre marché s’est négocié, l’instrument n’a pas eu de nouvelle cotation, et sa cotation suivante rattrape le retard. Un prix reporté plus longtemps tient lieu de jours où l’instrument a très bien pu bouger ; une série riche en de tels points rapporte donc **moins** de mouvement que l’instrument n’en a réellement connu. Ce sont les points que compte le statut `carried_forward`, et le statut est l’avertissement qu’un chiffre d’apparence calme peut l’être pour la mauvaise raison.

!!! warning "Une position valorisée à partir de ses transactions reste immobile"

    Sur le TWRR d’un portefeuille, une position qu’aucun marché ne cote est valorisée au [prix de son dernier achat ou de sa dernière vente](../performance-metrics/portfolio-engine/price-resolution.md) — ou, si elle n’a été reçue que par transfert, au coût de ce transfert —, de sorte que, dans sa propre devise, elle reste immobile d’une transaction à l’autre ; si elle n’a ni l’un ni l’autre, elle est valorisée à son coût, qui reste immobile dans la devise cible aussi. Pour un prêt détenu à sa valeur nominale — un investissement de crowdfunding typique —, c’est la vérité. Pour une position dont la valeur bouge réellement, cela aplatit chaque chiffre lu sur le TWRR, tout comme le fait un prix reporté. Aucun statut ne le signale : le rapport du portefeuille ne compte pas au débit de son statut une valorisation à partir de transactions ou au coût, et pour une position sans source de prix, il traite cette valorisation comme l’état voulu et permanent.

!!! warning "Aucun seuil de qualité n’écarte un chiffre"

    Hormis les nombres minimaux d’observations décrits ci-dessus, en dessous desquels une analyse n’est pas calculée du tout ou chaque cellule de corrélation revient `insufficient`, rien dans le système ne déclare une couverture ou une part de données reportées au-delà de laquelle un chiffre doit être écarté. Cette absence est délibérée — le chiffre honnête est celui qui vient avec sa propre provenance —, mais elle signifie que le jugement final vous appartient et ne peut être délégué à l’étiquette de statut.

---

## 🔗 Voir aussi {: #related }

- 📅 **[Annualisation observée](observed-annualization.md)** — le facteur d’annualisation compté à partir des mêmes observations, et pourquoi une série clairsemée n’est pas nécessairement défectueuse
- 🔗 **[Corrélation](correlation.md)** — rapporte le nombre d’observations derrière chaque cellule
- 📊 **[Volatilité](volatility.md)** — le chiffre le plus directement aplati par les prix reportés
