# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

Les plateformes de **P2P / Crowdfunding** permettent aux investisseurs de prêter des montants relativement modestes à des consommateurs, des entreprises ou des projets immobiliers. L'investisseur n'achète aucune part : il détient un **prêt**, qui verse généralement un intérêt fixe ou variable et possède une date d'échéance définie.

LibreFolio modélise ces instruments comme la **famille Crowdfunding** des
[types d'actifs](index.md#crowdfunding-family) : le générique `CROWDFUND` et sa spécialisation immobilière, `CROWDFUND_REAL_ESTATE`.

---

## 🔑 Caractéristiques clés

| Propriété | Détail |
|----------|--------|
| **Codes dans LibreFolio** | `CROWDFUND` — prêt P2P et aux entreprises, et membre générique de la famille · `CROWDFUND_REAL_ESTATE` — prêts adossés à des projets immobiliers |
| **Valorisation** | Non coté en bourse — la valeur correspond généralement au capital investi |
| **Devise** | Libellée dans la devise d'exploitation de la plateforme |
| **Revenus** | Versements d'intérêts périodiques (mensuels, trimestriels ou à l'échéance) |
| **Liquidité** | Très faible — les fonds sont bloqués jusqu'à l'échéance ou le rachat |
| **Fournisseurs typiques** | Investissement programmé, ou prix saisis manuellement dans l'[éditeur de données](../../../user/assets/detail/data-editor.md) |

---

## 🏷️ Quel code choisir {: #which-code-to-choose }

| | Code | Choisissez-le lorsque le prêt… |
|:---:|:---|:---|
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | `CROWDFUND_REAL_ESTATE` | finance un projet immobilier |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | `CROWDFUND` | est destiné à des consommateurs ou à des entreprises — ou lorsque son objet n'est pas précisé |

La règle porte sur ce que le prêt finance, et non sur la plateforme. En cas de doute, `CROWDFUND` — le membre résiduel de la famille — est le choix sûr ; le prix à payer est que, dans la
[vue contenu](index.md#two-views-of-one-instrument), le prêt ne compte plus comme de l'immobilier.

---

## 📊 Comment cela fonctionne

### 🏗️ Crowdfunding immobilier — `CROWDFUND_REAL_ESTATE`

1. Une plateforme référence un projet immobilier nécessitant un financement
2. Plusieurs investisseurs contribuent de petits montants (500 €–10 000 € typiquement)
3. Le projet verse des intérêts sur le capital investi
4. À l'échéance, le principal est remboursé (si le projet aboutit)

### 💸 Prêt P2P — `CROWDFUND`

1. Les emprunteurs — consommateurs ou entreprises — demandent des prêts via une plateforme
2. Les investisseurs financent des portions de prêts
3. Les emprunteurs remboursent le principal + les intérêts sur la durée du prêt
4. La plateforme distribue les versements aux investisseurs

---

## ⚠️ Facteurs de risque

| Risque | Description |
|------|-------------|
| **Risque de défaut** | L'emprunteur/le projet peut ne pas rembourser |
| **Risque de liquidité** | Impossible de vendre avant l'échéance (contrairement aux actions) |
| **Risque de plateforme** | La plateforme elle-même peut faire faillite |
| **Risque de concentration** | Chaque investissement porte sur un seul projet/emprunteur |

---

## 🏠 Trois façons de détenir de l'immobilier {: #three-ways-to-hold-property }

« Immobilier » désigne trois instruments différents dans LibreFolio, et ce qui les distingue est la différence entre **détenir** et **prêter** :

| | Code | Ce que vous détenez | Nature de la créance |
|:---:|:---|:---|:---|
| ![](../../../static/icons/asset-types/real-estate.png){: width="32" } | `REAL_ESTATE` | Une part d'une SIIC ou d'un autre véhicule immobilier coté | Actions : vous détenez une partie des revenus et de la valeur du bien |
| ![](../../../static/icons/asset-types/etf-real-estate.png){: width="32" } | `ETF_REAL_ESTATE` | Une part d'un ETF détenant de tels véhicules | Actions, via un panier |
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | `CROWDFUND_REAL_ESTATE` | Un prêt à un projet immobilier, via une plateforme | Dette : des intérêts et le principal vous sont dus, remboursés par le projet |

Les trois contiennent de l'immobilier, de sorte que la [vue contenu](index.md#two-views-of-one-instrument) les place dans la même classe, et leur badge est bleu sarcelle. Les créances, toutefois, se comportent très différemment lorsque les marchés chutent — et c'est là que les scénarios de stress divergent.

---

## 🌪️ Dans les scénarios de stress {: #in-stress-scenarios }

Un scénario de stress qui affecte le portefeuille par classe d'actifs attribue à chaque code sa propre catégorie d'exposition. Dans les valeurs par défaut des deux scénarios de classe d'actifs intégrés :

| Code | Krach sur les actions | Aversion globale au risque |
|:---|---:|---:|
| `REAL_ESTATE` | −20 % | −15 % |
| `ETF_REAL_ESTATE` | −20 % | −15 % |
| `CROWDFUND_REAL_ESTATE` | −10 % | −10 % |
| `CROWDFUND` | −10 % | −10 % |

`CROWDFUND_REAL_ESTATE` est choqué comme le **prêt** qu'il est, et non comme l'immobilier sous-jacent. L'immobilier coté est réévalué chaque jour de bourse, de sorte qu'une vague de ventes l'atteint immédiatement. Un prêt de crowdfunding est illiquide et non valorisé au prix du marché — rien ne le réévalue le lendemain matin — et son risque est un **défaut qui survient tardivement** ; dans un choc instantané, il évolue donc comme le reste de `CROWDFUND`.

!!! warning "Limite connue : une crise immobilière prolongée"

    Un choc hypothétique est un énoncé sur une seule période : il ne comporte aucune dimension temporelle. Le risque de crédit des prêts adossés à l'immobilier est précisément du type qui s'accumule avec le temps, à mesure qu'une crise immobilière se prolonge — ainsi le −10 % **sous-estime** ce risque dans une crise prolongée. Chaque choc par catégorie d'exposition est modifiable : si c'est le scénario que vous souhaitez tester, augmentez vous-même la valeur de la catégorie d'exposition `CROWDFUND_REAL_ESTATE`.

La manière dont les catégories d'exposition sont appliquées, et ce qu'il advient de celles que vous ne configurez pas, est expliquée dans
[Choc hypothétique](../../technical-analysis/risk-metrics/hypothetical-shock.md).

---

## 🔧 Modélisation dans LibreFolio

Le fournisseur **Investissement programmé** est conçu pour ces instruments. À partir de l'échéancier que vous configurez, il génère :

- **[Événements d'intérêts](../asset-events/interest.md)** — versements de coupons périodiques, lorsque l'échéancier est paramétré pour les générer
- **[Événements de règlement à l'échéance](../asset-events/maturity-settlement.md)** — le remboursement final du capital à la fin du terme

Les **[Événements d'ajustement de prix](../asset-events/price-adjustment.md)** que vous enregistrez vous-même — une dépréciation lorsqu'un projet sous-performe — sont appliqués à la valeur calculée.

---

## 🔗 En lien

- 📊 **[Types d'actifs](index.md)** — La taxonomie à deux niveaux et l'agrégation des sous-types
- 📈 **[Événements d'intérêts](../asset-events/interest.md)** — Comment fonctionne l'accumulation des intérêts
- 🏁 **[Règlement à l'échéance](../asset-events/maturity-settlement.md)** — Remboursement du capital en fin de vie
- 📅 **[Conventions de décompte des jours](../../fundamentals/day-count.md)** — Comment les périodes d'intérêts sont calculées
- ⚡ **[Choc hypothétique](../../technical-analysis/risk-metrics/hypothetical-shock.md)** — Comment les scénarios de stress affectent les catégories d'exposition par classe d'actifs
