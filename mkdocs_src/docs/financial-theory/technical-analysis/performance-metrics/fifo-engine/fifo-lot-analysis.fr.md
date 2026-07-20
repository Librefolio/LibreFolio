# 🔬 Analyse des Lots FIFO

L'analyse des lots FIFO est le complément **par lot** du [Prix Moyen Pondéré (PMP)](../weighted-average-cost.md).

Le PMP répond à la question : *« Quel est mon prix moyen global pour cette position ? »* L'analyse des lots FIFO répond à une question différente : *« Comment chaque lot d'achat individuel se comporte-t-il dans le temps ? »*

Au lieu de fusionner toutes les acquisitions en un seul ensemble, LibreFolio suit chaque lot à travers son propre cycle de vie — **ouvert**, **partiellement clos**, **totalement clos** — et associe les ventes dans l'ordre **FIFO** (premier entré, premier sorti).

!!! info "Complément, pas remplacement"

    Le PMP est agrégé et au niveau de la position. L'analyse des lots FIFO est granulaire et au niveau du lot. Les deux vues sont utiles : l'une pour le prix de base moyen, l'autre pour l'attribution économique lot par lot.

---

## 💡 Qu'est-ce que l'Analyse des Lots FIFO ?

Un **lot** est un lot d'acquisition : par exemple, un ACHAT de 100 actions, ou un transfert entrant qui préserve la base de coût historique.

Lorsqu'une VENTE a lieu, les lots les plus anciens encore ouverts sont fermés en premier. Cela crée un historique lot par lot :

- combien de chaque lot est encore ouvert
- combien a déjà été vendu
- combien de produit de vente ce lot a généré
- combien de revenus ont été gagnés pendant que ce lot était détenu
- combien de rendement provient du changement de prix par rapport aux revenus en espèces

Cela rend l'analyse des lots FIFO particulièrement utile lorsque deux positions dans le même actif ont été achetées à des prix ou dates très différents.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Chronologie de vie et de garde des lots — chaque barre représente un lot, colorée par courtier dépositaire, l'épaisseur étant proportionnelle à la quantité détenue">
</div>

La chronologie **Vie et Garde des Lots** ci-dessus rend le cycle de vie visuel : chaque barre est un lot, colorée par le courtier qui le détient actuellement, avec une épaisseur proportionnelle à la quantité encore détenue dans ce segment. Une barre qui se termine au milieu du graphique est un lot totalement clos ; une barre atteignant « aujourd'hui » est encore ouverte.

---

## 🧮 Rendement Ouvert par Lot

Le **Rendement Ouvert** isole le mouvement **uniquement lié au prix** d'un lot par rapport à son prix de référence d'ouverture.

$$
\text{RelativeReturn} = \frac{\text{MarketPrice}}{\text{ReferenceUnitPrice}} - 1
$$

En pratique :

- si un cours de marché existe à la date d'ouverture du lot, ce cours d'ouverture devient `reference_unit_price`
- si le lot a été ouvert avant le premier cours de marché disponible, le système utilise le coût d'ouverture du lot lui-même, mis à l'échelle selon les unités du cours de marché

Cette mesure exclut les dividendes, l'intérêt et les produits de vente réalisés. Elle répond à la question : *« De combien le prix du marché a-t-il évolué depuis l'ouverture de ce lot ? »*

!!! tip "Référence de repli"

    Lorsqu'aucun cours de marché du jour d'ouverture n'est disponible, LibreFolio utilise le prix d'acquisition du lot comme base de référence, mis à l'échelle selon la convention de cotation de l'actif. Cela évite des pourcentages de rendement trompeurs sur les instruments cotés pour 100 unités nominales.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="Graphique PMP / Prix du Marché — une bulle par lot, colorée par le courtier d'ouverture, dimensionnée par la valeur d'ouverture, tracée par rapport à la ligne du prix du marché">
</div>

Le graphique **PMP / Prix du Marché** trace chaque lot sous forme de bulle par rapport à la ligne du prix du marché : la couleur de la bulle indique le courtier où le lot a été ouvert, la taille de la bulle est fonction de la valeur d'ouverture du lot. Un lot valorisé uniquement au coût (pas de cours de marché en direct) est dessiné avec un contour en pointillés.

---

## 💰 Rendement Total par Lot

Le **Rendement Total** est plus large que le Rendement Ouvert. Il inclut la valeur de marché restante du lot, les éventuels produits de vente déjà réalisés à partir de ce lot, et les revenus alloués perçus pendant que le lot était détenu.

Le calcul des lots par LibreFolio utilise ces éléments constitutifs exacts :

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

Pour l'historique du rendement dans le temps, LibreFolio utilise :

$$
\text{TotalReturn}(t) = \frac{\text{TotalValue}(t) + \text{Income}(t)}{\text{OriginalCost}} - 1
$$

Cette mesure répond à la question : *« Quel est le rendement économique complet de ce lot, incluant à la fois le mouvement du prix et le rendement en espèces ? »*

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Graphique de comparaison Valeur / Rendement en mode Rendement — pourcentage de rendement par lot à partir de la date d'ouverture de chaque lot">
</div>

Le graphique de comparaison **Valeur / Rendement**, basculé en mode **Rendement**, trace exactement ce pourcentage — une ligne par lot, chacune mesurée à partir de sa propre date d'ouverture, sur l'ensemble de lots actuellement sélectionné.

---

## ⚙️ Mise à l'Échelle qbq

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

!!! warning "La mise à l'échelle qbq est importante"

    Supposons une obligation ayant une quantité nominale de 1 000 et cotée à **101,50 pour 100 nominal**.

    - `qbq = 100`
    - quantité du lot = `1 000`
    - valeur de marché = `(1 000 / 100) × 101,50 = 1 015,00`

    Si vous comparez directement `101,50` avec une base de coût par unité individuelle telle que `0,992`, vous obtenez des résultats absurdes car les deux nombres vivent sur des échelles différentes.

    La comparaison correcte remet à l'échelle le coût du lot sur l'axe du cours de marché :

    $$
    0,992 \times 100 = 99,20
    $$

    Ainsi, la comparaison de prix pertinente est **101,50 vs 99,20**, et non **101,50 vs 0,992**.

Sans cette mise à l'échelle, les rendements et valorisations des obligations peuvent être erronés de plusieurs ordres de grandeur.

---

## 🛟 Estimation au Coût

Si aucun cours de marché en direct n'est disponible pour un actif, LibreFolio **n'échoue pas** l'analyse. Au lieu de cela, il valorise temporairement la partie encore ouverte du lot à son coût :

$$
\text{OpenValue} = \text{OpeningValue}\cdot \frac{\text{OpenQuantity}}{\text{OriginalQuantity}}
$$

$$
\text{MarketPnL} = 0
$$

Implication pratique :

- le lot affiche encore une valeur résiduelle
- les produits déjà réalisés restent visibles
- les dividendes ou intérêts alloués restent visibles
- **la volatilité non réalisée est temporairement sous-estimée**

!!! info "Interprétation"

    L'estimation au coût est un repli opérationnel conservateur. Cela signifie : *« Nous savons ce que vous avez payé, mais nous ne savons pas actuellement ce que le marché paierait. »*

---

## 💸 Allocation des Revenus entre les Lots {: #income-allocation-across-lots }

Les dividendes et l'intérêt liés à un actif sont alloués **au prorata de tous les lots LONG qui sont ouverts à la date du revenu**.

Règle d'allocation exacte :

$$
w_i(t) = \frac{\text{OpenQty}_i(t)}{\sum_j \text{OpenQty}_j(t)}
$$

$$
\text{Income}_i = \text{Convert}(I, ccy, t)\cdot w_i(t)
$$

Où :

- $I$ = montant du revenu perçu
- $\text{Convert}(I, ccy, t)$ = revenu converti dans la devise cible à la date $t$
- seuls les lots LONG encore ouverts au moment $t$ participent au dénominateur

Cela signifie que les lots ouverts les plus importants reçoivent une part plus importante du dividende ou du coupon, tandis que les lots déjà clos n'en reçoivent aucun.

!!! tip "Règle de conservation"

    Les montants alloués aux lots totalisent exactement le montant total de l'événement de revenu converti. Le revenu est distribué, non créé.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Fenêtre modale des détails du lot — la ligne Revenu de l'Actif montre le dividende/intérêt au prorata alloué à ce lot spécifique, accompagné du badge Estimation au Coût lorsqu'aucun cours de marché en direct n'est disponible">
</div>

La ligne **Revenu de l'Actif** dans la fenêtre modale des détails du lot est exactement $\text{Income}_i$ de la formule ci-dessus — la part au prorata que ce lot spécifique a reçue. Lorsque le lot n'a pas de cours de marché en direct, la même fenêtre modale affiche également le badge **Estimation au Coût** de la section précédente.

---

## 📝 Exemple Pratique

??? example "Exemple : deux lots, un dividende, un cours de marché"

 Supposons la même action, la même devise, `qbq = 1`.

 | Date | Événement | Lot A Qté Ouverte | Lot B Qté Ouverte | Notes |
 |------|-----------|-------------------|-------------------|-------|
 | 2 janv. | ACHAT 100 @ 10 $ | 100 | 0 | Le lot A s'ouvre avec un coût initial de 1 000 $ |
 | 10 févr. | ACHAT 50 @ 14 $ | 100 | 50 | Le lot B s'ouvre avec un coût initial de 700 $ |
 | 15 mars | DIVIDENDE 30 $ | 100 | 50 | Les deux lots sont encore ouverts |
 | 1er avril | Cours du marché = 16 $ | 100 | 50 | Évaluer les deux lots |

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

 **Étape 2 — Rendement Ouvert pour chaque lot**

 $$
 \text{RelativeReturn}_A = \frac{16}{10} - 1 = 60,00\%
 $$

 $$
 \text{RelativeReturn}_B = \frac{16}{14} - 1 \approx 14,29\%
 $$

 **Étape 3 — Valeur de marché et Rendement Total**

 $$
 \text{OpenValue}_A = 100 \times 16 = 1 600
 \qquad
 \text{OpenValue}_B = 50 \times 16 = 800
 $$

 Comme aucune action n'a encore été vendue, les produits et le P&L réalisé sont tous deux nuls.

 $$
 \text{TotalPnL}_A = (1 600 - 1 000) + 20 = 620
 $$

 $$
 \text{TotalReturn}_A = \frac{620}{1 000} = 62,00\%
 $$

 $$
 \text{TotalPnL}_B = (800 - 700) + 10 = 110
 $$

 $$
 \text{TotalReturn}_B = \frac{110}{700} \approx 15,71\%
 $$

 **Étape 4 — Rendement agrégé sur les lots affichés**

 $$
 \text{AggregateReturn} = \frac{620 + 110}{1 000 + 700} = \frac{730}{1 700} \approx 42,94\%
 $$

 Même si les deux lots appartiennent au même actif, leurs rendements diffèrent car ils ont été ouverts à des prix différents.

---

## 📚 Des Lots aux Métriques Agrégées

Les rendements au niveau du lot peuvent être consolidés en une série de rendements agrégés, mais **les pourcentages ne doivent pas être ajoutés directement**.

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

Cette vue au niveau du lot aide à expliquer **d'où** provient le rendement. Les métriques de niveau supérieur telles que le [ROI](../portfolio-engine/roi.md) et le [TWRR](../portfolio-engine/twrr.md) répondent à des questions de portefeuille plus larges :

- Le **ROI** se concentre sur le gain par rapport au capital investi
- Le **TWRR** neutralise le moment des flux de trésorerie externes
- L'analyse des lots FIFO explique la contribution et le chemin **à l'intérieur** d'une position

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Tableau Unifié des Lots — une ligne par lot avec la date d'ouverture, le rendement total, la valeur actuelle, la garde et le statut, exactement les lignes par lot sur lesquelles les formules agrégées ci-dessus somment">
</div>

Le **Tableau Unifié des Lots** liste exactement les lignes par lot $i$ que les formules agrégées ci-dessus somment — date d'ouverture, rendement total, valeur actuelle, garde et statut, le tout filtrable sur le même ensemble de lots visibles utilisé par les graphiques.

---

## 🔗 Liens Connexes

- 📊 **[Prix Moyen Pondéré (PMP)](../weighted-average-cost.md)** — vue du prix de base moyen
- 🔁 **[Achat & Vente](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — bref aperçu de l'appariement FIFO
- 💸 **[Dividende & Intérêt](../../../instruments/transaction-types/dividend-interest.md)** — source des événements de revenus liés aux actifs
- 💰 **[Taxe](../../../fundamentals/taxation.md)** — contexte des plus-values et de l'appariement des lots
- ⚙️ **[Service d'Analyse des Lots](../../../../developer/backend/transactions/lots_analysis_service.md)** — plongée approfondie dans l'implémentation pour développeurs
