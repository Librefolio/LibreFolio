# 📈 Rendement net annualisé

## 💡 Objectif

LibreFolio n'affiche le rendement annualisé que lorsque la fenêtre observée est suffisamment longue pour que la capitalisation ait un sens. La conversion partagée est :

$$
\boxed{r_{\mathrm{ann}} = (1+r_{\mathrm{cum}})^{365/d}-1}
$$

où $d$ est le nombre de jours calendaires. C'est l'inverse de :

$$
r_{\mathrm{cum}}=(1+r_{\mathrm{ann}})^{d/365}-1
$$

L'implémentation renvoie `None` lorsque :

- $r_{\mathrm{cum}} \leq -1$
- $d < 30$
- le calcul produit un débordement

!!! warning "Garde-fou des trente jours"

    Un rendement d'une semaine annualisé sur 365 jours peut exploser en pourcentages dénués de sens. LibreFolio supprime donc l'annualisation en dessous de 30 jours et affiche une valeur vide au lieu d'un CAGR mathématiquement correct mais trompeur.

## 🧾 Vue des positions

Pour une position ouverte dans « Vos positions » / le résumé du portefeuille :

$$
r_{\mathrm{net}} =
\frac{
\mathrm{MarketComponent}
+ \mathrm{Income}
- \mathrm{FeesTaxes}
}{
\mathrm{CostBasis}
}
$$

où :

$$
\mathrm{MarketComponent} =
\begin{cases}
\mathrm{CurrentValue}-\mathrm{CostBasis}, & \text{la valeur de marché existe}\\
0, & \text{sans prix / valorisé au coût}
\end{cases}
$$

Fenêtre d'annualisation :

$$
d = t_{\mathrm{report}} - t_{\mathrm{first\ lot\ affecting}}
$$

Les types de transactions affectant les lots sont :

$$
\{\text{BUY},\ \text{SELL},\ \text{ADJUSTMENT},\ \text{TRANSFER}\}
$$

Cela inclut les successions en nature, les transferts entre courtiers et les positions initialisées par ajustement. L'ancienne détection limitée aux BUY/SELL manquerait ces positions.

## 🪟 Vue de la période

Pour la contribution par actif sur la période :

$$
\mathrm{PnL}_{period} =
\Delta \mathrm{UGL}
+ \mathrm{Realized}
+ \mathrm{Income}
- \mathrm{FeesTaxes}
$$

Le pourcentage de période affiché reste :

$$
r_{\mathrm{period}} = \frac{\mathrm{PnL}_{period}}{|\mathrm{StartValue}|}
$$

lorsque `StartValue` est non nul. L'annualisation peut se rabattre sur le coût de base de fin pour les actifs ouverts en cours de période :

$$
\mathrm{ann\_base}=
\begin{cases}
|\mathrm{StartValue}|, & |\mathrm{StartValue}|>0\\
\mathrm{CostBasis}_{end} + \sum_a \left(V_a - C_a\right), & \text{sinon}
\end{cases}
$$

La somme porte sur les transferts depuis un autre courtier du périmètre que la position a reçus au cours de la période, chacun étant compté comme dans [Positions clôturées dans la période](#closed-in-period) : ce que leurs unités ont gagné avant leur arrivée, c'est-à-dire la valeur à l'arrivée moins le coût historique déplacé (MF-A9). Le résultat de la position compte ces unités à partir de leur valeur à l'arrivée, et son coût de fin à leur coût historique, de sorte que la base ajoute le même montant. Cela ne s'applique que tant qu'aucune unité n'a quitté la position pendant la période, avant l'arrivée ou après celle-ci : une fois que des unités l'ont quittée, un transfert ne porte aucune quantité permettant de savoir quelle partie de la somme est partie avec elles, et la somme est abandonnée — le coût de fin seul constitue la base, comme pour toute position ouverte en cours de période qui a vendu une partie de ce qu'elle a acheté.

Le début de la fenêtre est borné inférieurement par le plus ancien lot FIFO encore ouvert à la fin de la période :

$$
t_{\mathrm{start}}=\max(t_{\mathrm{from}},\ t_{\mathrm{oldest\ open\ lot}})
$$

Les lots sont comptés chez chaque courtier : un transfert ouvre un lot daté de son arrivée chez le courtier récepteur. Une division d'actions rééchelonne les lots ouverts et conserve leurs dates, de sorte qu'elle ne raccourcit jamais la fenêtre. Les plus anciens lots qui détiennent ensemble $10^{-5}$ unités ou moins — le résidu laissé par une vente — sont mis de côté, comme une position clôturée compte un tel résidu comme clôturé : un résidu laissé il y a des années ne ramène pas le début de la fenêtre à sa date, et une position qui ne détient rien de plus que ce résidu n'a aucun lot ouvert (MF-A7). Les quantités sont celles du moteur, à la part du propriétaire dans le courtier : sur un courtier détenu à 50 %, un résidu de $0{,}000012$ unités vaut $0{,}000006$ pour le propriétaire, une poussière pour la fenêtre comme pour la ligne (MF-A10).

Ensuite :

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{ann\_base}},\ t_{\mathrm{end}}-t_{\mathrm{start}}\right)
$$

### 🔚 Positions clôturées dans la période {: #closed-in-period }

Une position est clôturée lorsque sa quantité à $t_{\mathrm{end}}$, à la part du propriétaire dans le courtier, est inférieure ou égale au seuil de poussière de $10^{-5}$ unités, de sorte qu'un résidu laissé par des rachats par tranches compte comme clôturé. Elle n'a pas de coût de fin, et une valeur de début ne dit rien d'une position vendue quelques semaines après le début. Son rendement annualisé utilise le capital engagé et la durée pendant laquelle elle a été détenue dans la période :

$$
\mathrm{CostOut} = \sum_{s\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} C_s \;+\; \sum_{m\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} C_m \;+\; \sum_{a\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} \left(V_a - C_a\right)
$$

$$
t_{\mathrm{start}} = \max(t_{\mathrm{from}},\ t_{\mathrm{first\ opening}}), \qquad t_{\mathrm{close}} = \text{dernier jour où sa quantité est tombée au seuil de poussière ou en dessous}
$$

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{CostOut}},\ t_{\mathrm{close}}-t_{\mathrm{start}}\right)
$$

- $C_s$ est le coût historique, en $C^*$, de chaque cession comptabilisée par le P&L réalisé de la période — un SELL, ou un ADJUSTMENT sortant non lié à une division ([Moteur de portefeuille — §8](index.md#8-realized-gain-loss)). Une cession exclue du P&L réalisé n'ajoute aucun coût.
- $C_m$ est le coût historique que chaque transfert vers un autre courtier du périmètre a fait sortir, lorsque la ligne compte le tract de ce transfert : il est parti après $t_{\mathrm{from}}$, est arrivé au plus tard à $t_{\mathrm{end}}$, et tant sa valeur à l'arrivée que le coût déplacé sont connus ([P&L période](period-pnl.md), décision de développement P22). Le résultat de la ligne porte ce que ces unités ont fait jusqu'à leur arrivée (l'ajustement de tract), de sorte que leur coût appartient à la base.
- $V_a - C_a$ est, pour chacun de ces transferts que la position a **reçus**, ce que ses unités ont gagné avant leur arrivée : leur valeur à l'arrivée moins le coût historique déplacé avec elles. Le résultat de la ligne initialise ces unités à $V_a$ (l'ajustement de tract retire $V_a - C_a$), tandis que $C_s$ et $C_m$ portent leur coût historique, de sorte que la base ajoute le même montant et les compte, elles aussi, à leur valeur à l'arrivée (MF-A8). Ainsi, $\mathrm{CostOut}$ n'est pas seulement un coût historique : pour les unités que la position a reçues, la base retient leur valeur à l'arrivée.
- $t_{\mathrm{first\ opening}}$ est la première acquisition de la position chez ce courtier : un transfert l'ouvre à son arrivée chez celui-ci, une division ne l'ouvre jamais. C'est la toute première acquisition, pas celle du dernier lot, de sorte que les jours à zéro entre deux clôtures à l'intérieur de la période restent dans la fenêtre.
- Le numérateur est le $\mathrm{PnL}_{period}$ entier de la ligne : pour une position détenue à $t_{\mathrm{from}}$, son $\Delta\mathrm{UGL}$ restitue la plus-value ou moins-value latente avec laquelle elle a commencé.
- Le pourcentage de période affiché conserve $|\mathrm{StartValue}|$ comme base : seule la valeur annualisée change de base et de fenêtre.

Lorsque cela ne donne aucune valeur, deux cas se présentent :

- **Moins de 30 jours de détention** dans la période, $t_{\mathrm{close}} - t_{\mathrm{start}} < 30$ : la ligne n'a pas de rendement annualisé (`—`), quelles que soient les autres raisons pour lesquelles la base est inutilisable. La règle ci-dessus annualiserait sur $t_{\mathrm{from}} \to t_{\mathrm{end}}$, comme si dix jours de détention avaient duré toute la période (MF-A3).
- **Sinon**, la ligne conserve la règle ci-dessus. Cela se produit lorsque des unités ont quitté la position d'une autre manière — un transfert hors du périmètre, ou encore en transit à $t_{\mathrm{end}}$, un transfert ou une cession dont la valeur ou le coût est inconnu — car le résultat de la ligne contiendrait alors plus que ce que sa base couvre ; et avec un rendement de $-100\%$ ou pire. La règle ci-dessus est : $|\mathrm{StartValue}|$ sur $t_{\mathrm{from}} \to t_{\mathrm{end}}$, et aucune valeur pour une position ouverte dans la période.

??? example "Exemple : une position vendue 90 jours après le début d'une période d'un an"

    À $t_{\mathrm{from}}$, la position vaut 1 100 pour un coût de 1 000. Tout est vendu 90 jours plus tard pour 1 250 :

    $$
    \mathrm{PnL}_{period} = (0 - 100) + (1\,250 - 1\,000) = +150
    $$

    $$
    r_{\mathrm{ann}} = \operatorname{annualize}\left(\frac{150}{1\,000},\ 90\right) = 1{,}15^{365/90} - 1 \approx +76{,}3\%
    $$

    La plus-value latente de +100 avec laquelle elle a commencé est retirée via le $\Delta\mathrm{UGL}$ ; le P&L réalisé ajoute +250. Le pourcentage de période reste $150 / 1\,100 = 13{,}64\%$ ; annualisé sur toute l'année sur la valeur de début, comme le serait une position ouverte, le même +150 afficherait également 13,64 %.

??? example "Exemple : moitié vendue, moitié transférée vers un autre courtier"

    À $t_{\mathrm{from}}$, la position détient 10 unités, d'une valeur de 1 100 pour un coût de 1 000. Cinq sont vendues pour 625 ; cinq sont transférées vers un autre courtier du périmètre et valent 600 à leur arrivée :

    $$
    \mathrm{PnL}_{period} = \underbrace{(0 - 100)}_{\Delta\mathrm{UGL}} + \underbrace{(625 - 500)}_{\text{Realized}} + \underbrace{(600 - 500)}_{\text{tract}} = +125
    $$

    $$
    \mathrm{CostOut} = 500 + 500 = 1\,000, \qquad \frac{125}{1\,000} = 12{,}5\%
    $$

    Le coût des seules unités vendues donnerait $125 / 500 = 25\%$ : le résultat des unités transférées dans le numérateur, sans leur coût dans la base (MF-A5).

    Le courtier qui a reçu les cinq unités et les a ensuite vendues pour 660 lit en miroir : son résultat est $(660 - 500) - (600 - 500) = +60$, et sa base $500 + (600 - 500) = 600$, donc $60 / 600 = 10\%$ — les unités comptent à partir de leur valeur à l'arrivée, dans le résultat comme dans la base (MF-A8).

## 🧬 Lots FIFO

Le rendement annualisé d'un lot FIFO est net des revenus, frais et impôts alloués :

$$
\mathrm{NetTotalPnL}_i =
\mathrm{MarketPnL}_i
+ \mathrm{RealizedPnL}_i
+ \mathrm{Income}_i
- \mathrm{Fees}_i
- \mathrm{Taxes}_i
$$

$$
\mathrm{NetTotalReturn}_i =
\frac{\mathrm{NetTotalPnL}_i}{\mathrm{OpeningValue}_i}
$$

La valeur annualisée utilise `net_total_return`, et non le `total_return` brut :

$$
r_{\mathrm{ann},i} =
\operatorname{annualize}
\left(
\mathrm{NetTotalReturn}_i,\ 
t_{\mathrm{lot\ end}}-t_{\mathrm{opening}}
\right)
$$

où $t_{\mathrm{lot\ end}}$ est la date de clôture pour les lots entièrement clôturés, sinon la date de fin de l'analyse.

## 🔗 Voir aussi

- 🧭 [Résolution des prix](price-resolution.md) — source des valorisations de marché et d'origine transactionnelle
- 📉 [ROI simple](roi.md) — contexte de rendement global et au niveau des positions
- 📊 [P&L période](period-pnl.md) — décomposition de la période
- 🔬 [Analyse des lots FIFO](../fifo-engine/fifo-lot-analysis.md) — métriques nettes par lot
- ⚙️ [Moteur de portefeuille](index.md) — modèle mathématique complet
