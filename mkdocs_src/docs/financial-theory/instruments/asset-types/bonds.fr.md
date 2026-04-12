# <img src="../../../static/icons/asset-types/bond.png" width="32" style="vertical-align: middle;" /> Obligations

Une **obligation** est un titre à revenu fixe représentant un prêt d'un investisseur à un emprunteur (gouvernement ou entreprise). L'emprunteur verse des intérêts périodiques (**coupons**) et rembourse le principal (**valeur nominale**) à l'échéance.

---

## 🔑 Caractéristiques Clés

| Propriété | Détail |
|----------|--------|
| **Code dans LibreFolio** | `BOND` |
| **Cotation** | Cotée en pourcentage de la valeur nominale (ex : 98,50 = 98,5 % du nominal) |
| **Devise** | Libellée dans la devise d'émission |
| **Coupons** | Taux fixe ou flottant, payés semestriellement ou annuellement |
| **Échéance** | Date fixe à laquelle le principal est remboursé |
| **Fournisseurs typiques** | Yahoo Finance, Scheduled Investment, Manuel |

---

## 📊 Concepts de Cotation des Obligations

### 💵 Valeur Nominale (Pair)

Le montant que l'émetteur remboursera à l'échéance — généralement 1 000 $ ou 1 000 € par obligation.

### 📈 Taux du Coupon

Le taux d'intérêt annuel payé sur la valeur nominale :

$$
\text{Coupon Annuel} = \text{Valeur Nominale} \times \text{Taux du Coupon}
$$

### 📊 Taux de Rendement à l'Échéance (YTM)

Le rendement total attendu si l'obligation est détenue jusqu'à l'échéance, en tenant compte du prix d'achat, des paiements de coupons et de la valeur nominale à l'échéance. La formule du YTM est une **approximation mathématique** largement utilisée pour comprendre comment le marché fixe le prix des obligations en réponse aux variations des taux d'intérêt, et sert de base à de nombreux autres indicateurs de titres à revenu fixe :

$$
P = \sum_{t=1}^{n} \frac{C}{(1 + y)^t} + \frac{F}{(1 + y)^n}
$$

où $P$ = prix, $C$ = coupon, $F$ = valeur nominale, $y$ = YTM, $n$ = périodes.

### 📉 Prix Plein vs Prix Net

- **Prix Net** : Le prix coté, hors intérêts courus
- **Prix Plein** : Prix net + intérêts courus (ce que vous payez réellement)

$$
\text{Prix Plein} = \text{Prix Net} + \text{Intérêts Courus}
$$

Les intérêts courus dépendent de la [Convention de Comptage des Jours](../../fundamentals/day-count.md).

---

## 📈 Relation Prix–Rendement

Les prix des obligations évoluent **inversement** aux rendements :

- Quand les taux d'intérêt augmentent → les prix des obligations baissent
- Quand les taux d'intérêt baissent → les prix des obligations augmentent

Ceci est dû au fait que les obligations existantes avec des coupons plus faibles deviennent moins attractives par rapport aux nouvelles obligations émises à des taux plus élevés.

---

## 🔗 Liens Connexes

- 📈 **[Événements d'intérêt](../asset-events/interest.md)** — Paiements de coupons et courus
- 🏁 **[Règlement à l'Échéance](../asset-events/maturity-settlement.md)** — Remboursement du capital à l'échéance
- 📊 **[Ajustement de Prix](../asset-events/price-adjustment.md)** — Mark-to-market et dépréciations
- 📅 **[Conventions de Comptage des Jours](../../fundamentals/day-count.md)** — Comment les intérêts courus sont calculés
