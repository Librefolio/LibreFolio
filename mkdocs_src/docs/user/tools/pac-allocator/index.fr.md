---
title: Allocateur PAC
description: Planifiez les achats qui rapprochent le plus possible un nouvel investissement de son allocation cible, en unités entières ou par montant, sans passer d'ordres.
---

# 🧮 Allocateur PAC

L'**allocateur PAC** répond à une question :

> Avec l'argent disponible pour ce cycle de versement, quels achats
> rapprochent le plus mon allocation de sa cible ?

Ouvrez **Outils** depuis la barre latérale et cliquez sur la carte Allocateur PAC : cela ouvre un
planificateur guidé. Vous décrivez un scénario étape par étape, appuyez sur **Calculer le plan**,
et obtenez un plan d'achat à évaluer. C'est une simulation : rien n'est acheté et
aucun ordre n'est envoyé à un courtier.

## 🗺️ Utilisation du planificateur

Le planificateur vous guide à travers ces étapes, dans l'ordre. L'étape **Change** n'apparaît
que lorsque le scénario nécessite des taux de change.

### 🎬 Scénario

Vous planifiez un nouvel investissement, un « PAC pur » : le calcul part d'un
portefeuille vide, donc ce que vous détenez déjà n'est pas compté, et il répartit
les liquidités que vous choisissez entre les actifs, aussi près que possible
des poids cibles.

Ici, vous définissez la **Devise de valorisation**, dans laquelle les montants sont comparés et
synthétisés. Au départ, c'est la **Devise par défaut** de vos préférences. L'argent
reste dans sa propre devise : chaque change nécessaire apparaît dans le plan.

La date de référence est toujours aujourd'hui : le planificateur la redéfinit avant chaque
copie depuis LibreFolio et avant chaque calcul.

### 💰 Liquidités

D'où vient l'argent ? Vous pouvez combiner plusieurs sources :

- **Depuis vos courtiers** : liquidités déjà présentes sur vos courtiers dans
  LibreFolio. Vous choisissez combien en utiliser.
- **Nouveau versement** : argent nouveau que vous ajoutez, comme le versement PAC.
- **Compte externe** : un solde sur un compte non enregistré dans LibreFolio,
  par exemple à votre banque. Vous déclarez combien s'y trouve et combien en utiliser.
  Rien n'est acheté depuis un compte externe : son argent est envoyé à un courtier.

Le courtier qui reçoit un nouveau versement ou l'argent d'un compte externe est
choisi à l'étape **Courtiers**. Chaque montant reste dans sa propre devise.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-liquidity" alt="L'étape Liquidités, à côté de la liste des étapes : des liquidités provenant d'un courtier, avec le montant à utiliser sur ce qui est disponible ; un nouveau versement, avec son montant et sa devise ; et un compte externe, avec ses liquidités déclarées et le montant à utiliser">
</div>

### 🏦 Courtiers

Ajoutez les courtiers où le plan peut acheter : **Choisir un courtier existant** copie l'un
des vôtres, et **Courtier manuel** en ajoute un à la main. Dans les deux cas, ce sont des
données de scénario : le courtier lui-même n'est jamais modifié. Les frais et modes d'ordre ne sont pas
enregistrés dans LibreFolio, c'est pourquoi vous les définissez ici.

Pour chaque devise dans laquelle vous achetez, définissez :

- Le mode d'ordre : **Par nombre d'unités** ou **Par montant**.
- L'**Incrément** $\Delta$ : chaque ordre proposé est un multiple entier de celui-ci.
  Avec $q$ la taille d'un ordre, en unités ou en montant :

    $$
    q = k\,\Delta, \qquad k = 0, 1, 2, \dots
    $$

    Par nombre d'unités, $\Delta$ est un nombre entier : $\Delta = 1$ signifie des unités
    entières uniquement. Par montant, $\Delta$ est le plus petit montant que vous pouvez saisir, comme
    $\Delta = 0.01$, et les unités obtenues peuvent être des fractions d'unité.

- Les **Frais d'achat** : une **Part fixe** $f$ plus un **Pourcentage** $r$ du
  montant de l'ordre $A$, marge sur le prix incluse. Le **Minimum** $f_{\min}$ et le
  **Maximum** $f_{\max}$ limitent uniquement la part en pourcentage, et un **Maximum** vide
  ne fixe aucune limite supérieure :

    $$
    \text{fee} = f + \min\big(\max(r\,A,\ f_{\min}),\ f_{\max}\big)
    $$

    Les frais sont prélevés sur chaque ordre, et aucun ordre signifie aucun frais. Ils sont payés
    depuis vos liquidités et ne sont pas investis. Par exemple, avec $r = 0.19\%$,
    $f_{\min} = 1.50$, $f_{\max} = 18$ et aucune part fixe, un ordre de $500$
    paie $1.50$, un de $2{,}000$ paie $3.80$, et un de $20{,}000$ paie $18$.

Chaque courtier a aussi deux réglages qui lui sont propres :

- **Liquidités utilisables** : l'argent que le plan peut utiliser pour acheter là-bas, c'est-à-dire
  les liquidités propres du courtier plus les nouveaux versements et autres comptes que vous autorisez. Tous
  sont autorisés au départ : vous pouvez exclure une source, plafonner combien en est utilisé là-bas,
  et lui donner une **Priorité** ($0$ = préféré).
- **Conversion de devise** : **Vous convertissez avant d'acheter** ou
  **Le courtier convertit lors de l'achat**. Les deux convertissent au taux de l'étape **Change**
  moins le spread, donc le calcul est identique dans les deux cas : seule la
  façon dont le plan montre la conversion change.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-brokers" alt="L'éditeur de courtier, en tant que données de scénario qui laissent le courtier inchangé : sous Comment vous achetez, devise par devise, le Type d'ordre Par montant, l'Incrément et les Frais d'achat avec leur minimum, pourcentage, maximum et part fixe ; Conversion de devise avec Le courtier convertit lors de l'achat sélectionné ; et Appliquer au brouillon">
</div>

Pas encore pris en charge : un régime fiscal, les pertes, et les frais de vente pour un courtier.

### 💼 Actifs

Ajoutez les actifs que le plan peut acheter, dans n'importe quel mélange :

- recherchez les actifs enregistrés dans LibreFolio ;
- ajoutez **Vos actifs** : ceux avec une position ouverte aujourd'hui chez vos courtiers,
  ajoutés en tant que lignes uniquement, sans quantités ;
- ajoutez un **Actif manuel**.

Chaque prix est soit :

- **Auto** : le dernier prix stocké dans LibreFolio, relu juste avant le
  calcul. Aucun fournisseur de données n'est appelé.
- **Manuel** : votre propre prix, utilisé tel que saisi et jamais relu.

Un prix manquant reste dans le brouillon : le calcul le réclame.

La composition par pays, secteur et type, copiée depuis l'actif ou saisie,
alimente uniquement les cartes et barres d'exposition du résultat, pas le calcul.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-assets" alt="L'étape Actifs : Rechercher un actif, Vos actifs et Actif manuel, puis un actif de LibreFolio avec un prix Auto, un autre avec un prix Manuel, et un Actif manuel avec son badge Manuel, chacun avec son prix et sa composition">
</div>

### 🔀 Routes

Pour chaque courtier, choisissez les actifs qu'il peut acheter : **Autoriser tout**,
**Exclure tout**, ou cliquez sur chacun.

Ensuite, uniquement là où vous en avez besoin, définissez des limites sur chaque route. Elles sont mesurées
comme les ordres de ce courtier, en unités ou en montant. Avec $q$ l'achat de
l'actif sur ce courtier :

- **Achat minimum** $q_{\min}$ : si le plan achète là-bas, il achète au moins
  ce montant, donc $q = 0$ ou $q \ge q_{\min}$.
- **Achat obligatoire** $q_{\text{req}}$ : acheté quoi qu'il arrive,
  $q \ge q_{\text{req}}$. Si les ressources ne suffisent pas, le plan devient
  impossible.
- **Achat maximum** $q_{\max}$ : le maximum que le plan peut acheter là-bas,
  $q \le q_{\max}$.

Deux autres réglages façonnent la façon dont le plan achète là-bas :

- **Priorité** ($0$ = préféré) : elle ne départage que les plans également
  proches de la cible.
- **Marge sur le prix** $m$ : chaque achat est compté à $p\,(1 + m)$ au lieu
  du prix $p$ d'une unité, pour couvrir une hausse du prix avant l'ordre. Une
  marge de $0.5\%$ sur un prix de $100$ compte $100.50$. La différence est une
  réserve, non investie. Par montant, un ordre de $A$ achète
  $A / \big(p\,(1 + m)\big)$ unités.

Les champs vides ne restreignent rien.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-routing" alt="L'étape Routes : pour chaque courtier, ses paramètres d'ordre, Autoriser tout, Exclure tout et combien d'actifs il peut acheter ; sur le premier courtier, des actifs exclus et un actif autorisé avec son Achat minimum, Achat obligatoire, Achat maximum, Marge sur le prix et Priorité">
</div>

### ⚖️ Cibles

Ici, vous répartissez l'argent que vous investissez maintenant entre les actifs : un poids cible $w_i$
par actif, en pourcentage, décimales autorisées. Pour calculer, les cibles doivent totaliser
exactement $100\%$ :

$$
\sum_i w_i = 100\%
$$

Deux actions vous aident à y parvenir :

- **Équilibrer tout** remet à l'échelle chaque cible, en conservant leurs ratios :

    $$
    w_i' = \frac{w_i}{\sum_j w_j} \cdot 100\%
    $$

    Si elles sont toutes à $0$, chaque actif reçoit une part égale. L'arrondi maintient le
    total à exactement $100\%$. Pour ne modifier que certaines lignes, **Équilibrer à 100 %** sur
    une ligne donne à cet actif ce qui manque, ou retire l'excédent, et
    **Équilibrer les lignes sélectionnées à 100 %** remet à l'échelle uniquement les lignes que vous cochez.

- **Copier la répartition actuelle** lit combien chacun de ces actifs pèse
  aujourd'hui dans les courtiers que vous cochez, en comptant uniquement ces actifs et non
  les liquidités. Avec $H_i$ la valeur de marché de l'actif $i$ détenu là-bas aujourd'hui :

    $$
    w_i = \frac{H_i}{\sum_j H_j} \cdot 100\%
    $$

    Les poids cibles sont arrondis à $0.01$ point de pourcentage et totalisent toujours
    exactement $100\%$, et un actif que vous avez saisi à la main obtient $0$. Ce ne sont
    que des poids cibles, une base à modifier et non un conseil : vous les voyez avant de les utiliser,
    et une cible que vous avez modifiée n'est pas écrasée sans votre confirmation.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-targets" alt="L'étape Cibles de l'allocateur PAC : un pourcentage cible par actif, avec sa barre de répartition, totalisant 100 % ; Équilibrer tout, désactivé car les cibles sont déjà équilibrées ; et Copier la répartition actuelle">
</div>

### 💱 Change (uniquement si nécessaire)

Cette étape n'apparaît que lorsque le scénario nécessite des taux de change. Elle contient un
taux $x$ par paire de devises en jeu, chacun **Auto** ou **Manuel** :

- **Auto** : le dernier taux stocké dans LibreFolio, lu à l'ouverture de l'étape et
  à nouveau juste avant le calcul. Aucun fournisseur de données n'est appelé.
- **Manuel** : votre propre taux.

Elle contient aussi un **Spread de conversion** $s$ : un pourcentage de chaque montant converti,
conservé comme marge pour une variation du taux officiel ou pour les frais du courtier. Convertir un
montant $D$ au taux $x$ (unités reçues pour chaque unité convertie) donne

$$
D \cdot x\,(1 - s)
$$

au lieu de $D \cdot x$. La valorisation, qui compare et additionne les montants dans la
devise de valorisation, utilise le taux officiel $x$ sans spread ; les conversions utilisent
le taux avec le spread, $x\,(1 - s)$.

Les taux doivent également être cohérents entre eux, afin qu'aucune conversion ne crée
de valeur : avec des liquidités en CHF, un actif en USD et une valorisation en EUR, par exemple,
un CHF converti en USD après le spread ne peut pas valoir plus en EUR qu'un CHF,

$$
x_{\text{CHF} \to \text{USD}}\,(1 - s)\,x_{\text{USD} \to \text{EUR}}
\le x_{\text{CHF} \to \text{EUR}}
$$

et il en va de même pour chaque conversion dont le plan peut avoir besoin entre deux
devises autres que la devise de valorisation. Sinon, le calcul ne démarre pas et le résultat est
**Entrée non valide** (voir [Lire le résultat](#reading-the-result)) : la cause peut être un taux **Manuel**
ou des taux **Auto** provenant de jours ou de sources différents, donc alignez les taux ou définissez un
**Spread de conversion** qui couvre la différence. Seul un écart suffisamment petit pour
provenir du stockage des taux avec dix décimales est toléré : la conversion utilise alors le taux via
la devise de valorisation lorsqu'il est plus faible,

$$
\min\left(x_{\text{CHF} \to \text{USD}}\,(1 - s),\;
\frac{x_{\text{CHF} \to \text{EUR}}}{x_{\text{USD} \to \text{EUR}}}\right)
$$

donc il ne crée toujours pas de valeur. Lorsque les taux concordent, ce taux est le
$x\,(1 - s)$ habituel. Vos taux ne sont pas modifiés : chaque conversion du plan montre
le taux dont elle part comme *spot* et le taux qu'elle utilise comme *effectif*.

Chaque montant que le plan comptabilise est arrondi une fois, sur sa valeur finale exacte,
à la plus petite unité de sa devise (le centime pour EUR ou USD), et toujours en défaveur du
plan : les montants qu'il reçoit (ce qu'une conversion délivre) sont arrondis à l'inférieur,
les montants qu'il paie (le coût d'un ordre et ses frais) sont arrondis au supérieur. Ainsi,
l'arrondi n'améliore jamais un plan, découper une conversion en plus petites n'apporte rien,
et la part d'arrondi de **Non investi** n'est jamais négative. La colonne **Arrondi** de
**Soldes par courtier et devise** montre combien de chaque ligne provient de l'arrondi :
≈ marque un chiffre affiché arrondi, comme lorsque la différence exacte n'a pas de forme
décimale finie (par exemple après une conversion USD → EUR à $1/1.085$), et une différence
inférieure à la plus petite unité conserve les chiffres dont elle a besoin, comme ≈ −0.0022
plutôt que ≈ −0.00.

Lorsque LibreFolio n'a pas de taux pour une paire, l'étape propose **Ajouter la paire** ou
**Télécharger les taux** : chacun ouvre la fenêtre correspondante de la page Change, et rien
n'est ajouté ou téléchargé tant que vous ne confirmez pas là-bas.

Pas encore pris en charge : un taux de change ou un spread différent par courtier, une
marge de sécurité sur le taux, des frais de conversion en plus du spread, et des conversions
en plus d'une étape (par exemple EUR → USD → CHF).

### 🧠 Stratégie

La stratégie est **Proportionnelle** : uniquement des achats, elle ne vend rien.

Parmi tous les plans d'achat qui respectent vos paramètres, elle choisit le meilleur avec une
cascade de critères, chacun ne décidant qu'entre les plans encore à égalité sur les précédents :

1. **Proximité avec les cibles (distance L2)** : la plus petite distance

    $$
    D = \sum_i \big(V_i - w_i\,R\big)^2
    $$

    où $V_i$ est la valeur de l'actif $i$ après le plan, $w_i$ son poids cible,
    et $R$ la **Base des cibles** : les liquidités que vous avez choisies et qui peuvent atteindre
    un courtier où elles peuvent acheter (dans un PAC, rien n'est déjà investi). Donc
    $w_i\,R$ est la valeur idéale de l'actif $i$. Les valeurs sont dans la devise de
    valorisation, au prix de cotation, sans frais ni marge sur le prix. Le carré fait que les
    grands écarts pèsent davantage, et $D$ est mesuré en argent au carré, par exemple EUR².

2. **Argent non investi** : le moins d'argent possible laissé en dehors des actifs,
    $R - \sum_i V_i$.

3. **Priorité des courtiers et des sources** : la plus petite somme des numéros de
    **Priorité** des ordres et des sources de liquidités que le plan utilise.

4. **Coûts explicites (frais, spread, marge)** : le total le plus faible des frais,
    du spread de conversion et de la marge sur le prix, dans la devise de valorisation.

5. **Nombre d'ordres** : le moins d'ordres.

Un ordre fixe d'actifs et de courtiers départage toute égalité finale, donc une recherche qui
se termine donne toujours le même plan pour les mêmes données ; une recherche arrêtée par une
limite de temps ou de nœuds peut donner un plan différent sur une machine plus lente ou plus chargée.

### ✅ Récapitulatif

Une dernière vérification avant le calcul. Elle liste la copie complète qui sera
envoyée (le backend reçoit cette copie, et uniquement celle-ci), signale les champs restant
à compléter, et propose **Calculer le plan**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-review" alt="L'étape Récapitulatif : le résumé de chaque étape, avec l'étape Cibles signalée ; le champ restant à compléter avant le calcul, avec un lien vers son étape ; Données de calcul repliées ; et Calculer le plan, désactivé jusqu'à ce que ce champ soit complété">
</div>

### 📋 Valeurs copiées ou saisies

Le planificateur fonctionne sans aucun courtier ou actif enregistré : tout peut être
saisi. Lorsque vous préférez partir de vos données LibreFolio, vous les copiez avec une
action explicite : **Choisir un courtier existant**, **Depuis vos courtiers**, la recherche
d'actif ou **Vos actifs**, et **Copier la répartition actuelle**. Dans l'étape **Change**, un taux
**Auto** est lu depuis LibreFolio dès que l'étape s'ouvre.

Chaque valeur indique sa provenance (**Copiée**, **Manuelle** ou **Modifiée**),
et une copie indique aussi sa date. Une copie ne suit pas sa source pendant que vous
modifiez, et une copie que vous avez modifiée peut être restaurée.

Lorsque vous appuyez sur **Calculer le plan**, le planificateur relit d'abord depuis
LibreFolio les prix, taux et soldes que vous avez copiés et n'avez pas modifiés.
Les valeurs que vous avez saisies ou modifiées restent telles quelles. Si cette lecture échoue,
rien n'est calculé : vous pouvez **Réessayer**, ou **Calculer avec les données copiées** pour
utiliser les copies précédentes.

### ⏳ Pendant le calcul

Pendant que la requête est active, le planificateur affiche **Calcul en cours** et
la configuration est verrouillée. **Arrêter l'attente** arrête seulement l'attente : le serveur
peut terminer malgré tout, et cette réponse est ignorée.

Si vous modifiez le brouillon après un résultat, une bannière **Résultat non à jour**
apparaît : les valeurs précédentes peuvent encore être consultées, mais elles ne décrivent
plus le brouillon actuel. Depuis la bannière, **Retour au récapitulatif** revient à
la dernière étape, et **Ignorer le résultat précédent** supprime l'ancien résultat et vous y amène aussi.

## 📊 Lire le résultat {: #reading-the-result }

Un plan calculé s'ouvre avec un en-tête : la date du scénario, la devise de
valorisation et la révision du brouillon, puis une rangée de badges. Chaque badge s'explique
lorsque vous le pointez, le touchez ou le mettez au focus. Un plan affiche aussi sa
**distance L2** par rapport aux cibles (le $D$ de l'étape **Stratégie**), combien est
**Non investi**, et combien de notes le calcul a laissées ; les notes sont listées juste en dessous,
sous **Notes sur le calcul**. **Modifier la configuration** vous ramène à l'étape
**Récapitulatif**, et **Calculer un nouveau plan** relance le calcul.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result" alt="Un plan calculé : l'en-tête avec ses badges de résultat, la distance L2, Non investi et les notes, Modifier la configuration et Calculer un nouveau plan ; les Chiffres clés, chacun avec ses parties, à côté de l'encadré Calcul ; et le tableau Allocation par actif, avec la part cible de chaque actif à côté de sa part après le plan, sa valeur après le plan et sa valeur idéale, et les totaux">
</div>

Un calcul se termine par l'un de ces résultats :

| Résultat | Ce que cela signifie |
|---|---|
| **Plan disponible** | Un plan qui respecte toutes les contraintes. Un second badge indique ce qu'il vaut. **Optimalité prouvée** : le solveur a prouvé, dans sa petite marge de calcul (qui augmente avec les montants), qu'aucun meilleur plan n'existe, objectif par objectif dans l'ordre de l'étape **Stratégie**, et la vérification exacte du plan correspond à ses nombres. **Optimalité non prouvée** : le solveur a atteint sa limite de temps ou de nœuds, ou ses propres nombres ne correspondent pas à la vérification exacte du plan ; c'est alors le meilleur plan trouvé, mais il n'est pas prouvé qu'il soit le meilleur. |
| **Aucune opération** | Avec les liquidités que vous avez choisies, aucun achat ne satisfait les contraintes : le plan consiste à ne rien faire. Aucun ordre, aucun change de devises et aucun financement. |
| **Infaisable avec ces contraintes** | Marqué **Infaisabilité prouvée** : aucune combinaison ne satisfait toutes les contraintes dures ensemble. Les contraintes impliquées sont listées (chaque **Achat obligatoire**, et les liquidités pouvant atteindre les courtiers), chacune avec un lien vers l'étape où vous pouvez la modifier. Le planificateur ne choisit pas laquelle assouplir, et aucun plan partiel n'est montré comme valide. |
| **Aucun plan dans les limites** | Le solveur n'a trouvé aucun plan avant d'atteindre sa limite. Ce n'est pas une preuve qu'il n'en existe aucun. Une recherche plus légère aide : moins d'actifs ou de routes, un **Achat maximum** plus bas, ou un **Incrément** plus grand. |
| **Données supplémentaires nécessaires** | Quelque chose manque. Votre brouillon est intact, et aucun actif n'est supprimé silencieusement : ajoutez l'information manquante ou supprimez l'actif vous-même. |
| **Entrée non valide** | Certaines données ne sont pas valides. |
| **Scénario non pris en charge** | Ce n'est pas une erreur dans vos données : l'outil ne gère pas encore ce cas. |

Chaque plan affiché a été revérifié en arithmétique décimale exacte,
indépendamment du solveur : c'est le badge **Vérifié en décimal**. Un dernier
badge indique comment la recherche s'est terminée : **Terminé** (le solveur a terminé sa recherche
de lui-même), **Limite de temps**, ou **Limite de nœuds**. Lorsqu'un plan a été trouvé mais que la recherche
s'est arrêtée à une limite, un avertissement ajoute qu'un meilleur plan peut exister ; le résultat
reste complet et peut être consulté. Si l'arrondi à la plus petite unité d'une devise
laisse un courtier légèrement à court, un avertissement indique combien de liquidités supplémentaires ce
courtier a besoin pour exécuter le plan.

Les trois derniers résultats signifient que le calcul n'a pas pu démarrer sur vos
données : rien n'est calculé, et les problèmes trouvés sont listés, avec un lien vers
l'étape concernée lorsqu'il y en a une. **Détails** ajoute le code backend de chaque problème.

Les erreurs de plateforme, comme un timeout, une file pleine ou un worker planté, ne sont pas des
conclusions financières sur votre scénario : votre brouillon reste intact, réessayez plus tard. Si l'outil
est indisponible, voir [Paramètres → À propos → Diagnostics des plugins](../../settings/about.md).

### 🗂️ Comment un plan est présenté

Sous le résultat, un plan est présenté dans cet ordre :

1. **Chiffres clés** : le plan en quelques nombres, **Base des cibles**,
   **Investi après**, **Non investi**, **Liquidités choisies**, **Coûts**, et
   **Ordres**, chacun avec un **?** qui l'explique et, sous la valeur, les
   parties qui le composent. À côté, l'encadré **Calcul** montre combien de temps l'optimiseur a travaillé,
   le temps alloué à chaque objectif, et combien d'objectifs il a clos.
2. **Allocation par actif** : pour chaque actif, sa part cible à côté de sa part
   après le plan, avec sa valeur idéale $w_i\,R$, sa valeur après le plan
   $V_i$, l'écart par rapport à l'idéal $V_i - w_i\,R$, et la valeur achetée.
3. **Plan opérationnel** : les étapes à suivre, dans l'ordre. D'abord les liquidités
   (**Liquidités disponibles**, **Virement**, **Dépôt**), puis les changes de devises
   que vous faites vous-même, puis un tableau d'ordres par courtier, avec
   l'**Instruction** à saisir chez le courtier, le **Prix**, le **Montant de l'ordre**,
   et les **Frais**. Une conversion que le courtier fait lui-même lors de l'achat
   n'a pas de nombre : elle apparaît au-dessus des ordres de ce courtier comme une
   **Conversion automatique**. Cette section n'est affichée que lorsque le plan a
   quelque chose à faire.
4. **Expositions – idéal vs réel** : cartes et barres par pays, type et secteur,
   construites à partir des compositions des actifs. Les graphiques ne modifient pas le
   plan.
5. **Soldes par courtier et devise** : comment chaque solde de trésorerie évolue, et ce
   qu'il reste.
6. **Preuve et solveur** : comment le résultat a été établi. Les badges de résultat, preuve
   et arrêt, la valeur exacte de chaque objectif, les étapes du solveur, et
   les temps backend.

**Allocation par actif** et **Plan opérationnel** s'ouvrent au départ ; les autres
sections s'ouvrent à la demande, et **Tout développer** / **Tout réduire** les ouvre ou les ferme
ensemble. Sans plan (**Infaisable avec ces contraintes** ou
**Aucun plan dans les limites**), **Preuve et solveur** est la seule section, et
les chiffres clés n'affichent que l'encadré **Calcul**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result-plan" alt="Le Plan opérationnel : étapes numérotées, d'abord les virements et le dépôt qui amènent les liquidités à un courtier, puis un change de devises avec son taux, chacun avec son montant ; puis les ordres de ce courtier, avec Instruction, Prix, Montant de l'ordre et Frais ; et les ordres du courtier suivant">
</div>

Cliquez sur un ordre, ou sur son bouton **Détail**, pour ouvrir son détail : l'instruction,
la quantité économique, les prix utilisés (prix source, prix médian et prix appliqué
avec la marge sur le prix), le débit de liquidités et les frais, les conversions qui le paient, et
la priorité, la limite et les minimums de sa route.
**Afficher la provenance** liste l'origine de chaque valeur, **Copiée** ou **Manuelle**,
avec la date et l'heure de la copie ou de votre saisie.

**Preuve et temps**, en haut du résultat, ouvre **Preuve et solveur** et y fait défiler.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result-proof" alt="La section Preuve et solveur : les badges Résultat, Preuve et Arrêt ; la valeur exacte de chaque objectif, dans l'ordre, avec le bris d'égalité final ; le tableau des Étapes du solveur ; les Temps backend ; et Où le temps a été passé, une barre des phases du calcul">
</div>

Chaque chiffre provient de la comptabilité du backend ; l'interface n'additionne rien.
Avec le mode confidentialité activé (voir [Préférences utilisateur](../../settings/preferences.md)),
le résultat masque ce qui révélerait combien vous possédez : chaque montant (chiffres clés,
valeurs, soldes, montants des ordres, frais et coûts, et les valeurs d'objectif et de solveur
mesurées en argent, la **distance L2** incluse), chaque quantité, et les limites d'achat
d'une route (**Achat minimum**, **Achat obligatoire**, **Achat maximum**). Les montants
dans les problèmes listés lorsqu'un calcul n'a pas pu démarrer sont aussi masqués. Les prix
de marché, taux de change, pourcentages (cibles, parts, poids d'exposition, spreads, et
marges), incréments, priorités, dénombrements, et dates restent visibles, car ils ne disent rien
sur ce que vous possédez.

## 🧮 Ce que fait le moteur de calcul

Le moteur derrière cet outil planifie des **achats**. Étant donné un ensemble d'actifs avec
leurs prix, les courtiers et routes d'achat utilisables pour les atteindre, les liquidités
et nouveaux versements disponibles, et un poids cible par actif, il recherche
la combinaison d'achats dont l'allocation résultante se rapproche le plus possible
de ces cibles.

Trois propriétés méritent d'être connues, car elles déterminent ce que le planificateur peut
promettre :

- **Il achète selon les incréments de chaque courtier.** Unités entières ou montants, toujours en
  multiples de l'incrément que vous définissez : incréments, frais, et devises
  impliquées font partie du problème qu'il résout, et non d'une étape d'arrondi appliquée
  après coup.
- **Ses nombres publiés proviennent d'une arithmétique exacte.** Chaque plan candidat est
  revérifié exactement avant que quoi que ce soit soit affiché. Un plan qui échoue à cette vérification
  n'est jamais publié.
- **Il ne fait jamais passer un plan non prouvé pour optimal.** Un plan arrêté par une limite
  de temps ou de nœuds est affiché comme le meilleur trouvé et marqué
  **Optimalité non prouvée**. Il en va de même pour un plan dont la vérification exacte ne correspond pas aux
  propres nombres du solveur, même lorsque la recherche s'est terminée d'elle-même. Lorsqu'aucun plan n'est
  trouvé, il le dit au lieu de deviner. Avec des montants d'environ dix milliards
  d'unités d'une devise ou plus, les calculs du solveur peuvent perdre en précision : l'outil
  peut alors s'arrêter avec une erreur, ou marquer le plan **Optimalité non prouvée**.

Un calcul terminé rapporte donc l'un des quelques résultats honnêtes
listés dans [Lire le résultat](#reading-the-result).

Le moteur planifie uniquement des achats. Il ne planifie pas de ventes.

## 🎯 Comment lire sa cible

L'allocateur PAC répartit les liquidités disponibles **maintenant** — liquidités
existantes plus nouveaux versements. Ses cibles décrivent comment cet argent doit être
alloué ; elles ne décrivent pas la composition finale d'un portefeuille que vous détenez déjà.

Le calcul ne prend pas du tout les positions que vous détenez déjà comme entrée, donc
les modifier ne peut pas changer ce que cet outil planifie. **Copier la répartition actuelle**
ne fait que les transformer en poids cibles à modifier, et ces poids cibles ne suivent pas
les changements ultérieurs.

## 🚫 Ce que cet outil ne fait jamais

Le planificateur et le calcul derrière lui restent dans le contrat de la plateforme
Outils :

- il ne passe pas d'ordres, n'exécute pas de transactions et ne contacte pas de courtier ;
- il n'écrit pas dans vos actifs, courtiers ou transactions ;
- il ne lit pas votre portefeuille de lui-même : le calcul reçoit uniquement le
  scénario envoyé depuis **Récapitulatif**, et le planificateur lit vos données LibreFolio
  uniquement lorsque vous copiez quelque chose ou ouvrez l'étape **Change** (pour ses taux
  **Auto**), puis à nouveau juste avant un calcul pour les valeurs copiées que vous n'avez
  pas modifiées ;
- son résultat est un plan à évaluer, pas un conseil et pas une instruction.

## 🔒 Vos données financières

Le calcul s'exécute sur le scénario soumis avec la requête. Il ne reçoit
ni portefeuille en direct, ni connexion à la base de données, ni votre session connectée, et
il ne produit rien qui soit stocké.

Votre brouillon vit uniquement dans la page ouverte : il n'est enregistré ni sur le serveur ni
dans le navigateur. Quitter le planificateur, ou recharger ou fermer l'onglet, avec un
brouillon en cours vous demande de confirmer d'abord. Se déconnecter ou changer de compte
supprime le brouillon sans demander.

Comme toujours, évitez de coller de vraies valeurs de portefeuille, des exports de courtiers ou des
identifiants de compte dans des exemples ou des messages d'assistance.

## 🔗 Voir aussi

- [Vue d'ensemble des outils](../index.md)
- [Préférences utilisateur](../../settings/preferences.md), y compris le mode confidentialité
