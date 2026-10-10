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
| Other | Résidu qui referme l'identité |

Le résidu est calculé comme suit :

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Comme le coût de base conserve ses taux de change historiques (voir [Valeur comptable](book-value.md)), l'effet des taux de change sur les actifs étrangers fait partie de $\Delta\mathrm{UGL}$ et non de Other. Ce que Other contient encore, c'est ce que les quatre composants ne peuvent pas voir, par exemple la valeur d'actifs transférés entre deux courtiers lors d'un jour de bascule, ou une vente exclue de Realized parce que son produit n'a pas pu être converti ou que le coût de sa position est incomplet.

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
    | $t_0$ | 520 USD | 0.78 | 405.60 | $(520-500) \times 0.78 = 15.60$ | $500 \times 0.78 - 400 = -10.00$ | 5.60 |
    | $t_1$ | 550 USD | 0.75 | 412.50 | $(550-500) \times 0.75 = 37.50$ | $500 \times 0.75 - 400 = -25.00$ | 12.50 |

    $$
    \Delta E^{\text{asset}} = +21.90, \qquad \Delta E^{\text{fx}} = -15.00, \qquad \Delta\mathrm{UGL} = +6.90 \text{ EUR}
    $$

    L'ETF a progressé en dollars (+€21.90), le dollar a perdu du terrain face à l'euro (−€15.00) : ensemble, les +€6.90 de la variation latente de la période.

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

- NAV à $t_0$ : €27,000
- Augmentation de la base de capital sur la période : €1,000
- NAV à $t_1$ : €33,000

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
