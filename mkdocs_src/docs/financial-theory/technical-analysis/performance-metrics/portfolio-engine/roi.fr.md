# 📉 ROI simple (Retour sur Investissement)

## 💡 Qu'est-ce que c'est ?

Le ROI simple mesure la valeur générée par rapport au capital investi. Dans le moteur de portefeuille actuel, le dénominateur du capital investi est la **base de capital** issue de `cumulative_external_cash_flow`, et non les seuls dépôts en espèces.

## 🧮 Formule

$$
\mathrm{ROI}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)}
{\mathrm{CapitalBaseline}(t)}
$$

La même base pilote le `total_gain_loss` principal :

$$
\mathrm{TotalGainLoss}(t)=\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)
$$

`CapitalBaseline` inclut les flux de trésorerie externes ordinaires et le capital d'AJUSTEMENT/TRANSFERT apporté en nature valorisé. Cela évite que les portefeuilles hérités ou initialisés n'affichent un ROI absurde parce qu'un actif est entré sans dépôt en espèces.

## 🎯 Quand l'utiliser

- Pour lire le gain/la perte global du portefeuille par rapport au capital économique contribué.
- Pour comparer la VNI actuelle à la base de capital actuelle.
- Pour vérifier la performance ajustée des flux de trésorerie avant d'examiner le TWRR/MWRR.

## 📈 Rendement annualisé net d'une position

Les positions exposent également un TCAC net :

$$
r_{\mathrm{net}}=
\frac{\mathrm{ComposanteMarché}+\mathrm{Revenus}-\mathrm{FraisImpôts}}
{\mathrm{CostBasis}}
$$

L'annualisation utilise :

$$
r_{\mathrm{ann}}=(1+r_{\mathrm{net}})^{365/d}-1
$$

La fenêtre commence à la première transaction affectant le lot : ACHAT, VENTE, AJUSTEMENT ou TRANSFERT. Les valeurs inférieures à 30 jours sont supprimées. Les définitions complètes se trouvent dans [Rendement annualisé net](net-annualized-return.md).

## ⚠️ Le défaut : Dilution par les flux de trésorerie

Le ROI simple reste sensible au montant et au moment du capital ajouté. Si vous ajoutez un apport important après que des gains ont déjà eu lieu, le ratio peut diminuer même si la valeur de marché n'a pas changé. Utilisez [P&L de période](period-pnl.md), [TWRR](twrr.md) et [MWRR](mwrr.md) pour séparer le profit absolu, le rendement de la stratégie et le rendement de l'investisseur pondéré par l'argent.
