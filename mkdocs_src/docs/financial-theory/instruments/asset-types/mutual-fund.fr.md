# <img src="../../../static/icons/asset-types/fund.png" width="32" style="vertical-align: middle;" /> Fonds Commun de Placement

Un **fonds commun de placement** est un véhicule d'investissement géré professionnellement qui regroupe l'argent de nombreux investisseurs pour acheter un portefeuille diversifié d'actions, d'obligations ou d'autres titres.

---

## 🔑 Caractéristiques Clés

| Propriété | Détail |
|----------|--------|
| **Code dans LibreFolio** | `FUND` |
| **Valorisation** | VNI (Valeur Liquidative) calculée une fois par jour, après la clôture du marché |
| **Devise** | Libellé dans la devise de référence du fonds |
| **Dividendes** | Peuvent être distribués (fonds de revenu) ou réinvestis (fonds de croissance) |
| **Frais** | Frais de gestion (TER), commissions d'entrée/sortie |
| **Fournisseurs typiques** | Yahoo Finance, Manuel |

---

## 📊 Fonctionnement des Fonds Communs de Placement

1. **Mise en commun** : Les investisseurs achètent des parts du fonds
2. **Gestion** : Un gestionnaire de fonds professionnel sélectionne et gère les titres sous-jacents
3. **Valorisation VNI** : La valeur du fonds est calculée quotidiennement comme suit : actifs totaux − passifs ÷ nombre de parts en circulation
4. **Distributions** : Les revenus (dividendes, intérêts) peuvent être distribués ou réinvestis

---

## 📐 Calcul de la VNI

$$
\text{VNI} = \frac{\text{Actifs Totaux} - \text{Passifs Totaux}}{\text{Nombre de parts en circulation}}
$$

Contrairement aux ETF, les fonds communs de placement ne s'échangent qu'à la VNI de fin de journée — vous ne pouvez pas acheter ou vendre aux prix intrajournaliers.

---

## 🔗 Liens connexes

- 📊 **[ETFs](etfs.md)** — Alternative cotée en bourse avec prix intrajournaliers
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales de la distribution vs l'accumulation
- 📈 **[Rendements et Taux de Croissance](../../fundamentals/returns.md)** — Mesurer la performance d'un fonds
