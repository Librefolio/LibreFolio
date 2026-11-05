# 📉 ROI simple (retour sur investissement)

## 💡 Qu'est-ce que c'est ?

Le ROI simple mesure la valeur générée par rapport au capital investi. Dans le moteur de portefeuille actuel, le dénominateur du capital investi est le **capital de référence** issu de `cumulative_external_cash_flow`, et non les seuls dépôts en espèces.

## 🧮 Formule

$$
\mathrm{ROI}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)}
{\mathrm{CapitalBaseline}(t)}
$$

Le même capital de référence détermine l'indicateur principal `total_gain_loss` :

$$
\mathrm{TotalGainLoss}(t)=\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)
$$

`CapitalBaseline` inclut les flux de trésorerie externes ordinaires et le capital en nature valorisé provenant des opérations ADJUSTMENT/TRANSFER. Cela évite que les portefeuilles hérités ou initialisés affichent un ROI absurde parce qu'un actif a été intégré sans dépôt en espèces.

## 🪟 Le ROI d'une période {: #dashboard-period-roi }

Le ROI affiché sur la carte Rendements du tableau de bord et sa ligne sur le graphique `%` mesurent la période sélectionnée, et non l'historique complet. Leur capital correspond à la valeur à l'ouverture de la période, augmentée des dépôts et diminuée des retraits effectués après cette ouverture :

$$
\mathrm{ROI}_{\mathrm{period}}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{NetInvested}(t)}{\mathrm{NetInvested}(t)},
\qquad
\mathrm{NetInvested}(t)=\max\!\left(0,\ \mathrm{NAV}(t_0)+\sum_{t_0<s\le t}\mathrm{CF}_s\right)
$$

où $t_0$ est le dernier jour de l'historique égal ou antérieur au début de la période, et $\mathrm{CF}_s$ comptabilise les flux externes — dépôts positifs, retraits négatifs, capital en nature inclus comme pour le capital de référence ci-dessus. La carte correspond au dernier point de la ligne ; lorsque $\mathrm{NetInvested}(t)$ est nul, le ROI vaut $0$, jamais une valeur manquante.

Lorsque la période commence **avant le premier jour du portefeuille**, il n'y a aucune valeur d'ouverture, et les flux de ce premier jour — le premier dépôt — seraient exclus de la somme. La période couvre alors tout l'historique, donc son capital correspond à l'ensemble des flux, premier dépôt compris : le ROI est identique à celui obtenu sans date de début, sur la carte comme à chaque point de la ligne.

## 🎯 Quand l'utiliser

- Pour lire le gain ou la perte globale du portefeuille au regard du capital économique apporté.
- Pour comparer la NAV actuelle au capital de référence actuel.
- Pour vérifier la cohérence de la performance ajustée en fonction des flux de trésorerie avant de consulter le TWRR/MWRR.

## 📈 Rendement annualisé net d'une position

Les positions ouvertes affichent également un CAGR net :

$$
r_{\mathrm{net}}=
\frac{\mathrm{MarketComponent}+\mathrm{Income}-\mathrm{FeesTaxes}}
{\mathrm{CostBasis}}
$$

L'annualisation s'appuie sur :

$$
r_{\mathrm{ann}}=(1+r_{\mathrm{net}})^{365/d}-1
$$

La fenêtre commence à la première transaction affectant un lot : BUY, SELL, ADJUSTMENT ou TRANSFER. Les valeurs sur une période inférieure à 30 jours sont supprimées. Les définitions complètes figurent dans [Rendement annualisé net](net-annualized-return.md).

## ⚠️ Le défaut : la dilution due aux flux de trésorerie

Le ROI simple reste sensible au montant et au moment de l'ajout de capital. Si vous ajoutez un apport important après que des gains se sont déjà produits, le ratio peut baisser alors que la valeur de marché n'a pas baissé. Utilisez [P&L période](period-pnl.md), [TWRR](twrr.md) et [MWRR](mwrr.md) pour distinguer le profit absolu, le rendement de la stratégie et le rendement de l'investisseur pondéré par les flux de trésorerie.
