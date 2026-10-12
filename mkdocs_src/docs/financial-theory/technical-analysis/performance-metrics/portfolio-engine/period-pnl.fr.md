# 📊 PnL de la période (Profit and Loss)

## 💡 Qu'est-ce que le PnL de la période ?

Le gain ou la perte monétaire absolue générée par votre portefeuille sur $[t_0, t_1]$, ajusté des flux de trésorerie externes.

---

## 🧮 Formule

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

Le delta de la base de capital provient de `cumulative_external_cash_flow`, il inclut donc les flux de trésorerie ainsi que le capital ADJUSTMENT/TRANSFER en nature valorisé.

---

## 🧮 Décomposition

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Composant | Définition |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variation des plus/moins-values latentes sur la période — pour les actifs libellés dans une autre devise, y compris l'effet du taux de change sur leur coût historique |
| Realized | Somme des (produits de vente − coût historique des unités vendues) pour les SELL de la période ; les produits sont convertis à la date de la vente |
| Income | DIVIDEND + INTEREST de la période |
| FeesTaxes | FEE + TAX de la période |
| Other | Ce qui referme l'identité : le résultat de change sur les liquidités détenues dans une autre devise (Effet de change sur les liquidités) plus un résidu |

Other est calculé comme suit :

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Comme le coût de base conserve ses taux de change historiques (voir [Valeur comptable](book-value.md)), l'effet des taux de change sur les actifs étrangers fait partie de $\Delta\mathrm{UGL}$ et non de Other. Les liquidités détenues dans une autre devise sont un cas à part : la NAV et la valeur comptable les valorisent toutes deux au taux de chaque jour, de sorte que leur effet de change s'annule dans les plus/moins-values latentes et n'est pas dans $\Delta\mathrm{UGL}$. C'est la première partie de Other, l'[Effet de change sur les liquidités](#fx-on-cash) de chaque courtier $b$, que la vue Performance affiche par courtier :

$$
\mathrm{Other} = \sum_{b \in S} \mathrm{FXonCash}_b + \mathrm{Residual}
$$

Le résidu contient ce que ni les quatre composants ni le résultat de change sur les liquidités ne peuvent voir :

- la variation du taux de change des liquidités pendant leur trajet entre deux courtiers : en transit, elles n'appartiennent au solde d'aucun courtier ;
- le coût d'un change de devises, chez un courtier ou entre deux : −1 000 USD valant 920 € au taux du jour, convertis en +900 €, donnent −20 €, qui ne sont ni des frais ni une vente ;
- la valeur d'actifs transférés entre deux courtiers lors d'un jour de bascule ;
- une vente exclue de Realized parce que son produit n'a pas pu être converti ou que le coût de sa position est incomplet.

### 💵 Effet de change sur les liquidités {: #fx-on-cash }

Pour chaque courtier $b$ détenant des liquidités dans une devise autre que $C^*$, sur la période $(t_0, t_1]$, $t_0$ étant l'état d'ouverture :

$$
\mathrm{FXonCash}_b = \sum_{c \neq C^*} \Bigl[N_{b,c}(t_1)\,\mathrm{fx}(c, C^*, t_1) - N_{b,c}(t_0)\,\mathrm{fx}(c, C^*, t_0)\Bigr] - \sum_{\substack{m \in (t_0, t_1] \\ \mathrm{ccy}(m) \neq C^*}} s_m \cdot \mathrm{amount}_m \cdot \mathrm{fx}(\mathrm{ccy}(m), C^*, d_m)
$$

$N_{b,c}(t)$ est le solde que $b$ détient dans la devise $c$ à la date $t$, au prorata de la part du courtier, et $\mathrm{fx}$ le dernier taux connu ce jour-là ou avant. La seconde somme parcourt les mouvements de $b$ dans une devise étrangère datés de la période : chaque montant, au prorata de la part $s_m$, au taux de sa propre date $d_m$. Le premier terme est la variation de valeur des liquidités en devises, le second ce que les mouvements ont apporté ou retiré : la différence est ce que les taux de change ont fait aux liquidités que le courtier détenait. Elle est égale aux résultats de change que le moteur comptabilise les jours de la période où le taux change ([Moteur de portefeuille — §6](index.md#exchange-result-on-foreign-cash)). Les liquidités en $C^*$ n'en ont pas.

??? example "Exemple : des dollars chez un courtier sur un tableau de bord en euros"

    Un courtier détient 1 000 USD pendant toute la période tandis que le taux passe de 0,90 à 0,92 EUR par USD :

    $$
    \mathrm{FXonCash} = 1\,000 \times 0.92 - 1\,000 \times 0.90 = +20 \text{ EUR}
    $$

    Avec un dépôt de 500 USD au milieu de la période à 0,91, et 0,92 à la fin :

    $$
    \mathrm{FXonCash} = 1\,500 \times 0.92 - 1\,000 \times 0.90 - 500 \times 0.91 = 1\,380 - 900 - 455 = +25 \text{ EUR}
    $$

    Le dépôt est entré dans le capital pour 455 € ; les +25 € sont ce que les dollars ont gagné face à l'euro pendant que le courtier les détenait.

---

## 💱 Variation latente par devise {: #unrealized-change-by-currency }

$\Delta\mathrm{UGL}$ est réparti selon la devise $A$ dans laquelle les actifs sont libellés. Pour les positions en devise $A$ au jour $t$, soit

| Symbole | Signification |
|--------|---------|
| $\mathrm{MV}_A(t)$ | Leur valeur de marché en $C^*$, au prix et au taux du jour |
| $\mathrm{Cost}^{A}_A(t)$ | Leur coût historique en $A$ |
| $\mathrm{Cost}^{*}_A(t)$ | Leur coût historique en $C^*$ |
| $r_A(t) = \mathrm{fx}(A, C^*, t)$ | Le taux de change du jour |

Le coût en $A$ de chaque acquisition provient de son coût en $C^*$ à la date d'acquisition, $c^{A} = c^{*} \cdot \mathrm{fx}(C^*, A, d)$ (ou du montant payé, lorsque le paiement est effectué en $A$). La plus/moins-value latente se décompose alors exactement en un **effet actif** et un **effet de taux de change** :

$$
E^{\text{asset}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{A}_A(t)\, r_A(t)
$$

$$
E^{\text{fx}}_A(t) = \mathrm{Cost}^{A}_A(t)\, r_A(t) - \mathrm{Cost}^{*}_A(t)
$$

$$
E^{\text{asset}}_A(t) + E^{\text{fx}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{*}_A(t) = \mathrm{UGL}_A(t)
$$

Pour une cotation exprimée en $A$, $\mathrm{MV}_A(t) = \frac{q}{qbq} \cdot \mathrm{mark}_A(t) \cdot r_A(t)$, l'effet actif est donc la variation propre des actifs dans leur devise, convertie au taux du jour : $E^{\text{asset}}_A(t) = \bigl(\frac{q}{qbq} \cdot \mathrm{mark}_A(t) - \mathrm{Cost}^{A}_A(t)\bigr)\, r_A(t)$. L'effet de taux de change est nul le jour de chaque achat. Pour $A = C^*$, $r = 1$ et $\mathrm{Cost}^{A} = \mathrm{Cost}^{*}$ : l'effet de taux de change disparaît, et les actifs déjà dans la devise de reporting n'ont qu'un effet actif.

Une position dans une devise $A \neq C^*$ qui ne peut pas être décomposée au jour $t$ — pas de valeur de marché, pas de taux $r_A(t)$, ou un coût incomplet dans l'une ou l'autre devise — ajoute au contraire la totalité de son $\mathrm{MV} - \mathrm{Cost}^{*}$ (avec $\mathrm{MV} = 0$ lorsqu'elle n'a pas de valeur de marché) à une part **non répartie** $E^{\text{unsplit}}_A(t)$. Les positions en $C^*$ comptent toujours dans l'effet actif.

Les lignes de la période sont les variations entre les deux états limites de la période — le dernier état à $t_0$ ou avant (zéro s'il n'y en a pas) et l'état à $t_1$ —, les deux mêmes états que $\Delta\mathrm{UGL}$ :

$$
\Delta E^{k}_A = E^{k}_A(t_1) - E^{k}_A(t_0), \qquad k \in \{\text{asset}, \text{fx}, \text{unsplit}\}
$$

$$
\sum_{A}\ \sum_{k} \Delta E^{k}_A = \Delta\mathrm{UGL} \quad \text{exactement}
$$

??? example "Exemple : un ETF américain sur un tableau de bord en euros"

    10 unités achetées pour 400 € alors qu'elles valaient 500 USD, donc $\mathrm{Cost}^{*} = 400$ EUR et $\mathrm{Cost}^{A} = 500$ USD.

    | Jour | Valeur en USD | $r_{USD}$ | MV en EUR | $E^{\text{asset}}$ | $E^{\text{fx}}$ | $\mathrm{UGL}$ |
    |-----|-------|-----------|---------------|--------------------|-----------------|----------------|
    | $t_0$ | 520 USD | 0,78 | 405,60 | $(520-500) \times 0.78 = 15.60$ | $500 \times 0.78 - 400 = -10.00$ | 5,60 |
    | $t_1$ | 550 USD | 0,75 | 412,50 | $(550-500) \times 0.75 = 37.50$ | $500 \times 0.75 - 400 = -25.00$ | 12,50 |

    $$
    \Delta E^{\text{asset}} = +21.90, \qquad \Delta E^{\text{fx}} = -15.00, \qquad \Delta\mathrm{UGL} = +6.90 \text{ EUR}
    $$

    L'ETF a progressé en dollars (+€21,90), le dollar a perdu du terrain face à l'euro (−€15,00) : ensemble, les +€6,90 de la variation latente de la période.

---

## 🎯 Contribution par actif

Pour chaque position $(a,b)$ :

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

L'ensemble des positions inclut **toute l'activité** de la période :

$$
\mathcal{P} = \text{positions avec une activité BUY/SELL/ADJUSTMENT/TRANSFER ou une quantité aux bornes}
$$

Le rendement annualisé de la période borne le début de sa fenêtre à la plus tardive entre le début demandé et la date du plus ancien lot ouvert. Il utilise $|\mathrm{StartValue}|$ comme base d'annualisation, avec un fallback sur le coût de base de fin pour les positions ouvertes en cours de période. Voir [Rendement annualisé net](net-annualized-return.md).

🔗 Voir **[Moteur de portefeuille — §7 Contribution de la période](index.md#7-period-contribution)** pour plus de détails.

---

## 📝 Exemple

- NAV à $t_0$ : €27 000
- Augmentation de la base de capital sur la période : €1 000
- NAV à $t_1$ : €33 000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Voir aussi

- 💼 [NAV](nav.md) — terme final de chaque formule de PnL
- 📖 [Valeur comptable](book-value.md) — coût de base historique derrière la plus/moins-value latente
- 💸 [Capital versé](deposited-capital.md) — PnL total depuis l'origine
- ⚙️ [Moteur de portefeuille](index.md) — modèle mathématique complet
- 📈 [Vue d'ensemble des métriques de performance](../index.md) — toutes les métriques de performance en un coup d'œil
