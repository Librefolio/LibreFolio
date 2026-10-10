# 💸 Rendement sur coût (YOC)

Le rendement sur coût (YOC) mesure le **revenu brut enregistré non négatif produit par unité actuelle sur les 365 dernières dates calendaires**, par rapport au prix de revient unitaire de la position ouverte ([prix de revient unitaire, ou PRU](../weighted-average-cost.md)).

LibreFolio le calcule séparément pour chaque paire $(a,b)$ :

$$
(a,b) = (\text{actif},\ \text{courtier})
$$

Le même actif détenu chez deux courtiers a donc deux valeurs de YOC indépendantes.

!!! warning "Revenu brut enregistré — pas un rendement net d'impôt"

    Le YOC utilise uniquement des montants en espèces non négatifs provenant de transactions `DIVIDEND` et `INTEREST` liées à un actif. Le zéro exact est accepté ; les montants de revenus négatifs ne sont pas pris en charge. Les transactions `TAX` et `FEE` séparées ne sont pas soustraites, le résultat ne doit donc pas être interprété comme une performance après impôt ou un revenu net.

---

## 🧭 Portée et fenêtre glissante

Soit $T$ la date de fin de rapport sélectionnée. Le YOC utilise toujours la fenêtre inclusive :

$$
\boxed{[T-364,\ T]}
$$

Cette fenêtre contient 365 dates calendaires et est **indépendante de la date de début du rapport**. Déplacer le début d'un rapport de tableau de bord ne change pas le YOC lorsque $T$ reste inchangé.

Seules les écritures non négatives et liées à un actif du registre de transactions personnel sont éligibles :

| Inclus | Exclus |
|---|---|
| Lignes `Transaction` liées à un actif de type `DIVIDEND` ou `INTEREST`, avec un montant en espèces égal ou supérieur à zéro | Transactions `TAX`, `FEE` et `ADJUSTMENT` séparées |
| Le montant en espèces non négatif, la devise, la date, l'actif et le courtier payeur | Revenus `AssetEvent` du fournisseur ou manuels |
| Revenus affectés à la paire $(a,b)$ exacte | Revenus sans actif |

Le schéma de transaction accepte un montant en espèces `DIVIDEND` ou `INTEREST` exactement nul, mais rejette un montant négatif. Un `ADJUSTMENT` peut affecter la quantité rejouée, le PRU ou les entrées de division liée, mais il n'entre jamais dans le numérateur des revenus du YOC.

Le calcul n'a pas de liste d'autorisation par classe d'actifs. Il s'applique à tout type de position longue ouverte représenté par le moteur de portefeuille, y compris les crypto-actifs et les actifs manuels, à condition que les entrées requises du registre, du PRU, de la division et du FX soient valides.

---

## 🧮 Définition mathématique

Pour chaque transaction de revenu éligible $j$ :

| Symbole | Signification |
|---|---|
| $D_j$ | Date de transaction |
| $I_j$ | Montant brut en espèces de la transaction non négatif dans la devise $c_j$, avec $I_j\geq0$ |
| $C^*$ | Devise de rapport sélectionnée |
| $q_j$ | Quantité longue éligible chez le courtier payeur à la fin du jour $D_j-1$ |
| $s_j$ | Produit des ratios de division liés datés de $D_j$ à $T$ inclus |
| $w_{a,b,T}$ | Prix d'achat moyen par unité (PRU) de la paire $(a,b)$ à $T$, conservé en $C^*$ aux taux historiques |

### 💱 Conversion des revenus

Chaque montant de revenu est converti dans la devise de rapport à sa propre date de transaction :

$$
I_j^* =
I_j \cdot \mathrm{fx}(c_j,C^*,D_j)
$$

### 🧬 Normalisation en unités actuelles

Le revenu par unité est d'abord réparti sur la quantité éligible de la veille, puis normalisé pour chaque division liée valide à la date du revenu ou après :

$$
g_{a,b,T}
=
\sum_{\substack{j \in (a,b)\\T-364 \leq D_j \leq T}}
\frac{I_j^*}{q_j \cdot s_j}
$$

Pour une division 2 pour 1, $s_j=2$ : le revenu historique par ancienne unité est divisé par deux afin qu'il soit comparable aux unités actuelles. Une division liée datée au $D_j$ est également incluse.

### 📊 Dénominateur du prix d'achat moyen

Le dénominateur est le prix d'achat moyen par unité de la position, **déjà exprimé dans la devise de rapport** : lors de la construction de la moyenne, chaque acquisition y est entrée au taux de sa propre date (voir la section multi-devises de [prix de revient unitaire](../weighted-average-cost.md)) :

$$
w_{a,b,T}^*
=
\frac{C^{*}_{a,b,T}}{Q_{a,b,T}}
$$

où $Q_{a,b,T}$ est la quantité du pool de coût moyen de la paire à $T$ et $C^{*}_{a,b,T}$ son coût historique en $C^*$ : chaque acquisition $i$ a ajouté $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ pour le montant $P_i$ payé à la date $d_i$, et chaque réduction a retiré sa part proportionnelle.

Aucune conversion n'est appliquée à la date de fin de rapport $T$ : le dénominateur correspond à ce qui a été payé et ne bouge pas avec le taux de change du jour.

LibreFolio affiche ensuite :

$$
\boxed{
\mathrm{YOC}_{a,b,T}
=
\frac{g_{a,b,T}}{w_{a,b,T}^*}
}
$$

La valeur de l'API est une fraction, et le tableau Positions la restitue sous forme de pourcentage. Une valeur disponible peut être positive ou exactement nulle.

---

## 🔁 Règles de quantité, conservation, transfert et division

La quantité éligible $q_j$ est délibérément évaluée à la **fin du jour précédant le paiement** :

- seule la quantité `LONG` compte ;
- un **achat du jour même est exclu** ;
- une **vente du jour même est incluse**, car ces unités existaient à la fin du jour $D_j-1$ ;
- la conservation par courtier est respectée tout au long du rejeu des transferts ;
- un fragment en transit compte toujours pour son courtier d'origine, jamais pour la destination avant son arrivée.

Les revenus restent rattachés au courtier qui les a enregistrés. Déplacer des unités du courtier A vers le courtier B ne **transfère pas** automatiquement les revenus historiques de A dans le YOC de B. Les revenus ultérieurs enregistrés chez B utilisent la quantité éligible de la veille de B et le prix d'achat moyen de B.

Les divisions liées ultérieures et du jour même remettent à l'échelle les revenus par unité antérieurs dans les unités qui existent à $T$. LibreFolio utilise des lignes de division liées explicites ; il ne déduit pas de retraitement à l'échelle de l'actif à partir d'une division enregistrée uniquement chez un autre courtier. Si un rejeu connecté entre courtiers contient une division mais n'a pas de ligne de division correspondante pour le courtier des revenus/actuel, la normalisation est ambiguë et le YOC échoue en mode fermé. Une division liée invalide, dupliquée, non concordante ou non positive rend également la paire concernée indisponible au lieu de produire un résultat approximatif.

Les transactions `ADJUSTMENT` restent uniquement des entrées de rejeu : elles peuvent modifier la quantité ou le PRU et porter une division liée, mais leurs montants ne comptent jamais comme revenus.

??? example "Transactions du jour même et division ultérieure"

    Supposons qu'un dividende de 20 € soit enregistré le 30 juin. Le courtier payeur détenait 100 unités longues éligibles à la fin du jour du 29 juin. Un achat ou une vente le 30 juin ne change pas ce dénominateur.

    Une division liée 2 pour 1 survient entre le 30 juin et $T$, donc :

    $$
    g = \frac{20}{100 \times 2} = 0.10\ \mathrm{EUR}
    $$

    Si le prix d'achat moyen (PRU) à $T$ est de 4,00 € par unité actuelle :

    $$
    \mathrm{YOC} =
    \frac{0.10\ \mathrm{EUR}}{4.00\ \mathrm{EUR}}
    = 2.50\%
    $$

---

## 🌍 Résolution FX et provenance

Le YOC utilise la politique FX historique actuelle du portefeuille :

- les revenus demandent un FX pour $D_j$ ;
- le prix d'achat moyen (PRU) n'a pas besoin de FX à $T$ : chacune de ses acquisitions a été convertie à sa propre date lors de la construction de la moyenne ;
- lorsque la date exacte est absente, le dernier taux stocké à cette date ou avant est utilisé ;
- aucun taux à terme n'est substitué.

La provenance conserve à la fois la **date demandée** et la **date réelle du taux** de chaque conversion de revenu, ainsi que la paire de devises et les jours reportés en arrière. L'infobulle Positions peut donc montrer, par exemple, qu'une conversion de revenu du 30 juin a utilisé le taux le plus récent du 28 juin.

Si une conversion de revenu requise ne peut pas être résolue, la paire entière est indisponible. Si le coût d'une acquisition ne peut pas être converti — ou si un transfert ou un ajustement n'a pas de coût de base — le prix d'achat moyen lui-même est indisponible, et le YOC aussi. LibreFolio n'omet pas silencieusement la transaction concernée ni ne réutilise une valeur non liée.

---

## 🚦 Disponibilité et comportement d'échec en mode fermé

Le YOC distingue une absence valide de revenus d'un calcul auquel on ne peut pas faire confiance.

| État | Signification | Cellule Positions |
|---|---|---|
| **Disponible** | Au moins une transaction de revenu éligible existe et chaque entrée requise est valide. Le résultat est positif lorsqu'un montant éligible est positif ; il est exactement nul lorsqu'une ou plusieurs lignes éligibles sont enregistrées à un montant nul et qu'aucune n'a de montant positif. La provenance marque ce cas exactement nul avec `net_zero=true`. Aucun âge minimal de la paire ne s'applique. | Pourcentage avec deux décimales : par exemple, `2.50%` ou `0.00%`. |
| **Aucun revenu** | Aucune ligne de revenu éligible n'existe dans la fenêtre, et la paire dispose d'un historique de registre complet de 365 dates. La valeur de l'API est nulle, mais cet état se distingue d'un zéro disponible. | `-` avec une infobulle explicative et sans icône d'avertissement. |
| **Indisponible** | La paire sans revenu est trop jeune, ou une entrée requise du registre/calcul a échoué à la validation. Sa valeur est `null` et sa raison identifie l'échec. | `-` avec une icône d'information et une infobulle de raison personnalisée. |

Le champ externe `yield_on_cost` est requis et non nul pour chaque position. Un résultat indisponible est donc représenté par le statut `unavailable` de l'objet de résultat et une `value` nulle, et non par un champ externe manquant ou nul.

Soit $F_{a,b}$ la toute première date de transaction liée à un actif pour la paire. Un résultat sans revenu devient valide uniquement lorsque :

$$
(T-F_{a,b})+1 \geq 365
$$

De manière équivalente, $F_{a,b} \leq T-364$. Fermer puis rouvrir la position plus tard ne **réinitialise pas** cet âge : la première transaction d'origine de la paire reste l'ancre.

Ce seuil d'un an est évalué **uniquement lorsque la fenêtre glissante ne contient aucune transaction de revenu éligible**. Ce n'est pas une règle d'annualisation : une paire plus jeune avec des revenus enregistrés valides peut avoir un YOC disponible, car la métrique additionne simplement les revenus observés à l'intérieur de $[T-364,T]$.

Le calcul échoue en mode fermé pour l'une quelconque de ces conditions :

- le revenu n'a pas de quantité longue éligible à la fin du jour $D_j-1$ ;
- le rejeu des transactions ou des transferts est incohérent ;
- les données de division liée sont invalides ou incohérentes ;
- le FX historique requis est manquant ;
- le prix d'achat moyen (PRU) est manquant ou non positif — manquant inclut une acquisition dont le coût n'a pas pu être converti ou qui n'a pas de coût de base.

Une seule entrée requise incorrecte rend la paire entière indisponible. Il n'y a pas de somme partielle, de substitut d'événement d'actif, de fallback sur les revenus du fournisseur ou d'approximation par la quantité actuelle.

---

## 🖥️ Lecture du YOC dans LibreFolio

Le YOC apparaît dans le tableau **Positions** partagé, utilisé à la fois par l'onglet Positions du tableau de bord et par l'onglet Positions de chaque courtier :

- visible par défaut immédiatement à côté de **Annualisé** ;
- les valeurs disponibles, y compris le zéro exact, sont fixées à deux décimales ;
- les valeurs positives n'ont pas de `+` initial ;
- un zéro disponible apparaît comme `0.00%` et a `net_zero=true` dans sa provenance ;
- un tiret normal sans revenu n'a pas d'icône d'avertissement ;
- un tiret indisponible a une icône d'information dont l'infobulle explique la raison spécifique et la provenance disponible ;
- les choix d'affichage/masquage sont partagés entre les vues Tableau de bord et courtier et persistent entre les sessions.

Chaque ligne reste spécifique à un courtier. Dans la portée multi-courtiers du tableau de bord, deux lignes pour le même actif peuvent donc afficher des valeurs différentes. Voir [Positions et analyse](../../../../user/dashboard/positions.md) pour le guide du tableau destiné à l'utilisateur.

---

## ⚖️ Ce que le YOC n'est pas

| Métrique | Dénominateur et horizon | Pourquoi elle diffère du YOC de LibreFolio |
|---|---|---|
| [**Rendement du dividende de marché**](../../../instruments/asset-events/dividend.md) | Dividende annuel par action divisé par le prix de marché actuel | Mesure de marché/fournisseur ; le YOC utilise uniquement les revenus personnels enregistrés et le prix d'achat moyen (PRU). |
| **Rendement cumulé en espèces** | Revenu total sur la durée de vie divisé par le coût de base total actuel | Le YOC utilise uniquement $[T-364,T]$, reconstruit le revenu par unité historique éligible et ne divise pas les espèces sur la durée de vie par le coût de base agrégé d'aujourd'hui. |
| [**Rendement net annualisé / CAGR**](net-annualized-return.md) | Rendement total net composé sur la fenêtre de détention | Inclut la performance de marché, les revenus, les frais et les impôts ; le YOC isole le revenu brut enregistré et n'est pas annualisé à partir d'un rendement cumulé. |
| [**Rendement courant d'une obligation**](../../../instruments/asset-events/interest.md) | Coupon annuel divisé par le prix actuel de l'obligation | Mesure du coupon/prix au niveau du titre ; le YOC utilise le registre de courtier enregistré de l'investisseur et le PRU. |
| [**Rendement à l'échéance (YTM)**](../../../instruments/asset-events/interest.md) | Taux d'actualisation égalisant les coupons futurs et la valeur de remboursement d'une obligation à son prix | TRI obligataire prospectif ; le YOC est rétrospectif, basé sur les transactions et s'applique à tout type de position. |

---

## 🔗 Connexe

- 📊 [prix de revient unitaire](../weighted-average-cost.md) — dénominateur du prix d'achat moyen
- 🖥️ [Positions du tableau de bord](../../../../user/dashboard/positions.md) — états des colonnes, formatage et préférence partagée
- 💰 [Transactions de dividendes et d'intérêts](../../../instruments/transaction-types/dividend-interest.md) — écritures éligibles du registre personnel
- ⚙️ [Moteur de portefeuille](index.md) — état de position et couche de métriques
