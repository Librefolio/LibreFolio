# ![](../../../static/icons/asset-types/etf.png){: width="32" style="vertical-align: middle;" } ETFs (Exchange Traded Funds)

Un **ETF** est un panier de titres (actions, obligations, matières premières ou un mélange) qui s'échange en bourse comme une action. Les ETFs combinent la diversification des fonds communs de placement avec la flexibilité de négociation en temps réel des actions.

---

## 🔑 Caractéristiques principales

| Propriété | Détail |
|----------|--------|
| **Code dans LibreFolio** | `ETF` |
| **Prix** | Prix de bourse en temps réel, comme les actions |
| **Devise** | Libellé dans la devise de la bourse de cotation |
| **Dividendes** | Peuvent être distribués (Dist) ou réinvestis en interne (Acc) |
| **TER** | Total Expense Ratio — frais de gestion annuels déduits du NAV |
| **Fournisseurs typiques** | Yahoo Finance, justETF, CSS Scraper |

Dans LibreFolio, `ETF` est le code d'un fonds au contenu mixte ou non précisé ; un fonds qui détient une seule classe d'actifs prend l'un des six sous-types (`ETF_STOCK`, `ETF_BOND`, `ETF_COMMODITY`, `ETF_REAL_ESTATE`, `ETF_CRYPTO`, `ETF_MONETARY`), répertoriés dans le tableau de la [famille ETF](index.md#etf-family) avec leurs icônes composites et la classe à laquelle chacun se rattache.

---

## 📊 Accumulation vs Distribution

| Caractéristique | Accumulation (Acc) | Distribution (Dist) |
|---------|-------------------|-------------------|
| **Dividendes** | Réinvestis en interne | Versés aux détenteurs |
| **Événement fiscal** | Uniquement lors de la vente | À chaque distribution |
| **Capitalisation** | Croissance composée complète | Réduite par le frein fiscal |
| **Idéal pour** | Croissance à long terme | Besoins de revenus |

L'[avantage du report d'imposition](../../fundamentals/taxation.md#tax-deferral-advantage) des ETFs d'accumulation peut être significatif sur de longs horizons.

---

## 📈 NAV vs Prix de Marché

- **NAV** (Net Asset Value, valeur liquidative) : La valeur réelle des positions sous-jacentes ÷ actions en circulation. Calculée quotidiennement.
- **Prix de Marché** : Le prix auquel l'ETF s'échange réellement en bourse. Peut dévier légèrement du NAV.
- **Prime/Décote** : Lorsque le prix de marché > NAV, l'ETF s'échange avec une prime ; lorsqu'il est < NAV, avec une décote.

---

## 🔍 Suivi de l'indice de référence

La plupart des ETFs suivent un indice de référence (ex: S&P 500, MSCI World). L'**erreur de suivi** (tracking error) mesure à quel point le rendement de l'ETF s'écarte de celui de l'indice de référence :

$$
TE = \sigma(R_{ETF} - R_{index})
$$

Une erreur de suivi plus faible = une meilleure réplication de l'indice de référence.

---

## 🔗 Liens connexes

- 💰 **[Événements de Dividendes](../asset-events/dividend.md)** — Distributions provenant des positions de l'ETF
- 📈 **[Indices et indices de référence](index-benchmark.md)** — Fonctionnement des indices de référence
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales Acc vs Dist
