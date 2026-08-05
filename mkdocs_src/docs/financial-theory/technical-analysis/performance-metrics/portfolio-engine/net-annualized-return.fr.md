# 📈 Rendement Annualisé Net

*[⬅️ Retour au Moteur de Portefeuille](index.md)*

## 💡 Objectif

LibreFolio affiche le rendement annualisé uniquement lorsque la fenêtre d'observation est suffisamment longue pour rendre la capitalisation pertinente. La conversion utilisée est :

$$
\boxed{r_{\mathrm{ann}} = (1+r_{\mathrm{cum}})^{365/d}-1}
$$

où $d$ est le nombre de jours calendaires. Il s'agit de l'inverse de :

$$
r_{\mathrm{cum}}=(1+r_{\mathrm{ann}})^{d/365}-1
$$

L'implémentation renvoie `None` lorsque :

- $r_{\mathrm{cum}} \leq -1$
- $d < 30$
- le calcul provoque un dépassement de capacité (overflow)

!!! warning "Protection à 30 jours"

    Un rendement hebdomadaire annualisé sur 365 jours peut exploser en pourcentages dénués de sens. LibreFolio supprime donc l'annualisation en dessous de 30 jours et affiche une valeur vide au lieu d'un CAGR mathématiquement correct mais trompeur.

## 🧾 Vue des Positions

Pour une position ouverte dans « Vos positions » / résumé du portefeuille :

$$
r_{\mathrm{net}} =
\frac{
\mathrm{ComposanteMarché}
+ \mathrm{Revenus}
- \mathrm{FraisTaxes}
}{
\mathrm{BaseDeCoût}
}
$$

où :

$$
\mathrm{ComposanteMarché} =
\begin{cases}
\mathrm{ValeurActuelle}-\mathrm{BaseDeCoût}, & \text{valeur de marché existante}\\
0, & \text{sans prix / valorisé au coût}
\end{cases}
$$

Fenêtre d'annualisation :

$$
d = t_{\mathrm{rapport}} - t_{\mathrm{premier\ lot\ affectant}}
$$

Les types de transactions affectant les lots sont :

$$
\{\text{ACHAT},\ \text{VENTE},\ \text{AJUSTEMENT},\ \text{TRANSFERT}\}
$$

Cela inclut les successions en nature, les transferts de courtier et les positions initiées par ajustement. Une ancienne analyse basée uniquement sur ACHAT/VENTE aurait manqué ces positions.

## 🪟 Vue Périodique

Pour la contribution périodique par actif :

$$
\mathrm{PnL}_{période} =
\Delta \mathrm{PVN}
+ \mathrm{Réalisé}
+ \mathrm{Revenus}
- \mathrm{FraisTaxes}
$$

Le pourcentage affiché pour la période reste :

$$
r_{\mathrm{période}} = \frac{\mathrm{PnL}_{période}}{|\mathrm{ValeurDépart}|}
$$

lorsque `ValeurDépart` est non nul. L'annualisation peut revenir à la base de coût finale pour les actifs ouverts en milieu de période :

$$
\mathrm{base\_ann}=
\begin{cases}
|\mathrm{ValeurDépart}|, & |\mathrm{ValeurDépart}|>0\\
\mathrm{BaseDeCoût}_{fin}, & \text{sinon}
\end{cases}
$$

Le début de la fenêtre est limité au lot FIFO le plus ancien encore ouvert à la fin de la période :

$$
t_{\mathrm{début}}=\max(t_{\mathrm{from}},\ t_{\mathrm{lot\ ouvert\ le\ plus\ ancien}})
$$

Ensuite :

$$
r_{\mathrm{ann}} =
\operatorname{annualiser}\left(\frac{\mathrm{PnL}_{période}}{\mathrm{base\_ann}},\ t_{\mathrm{fin}}-t_{\mathrm{début}}\right)
$$

## 🧬 Lots FIFO

Le rendement annualisé d'un lot FIFO est net des revenus, frais et taxes alloués :

$$
\mathrm{PnLNetTotal}_i =
\mathrm{PnLMarché}_i
+ \mathrm{PnLRéalisé}_i
+ \mathrm{Revenus}_i
- \mathrm{Frais}_i
- \mathrm{Taxes}_i
$$

$$
\mathrm{RendementNetTotal}_i =
\frac{\mathrm{PnLNetTotal}_i}{\mathrm{ValeurDOuverture}_i}
$$

La valeur annualisée utilise `rendement_net_total`, pas le `rendement_total` brut :

$$
r_{\mathrm{ann},i} =
\operatorname{annualiser}
\left(
\mathrm{RendementNetTotal}_i,\ 
t_{\mathrm{fin\ du\ lot}}-t_{\mathrm{ouverture}}
\right)
$$

où $t_{\mathrm{fin\ du\ lot}}$ est la date de clôture pour les lots entièrement clos, sinon la date de fin de la période d'analyse.

## 🔗 Liens connexes

- 🧭 [Résolution des Prix](price-resolution.md) — source des valorisations de marché et d'origine transactionnelle
- 📉 [ROI Simple](roi.md) — contexte du rendement principal et au niveau de la position
- 📊 [PnL Périodique](period-pnl.md) — décomposition périodique
- 🔬 [Analyse des Lots FIFO](../fifo-engine/fifo-lot-analysis.md) — métriques nettes par lot
