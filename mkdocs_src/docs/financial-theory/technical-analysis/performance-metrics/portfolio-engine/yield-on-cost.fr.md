# 💸 Rendement sur coût (YOC)

Le rendement sur coût (YOC) mesure le **revenu brut enregistré produit par unité actuelle sur les 365 dates calendaires glissantes**, par rapport au prix d’achat moyen par unité de la position ouverte ([prix de revient unitaire, ou PRU](../weighted-average-cost.md)). Chaque montant de revenu compte avec son signe, de sorte qu’une correction enregistrée diminue le revenu au lieu de s’y ajouter.

LibreFolio le calcule séparément pour chaque paire $(a,b)$ :

$$
(a,b) = (\text{actif},\ \text{courtier})
$$

Le même actif détenu chez deux courtiers a donc deux valeurs YOC indépendantes.

!!! warning "Revenu brut enregistré — pas un rendement net d’impôt"

    Le YOC utilise uniquement les montants en liquidités des transactions `DIVIDEND` et `INTEREST` liées à un actif, chaque montant étant compté avec son signe. Un nouveau montant négatif est refusé, mais des lignes plus anciennes peuvent encore en contenir un : une telle correction diminue le revenu, comme dans le tableau de bord. Les transactions `TAX` et `FEE` distinctes ne sont pas soustraites, de sorte que le résultat ne doit pas être lu comme une performance après impôt ni comme une performance de revenu net.

---

## 🧭 Périmètre et fenêtre glissante

Soit $T$ la date de fin de rapport sélectionnée. Le YOC utilise toujours la fenêtre inclusive :

$$
\boxed{[T-364,\ T]}
$$

Cette fenêtre contient 365 dates calendaires et est **indépendante de la date de début du rapport**. Déplacer le début d’un rapport du tableau de bord ne change pas le YOC lorsque $T$ reste inchangée.

Seules les écritures liées à un actif issues du registre personnel des transactions sont éligibles :

| Inclus | Exclus |
|---|---|
| Lignes `Transaction` liées à un actif de type `DIVIDEND` ou `INTEREST`, quel que soit le signe de leur montant en liquidités | Transactions `TAX`, `FEE` et `ADJUSTMENT` distinctes |
| Le montant en liquidités signé, la devise, la date, l’actif et le courtier payeur | Revenus `AssetEvent` de fournisseur ou manuels |
| Revenus affectés à la paire $(a,b)$ exacte | Revenus sans actif |

Le schéma de transaction accepte un montant en liquidités exactement nul pour une transaction `DIVIDEND` ou `INTEREST`, mais refuse tout nouveau montant négatif. Une ligne négative enregistrée auparavant reste éligible et compte avec son signe. Un `ADJUSTMENT` peut affecter la quantité rejouée, le PRU ou les entrées de division liée, mais il n’entre jamais dans le numérateur des revenus du YOC.

Le calcul n’applique pas de liste d’autorisation par classe d’actif. Il s’applique à tout type de position longue ouverte représenté par le moteur de portefeuille, y compris les cryptomonnaies et les actifs manuels, à condition que les entrées requises de registre, de PRU, de division et de FX soient valides.

---

## 🧮 Définition mathématique

Pour chaque transaction de revenu éligible $j$ :

| Symbole | Signification |
|---|---|
| $D_j$ | Date de la transaction |
| $I_j$ | Montant brut en liquidités de la transaction dans la devise $c_j$, avec son signe : $I_j<0$ pour une correction négative antérieure |
| $C^*$ | Devise de rapport sélectionnée |
| $q_j$ | Quantité longue éligible chez le courtier payeur à la fin de la journée $D_j-1$ |
| $s_j$ | Produit des ratios des divisions liées datées de $D_j$ à $T$, bornes incluses |
| $w_{a,b,T}$ | Prix de revient unitaire (PRU) de la paire $(a,b)$ à $T$, conservé en $C^*$ aux taux historiques |

### 💱 Conversion des revenus

Chaque montant de revenu est converti dans la devise de rapport à sa propre date de transaction :

$$
I_j^* =
I_j \cdot \mathrm{fx}(c_j,C^*,D_j)
$$

### 🧬 Normalisation par unité actuelle

Le revenu par unité est d’abord réparti sur la quantité éligible de la veille, puis normalisé pour chaque division liée valide à la date du revenu ou après :

$$
g_{a,b,T}
=
\sum_{\substack{j \in (a,b)\\T-364 \leq D_j \leq T}}
\frac{I_j^*}{q_j \cdot s_j}
$$

Pour une division 2 pour 1, $s_j=2$ : le revenu historique par ancienne unité est divisé par deux afin d’être comparable aux unités actuelles. Une division liée datée de $D_j$ est également incluse.

### 📊 Dénominateur du prix de revient unitaire

Le dénominateur est le prix de revient unitaire de la position, **déjà exprimé dans la devise de rapport** : lors de la construction de la moyenne, chaque acquisition y est entrée au taux de sa propre date (voir la section multidevise de [Prix de revient unitaire (PRU)](../weighted-average-cost.md)) :

$$
w_{a,b,T}^*
=
\frac{C^{*}_{a,b,T}}{Q_{a,b,T}}
$$

où $Q_{a,b,T}$ est la quantité du pool de coût moyen de la paire à $T$ et $C^{*}_{a,b,T}$ son coût historique en $C^*$ : chaque acquisition $i$ a ajouté $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ pour le montant $P_i$ payé à la date $d_i$, et chaque réduction a retiré sa part proportionnelle.

Aucune conversion n’est appliquée à la date de fin de rapport $T$ : le dénominateur correspond à ce qui a été payé et ne varie pas avec le taux de change du jour.

LibreFolio indique ensuite :

$$
\boxed{
\mathrm{YOC}_{a,b,T}
=
\frac{g_{a,b,T}}{w_{a,b,T}^*}
}
$$

La valeur de l’API est une fraction, et le tableau Positions l’affiche sous forme de pourcentage. Une valeur disponible peut être positive ou exactement nulle. Lorsque $g_{a,b,T}<0$ — les corrections de la fenêtre dépassent ses revenus — LibreFolio n’affiche aucun YOC (voir les règles de disponibilité ci-dessous).

---

## 🔁 Règles de quantité, de conservation, de transfert et de division

La quantité éligible $q_j$ est délibérément évaluée à la **fin de la journée précédant le paiement** :

- seule la quantité `LONG` compte ;
- un **achat le même jour est exclu** ;
- une **vente le même jour est incluse**, car ces unités existaient à la fin de la journée $D_j-1$ ;
- la conservation par le courtier est respectée tout au long du rejeu des transferts ;
- un fragment en transit compte toujours pour son courtier source, jamais pour la destination avant son arrivée ;
- les unités qui arrivent d’un courtier que vous ne pouvez pas voir — par exemple en tant que copropriétaire du courtier destinataire — comptent à partir de leur arrivée : l’autre courtier n’est jamais rejoué, et leur coût est le coût de base propre du transfert entrant, qui fait partie du prix de revient unitaire (sans celui-ci, le YOC est indisponible).

Le revenu reste rattaché au courtier qui l’a enregistré. Déplacer des unités du courtier A vers le courtier B ne transfère **pas** automatiquement les revenus historiques de A dans le YOC de B. Les revenus ultérieurs enregistrés chez B utilisent la quantité éligible de la veille de B et le prix de revient unitaire de B.

Les divisions liées ultérieures et du même jour remettent à l’échelle les revenus antérieurs par unité dans les unités qui existent à $T$. LibreFolio utilise des lignes de division liée explicites ; il ne déduit pas un retraitement à l’échelle de l’actif à partir d’une division enregistrée uniquement chez un autre courtier. Si un rejeu connecté entre courtiers contient une division mais ne comporte pas de ligne de division correspondante pour le courtier du revenu ou le courtier actuel, la normalisation est ambiguë et le YOC échoue en mode fermé. Une division liée invalide, dupliquée, non concordante ou non positive rend de même la paire concernée indisponible au lieu de produire un résultat approximatif.

Les transactions `ADJUSTMENT` restent uniquement des entrées de rejeu : elles peuvent modifier la quantité ou le PRU et peuvent porter une division liée, mais leurs montants ne comptent jamais comme revenus.

??? example "Transactions du même jour et division ultérieure"

    Supposons qu’un dividende de 20 € soit enregistré le 30 juin. Le courtier payeur détenait 100 unités longues éligibles à la fin de la journée du 29 juin. Un achat ou une vente le 30 juin ne change pas ce dénominateur.

    Une division liée 2 pour 1 intervient entre le 30 juin et $T$, donc :

    $$
    g = \frac{20}{100 \times 2} = 0.10\ \mathrm{EUR}
    $$

    Si le prix de revient unitaire (PRU) à $T$ est de 4,00 € par unité actuelle :

    $$
    \mathrm{YOC} =
    \frac{0.10\ \mathrm{EUR}}{4.00\ \mathrm{EUR}}
    = 2.50\%
    $$

---

## 🌍 Résolution FX et provenance

Le YOC utilise la politique FX historique actuelle du portefeuille :

- les revenus demandent une conversion FX pour $D_j$ ;
- le prix de revient unitaire (PRU) ne nécessite aucune conversion FX à $T$ : chacune de ses acquisitions a été convertie à sa propre date lors de la construction de la moyenne ;
- lorsque la date exacte est absente, le dernier taux de change stocké à cette date ou avant est utilisé ;
- aucun taux futur n’est substitué.

La provenance conserve à la fois la **date demandée** et la **date réelle du taux** de chaque conversion de revenu, ainsi que la paire de devises et le nombre de jours reportés en arrière. L’infobulle du tableau Positions peut donc montrer, par exemple, qu’une conversion de revenu du 30 juin a utilisé le taux le plus récent du 28 juin.

Si une conversion de revenu requise ne peut pas être résolue, toute la paire est indisponible. Si le coût d’une acquisition ne peut pas être converti — ou si un transfert ou un ajustement n’a pas de coût de base — le prix de revient unitaire lui-même est indisponible, et le YOC l’est aussi. LibreFolio n’omet pas silencieusement la transaction concernée et ne réutilise pas une valeur sans rapport.

---

## 🚦 Disponibilité et comportement en mode fermé

Le YOC distingue une absence valide de revenu d’un calcul auquel on ne peut pas faire confiance.

| État | Signification | Cellule du tableau Positions |
|---|---|---|
| **Disponible** | Il existe au moins une transaction de revenu éligible, chaque entrée requise est valide et le revenu signé par unité $g_{a,b,T}$ est supérieur ou égal à zéro. Le résultat est positif lorsque $g_{a,b,T}>0$ ; il est exactement nul lorsque $g_{a,b,T}=0$ — par exemple lorsque chaque ligne éligible est enregistrée avec un montant nul, ou qu’une correction compense exactement le revenu. La provenance marque ce cas de zéro exact avec `net_zero=true`. Aucun âge minimum de paire ne s’applique. | Pourcentage avec deux décimales : par exemple, `2.50%` ou `0.00%`. |
| **Aucun revenu** | Aucune ligne de revenu éligible n’existe dans la fenêtre, et la paire possède un historique de registre complet de 365 dates. La valeur de l’API est nulle, mais cet état se distingue d’un zéro disponible. | `-` avec une infobulle explicative et sans icône d’avertissement. |
| **Indisponible** | La paire sans revenu est trop jeune, une entrée requise de registre/calcul a échoué à la validation, ou les corrections laissent le revenu par unité inférieur à zéro. Sa valeur est `null` et sa raison identifie la cause. | `-` avec une icône d’information et une infobulle personnalisée indiquant la raison. |

Le champ externe `yield_on_cost` est obligatoire et non nul pour chaque position. Un résultat indisponible est donc représenté par le statut `unavailable` et une `value` à null de l’objet de résultat, et non par un champ externe absent ou nul.

Soit $F_{a,b}$ la toute première date de transaction liée à un actif pour la paire. Un résultat sans revenu ne devient valide que lorsque :

$$
(T-F_{a,b})+1 \geq 365
$$

De manière équivalente, $F_{a,b} \leq T-364$. La clôture puis la réouverture ultérieure de la position ne réinitialise **pas** cet âge : la première transaction d’origine de la paire reste l’ancre.

Ce seuil d’un an est évalué **uniquement lorsque la fenêtre glissante ne contient aucune transaction de revenu éligible**. Ce n’est pas une règle d’annualisation : une paire plus jeune avec des revenus enregistrés valides peut avoir un YOC disponible, car la mesure additionne simplement les revenus observés dans $[T-364,T]$.

Le calcul échoue en mode fermé pour l’une des conditions suivantes :

- le revenu ne dispose d’aucune quantité longue éligible à la fin de la journée $D_j-1$ ;
- le rejeu des transactions ou des transferts est incohérent ;
- les données de division liée sont invalides ou incohérentes ;
- la conversion FX historique requise est manquante ;
- le prix de revient unitaire (PRU) est manquant ou non positif — le terme « manquant » englobe le cas d’une acquisition dont le coût n’a pas pu être converti ou qui n’a pas de coût de base.

Une seule entrée requise incorrecte rend toute la paire indisponible. Il n’y a ni somme partielle, ni substitut d’événement d’actif, ni fallback sur les revenus du fournisseur, ni approximation par la quantité actuelle.

Un revenu négatif n’est pas une entrée incorrecte, mais il ne laisse aucun rendement à afficher. Lorsque toutes les entrées sont valides et que $g_{a,b,T}<0$ — les corrections enregistrées dans la fenêtre dépassent ses revenus — la paire est indisponible avec la raison `negative_net_income`, et l’infobulle du tableau Positions affiche *Les corrections dépassent les revenus de l’année écoulée.* Sa provenance conserve le revenu négatif par unité (`gross_income_per_unit`). Une somme exactement nulle n’entre pas dans ce cas : elle reste disponible à `0.00%`, avec `net_zero=true`.

---

## 🖥️ Lire le YOC dans LibreFolio

Le YOC apparaît dans le tableau **Positions** partagé, utilisé à la fois par l’onglet Positions du tableau de bord et par l’onglet Positions de chaque courtier :

- visible par défaut immédiatement à côté de **Annualisé** ;
- les valeurs disponibles, y compris le zéro exact, sont fixées à deux décimales ;
- les valeurs positives n’ont pas de `+` initial ;
- un zéro disponible apparaît sous la forme `0.00%` et a `net_zero=true` dans sa provenance ;
- un tiret normal sans revenu n’a pas d’icône d’avertissement ;
- un tiret indisponible a une icône d’information dont l’infobulle explique la raison précise et la provenance disponible ;
- les choix d’affichage/masquage sont partagés entre les vues du tableau de bord et du courtier et persistent d’une session à l’autre.

Chaque ligne reste propre au courtier. Dans le périmètre multi-courtiers du tableau de bord, deux lignes pour le même actif peuvent donc afficher des valeurs différentes. Voir [Positions et analyse](../../../../user/dashboard/positions.md) pour le guide du tableau destiné à l’utilisateur.

---

## ⚖️ Ce que le YOC n’est pas

| Métrique | Dénominateur et horizon | Pourquoi elle diffère du YOC de LibreFolio |
|---|---|---|
| [**Rendement du dividende de marché**](../../../instruments/asset-events/dividend.md) | Dividende annuel par action divisé par le cours actuel du marché | Mesure de marché/fournisseur ; le YOC utilise uniquement les revenus personnels enregistrés et le prix de revient unitaire (PRU). |
| **Rendement cumulé des liquidités** | Revenus totaux sur la durée de vie divisés par le coût de base total actuel | Le YOC utilise uniquement $[T-364,T]$, reconstruit le revenu par unité historique éligible et ne divise pas les liquidités sur la durée de vie par le coût de base agrégé du jour. |
| [**Rendement net annualisé / CAGR**](net-annualized-return.md) | Rendement total net composé sur la fenêtre de détention | Inclut la performance de marché, les revenus, les frais et les impôts ; le YOC isole les revenus bruts enregistrés et n’est pas annualisé à partir d’un rendement cumulé. |
| [**Rendement courant d’une obligation**](../../../instruments/asset-events/interest.md) | Coupon annuel divisé par le prix actuel de l’obligation | Mesure coupon/prix au niveau du titre ; le YOC utilise le registre de courtier consigné par l’investisseur et le PRU. |
| [**Rendement à l’échéance (YTM)**](../../../instruments/asset-events/interest.md) | Taux d’actualisation égalant les coupons futurs et la valeur de remboursement d’une obligation à son prix | TRI obligataire prospectif ; le YOC est rétrospectif, fondé sur les transactions et s’applique à tout type de position. |

---

## 🔗 Voir aussi

- 📊 [Prix de revient unitaire (PRU)](../weighted-average-cost.md) — dénominateur du prix de revient unitaire
- 🖥️ [Positions du tableau de bord](../../../../user/dashboard/positions.md) — états des colonnes, formatage et préférence partagée
- 💰 [Transactions de dividendes et d’intérêts](../../../instruments/transaction-types/dividend-interest.md) — écritures éligibles du registre personnel
- ⚙️ [Moteur de portefeuille](index.md) — état des positions et couche de métriques
