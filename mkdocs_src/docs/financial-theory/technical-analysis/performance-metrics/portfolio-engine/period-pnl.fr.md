# 📊 P&L période (profits et pertes)

## 💡 Qu'est-ce que le P&L période ?

Le résultat monétaire absolu (gain ou perte) généré par votre portefeuille sur $[t_0, t_1]$, ajusté des flux de trésorerie externes.

---

## 🧮 Formule

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

Le delta de la base provient de `cumulative_external_cash_flow`, il inclut donc les flux de trésorerie et le capital en nature valorisé des AJUSTEMENTS/TRANSFERTS. Un AJUSTEMENT sortant n'a pas de valeur et ne retire rien ([Capital versé — Ajustements sortants](deposited-capital.md#outgoing-adjustments)).

---

## 🧮 Décomposition

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Composante | Définition |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variation de la plus-value/moins-value latente sur la période : valeur de marché − coût de base des positions ouvertes détenues à chaque limite, les titres en transit étant exclus ([le P&L latent de la période](index.md#two-unrealized-figures)) — pour les actifs valorisés dans une autre devise, y compris l'effet du taux de change sur leur coût historique |
| Realized | Somme de (produit de cession − coût historique des unités cédées) pour les VENTES de la période et les AJUSTEMENTS sortants non liés à une division, dont le produit de cession est nul ; les produits de cession sont convertis à la date de la transaction ([Moteur de portefeuille — §8](index.md#8-realized-gain-loss)) |
| Income | DIVIDENDE + INTÉRÊT de la période |
| FeesTaxes | FRAIS + IMPÔT de la période |
| Other | Ce qui ferme l'identité : le résultat de change sur les liquidités détenues dans une autre devise (effet de change sur les liquidités), le gain que les titres ont accumulé hors de la vue avant d'en franchir la limite (transferts à la valeur de marché), plus un résidu |

Other se calcule comme :

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Comme le coût de base conserve ses taux de change historiques (voir [Valeur comptable](book-value.md)), l'effet des taux de change sur les actifs étrangers fait partie de $\Delta\mathrm{UGL}$, et non de Other. Les liquidités détenues dans une autre devise sont différentes : la NAV et la valeur comptable les valorisent toutes deux au taux de chaque jour, si bien que leur effet de taux de change s'annule dans la plus-value/moins-value latente et n'est pas dans $\Delta\mathrm{UGL}$. Il constitue la première partie de Other, l'[effet de change sur les liquidités](#fx-on-cash) de chaque courtier $b$, que la vue Période affiche par courtier. La seconde partie, les [transferts à la valeur de marché](#transfers-at-market-value), est également affichée par courtier :

$$
\mathrm{Other} = \sum_{b \in S} \mathrm{FXonCash}_b + \sum_{b \in S} \mathrm{TMV}_b + \mathrm{Residual}
$$

Le résidu contient ce que ni les quatre composantes, ni le résultat de change sur les liquidités, ni les transferts à la valeur de marché ne peuvent voir :

- la variation du taux de change des liquidités pendant qu'elles circulent entre deux courtiers : en transit, elles n'appartiennent au solde d'aucun courtier ;
- le coût d'un change de devises, chez un courtier ou entre deux : −1 000 USD valant 920 € au taux du jour, échangés en +900 €, donnent −20 €, ce qui n'est ni des frais ni une vente ;
- la valeur des actifs qui circulent entre deux courtiers un jour de limite ;
- une vente exclue de Realized parce que son produit de cession n'a pas pu être converti, ou une vente ou un AJUSTEMENT sortant exclu parce que le coût de sa position est incomplet.
- le coût du dust : une vente qui laisse $10^{-5}$ unités ou moins dans une position retire ce qui reste du coût de base des positions ouvertes sans le vendre, si bien que son coût n'est ni dans $\Delta\mathrm{UGL}$ ni dans Realized — 0,00001 unité achetée à 100 000 laisse −1,00 ici ([§7](index.md#7-period-contribution)).

### 💵 Effet de change sur les liquidités {: #fx-on-cash }

Pour chaque courtier $b$ détenant des liquidités dans une devise autre que $C^*$, sur la période $(t_0, t_1]$, $t_0$ étant l'état d'ouverture :

$$
\mathrm{FXonCash}_b = \sum_{c \neq C^*} \Bigl[N_{b,c}(t_1)\,\mathrm{fx}(c, C^*, t_1) - N_{b,c}(t_0)\,\mathrm{fx}(c, C^*, t_0)\Bigr] - \sum_{\substack{m \in (t_0, t_1] \\ \mathrm{ccy}(m) \neq C^*}} s_m \cdot \mathrm{amount}_m \cdot \mathrm{fx}(\mathrm{ccy}(m), C^*, d_m)
$$

$N_{b,c}(t)$ est le solde que $b$ détient dans la devise $c$ à $t$, pondéré par la part du courtier, et $\mathrm{fx}$ le dernier taux connu à la date ou avant. La seconde somme porte sur les mouvements de $b$ dans une devise étrangère datés de la période : chaque montant, pondéré par la part $s_m$, au taux de sa propre date $d_m$. Le premier terme est la variation de valeur des liquidités étrangères, le second ce que les mouvements ont apporté ou retiré : la différence est ce que les taux de change ont fait aux liquidités détenues par le courtier. Elle est égale aux résultats de change que le moteur enregistre les jours de variation de taux de la période ([Moteur de portefeuille — §6](index.md#exchange-result-on-foreign-cash)). Les liquidités en $C^*$ n'en ont pas.

??? example "Exemple : des dollars chez un courtier sur un tableau de bord en euros"

    Un courtier détient 1 000 USD pendant toute la période, tandis que le taux passe de 0,90 à 0,92 EUR par USD :

    $$
    \mathrm{FXonCash} = 1{,}000 \times 0.92 - 1{,}000 \times 0.90 = +20 \text{ EUR}
    $$

    Avec un dépôt de 500 USD au milieu de la période à 0,91, et 0,92 à la fin :

    $$
    \mathrm{FXonCash} = 1{,}500 \times 0.92 - 1{,}000 \times 0.90 - 500 \times 0.91 = 1{,}380 - 900 - 455 = +25 \text{ EUR}
    $$

    Le dépôt est entré dans le capital à 455 € ; les +25 € correspondent à ce que les dollars ont gagné face à l'euro pendant que le courtier les détenait.

### 🔀 Transferts à la valeur de marché {: #transfers-at-market-value }

Dans une vue qui ne sélectionne que certains courtiers, une jambe de transfert dont l'autre côté est hors de la vue — titres envoyés à un courtier non sélectionné, reçus de l'un d'eux, ou transfert sans contrepartie — constitue du capital en nature à sa valeur de marché à sa date, tandis que le coût de la position suit ([Capital versé](deposited-capital.md)). Le gain que les unités ont accumulé chez l'autre courtier n'est donc ni dans $\Delta\mathrm{UGL}$ ni dans Realized, et finissait auparavant dans le résidu. C'est la deuxième partie de Other. Pour chaque courtier $b$ de la vue, sur les jambes $\ell$ datées dans $(t_0, t_1]$ :

$$
\mathrm{TMV}_b = \sum_{\ell \in (t_0, t_1]} \bigl(\mathrm{Cost}_\ell - \mathrm{Capital}_\ell\bigr)
$$

$\mathrm{Capital}_\ell$ est la valeur de marché que la jambe ajoute au capital (positive lorsqu'elle est reçue, négative lorsqu'elle est envoyée) et $\mathrm{Cost}_\ell$ le coût qu'elle déplace dans la position (même signe), tous deux en $C^*$ à la part du courtier. Pour des unités de valeur de marché $\mathrm{MV}$ et de coût $C$ :

| Jambe | $\mathrm{Capital}$ | $\mathrm{Cost}$ | Contribution |
|-----|---------|------|--------------|
| Envoyée hors de la vue | $-\mathrm{MV}$ | $-C$ | $+(\mathrm{MV} - C)$ |
| Reçue de l'extérieur de la vue | $+\mathrm{MV}$ | $+C$ | $-(\mathrm{MV} - C)$ |

La vue de l'expéditeur considère comme son propre résultat le gain que les unités ont réalisé pendant que le courtier expéditeur les détenait ; la vue du destinataire part de la valeur avec laquelle elles arrivent, si bien que ce qu'elles ont gagné auparavant n'est pas son résultat et est retiré. Une valeur inférieure au seuil d'arrondi n'est pas affichée, et le résidu diminue du montant affiché. Lorsque les deux courtiers sont sélectionnés, rien ne change : la paire est interne, et les unités ne font que répartir le résultat entre les deux lignes (voir le transfert interne dans Contribution par actif ci-dessous).

??? example "Exemple : unités achetées chez un courtier et envoyées à un autre"

    10 unités achetées à 50 chacune (coût 500 €) chez le courtier A sont envoyées au courtier B lorsqu'elles valent 800 €.

    - **Vue sur A uniquement :** les unités sortent avec 800 € de capital et emportent 500 € de coût : $\mathrm{TMV}_A = -500 + 800 = +300$ EUR.
    - **Vue sur B uniquement :** les unités arrivent avec 800 € de capital et 500 € de coût : $\mathrm{TMV}_B = 500 - 800 = -300$ EUR.
    - **Vue sur A et B :** aucune ligne de ce type.

---

## 💱 Variation non réalisée par devise {: #unrealized-change-by-currency }

$\Delta\mathrm{UGL}$ est réparti selon la devise $A$ dans laquelle les actifs sont valorisés. Pour les positions en devise $A$ au jour $t$, soit

| Symbole | Signification |
|--------|---------|
| $\mathrm{MV}_A(t)$ | Leur valeur de marché en $C^*$, au prix et au taux du jour |
| $\mathrm{Cost}^{A}_A(t)$ | Leur coût historique en $A$ |
| $\mathrm{Cost}^{*}_A(t)$ | Leur coût historique en $C^*$ |
| $r_A(t) = \mathrm{fx}(A, C^*, t)$ | Le taux de change du jour |

Le coût de chaque acquisition en $A$ provient de son coût en $C^*$ à la date d'acquisition, $c^{A} = c^{*} \cdot \mathrm{fx}(C^*, A, d)$ (ou du montant payé, lorsque le paiement est effectué en $A$). La plus-value/moins-value latente se décompose alors exactement en un **effet actif** et un **effet de taux de change** :

$$
E^{\text{asset}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{A}_A(t)\, r_A(t)
$$

$$
E^{\text{fx}}_A(t) = \mathrm{Cost}^{A}_A(t)\, r_A(t) - \mathrm{Cost}^{*}_A(t)
$$

$$
E^{\text{asset}}_A(t) + E^{\text{fx}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{*}_A(t) = \mathrm{UGL}_A(t)
$$

Pour une cotation exprimée en $A$, $\mathrm{MV}_A(t) = \frac{q}{qbq} \cdot \mathrm{mark}_A(t) \cdot r_A(t)$, donc l'effet actif est la variation propre des actifs dans leur devise, convertie au taux du jour : $E^{\text{asset}}_A(t) = \bigl(\frac{q}{qbq} \cdot \mathrm{mark}_A(t) - \mathrm{Cost}^{A}_A(t)\bigr)\, r_A(t)$. L'effet de taux de change est nul le jour de chaque achat. Pour $A = C^*$, $r = 1$ et $\mathrm{Cost}^{A} = \mathrm{Cost}^{*}$ : l'effet de taux de change disparaît, et les actifs déjà dans la devise de reporting n'ont qu'un effet actif.

Une position dans une devise $A \neq C^*$ qui ne peut pas être décomposée au jour $t$ — pas de valeur de marché, pas de taux $r_A(t)$, ou un coût incomplet dans l'une ou l'autre devise — ajoute à la place l'intégralité de son $\mathrm{MV} - \mathrm{Cost}^{*}$ (avec $\mathrm{MV} = 0$ lorsqu'elle n'a pas de valeur de marché) à une partie **non décomposée** $E^{\text{unsplit}}_A(t)$. Les positions en $C^*$ comptent toujours dans l'effet actif. Une position valorisée à son coût parce que son actif n'a aucune cotation ([Moteur de portefeuille — §3](index.md#3-position-state)) a $\mathrm{MV} = \mathrm{Cost}^{*}$ et n'ajoute à aucune partie : la décomposer inventerait un effet actif et un effet de taux de change de signes opposés.

Les lignes de la période sont les variations entre les deux états limites de la période — le dernier état à $t_0$ ou avant (zéro s'il n'y en a pas) et l'état à $t_1$ —, les mêmes deux états que $\Delta\mathrm{UGL}$ :

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

    L'ETF a gagné en dollars (+21,90 €), le dollar a perdu du terrain face à l'euro (−15,00 €) : ensemble, les +6,90 € de variation non réalisée de la période.

---

## 🎯 Contribution par actif

Pour chaque position $(a,b)$ :

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

L'ensemble des positions inclut **toute l'activité** de la période :

$$
\mathcal{P} = \text{positions avec activité ACHAT/VENTE/AJUSTEMENT/TRANSFERT ou quantité aux limites}
$$

Les valeurs de début et de fin d'une position sont la valorisation propre qu'en fait le portefeuille à la fin de $t_0$ et de $t_1$, les deux états de $\Delta\mathrm{UGL}$ ([Moteur de portefeuille — §3](index.md#3-position-state)) :

- sa cotation ([§2](index.md#2-valuation-price)) : une cotation de marché, ou à défaut un prix ACHAT/VENTE — ou, pour un actif sans aucune autre référence, le coût d'un transfert entrant à titre d'estimation —, un prix de transaction étant retraité à travers toute division ultérieure ;
- son coût de base, pour une position dont l'actif n'a aucune cotation (`ESTIMATED_AT_COST`) ;
- converties au taux de change du jour limite lui-même.

Les lignes totalisent donc le portefeuille : lorsque chaque ligne est connue, $\sum_{(a,b)} \Delta\mathrm{UGL}(a,b) = \Delta\mathrm{UGL}$, et les lignes plus les autres effets de la période — revenus et coûts non alloués, effet de change sur les liquidités, transferts à la valeur de marché, le résidu — bouclent $\mathrm{PnL}_{\text{period}}$. Other ne contient aucune différence de valorisation. Une position laissée avec $10^{-5}$ unités ou moins — dust — n'est détenue ni par une ligne ni par le portefeuille, si bien qu'elle ne change rien dans l'identité ([§3](index.md#3-position-state)) ; son coût se trouve dans le résidu (ci-dessus).

- **Transfert interne.** Un titre déplacé entre deux de vos courtiers au cours de la période répartit son résultat : la ligne du courtier expéditeur rend compte des unités jusqu'à leur arrivée, celle du courtier destinataire à partir de leur arrivée, et le total reste inchangé. Un transfert déjà en transit à $t_0$, ou encore en transit à $t_1$, conserve les valeurs limites simples ([§7](index.md#7-period-contribution)).
- **Valeurs inconnues.** Une position détenue à une limite dont la plus-value/moins-value latente y est inconnue — taux de change manquant, coût incomplet — a un $\Delta\mathrm{UGL}(a,b)$ inconnu, jamais le côté connu moins zéro.

Le rendement annualisé de la période borne le début de sa fenêtre à la plus tardive entre la date de début demandée et la date du lot ouvert le plus ancien. Il utilise $|\mathrm{StartValue}|$ comme base d'annualisation, en se rabattant sur le coût de base de fin pour les positions ouvertes en cours de période. Voir [Rendement annualisé net](net-annualized-return.md).

Une position clôturée au cours de la période — plus rien à $t_1$ — s'annualise différemment : sur le coût historique des unités qui l'ont quittée au cours de la période — vendues, ou déplacées vers un autre courtier du périmètre — sur la durée pendant laquelle elles y ont été détenues, depuis la plus tardive entre $t_0$ et sa première ouverture jusqu'au jour où ses dernières unités l'ont quittée. Son pourcentage de période conserve $|\mathrm{StartValue}|$ comme base. Voir [Rendement annualisé net — Positions clôturées au cours de la période](net-annualized-return.md#closed-in-period).

🔗 Voir **[Moteur de portefeuille — §7 Contribution de la période](index.md#7-period-contribution)** pour les détails.

---

## 📝 Exemple

- NAV à $t_0$ : 27 000 €
- Augmentation de la base de capital sur la période : 1 000 €
- NAV à $t_1$ : 33 000 €

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Voir aussi

- 💼 [NAV](nav.md) — point d'aboutissement de chaque formule de P&L
- 📖 [Valeur comptable](book-value.md) — coût de base historique derrière la plus-value/moins-value latente
- 💸 [Capital versé](deposited-capital.md) — P&L total depuis l'origine
- ⚙️ [Moteur de portefeuille](index.md) — modèle mathématique complet
- 📈 [Vue d'ensemble des métriques de performance](../index.md) — toutes les métriques de performance en un coup d'œil
