# 🔬 Analyse des lots FIFO

L'analyse des lots FIFO est le complément **par lot** au [prix de revient unitaire (PRU)](../weighted-average-cost.md).

Le PRU répond à la question : _« Quel est mon coût moyen combiné pour cette position ? »_ L'analyse des lots FIFO répond à une autre question : _« Comment chaque lot d'achat individuel se comporte-t-il dans le temps ? »_

Au lieu de fusionner toutes les acquisitions dans un seul ensemble, LibreFolio suit chaque lot tout au long de son cycle de vie — **ouvert**, **partiellement clôturé**, **entièrement clôturé** — et apparie les ventes dans l'ordre **FIFO** (premier entré, premier sorti).

!!! info "Complément, pas remplacement"

    Le PRU est agrégé et au niveau de la position. L'analyse des lots FIFO est granulaire et au niveau du lot. Les deux vues sont utiles : l'une pour le coût de base combiné, l'autre pour l'attribution économique lot par lot.

---

## 💡 Qu'est-ce que l'analyse des lots FIFO ?

Un **lot** est un lot d'acquisition : par exemple, un achat de 100 actions, ou un transfert entrant qui conserve le coût de base historique.

Lorsqu'une vente se produit, les lots encore ouverts les plus anciens sont clôturés en premier. Cela crée un historique lot par lot :

- quelle part de chaque lot est encore ouverte
- quelle part a déjà été vendue
- quel produit de vente ce lot a généré
- quel revenu a été perçu pendant que ce lot était détenu
- quelle part du rendement provient de la variation de prix par rapport aux revenus en espèces

Cela rend l'analyse des lots FIFO particulièrement utile lorsque deux positions sur le même actif ont été achetées à des prix ou à des dates très différents.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Chronologie de la vie et de la conservation des lots — chaque barre représente un lot, colorée selon le courtier dépositaire, avec une épaisseur proportionnelle à la quantité détenue">
</div>

La chronologie **Vie et conservation des lots** ci-dessus visualise le cycle de vie : chaque barre est un lot, colorée selon le courtier qui le détient actuellement, avec une épaisseur proportionnelle à la quantité encore détenue dans ce segment. Une barre qui se termine au milieu du graphique correspond à un lot entièrement clôturé ; une barre qui atteint « aujourd'hui » est encore ouverte.

---

## 🧮 Rendement ouvert par lot

**Le rendement ouvert** isole la variation **de prix seule** d'un lot par rapport à son prix de référence d'ouverture.

$$
\text{RelativeReturn} = \frac{\text{MarketPrice}}{\text{ReferenceUnitPrice}} - 1
$$

$\text{MarketPrice}$ est le prix de marquage de l'actif issu du [résolveur unifié](../portfolio-engine/price-resolution.md) : à la date de fin pour le résumé du lot, chaque jour pour l'historique du rendement. La référence dépend de ce qui a ouvert le lot :

- **Une opération** — un achat, ou une vente qui ouvre un lot short : le prix unitaire propre au lot, même lorsque l'actif dispose d'une cotation de marché ce jour-là. Une opération est un prix.
- **Un ajustement** — une position d'ouverture, une succession, un transfert depuis un courtier non suivi : son coût de base est un coût, pas un prix ; la référence est donc le prix de marquage de l'actif le jour d'ouverture. Il s'agit du prix du dernier jour, à cette date ou avant, qui en dispose — sa cotation de marché ou, à défaut de cotation, le prix moyen de ses opérations d'achat et de vente, jamais un ajustement — reporté. Pour un actif qui n'a encore rien d'autre, le coût d'un transfert entrant constitue lui aussi un tel prix, à titre d'[estimation](../portfolio-engine/price-resolution.md#transfer-cost-estimate) : un transfert depuis un courtier hors périmètre, sur un actif sans cotation et sans autre opération à cette date ou avant, obtient son propre coût comme référence, signalé comme fallback (`REFERENCE_PRICE_FALLBACK`).
- **Un ajustement avant tout prix** — aucune cotation, aucun achat, aucune vente ni aucune estimation de coût de transfert à sa date d'ouverture ou avant : le prix unitaire propre au lot, son coût de base unitaire. Sans coût de base, ce prix est nul, et le lot n'a pas de rendement ouvert.

`reference_price_source` vaut `exact` pour une cotation de marché du jour d'ouverture lui-même et pour le prix propre au lot, et `fallback` pour une cotation reportée depuis un jour antérieur ou un prix dérivé d'opérations. La bannière de qualité des données signale un tel fallback (`REFERENCE_PRICE_FALLBACK`), ainsi qu'un ajustement sans prix à sa date d'ouverture ou avant (`REFERENCE_PRICE_UNAVAILABLE`).

Chaque prix est converti dans la devise cible au taux de son propre jour : $\text{MarketPrice}$ au taux du jour qu'il valorise, la référence au taux de la date d'ouverture, même lorsqu'elle a été reportée depuis une cotation ou une opération antérieure. Pour un prix dans une devise autre que la devise cible, le rendement ouvert inclut donc la variation du taux de change depuis l'ouverture.

Cette mesure exclut les dividendes, les intérêts et les produits de vente réalisés. Elle répond à la question : _« Dans quelle mesure le prix du marché a-t-il évolué depuis l'ouverture de ce lot ? »_

!!! example "Un lot reçu par succession"

    Un actif est coté à 50 le 7 mars et acheté à 52 le 9 mars, sans cotation depuis. Un lot reçu par succession le 10 mars a une référence de **52** : l'achat constitue le prix le plus récent de l'actif à cette date ou avant, reporté. Son `reference_price_source` est `fallback`, car 52 n'est pas une cotation du 10 mars ; une cotation du 10 mars lui-même serait la référence, avec `exact`.

!!! tip "Le prix propre au lot, sur l'axe des cotations"

    Lorsque la référence est le prix propre au lot, LibreFolio le met à l'échelle de la convention de cotation de l'actif. Cela évite des rendements en pourcentage trompeurs sur les instruments cotés pour 100 unités nominales. Un prix de marquage issu du résolveur est déjà sur cet axe.

    La référence est alors $\text{OpeningUnitPrice}\times qbq$. Pour `qbq = 100`, une obligation achetée à `0.992` se compare à l'axe de cotation du marché comme `99.20`, et non `0.992`.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="Graphique PRU / Prix du marché — une bulle par lot, colorée selon le courtier d'ouverture, dimensionnée selon la valeur d'ouverture, tracée face à la ligne du prix du marché">
</div>

Le graphique **PRU / Prix du marché** représente chaque lot sous forme de bulle face à la ligne du prix du marché : la couleur de la bulle indique le courtier où le lot a été ouvert, sa taille est proportionnelle à la valeur d'ouverture du lot. Un lot dont la valeur actuelle est estimée au coût — son actif n'a aucun prix à la date de fin, voir [Estimé au coût](#estimated-at-cost) — est dessiné avec un contour en pointillés.

---

## 💰 Rendement total par lot

**Le rendement total** est plus large que le rendement ouvert. Il inclut la valeur de marché restante du lot, tout produit de vente déjà réalisé sur ce lot — un ajustement sortant n'en ajoute aucun, n'ayant pas de valeur — et tout revenu alloué perçu pendant que le lot était détenu.

Les calculs de lots de LibreFolio utilisent exactement ces blocs de construction :

$$
\text{OpeningValue} = \text{OriginalCost}
$$

$$
\text{Proceeds}(t) = \sum \text{Closure Proceeds} \text{ up to } t
$$

$$
\text{TotalValue}(t) = \text{OpenValue}(t) + \text{Proceeds}(t)
$$

$$
\text{PnL}(t) = \text{TotalValue}(t) - \text{OriginalCost}
$$

$$
\text{MarketPnL} = \text{PnL} - \text{RealizedPnL}
$$

$$
\text{RealizedPnL} = \sum \text{Closure Realized PnL}
$$

$$
\text{AssetIncome} = \sum_t \text{Income}_i(t)
$$

$$
\text{TotalPnL} = \text{MarketPnL} + \text{RealizedPnL} + \text{AssetIncome}
$$

Chaque montant est dans la devise cible de l'analyse. Pour un lot acheté ou vendu dans une autre devise, chaque clôture convertit ses deux jambes à leurs propres dates — voir [Lots dans une autre devise](#lots-in-another-currency).

Pour le résumé scalaire du lot, le pourcentage de rendement est :

$$
\text{TotalReturn} = \frac{\text{TotalPnL}}{\text{OpeningValue}}
$$

Pour l'historique du rendement dans le temps, LibreFolio utilise :

$$
\text{TotalReturn}(t) = \frac{\text{TotalValue}(t) + \text{Income}(t)}{\text{OriginalCost}} - 1
$$

Cela répond à la question : _« Quel est le rendement économique complet de ce lot, en incluant à la fois la variation de prix et le rendement en espèces ? »_

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Graphique de comparaison Valeur / Rendement en mode Rendement — pourcentage de rendement par lot depuis la propre date d'ouverture de chaque lot">
</div>

Le graphique de comparaison **Valeur / Rendement**, basculé en mode **Rendement**, trace exactement ce pourcentage — une ligne par lot, chacune mesurée depuis sa propre date d'ouverture, sur l'ensemble de lots actuellement sélectionné.

### 💱 Lots dans une autre devise {: #lots-in-another-currency }

Les deux jambes d'une clôture sont converties dans la devise cible **chacune dans sa propre devise, à sa propre date** : le coût des unités dans la devise du lot à la date d'ouverture du lot — le taux d'achat — et le prix de clôture dans la devise de la transaction de clôture à la date de clôture — le taux de vente. Avec $\text{Convert}(x, ccy, D)$ le montant $x$ dans la devise $ccy$ converti dans la devise cible au taux de la date $D$, une clôture de $q$ unités d'un lot LONG ouvert le $D_{\text{open}}$ à $\text{LotUnitCost}$ dans $ccy_{\text{lot}}$, et clôturé le $D_{\text{close}}$ à $\text{ClosePrice}$ dans $ccy_{\text{close}}$, donne :

$$
\text{Closure Proceeds} = \text{Convert}\left(q \cdot \text{ClosePrice},\ ccy_{\text{close}},\ D_{\text{close}}\right)
$$

$$
\text{Closure Cost} = \text{Convert}\left(q \cdot \text{LotUnitCost},\ ccy_{\text{lot}},\ D_{\text{open}}\right)
$$

$$
\text{Closure Realized PnL} = \text{Closure Proceeds} - \text{Closure Cost}
$$

$\text{ClosePrice}$ est le prix unitaire d'une vente, dans la devise de la vente, ou zéro, dans la devise du lot, pour un ajustement sortant, qui n'a pas de valeur (voir [Ajustements sortants](../../../instruments/transaction-types/adjustment.md#outgoing-adjustments)). $ccy_{\text{close}}$ ne doit pas nécessairement être $ccy_{\text{lot}}$ : un lot transféré vers un courtier d'une autre devise et vendu là-bas convertit la vente depuis cette devise. Un lot SHORT applique la règle en miroir : il réalise le produit de sa vente d'ouverture, $\text{Convert}(q \cdot \text{LotUnitCost}, ccy_{\text{lot}}, D_{\text{open}})$, moins le coût de l'achat qui le clôture, $\text{Convert}(q \cdot \text{ClosePrice}, ccy_{\text{close}}, D_{\text{close}})$.

Lorsqu'un lot est acheté et vendu dans une seule devise, avec les taux $r_{\text{open}}$ et $r_{\text{close}}$ aux deux dates, son résultat réalisé se décompose en la plus-value de prix au taux de vente et en la variation du taux de change sur le coût des unités vendues :

$$
\text{Closure Realized PnL} = q\,(\text{ClosePrice} - \text{LotUnitCost})\,r_{\text{close}} + q\,\text{LotUnitCost}\,(r_{\text{close}} - r_{\text{open}})
$$

La variation du taux de change entre l'achat et la vente est donc réalisée avec les unités, comme dans le tableau de bord, où le produit d'une vente est converti à sa date et où les unités sortent à leur coût historique (voir [PRU](../weighted-average-cost.md)). Un taux manquant laisse le P&L réalisé de la clôture inconnu, et avec lui le $\text{RealizedPnL}$ du lot : il n'est jamais calculé à partir des montants d'origine.

Le coût de chaque clôture est converti à la date d'ouverture, comme $\text{OriginalCost}$, de sorte que le P&L de marché d'un lot LONG est la valeur de ses unités ouvertes moins leur coût au taux d'achat :

$$
\text{MarketPnL} = \text{PnL} - \text{RealizedPnL} = \text{OpenValue} - \left(\text{OriginalCost} - \sum \text{Closure Cost}\right)
$$

Un lot LONG entièrement clôturé n'a pas de P&L de marché : les coûts de ses clôtures totalisent son $\text{OriginalCost}$, et tout son P&L est réalisé.

!!! example "Un lot en dollars, devise cible EUR"

    Achetez 1 unité à 100 USD alors que 1 USD = 1,00 EUR ; vendez-la à 110 USD alors que 1 USD = 0,90 EUR.

    $$
    \text{Closure Proceeds} = 110 \times 0.90 = 99 \text{ EUR}
    \qquad
    \text{Closure Cost} = 100 \times 1.00 = 100 \text{ EUR}
    $$

    $$
    \text{RealizedPnL} = 99 - 100 = -1 \text{ EUR}
    \qquad
    \text{MarketPnL} = \text{PnL} - \text{RealizedPnL} = (99 - 100) - (-1) = 0
    $$

    La plus-value de prix, $10 \times 0.90 = +9$ EUR, est contrebalancée par la baisse du dollar sur le coût, $100 \times (0.90 - 1.00) = -10$ EUR. Convertir le P&L réalisé d'origine, 10 USD, au taux de vente déclarerait au contraire $+9$ EUR réalisés et $-10$ EUR de P&L de marché sur un lot qui n'est plus détenu ; le total, $-1$ EUR, reste le même dans les deux cas.

---

## ⚙️ Mise à l'échelle qbq

Certains instruments sont cotés **par quantité de base**, et non par unité simple. LibreFolio appelle cette quantité de base `qbq` (`quote_base_quantity`).

- Pour la plupart des actions, `qbq = 1`
- Pour de nombreuses obligations, `qbq = 100`

La règle de valorisation exacte est :

$$
\text{HoldingValue}(qty, price, qbq) = \left(\frac{qty}{qbq}\right)\cdot price
$$

$$
\text{OpenValue}(t) = \left(\frac{\text{OpenQuantity}(t)}{qbq}\right)\cdot \text{MarketPrice}(t)
$$

!!! warning "La mise à l'échelle qbq compte"

    Supposons qu'une obligation ait une quantité nominale de 1 000 et soit cotée à **101,50 pour 100 de nominal**.

    - `qbq = 100`
    - quantité du lot = `1,000`
    - valeur de marché = `(1,000 / 100) × 101.50 = 1,015.00`

    Si vous comparez directement `101.50` avec un coût de base par unité simple tel que `0.992`, vous obtenez des résultats absurdes, car les deux nombres appartiennent à des échelles différentes.

    La comparaison correcte remet le coût du lot à l'échelle de l'axe de cotation du marché :

    $$
    0.992 \times 100 = 99.20
    $$

    La comparaison de prix pertinente est donc **101,50 vs 99,20**, et non **101,50 vs 0,992**.

Sans cette mise à l'échelle, les rendements et les valorisations des obligations peuvent être décalés de plusieurs ordres de grandeur.

---

## 🛟 Estimé au coût {: #estimated-at-cost }

Chaque jour, un lot est valorisé au prix de marquage de l'actif issu du [résolveur unifié](../portfolio-engine/price-resolution.md) : une cotation de marché, ou le prix moyen des opérations d'achat et de vente d'un jour, reporté. Un ajustement n'est jamais un prix, avec ou sans coût de base ; le coût d'un transfert entrant n'en constitue un qu'à titre d'[estimation](../portfolio-engine/price-resolution.md#transfer-cost-estimate), tant que l'actif n'a ni cotation ni autre opération à cette date ou avant. Un jour **sans aucun prix** — aucune cotation de marché, aucun achat ni vente et aucune estimation de ce type à cette date ou avant — **ne fait pas** échouer l'analyse : LibreFolio valorise ce jour-là au coût la portion encore ouverte d'un lot LONG, selon la règle jour par jour que le tableau de bord applique à une position sans prix :

$$
\text{OpenValue}(t) = \text{OpeningValue}\cdot \frac{\text{OpenQuantity}(t)}{\text{OriginalQuantity}}
$$

$$
\text{MarketPnL}(t) = 0
$$

avec $\text{OpeningValue}$ le coût d'origine du lot converti à sa date d'ouverture. Le choix est fait jour par jour, sans anticipation. Un prix, une fois observé, est reporté, de sorte que ces jours se situent tous avant la première cotation, le premier achat, la première vente ou la première estimation de coût de transfert de l'actif : ils vont de la première transaction de l'analyse au jour précédant ce premier prix, ou à la date de fin lorsque l'actif n'en a aucun — et ces jours n'existent pas lorsque l'actif dispose déjà d'un prix le jour de la première transaction.

- **Avant le premier prix.** Un lot ouvert avant le premier prix de l'actif — par un ajustement, par exemple — est valorisé au coût depuis son ouverture jusqu'au jour précédant ce prix, même lorsque l'actif est valorisé plus tard : sa ligne de valeur reste plate au coût, sans gain ni perte de marché, puis suit le prix.
- **Aucun prix du tout.** Un actif sans cotation, sans achat, sans vente ni estimation de coût de transfert jusqu'à la date de fin — détenu uniquement via des ajustements, ou via des transferts sans coût de base — est valorisé au coût chaque jour, et le résumé du lot indique `value_source = ESTIMATED_AT_COST`. Avec un prix à la date de fin ou avant, le résumé valorise plutôt le lot à ce prix : `value_source = MARKET_PRICE`, le libellé de tout prix de marquage, cotation, opération ou estimation de coût de transfert. Un actif arrivé uniquement par des transferts avec un coût de base n'a donc aucun jour valorisé au coût : dès son premier transfert, il est valorisé à ce coût, converti au taux de change de chaque jour, et les séries de prix comportent un point pour lui, signalé comme estimé.
- **Un prix sans taux.** Un jour dont le prix de marquage n'a pas de taux de change vers la devise cible n'est pas valorisé au coût : un lot encore ouvert n'a pas de valeur ce jour-là, et à la date de fin le résumé du lot n'a ni valeur ni `value_source`.
- **Un ajustement sans coût de base.** Un ajustement sans coût, comme un don ou une scission, ouvre un lot à coût nul, et ce lot vaut 0 les jours valorisés au coût jusqu'à l'arrivée d'un prix. Il compte pour zéro ces jours-là, tandis que le coût moyen du tableau de bord traite ce coût comme inconnu et laisse la position non valorisée. Une telle ligne est rare : un [ajustement](../../../instruments/transaction-types/adjustment.md) positif ne peut être enregistré sans coût de base que tant qu'il est lié à une division, et il n'ouvre alors aucun lot ; elle provient donc d'une version plus ancienne, ou d'une version dont l'événement de division a ensuite été transformé en ajustement de prix.

Conséquence pratique, les jours valorisés au coût :

- le lot affiche toujours une valeur résiduelle
- les produits déjà réalisés restent visibles
- les dividendes ou intérêts alloués restent visibles
- **la volatilité latente est temporairement sous-estimée**
- `market_pnl = 0`, et aucun rendement ouvert : il n'y a pas de prix de marché à comparer à la référence
- aucun ROI ni TWRR dans l'historique de performance des lots, qui ne lit que les jours disposant d'un prix

!!! info "Interprétation"

    L'estimation au coût est un fallback opérationnel prudent. Elle signifie : _« Nous savons ce que vous avez payé, mais nous ne savons pas actuellement ce que le marché paierait. »_

L'avertissement de qualité des données `CURRENT_PRICE_ASSUMED_AT_COST` — *« Aucun prix de marché disponible entre {date_from} et {date_to} — valeur ouverte estimée au coût, P&L de marché exclu »* — nomme exactement ces jours : de la première transaction au jour précédant le premier prix de l'actif, ou à la date de fin lorsque l'actif n'en a aucun. Il est émis dès que de tels jours existent et que le résumé du lot ou l'historique des valeurs, rendements, prix ou performances est demandé.

---

## 💸 Allocation des revenus entre les lots {: #income-allocation-across-lots }

Les dividendes et intérêts liés à un actif sont alloués **au prorata entre les lots LONG éligibles
à la date du jour précédant la date de revenu (D-1)**, et uniquement entre les lots détenus **chez le courtier payeur**.

Règle d'allocation exacte :

$$
w_i(D) = \frac{\text{EligibleQty}_i(D)}{\sum_j \text{EligibleQty}_j(D)}, \qquad
\text{EligibleQty}_i(D) = \text{OpenQty}_i(D-1)
$$

$$
\text{Income}_i = \text{Convert}(I, ccy, D)\cdot w_i(D)
$$

Où :

- $I$ = montant du revenu reçu à la date $D$
- $\text{Convert}(I, ccy, D)$ = revenu converti dans la devise cible à la date $D$
- $\text{EligibleQty}_i(D)$ = quantité du lot $i$ ouverte **chez le courtier payeur** à $D-1$ (la quantité qui a quitté
  ce courtier en transit compte toujours comme y trouvant son origine)
- seuls les lots LONG participent au dénominateur

La règle **D-1** préserve la propreté du jour d'enregistrement : un achat effectué *le jour* de la date de revenu ne donne pas droit à cette
distribution, et un lot vendu la veille non plus. Les lots éligibles plus importants reçoivent une part plus importante ;
les lots détenus chez d'autres courtiers, ou pas encore (ou plus) éligibles, ne reçoivent rien.

Le revenu conserve son signe : une correction négative d'un dividende ou d'un intérêt réduit le revenu du lot, comme
dans le tableau de bord.

!!! warning "Modifié dans FIFO v5"

    Les versions antérieures utilisaient la date de revenu elle-même avec **tous** les courtiers ($\text{OpenQty}_i(t)$ sur chaque lot).
    Le moteur actuel utilise l'éligibilité à D-1 limitée au courtier payeur. Si aucun lot n'est éligible, le revenu est
    conservé comme **revenu orphelin au niveau de l'actif** (jamais supprimé, jamais affecté au mauvais lot).

!!! tip "Règle de conservation"

    La somme des montants alloués aux lots correspond exactement au total converti de l'événement de revenu. Le revenu est distribué, non créé.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Fenêtre de détail du lot — la ligne Revenu de l'actif affiche le dividende/intérêt au prorata alloué à ce lot précis, aux côtés du badge Estimé au coût lorsque la valeur actuelle du lot est estimée au coût">
</div>

La ligne **Revenu de l'actif** de la fenêtre modale de détail du lot correspond exactement à $\text{Income}_i$ de la formule ci-dessus — la part au prorata reçue par ce lot précis. Lorsque la valeur actuelle du lot est estimée au coût — son actif n'a aucun prix à la date de fin —, la même fenêtre affiche également le badge **Estimé au coût** de la section précédente.

---

## 💸 Coûts et indicateurs nets {: #costs-and-net-metrics }

Les `FEE` et `TAX` liés à un actif sont alloués aux lots selon une **cascade déterministe d'appariement des opérations**, puis
soustraits pour produire des chiffres **nets** aux côtés des chiffres bruts.

### 🧭 Allocation déterministe des coûts

Un groupe de coûts (même courtier, même jour, même type) est apparié à la première cible non vide dans cet ordre :

| Coût | Ordre d'appariement |
|------|----------------|
| `FEE` | opérations du même jour → opérations de la veille → positions ouvertes → orphelin de l'actif |
| `TAX` | revenus du même jour → opérations du même jour → revenus de la veille → opérations de la veille → positions ouvertes → orphelin de l'actif |

Au sein d'une opération appariée, le coût **se répercute sur les lots précis touchés par cette opération** — le coût d'un achat est affecté au lot qu'il a ouvert, le coût d'une vente est affecté aux lots consommés selon FIFO — de sorte que l'attribution des coûts ne contredit jamais l'appariement FIFO lui-même. Les montants sont convertis dans la devise cible et stockés sous forme de magnitudes positives.

!!! tip "Conservation"

    Par groupe, $\sum_i \text{Cost}_i + \text{Orphan} = \text{Convert}(\text{pool}, ccy, D)$. Un coût qui ne trouve
    aucun lot éligible (par exemple, des frais comptabilisés après la clôture complète de la position) devient un **coût orphelin au niveau de l'actif**
    plutôt que d'être supprimé ou attribué de force à un lot sans rapport.

### ⚖️ Brut vs net

Avec les coûts attribués par lot, LibreFolio rapporte à la fois les performances brutes et nettes :

$$
\text{NetTotalPnL}_i = \text{TotalPnL}_i - \text{Fees}_i - \text{Taxes}_i
$$

$$
\text{NetTotalReturn}_i = \frac{\text{NetTotalPnL}_i}{\text{OpeningValue}_i}
$$

où $\text{TotalPnL}_i$ **inclut déjà** les revenus (P&L de marché + P&L réalisé + revenus de l'actif). La série
d'historique de valeur par lot rapporte en revanche un P&L net *en capital uniquement*, $\text{pnl}_i - \text{Fees}_i - \text{Taxes}_i$,
qui **exclut** les revenus — chaque ligne nette reflète sa contrepartie brute moins les coûts.

Le rendement annualisé d'un lot utilise le rendement **net**, et non le rendement brut :

$$
\mathrm{AnnualizedReturn}_i =
\left(1+\mathrm{NetTotalReturn}_i\right)^{365/d_i}-1
$$

avec $d_i$ de la date d'ouverture à la date de clôture pour les lots clôturés, ou à la date de fin de l'analyse pour les lots ouverts. Les fenêtres inférieures à 30 jours ne renvoient aucune valeur annualisée ; voir [Rendement annualisé net](../portfolio-engine/net-annualized-return.md).

!!! example "Chiffres de référence"

    ACHAT 10×100, VENTE 4×120, prix actuel 110, dividende 50, frais 8, impôts 5 :
    P&L total brut $= 60 + 80 + 50 = 190$ ; P&L total net $= 190 - 13 = 177$ ; sur une valeur d'ouverture de 1 000, cela donne un
    rendement total de **19 %** brut contre **17,7 %** net.

Les coûts avec `asset_id = null` ne font **pas** partie de cette vue au niveau du lot — ils sont au niveau du portefeuille et traités
par le [moteur de portefeuille](../portfolio-engine/roi.md). Voir
[Frais et impôts](../../../instruments/transaction-types/fee.md) pour la théorie au niveau de l'instrument.

---

## 📝 Exemple détaillé

??? example "Exemple : deux lots, un dividende, un prix de marché"

    Supposons la même action, la même devise, `qbq = 1`.

    | Date | Événement | Qté ouverte lot A | Qté ouverte lot B | Notes |
    |------|-------|----------------|----------------|-------|
    | 2 janv. | ACHAT 100 @ $10 | 100 | 0 | Le lot A s'ouvre avec un coût d'origine de 1 000 $ |
    | 10 févr. | ACHAT 50 @ $14 | 100 | 50 | Le lot B s'ouvre avec un coût d'origine de 700 $ |
    | 15 mars | DIVIDENDE 30 $ | 100 | 50 | Les deux lots sont encore ouverts |
    | 1 avr. | Prix du marché = $16 | 100 | 50 | Évaluer les deux lots |

    **Étape 1 — Allouer le dividende au prorata**

    $$
    w_A = \frac{100}{100 + 50} = \frac{2}{3}
    \qquad
    w_B = \frac{50}{100 + 50} = \frac{1}{3}
    $$

    $$
    \text{Income}_A = 30 \times \frac{2}{3} = 20
    \qquad
    \text{Income}_B = 30 \times \frac{1}{3} = 10
    $$

    **Étape 2 — Rendement ouvert pour chaque lot**

    $$
    \text{RelativeReturn}_A = \frac{16}{10} - 1 = 60.00\%
    $$

    $$
    \text{RelativeReturn}_B = \frac{16}{14} - 1 \approx 14.29\%
    $$

    **Étape 3 — Valeur de marché et rendement total**

    $$
    \text{OpenValue}_A = 100 \times 16 = 1,600
    \qquad
    \text{OpenValue}_B = 50 \times 16 = 800
    $$

    Comme aucune action n'a encore été vendue, les produits et le P&L réalisé sont tous deux nuls.

    $$
    \text{TotalPnL}_A = (1,600 - 1,000) + 20 = 620
    $$

    $$
    \text{TotalReturn}_A = \frac{620}{1,000} = 62.00\%
    $$

    $$
    \text{TotalPnL}_B = (800 - 700) + 10 = 110
    $$

    $$
    \text{TotalReturn}_B = \frac{110}{700} \approx 15.71\%
    $$

    **Étape 4 — Rendement agrégé sur les lots affichés**

    $$
    \text{AggregateReturn} = \frac{620 + 110}{1,000 + 700} = \frac{730}{1,700} \approx 42.94\%
    $$

    Bien que les deux lots appartiennent au même actif, leurs rendements diffèrent parce qu'ils ont été ouverts à des prix différents.

---

## 📚 Des lots aux indicateurs agrégés

Les rendements au niveau des lots peuvent être consolidés en une série de rendement agrégé, mais **les pourcentages ne doivent pas être additionnés directement**.

LibreFolio utilise cette règle d'agrégation exacte sur les lots affichés :

$$
\text{AggregatePnL}(t) = \sum_i \left(\text{PnL}_i(t) + \text{Income}_i(t)\right)
$$

$$
\text{AggregateOpeningValue}(t) = \sum_i \text{OriginalCost}_i
$$

$$
\text{AggregateReturn}(t) = \frac{\text{AggregatePnL}(t)}{\text{AggregateOpeningValue}(t)}
$$

Cette vue au niveau des lots aide à expliquer **d'où** vient le rendement. Les indicateurs de niveau supérieur tels que le [ROI](../portfolio-engine/roi.md) et le [TWRR](../portfolio-engine/twrr.md) répondent à des questions plus larges sur le portefeuille :

- **ROI** se concentre sur le gain par rapport au capital investi
- **TWRR** neutralise le calendrier des flux de trésorerie externes
- L'analyse des lots FIFO explique la contribution et le parcours **à l'intérieur** d'une position

La recherche de prix est délibérément en dehors du moteur FIFO lui-même. Le moteur produit les lots et les clôtures, et ne demande un prix que pour fournir sa référence à un lot ouvert par un ajustement ; `LotsAnalysisService` répond à partir du résolveur unifié ([Résolution des prix](../portfolio-engine/price-resolution.md)), puis applique le même résolveur et le fallback d'estimation au coût lors du calcul des indicateurs de valorisation.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Table unifiée des lots — une ligne par lot avec date d'ouverture, rendement total, valeur actuelle, conservation et statut, exactement les lignes par lot sur lesquelles les formules agrégées ci-dessus effectuent la somme">
</div>

La **Table unifiée des lots** liste exactement les lignes par lot $i$ sur lesquelles les formules agrégées ci-dessus effectuent la somme — date d'ouverture, rendement total, valeur actuelle, conservation et statut, le tout filtrable sur le même ensemble de lots visible que celui utilisé par les graphiques.

---

## 🔗 Voir aussi

- 📊 **[Prix de revient unitaire (PRU)](../weighted-average-cost.md)** — vue du coût de base combiné
- 🔁 **[Achat et vente](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — brève vue d'ensemble de l'appariement FIFO
- 💸 **[Dividende et intérêt](../../../instruments/transaction-types/dividend-interest.md)** — source des événements de revenu liés à l'actif
- 💰 **[Fiscalité](../../../fundamentals/taxation.md)** — contexte des plus-values et de l'appariement des lots
- ⚙️ **[Service d'analyse des lots](../../../../developer/backend/transactions/lots_analysis_service.md)** — analyse approfondie de l'implémentation côté développeur
