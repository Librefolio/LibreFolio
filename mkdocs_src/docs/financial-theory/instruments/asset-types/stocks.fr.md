# ![](../../../static/icons/asset-types/stock.png){: width="32" style="vertical-align: middle;" } Actions

Une **action** (ou titre de propriété) représente une part du capital d'une société cotée en bourse. Lorsque vous achetez une action, vous devenez actionnaire avec un droit proportionnel sur les actifs et les bénéfices de la société.

---

## 🔑 Caractéristiques Clés

| Propriété | Détail |
|----------|--------|
| **Code dans LibreFolio** | `STOCK` |
| **Cotation** | Cotations en temps réel ou différées provenant des bourses (NYSE, NASDAQ, LSE, etc.) |
| **Devise** | Libellée dans la devise locale de la bourse |
| **Dividendes** | De nombreuses actions versent des dividendes périodiques en espèces (trimestriels aux États-Unis, semestriels en Europe) |
| **Splits** | Les sociétés peuvent fractionner les actions (ex: 4:1) pour abaisser le prix par action |
| **Fournisseurs typiques** | Yahoo Finance, CSS Scraper |

---

## 📊 Fonctionnement des Actions

1. **Découverte du prix** : Les actions s'échangent sur des bourses publiques pendant les heures d'ouverture du marché. Le prix reflète l'offre et la demande.
2. **Dividendes** : Les sociétés peuvent distribuer une partie des bénéfices aux actionnaires. Cela crée un [Événement de dividende](../asset-events/dividend.md) à la date de détachement (ex-date).
3. **Plus-values** : La différence entre le prix d'achat et le prix de vente détermine votre profit ou votre perte. Voir [Fiscalité](../../fundamentals/taxation.md).
4. **Splits** : Une société peut fractionner ses actions pour améliorer la liquidité. Un split 4:1 signifie que chaque action devient 4 actions à ¼ du prix. Voir [Événement de split](../asset-events/split.md).

---

## 📐 Rendement Total

Le rendement total d'une action inclut à la fois l'appréciation du prix et les dividendes :

$$
R_{total} = \frac{P_{end} - P_{start} + \sum D_i}{P_{start}}
$$

où $D_i$ représente tous les versements de dividendes reçus pendant la durée de la position.

---

## 🔗 Liens Connexes

- 💰 **[Événements de dividende](../asset-events/dividend.md)** — Comment les dividendes affectent le prix des actions
- ✂️ **[Événements de split](../asset-events/split.md)** — Divisions et regroupements d'actions
- 📈 **[Rendements & Taux de Croissance](../../fundamentals/returns.md)** — Mesurer la performance des actions
