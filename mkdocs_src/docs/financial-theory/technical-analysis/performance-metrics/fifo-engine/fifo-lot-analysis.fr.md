# 🔬 Analyse des lots FIFO

L'analyse des lots FIFO est le complément **par lot** du [prix moyen pondéré (PMP)](../weighted-average-cost.md).

Le PMP répond à la question : _« Quel est mon prix moyen pondéré pour cette position ? »_ L'analyse des lots FIFO répond à une question différente : _« Comment chaque lot d'achat individuel se comporte-t-il dans le temps ? »_

Au lieu de fusionner toutes les acquisitions dans un seul pool, LibreFolio suit chaque lot à travers son propre cycle de vie — **ouvert**, **partiellement clos**, **entièrement clos** — et fait correspondre les ventes dans l'ordre **FIFO** (premier entré, premier sorti).

!!! info "Complément, pas remplacement"

    Le PMP est agrégé et au niveau de la position. L'analyse des lots FIFO est granulaire et au niveau du lot. Les deux vues sont utiles : l'une pour le coût de base moyen, l'autre pour l'attribution économique lot par lot.

---

## 💡 Qu'est-ce que l'analyse des lots FIFO ?

Un **lot** est un lot d'acquisition : par exemple, un ACHAT de 100 actions, ou un transfert entrant qui préserve le coût de base historique.

Lorsqu'une VENTE se produit, les lots ouverts les plus anciens sont clos en premier. Cela crée un historique lot par lot :

- quelle quantité de chaque lot est encore ouverte
- quelle quantité a déjà été vendue
- combien de produit de vente ce lot a généré
- combien de revenus ont été gagnés pendant que ce lot était détenu
- combien de rendement provient de la variation de prix par rapport aux revenus en espèces

Cela rend l'analyse des lots FIFO particulièrement utile lorsque deux positions sur le même actif ont été achetées à des prix ou à des dates très différents.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Chronologie de la vie du lot et de la garde — chaque barre est un lot, colorée par courtier dépositaire, épaisseur proportionnelle à la quantité détenue">
</div>

La chronologie **Lot Life & Custody** ci-dessus rend le cycle de vie visuel : chaque barre est un lot, colorée par le courtier qui le détient actuellement, avec une épaisseur proportionnelle à la quantité encore détenue dans ce segment. Une barre qui se termine au milieu du graphique est un lot entièrement clos ; une barre qui atteint « aujourd'hui » est encore ouverte.

---

## 🧮 Rendement ouvert par lot

Le **rendement ouvert** isole la variation **uniquement liée au prix** d'un lot par rapport à son prix de référence d'ouverture.

$$
\text{RelativeReturn} = \frac{\text{MarketPrice}}{\text{ReferenceUnitPrice}} - 1
$$

En pratique :

- si une cotation de marché existe à la date d'ouverture du lot, cette cotation d'ouverture devient `reference_unit_price`
- si le lot a été ouvert avant la première cotation de marché disponible, le système retient en fallback le coût d'ouverture du lot lui-même, mis à l'échelle selon les unités de cotation du marché
- `reference_price_source` enregistre si la référence était `exact`, `fallback` ou `unavailable`

Cette métrique exclut les dividendes, les intérêts et les produits de vente réalisés. Elle répond à la question : _« De combien le prix de marché a-t-il évolué depuis l'ouverture de ce lot ? »_

!!! tip "Fallback du prix de référence"

    Lorsqu'aucune cotation de marché du jour d'ouverture n'existe, LibreFolio utilise le prix d'acquisition du lot comme base de référence, mis à l'échelle selon la convention de cotation de l'actif. Cela évite des rendements en pourcentage trompeurs sur les instruments cotés pour 100 unités nominales.

    Le fallback est $\text{OpeningUnitPrice}\times qbq$. Pour `qbq = 100`, une obligation achetée à `0.992` est comparée à l'axe de cotation du marché comme `99.20`, et non `0.992`.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="Graphique PMP / prix de marché — une bulle par lot, colorée par courtier d'ouverture, dimensionnée par la valeur d'ouverture, tracée par rapport à la ligne du prix de marché">
</div>

Le graphique **PMP / Prix du marché** trace chaque lot comme une bulle par rapport à la ligne du prix de marché : la couleur de la bulle marque le courtier où le lot a été ouvert, la taille de la bulle est fonction de la valeur d'ouverture du lot. Un lot valorisé uniquement au coût (sans prix de marché en direct) est dessiné avec un contour en pointillés.

---

## 💰 Rendement total par lot

Le **rendement total** est plus large que le rendement ouvert. Il inclut la valeur de marché restante du lot, tout produit de vente déjà réalisé à partir de ce lot, et tout revenu alloué reçu pendant que le lot était détenu.

Le calcul des lots de LibreFolio s'appuie sur ces briques de calcul exactes :

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

Pour le résumé scalaire du lot, le pourcentage de rendement est :

$$
\text{TotalReturn} = \frac{\text{TotalPnL}}{\text{OpeningValue}}
$$

Pour l'historique de rendement dans le temps, LibreFolio utilise :

$$
\text{TotalReturn}(t) = \frac{\text{TotalValue}(t) + \text{Income}(t)}{\text{OriginalCost}} - 1
$$

Cela répond à la question : _« Quel est le rendement économique complet de ce lot, incluant à la fois le mouvement de prix et le rendement en espèces ? »_

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Graphique comparatif Valeur / Rendement en mode Rendement — pourcentage de rendement par lot à partir de la date d'ouverture de chaque lot">
</div>

Le graphique comparatif **Value / Return**, basculé en mode **Rendement**, trace exactement ce pourcentage — une ligne par lot, chacune mesurée à partir de sa propre date d'ouverture, sur l'ensemble des lots actuellement sélectionnés.

---

## ⚙️ Échelle qbq

Certains instruments sont cotés **par quantité de base**, et non par unité individuelle. LibreFolio appelle cette quantité de base `qbq` (`quote_base_quantity`).

- Pour la plupart des actions, `qbq = 1`
- Pour de nombreuses obligations, `qbq = 100`

La règle de valorisation exacte est :

$$
\text{HoldingValue}(qty, price, qbq) = \left(\frac{qty}{qbq}\right)\cdot price
$$

$$
\text{OpenValue}(t) = \left(\frac{\text{OpenQuantity}(t)}{qbq}\right)\cdot \text{MarketPrice}(t)
$$

!!! warning "L'échelle qbq a son importance"

    Supposons une obligation avec une quantité nominale de 1 000 et cotée à **101,50 pour 100 de nominal**.

    - `qbq = 100`
    - quantité du lot = `1,000`
    - valeur de marché = `(1,000 / 100) × 101.50 = 1,015.00`

    Si vous comparez `101.50` directement avec un coût de base par unité unique tel que `0.992`, vous obtenez un non-sens car les deux nombres se situent sur des échelles différentes.

    La comparaison correcte remet à l'échelle le coût du lot sur l'axe de cotation du marché :

    $$
    0.992 \times 100 = 99.20
    $$

    La comparaison de prix significative est donc **101,50 vs 99,20**, et non **101,50 vs 0,992**.

Sans cette mise à l'échelle, les rendements et les valorisations des obligations peuvent être décalés de plusieurs ordres de grandeur.

---

## 🛟 Estimé au coût {: #estimated-at-cost }

Si aucun prix de marché en direct n'est disponible pour un actif, LibreFolio **ne fait pas échouer** l'analyse. Au lieu de cela, il valorise temporairement la partie encore ouverte du lot au coût :

$$
\text{OpenValue} = \text{OpeningValue}\cdot \frac{\text{OpenQuantity}}{\text{OriginalQuantity}}
$$

$$
\text{MarketPnL} = 0
$$

Implication pratique :

- le lot affiche toujours une valeur résiduelle
- les produits déjà réalisés restent visibles
- les dividendes ou intérêts alloués restent visibles
- **la volatilité non réalisée est temporairement sous-estimée**
- `value_source = ESTIMATED_AT_COST`
- `market_pnl = 0`
- code de problème de qualité des données : `CURRENT_PRICE_ASSUMED_AT_COST`

!!! info "Interprétation"

    L'estimation au coût est un fallback opérationnel conservateur. Cela signifie : _« Nous savons ce que vous avez payé, mais nous ne savons pas actuellement ce que le marché paierait. »_

L'avertissement correspondant de qualité des données est une déclaration **à la date de valorisation**. Ce n'est pas une union historique de chaque jour où un actif a été valorisé au coût.

---

## 💸 Répartition des revenus entre les lots {: #income-allocation-across-lots }

Les dividendes et intérêts liés à un actif sont répartis **au prorata entre les lots LONG éligibles à la date précédant la date du revenu (J-1)**, et uniquement entre les lots détenus **auprès du courtier payeur**.

Règle de répartition exacte :

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
- $\text{EligibleQty}_i(D)$ = quantité du lot $i$ ouverte auprès du **courtier payeur** à $J-1$ (une quantité qui a quitté ce courtier en transit est toujours considérée comme provenant de ce courtier)
- seuls les lots LONG participent au dénominateur

La règle **J-1** préserve l'intégrité du jour d'enregistrement : un achat effectué *à la date même du revenu* ne donne pas droit à cette distribution, et un lot vendu la veille non plus. Les lots éligibles plus importants reçoivent une part plus importante ; les lots détenus auprès d'autres courtiers, ou pas encore (ou plus) éligibles, ne reçoivent rien.

!!! warning "Modifié dans FIFO v5"

    Les versions antérieures utilisaient la date du revenu elle-même avec **tous** les courtiers ($\text{OpenQty}_i(t)$ sur chaque lot). Le moteur actuel utilise l'éligibilité J-1 limitée au courtier payeur. Si aucun lot n'est éligible, le revenu est conservé comme **revenu orphelin au niveau de l'actif** (jamais abandonné, jamais assigné au mauvais lot).

!!! tip "Règle de conservation"

    La somme des montants alloués aux lots correspond exactement au total converti de l'événement de revenu. Le revenu est distribué, non créé.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Modale de détail du lot — la ligne Revenu d'actif affiche le dividende/intérêt au prorata alloué à ce lot spécifique, accompagné du badge Estimé au coût lorsqu'aucun prix de marché en direct n'est disponible">
</div>

La ligne **Revenu d'actif** de la modale de détail du lot est exactement $\text{Income}_i$ de la formule ci-dessus — la part au prorata que ce lot spécifique a reçue. Lorsque le lot n'a pas de prix de marché en direct, la même modale affiche également le badge **Estimé au coût** de la section précédente.

---

## 💸 Coûts et métriques nettes {: #costs-and-net-metrics }

Les `FEE` et `TAX` liés à l'actif sont alloués aux lots selon une **cascade déterministe de mise en correspondance des opérations**, puis soustraits pour produire des chiffres **nets** aux côtés des chiffres bruts.

### 🧭 Allocation déterministe des coûts

Un pool de coûts (même courtier, même jour, même type) est mis en correspondance avec la première cible non vide dans cet ordre :

| Coût | Ordre de correspondance |
|------|-------------------------|
| `FEE` | transactions du jour → transactions du jour précédent → positions ouvertes → orphelin d'actif |
| `TAX` | revenus du jour → transactions du jour → revenus du jour précédent → transactions du jour précédent → positions ouvertes → orphelin d'actif |

Au sein d'une transaction mise en correspondance, le coût **est imputé aux lots mêmes que la transaction a touchés** — le coût d'un ACHAT est imputé au lot qu'il a ouvert, celui d'une VENTE est imputé aux lots consommés en FIFO — de sorte que l'attribution des coûts ne contredit jamais la correspondance FIFO elle-même. Les montants sont convertis dans la devise cible et stockés comme des valeurs positives.

!!! tip "Conservation"

    Par pool, $\sum_i \text{Cost}_i + \text{Orphan} = \text{Convert}(\text{pool}, ccy, D)$. Un coût qui ne trouve aucun lot éligible (par exemple, des frais comptabilisés après la clôture complète de la position) devient **coût orphelin au niveau de l'actif** plutôt que d'être abandonné ou attribué de force à un lot sans rapport.

### ⚖️ Brut vs net

Avec les coûts attribués par lot, LibreFolio rapporte à la fois les performances brutes et nettes :

$$
\text{NetTotalPnL}_i = \text{TotalPnL}_i - \text{Fees}_i - \text{Taxes}_i
$$

$$
\text{NetTotalReturn}_i = \frac{\text{NetTotalPnL}_i}{\text{OpeningValue}_i}
$$

où $\text{TotalPnL}_i$ **inclut déjà** les revenus (P&L de marché + P&L réalisé + revenus d'actif). La série historique de valeur par lot rapporte quant à elle un P&L net *capital uniquement*, $\text{pnl}_i - \text{Fees}_i - \text{Taxes}_i$, qui **exclut** les revenus — chaque ligne nette reflète sa propre contrepartie brute moins les coûts.

Le rendement annualisé du lot utilise le rendement **net**, et non le rendement brut :

$$
\mathrm{AnnualizedReturn}_i =
\left(1+\mathrm{NetTotalReturn}_i\right)^{365/d_i}-1
$$

avec $d_i$ de la date d'ouverture à la date de clôture pour les lots clos, ou jusqu'à la date de fin d'analyse pour les lots ouverts. Les fenêtres de moins de 30 jours ne renvoient aucune valeur annualisée ; voir [Rendement annualisé net](../portfolio-engine/net-annualized-return.md).

!!! example "Chiffres canoniques"

    ACHAT 10×100, VENTE 4×120, prix actuel 110, dividende 50, frais 8, taxes 5 :
    P&L total brut $= 60 + 80 + 50 = 190$ ; P&L total net $= 190 - 13 = 177$ ; sur une valeur d'ouverture de 1 000, cela donne un rendement total **19 %** brut vs **17,7 %** net.

Les coûts avec `asset_id = null` ne font **pas** partie de cette vue au niveau du lot — ils sont au niveau du portefeuille et sont traités par le [moteur de portefeuille](../portfolio-engine/roi.md). Voir [Frais et taxes](../../../instruments/transaction-types/fee.md) pour la théorie au niveau de l'instrument.

---

## 📝 Exemple détaillé

??? example "Exemple : deux lots, un dividende, un prix de marché"

     Supposons la même action, la même devise, `qbq = 1`.

     | Date | Événement | Qté ouverte lot A | Qté ouverte lot B | Notes |
     |------|-----------|-------------------|-------------------|-------|
     | 2 janv. | ACHAT 100 à 10 $ | 100 | 0 | Le lot A s'ouvre avec un coût initial de 1 000 $ |
     | 10 févr. | ACHAT 50 à 14 $ | 100 | 50 | Le lot B s'ouvre avec un coût initial de 700 $ |
     | 15 mars | DIVIDENDE 30 $ | 100 | 50 | Les deux lots sont encore ouverts |
     | 1 avr. | Prix de marché = 16 $ | 100 | 50 | Évaluer les deux lots |

     **Étape 1 — Répartir le dividende au prorata**

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
     \text{OpenValue}_A = 100 \times 16 = 1\,600
     \qquad
     \text{OpenValue}_B = 50 \times 16 = 800
     $$

     Comme aucune action n'a encore été vendue, les produits et le P&L réalisé sont tous deux nuls.

     $$
     \text{TotalPnL}_A = (1\,600 - 1\,000) + 20 = 620
     $$

     $$
     \text{TotalReturn}_A = \frac{620}{1\,000} = 62.00\%
     $$

     $$
     \text{TotalPnL}_B = (800 - 700) + 10 = 110
     $$

     $$
     \text{TotalReturn}_B = \frac{110}{700} \approx 15.71\%
     $$

     **Étape 4 — Rendement agrégé sur les lots affichés**

     $$
     \text{AggregateReturn} = \frac{620 + 110}{1\,000 + 700} = \frac{730}{1\,700} \approx 42.94\%
     $$

     Même si les deux lots appartiennent au même actif, leurs rendements diffèrent car ils ont été ouverts à des prix différents.

---

## 📚 Des lots aux métriques agrégées

Les rendements au niveau du lot peuvent être regroupés en une série de rendements agrégés, mais **les pourcentages ne doivent pas être additionnés directement**.

LibreFolio utilise cette règle agrégée exacte sur les lots affichés :

$$
\text{AggregatePnL}(t) = \sum_i \left(\text{PnL}_i(t) + \text{Income}_i(t)\right)
$$

$$
\text{AggregateOpeningValue}(t) = \sum_i \text{OriginalCost}_i
$$

$$
\text{AggregateReturn}(t) = \frac{\text{AggregatePnL}(t)}{\text{AggregateOpeningValue}(t)}
$$

Cette vue au niveau du lot aide à expliquer **d'où** vient le rendement. Les métriques de niveau supérieur telles que le [ROI](../portfolio-engine/roi.md) et le [TWRR](../portfolio-engine/twrr.md) répondent à des questions plus larges sur le portefeuille :

- Le **ROI** se concentre sur le gain par rapport au capital investi
- Le **TWRR** neutralise le calendrier des flux de trésorerie externes
- L'analyse des lots FIFO explique la contribution et le chemin **à l'intérieur** d'une position

La recherche de prix est délibérément en dehors du moteur FIFO lui-même. Le moteur produit les lots et les clôtures ; `LotsAnalysisService` applique le résolveur unifié ([Résolution des prix](../portfolio-engine/price-resolution.md)) et le fallback estimé au coût lors de la dérivation des métriques de valorisation.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Tableau unifié des lots — une ligne par lot avec date d'ouverture, rendement total, valeur actuelle, garde et statut, les lignes exactes par lot que les formules agrégées ci-dessus additionnent">
</div>

Le **Tableau unifié des lots** liste exactement les lignes par lot $i$ que les formules agrégées ci-dessus additionnent — date d'ouverture, rendement total, valeur actuelle, garde et statut, toutes filtrables sur le même ensemble visible de lots utilisé par les graphiques.

---

## 🔗 Liens connexes

- 📊 **[Prix moyen pondéré (PMP)](../weighted-average-cost.md)** — vue du coût de base moyen
- 🔁 **[Achat et Vente](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — aperçu concis de la correspondance FIFO
- 💸 **[Dividende et Intérêts](../../../instruments/transaction-types/dividend-interest.md)** — source des événements de revenus liés à l'actif
- 💰 **[Fiscalité](../../../fundamentals/taxation.md)** — contexte des plus-values et de la correspondance des lots
- ⚙️ **[Service d'analyse des lots](../../../../developer/backend/transactions/lots_analysis_service.md)** — plongée approfondie dans l'implémentation pour développeurs
