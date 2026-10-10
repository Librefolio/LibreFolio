# ⚡ Choc hypothétique

Un choc hypothétique remplace l'épisode historique par un épisode choisi, ce qui permet de tester un scénario que l'historique disponible n'a jamais contenu.

Le [Rejeu historique](historical-replay.md) pose la question *que me ferait cet épisode ?* — les mouvements sont réels et vous ne choisissez que les dates. Un choc hypothétique pose la question *que se passerait-il si je décidais ceci ?* — vous choisissez les mouvements. Ni l'un ni l'autre n'est une prévision, et la différence entre eux réside dans l'origine des chiffres.

---

## 🔢 Comment le choc est calculé {: #how-the-shock-is-computed }

Vous choisissez une **dimension** selon laquelle appliquer le choc — classe d'actifs, secteur ou zone géographique — et attribuez un rendement à ses catégories : *la technologie chute de 30 %, l'énergie monte de 5 %*. L'analyse procède ensuite en deux étapes.

Premièrement, le choc de chaque position est assemblé à partir de ses expositions à ces catégories :

$$
s_i = \sum_b e_{ib} \cdot \text{shock}_b
$$

où $e_{ib}$ est l'exposition de la position $i$ à la catégorie $b$. Cela compte plus qu'il n'y paraît : une position est rarement *dans* une seule catégorie. Un fonds diversifié réparti sur plusieurs secteurs reçoit un **mélange pondéré par les expositions** des chocs que vous avez configurés, et non l'un d'entre eux. Le chiffre par position que vous lisez est déjà un mélange.

Deuxièmement, l'impact sur le portefeuille est la somme pondérée de ces chocs par position, et la contribution de chaque position est son propre terme :

$$
r_{shock} = \sum_i w_i \, s_i, \qquad \text{contribution}_i = w_i \, s_i
$$

Il n'y a aucun historique de rendement dans ce calcul. Contrairement à toutes les autres analyses de cette section, un choc hypothétique ne lit pas la moindre observation passée : il a besoin des pondérations actuelles et des classifications actuelles, et rien d'autre. Le résultat indique zéro observation pour exactement cette raison.

---

## 🧾 Que se passe-t-il pour ce que vous n'avez pas configuré {: #what-you-did-not-configure }

Un scénario n'est jamais complet. Vous appliquez un choc à la technologie, et le portefeuille contient aussi des obligations, de l'or et un fonds auquel vous n'avez jamais pensé. Ce que l'analyse fait du reste est la chose la plus importante de cette page — et ce n'est **pas la même chose pour chaque dimension**.

| Dimension | Ce qui arrive à ce que vous n'avez pas configuré |
|---|---|
| **Secteur**, **zone géographique** | Vous ne pouvez pas le laisser indéfini. Le scénario est **refusé** à moins qu'il n'inclue une catégorie `Other`, de sorte que le reste évolue d'un montant **que vous avez choisi** |
| **Classe d'actifs** | Une catégorie non configurée reçoit un choc de **zéro**, et le résultat étiquette cette ligne *Non configuré → choc nul* |

Le refus de la première ligne se produit dès l'entrée : un scénario sectoriel ou géographique sans catégorie `Other` est rejeté **avant que quoi que ce soit ne soit calculé**, de sorte qu'il n'existe jamais de résultat partiel construit sur un résidu non déclaré.

!!! warning "Un choc nul n'est pas une neutralité — c'est une prévision"

    Laisser une position sans choc ne la retire pas du scénario. Cela revient à affirmer que, pendant que les actions chutent de 30 %, cette position ne bouge **pas**. C'est une affirmation sur le monde, et lors d'une vente généralisée, elle est généralement généreuse.

    Ce qui rend la conception défendable n'est pas qu'elle soit prudente — c'est que l'affirmation est **écrite noir sur blanc**. Le scénario ne suppose pas discrètement que le reste du portefeuille reste immobile ; il consigne, pour chaque position et chaque catégorie, qu'un zéro a été appliqué parce que rien n'a été configuré. L'hypothèse reste une hypothèse. Simplement, elle n'est pas cachée.

L'asymétrie entre les dimensions mérite d'être connue plutôt que jugée : sur le secteur et la zone géographique, vous êtes **contraint** de déclarer le résidu, sur la classe d'actifs, vous ne l'êtes pas. La dimension dans laquelle vous travaillez détermine ce que vous devez vérifier — et si vous appliquez un choc par classe d'actifs, ce qu'il faut vérifier est si quelque chose est revenu comme non configuré.

---

## 🖥️ Ce que montre le résultat {: #what-the-result-shows }

Un choc hypothétique est proposé dans l'onglet **Risque** du Tableau de bord et de la page d'un courtier, comme second outil de **Et si… ?**, et dans l'onglet **Risque & Scénarios** de la page de détail d'un actif. L'onglet [Corrélation](../../../user/assets/correlation.md#what-if) de la page des Actifs ne le propose pas : une sélection n'a pas de pondérations à choquer.

Sur le Tableau de bord et sur la page d'un courtier, un scénario se lance en un clic. Chaque scénario nommé — *Aversion mondiale au risque*, *Krach actions*, *Crise bancaire*, *Choc sur l'Union européenne* — s'exécute dès qu'il est choisi, selon la dimension pour laquelle il est écrit. **Afficher le choc par catégorie** déploie ses catégories, chacune avec son choc en pourcentage entier ; modifier l'une met de côté le scénario nommé, puisque ce qui est à l'écran n'est plus ce scénario, et **Lancer le scénario** exécute celui qui a été modifié. Le résultat affiche :

- le total, $r_{shock}$, sous la forme *Ce scénario déplacerait le périmètre de …*, avec le montant qu'il représente ;
- un tableau avec **une ligne par catégorie du scénario**, et non une par position, en commençant par les pires : le choc appliqué à la catégorie (**Rendement**), ce que les positions qui y sont tombées ont fait au total (**Contribution** : la pondération de chaque position multipliée par la part de son choc fournie par cette catégorie, sommée sur les positions, de sorte que les lignes s'additionnent pour donner le total), et une barre de cette contribution (**Effet**), sur une échelle unique partagée par toutes les lignes ;
- lorsque toutes les positions n'ont pas pu être classées, une note donnant la part qui a pu l'être — voir [Quand la classification est manquante](#when-the-classification-is-missing).

La vue position par position, avec la règle derrière chaque choc appliqué, constitue l'audit ci-dessous. Elle apparaît dans l'onglet **Risque & Scénarios** de l'actif, où la dimension et le choc de chaque catégorie peuvent aussi être définis manuellement.

---

## 🔍 Lire l'audit {: #reading-the-audit }

Dans l'onglet **Risque & Scénarios** de l'actif, l'impact s'accompagne d'un audit par catégorie, là où un scénario cesse d'être quelque chose que vous croyez pour devenir quelque chose que vous vérifiez. Chaque ligne indique :

| Colonne | Ce qu'elle vous dit |
|---|---|
| Catégorie d’exposition | La catégorie de la dimension choisie dont cette ligne traite |
| Exposition | Quelle part de la position se trouve dans cette catégorie |
| Catégorie appliquée | La catégorie dont le choc a réellement été utilisé — souvent, mais pas toujours, la même |
| Choc | Le rendement appliqué |
| Contribution | Ce choc mis à l'échelle par l'exposition |
| Règle | **Comment** la catégorie appliquée a été choisie |

La dernière colonne est celle à lire en premier, car deux positions peuvent afficher le même choc pour des raisons totalement différentes et seule la règle permet de les distinguer. Six règles existent, et sur la dimension géographique elles forment une cascade essayée dans l'ordre :

| Règle | Quand une ligne la porte |
|---|---|
| **Direct** | La catégorie propre à la position est l'une de celles que vous avez configurées — le cas ordinaire en classe d'actifs et en secteur |
| **Pays** | Zone géographique, première étape : vous avez configuré **ce pays** lui-même |
| **Groupe géographique** | Zone géographique, deuxième étape : pas le pays, mais un **groupe qui le contient**, tel qu'une catégorie régionale |
| **Other** | Zone géographique, dernière étape — et l'équivalent sectoriel : rien de ce qui précède ne correspondait, la catégorie résiduelle obligatoire s'est donc appliquée |
| **Métadonnées manquantes → Other** | La classification de la position était indisponible, elle a donc été traitée comme `Other` à 100 % |
| **Non configuré → choc nul** | Classe d'actifs uniquement : la catégorie n'a jamais été configurée, et zéro a été appliqué |

Lire cette liste de haut en bas indique jusqu'où un choc a voyagé avant d'atterrir, par rapport à votre intention. Une ligne *Pays* est le scénario que vous avez écrit ; une ligne *Other* est la catégorie résiduelle qui capture quelque chose que vous n'avez pas nommé ; une ligne *Métadonnées manquantes* est un problème de classification habillé de la même manière.

!!! info "L'ambiguïté est refusée, pas résolue"

    Un pays peut appartenir à plus d'un groupe que vous avez configuré — une position dans un pays couvert par deux catégories régionales qui se chevauchent n'a pas de choc correct unique. Plutôt que d'en choisir un et de rapporter un chiffre, l'analyse **s'arrête et signale le conflit**, en nommant le pays et les groupes qui se sont heurtés. C'est le même principe que la catégorie résiduelle, appliqué à un cas que la plupart des utilisateurs n'anticiperaient jamais : lorsque le scénario est véritablement indéterminé, la réponse n'est pas une valeur.

---

## 🏷️ Quand la classification est manquante {: #when-the-classification-is-missing }

Les chocs sectoriels et géographiques dépendent de la connaissance de ce à quoi chaque position est exposée. Lorsque ces métadonnées sont indisponibles, la position n'est ni écartée ni devinée : elle est traitée comme **`Other` à 100 %**, ce qui explique pourquoi ces deux dimensions exigent la catégorie `Other` en premier lieu. La position est signalée, de sorte que le fallback soit visible là où il s'est produit.

!!! info "Le taux de couverture sur cette analyse ne concerne pas la densité des données"

    Ailleurs dans cette section, la couverture décrit la densité d'échantillonnage d'une période — voir [Qualité des données](data-quality.md). Un choc hypothétique ne lit aucun historique, de sorte que sur cette analyse le taux de couverture véhicule autre chose : la part du périmètre qui a été classée à partir de **véritables métadonnées** plutôt que d'utiliser le fallback `Other`. Un taux faible ne signifie pas des prix clairsemés ; il signifie qu'une grande partie du scénario a atterri sur la catégorie résiduelle au lieu des catégories que vous avez configurées.

---

## 💡 Interprétation {: #interpretation }

Le résultat est un énoncé linéaire sur une période unique : *si ces mouvements se produisaient, d'un coup, sur un portefeuille composé tel qu'il est aujourd'hui, l'impact serait celui-ci.*

Chaque mot de cette phrase porte du sens.

- **Période unique.** Il n'y a pas de trajectoire. L'arithmétique donne un point d'arrivée, pas une séquence, de sorte que rien du chemin qui y mène ne peut être lu dans le résultat — aucun repli en cours de route, aucun [temps de récupération](max-drawdown.md#recovery-time), aucun ordre des événements.
- **Linéaire.** L'impact est exactement la somme pondérée de ce que vous avez spécifié. Il n'y a pas d'effets de second ordre, pas de rétroaction, pas de contagion d'une catégorie vers une autre.
- **Aucune corrélation.** C'est la différence la plus marquée avec le reste de cette section. La [Corrélation](correlation.md) et la [Contribution au risque](risk-contribution.md) déduisent l'évolution conjointe des positions à partir de l'historique ; un choc hypothétique ne consulte rien de tout cela. Si vous configurez la technologie en baisse et les obligations stables, elles font exactement cela, quel qu'ait été leur comportement conjoint passé. Les co-mouvements du scénario sont ceux que **vous** avez affirmés.

La part de liquidités n'est pas choquée : elle ne contribue en rien à l'impact, de sorte qu'un portefeuille détenant des liquidités voit le résultat réduit à hauteur de la fraction investie seule. Pour les liquidités, c'est une hypothèse bien plus faible que pour une position non configurée — mais c'est le même mécanisme.

Bien utilisé, cet outil répond à une question que l'historique ne peut pas trancher, parce que le scénario que vous voulez tester ne s'est jamais produit. Utilisé à la légère, il permet d'obtenir n'importe quel chiffre : le résultat ne peut être aussi discipliné que les chocs qui y sont injectés, et rien dans l'arithmétique ne vous signalera qu'un scénario est invraisemblable.

---

## ⚠️ Limites {: #limitations }

!!! warning "Il ne peut pas vous contredire"

    Toutes les autres métriques de cette section sont contraintes par les données. Celle-ci n'est contrainte que par votre jugement : elle calculera fidèlement l'impact d'un scénario intrinsèquement incohérent — où des actifs corrélés évoluent en sens opposés, ou où un choc est bien au-delà de tout ce qui s'est jamais produit — sans aucun signal que quelque chose cloche.

!!! warning "Il ne dit rien sur la probabilité"

    L'impact est conditionnel à la réalisation du scénario exactement tel que spécifié. L'analyse ne lui attribue aucune probabilité, et un impact plus important issu d'un scénario plus extrême ne prouve pas que ce scénario est plus probable. Comparer deux chocs revient à comparer deux hypothèses, pas deux risques.

!!! warning "La composition est celle d'aujourd'hui"

    Comme le [Rejeu historique](historical-replay.md), le choc est appliqué au portefeuille tel qu'il se présente maintenant. C'est un énoncé sur l'exposition actuelle, et non sur ce qui était détenu auparavant.

---

## 🔗 Voir aussi {: #related }

- ⏮️ **[Rejeu historique](historical-replay.md)** — la même structure avec un épisode réel au lieu d'un épisode choisi
- 🧩 **[Contribution au risque](risk-contribution.md)** — quelles positions portent le risque, déduit de l'historique plutôt qu'affirmé
- 🔗 **[Corrélation](correlation.md)** — les co-mouvements qu'un choc hypothétique n'utilise délibérément pas
- 📉 **[Perte maximale](max-drawdown.md)** — la vue sensible à la trajectoire qu'un choc sur une période unique ne peut produire
- 🧪 **[Qualité des données](data-quality.md)** — ce que signifie la couverture sur les analyses qui, elles, lisent l'historique
