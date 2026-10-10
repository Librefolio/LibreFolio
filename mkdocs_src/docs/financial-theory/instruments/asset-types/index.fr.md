# 📊 Types d'actifs

Les instruments diffèrent dans le monde réel — leur mode de valorisation, le versement ou non de
revenus, leur fiscalité — et les pages détaillées ci-dessous couvrent ces différences. Dans
LibreFolio, chaque actif porte exactement un **type d'actif**, et ce type est une **classification**
lue à trois endroits : il choisit l'icône et le libellé que vous voyez, il détermine où l'actif est
comptabilisé dans les graphiques d'[allocation](../../portfolio-theory/asset-allocation.md), et il
nomme le compartiment dans lequel l'actif est rangé lorsqu'un
[scénario de stress](../../technical-analysis/risk-metrics/hypothetical-shock.md) applique un choc au
portefeuille par classe d'actifs. `INDEX` est, de plus, le seul type qui n'accepte aucune
transaction.

La taxonomie comporte **deux niveaux**. La plupart des types sont autonomes ; deux d'entre eux —
**ETF** et **Crowdfunding** — sont des **familles**, dont les membres précisent également ce que
l'instrument *contient*.

---

## 📋 Types de base {: #base-types }

| | Type | Code | Description | |
|:---:|:---|:---|---|:---:|
| ![](../../../static/icons/asset-types/stock.png){: width="32" } | **Action** | `STOCK` | Actions d'une seule entreprise. Les prix sont généralement récupérés depuis les marchés publics. | [📖](stocks.md) |
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Exchange Traded Fund à contenu mixte ou non précisé (équilibré, multi-actifs) — le membre générique de la [famille ETF](#etf-family). | [📖](etfs.md) |
| ![](../../../static/icons/asset-types/bond.png){: width="32" } | **Obligation** | `BOND` | Titres à revenu fixe représentant un prêt accordé à un emprunteur (État ou entreprise). | [📖](bonds.md) |
| ![](../../../static/icons/asset-types/crypto.png){: width="32" } | **Crypto** | `CRYPTO` | Devises et jetons numériques (Bitcoin, Ethereum, etc.). | [📖](crypto.md) |
| ![](../../../static/icons/asset-types/fund.png){: width="32" } | **Fonds** | `FUND` | Fonds communs de placement et autres fonds d'investissement gérés professionnellement. | [📖](mutual-fund.md) |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **Crowdfunding** | `CROWDFUND` | Prêts de financement participatif entre particuliers et destinés aux entreprises, souvent valorisés via des paiements d'intérêts planifiés — le membre générique de la [famille Crowdfunding](#crowdfunding-family). | [📖](real-estate.md) |
| ![](../../../static/icons/asset-types/hold.png){: width="32" } | **Actif détenu** | `HOLD` | Actifs sans valorisation automatique par le marché : art, objets de collection, parts d'entreprises non cotées. | — |
| ![](../../../static/icons/asset-types/commodity.png){: width="32" } | **Matière première** | `COMMODITY` | Biens physiques et leurs expositions directes : or, pétrole, produits agricoles. | [📖](commodities.md) |
| ![](../../../static/icons/asset-types/real-estate.png){: width="32" } | **Immobilier** | `REAL_ESTATE` | Exposition immobilière : REIT et autres véhicules immobiliers cotés. | [📖](real-estate.md#three-ways-to-hold-property) |
| ![](../../../static/icons/asset-types/index.png){: width="32" } | **Indice** | `INDEX` | Indices de marché (S&amp;P 500, MSCI World) utilisés comme indices de référence — non négociables directement, donc aucune transaction n'est autorisée. | [📖](index-benchmark.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Autre** | `OTHER` | Tout actif que les types ci-dessus ne décrivent pas. | [📖](other.md) |

Un type correspond à **un seul libellé par actif** : un ETF équilibré est compté en entier sous
`ETF`, jamais scindé entre ses composantes actions et obligations. Analyser un instrument *en
transparence* relève de ses répartitions sectorielle et géographique, non de son type.

---

## 🧬 Familles et sous-types {: #families-and-subtypes }

Un sous-type répond à une seule question : **quel type de base cet instrument contient-il ?** Le
second niveau n'est donc pas une taxonomie parallèle — il *est* l'ensemble des types de base, vus à
travers une enveloppe. Le membre générique de chaque famille (`ETF`, `CROWDFUND`) reste un choix
valable en soi : c'est le résidu pour les contenus mixtes ou non précisés, et le menu des types le
liste en premier dans sa famille, avec une indication en ce sens.

L'icône d'un sous-type est celle de sa famille avec un petit disque dans le coin — une **pastille** —
indiquant son contenu : le contenant dit ce que l'instrument *est*, la pastille ce qu'il *contient*.
La pastille est l'icône du type de base contenu par le sous-type ; l'ETF monétaire, qui ne contient
aucun type de base, emprunte l'icône de liquidité. Partout où LibreFolio affiche l'icône de type, un
sous-type montre son composite — un actif doté d'une icône personnalisée conserve la sienne.

### 📦 Famille ETF {: #etf-family }

| | Type | Code | Contient | Se rattache à |
|:---:|:---|:---|:---|:---|
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Contenu mixte ou non précisé — le membre générique | `ETF` (lui-même) |
| ![](../../../static/icons/asset-types/etf-stock.png){: width="32" } | **ETF actions** | `ETF_STOCK` | Actions | `STOCK` |
| ![](../../../static/icons/asset-types/etf-bond.png){: width="32" } | **ETF obligations** | `ETF_BOND` | Obligations | `BOND` |
| ![](../../../static/icons/asset-types/etf-commodity.png){: width="32" } | **ETF matières premières** | `ETF_COMMODITY` | Matières premières | `COMMODITY` |
| ![](../../../static/icons/asset-types/etf-real-estate.png){: width="32" } | **ETF immobilier** | `ETF_REAL_ESTATE` | Immobilier | `REAL_ESTATE` |
| ![](../../../static/icons/asset-types/etf-crypto.png){: width="32" } | **ETF crypto** | `ETF_CRYPTO` | Actifs crypto | `CRYPTO` |
| ![](../../../static/icons/asset-types/etf-liquidity.png){: width="32" } | **ETF monétaire** | `ETF_MONETARY` | Instruments du marché monétaire | `ETF_MONETARY` (lui-même — voir [ci-dessous](#two-views-of-one-instrument)) |

L'instrument lui-même est décrit sur la page [ETF](etfs.md).

### 🤝 Famille Crowdfunding {: #crowdfunding-family }

| | Type | Code | Contient | Se rattache à |
|:---:|:---|:---|:---|:---|
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **Crowdfunding** | `CROWDFUND` | Prêts P2P et aux entreprises — le membre générique | `CROWDFUND` (lui-même) |
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | **Crowdfunding immobilier** | `CROWDFUND_REAL_ESTATE` | Prêts adossés à des projets immobiliers | `REAL_ESTATE` |

Les deux sont décrits sur la page [P2P / Crowdfunding](real-estate.md).

---

## ⚖️ Deux lectures d'un même instrument {: #two-views-of-one-instrument }

Les deux niveaux répondent à deux questions différentes, et LibreFolio les tient distincts.

- **La vue du contenant** — *de quel type d'instrument s'agit-il ?* — est la famille. Le menu des
  types regroupe par famille, l'icône conserve la forme de la famille et le libellé indique *ETF
  actions* : c'est l'instrument que vous détenez réellement.
- **La vue du contenu** — *à quoi suis-je exposé ?* — est le rattachement : un sous-type appartient au
  type de base qu'il contient. Un ETF actions et une action représentent tous deux une exposition aux
  actions, et à la question *suis-je aussi diversifié que je le pense ?*, l'enveloppe ne dit rien.

Formellement, soit $c$ l'application qui envoie chaque sous-type vers le type de base qu'il contient,
et tout autre type — y compris les membres génériques et `ETF_MONETARY` — vers lui-même. Le poids
d'une classe de contenu $k$ est alors

$$
W_k = \sum_{i \,:\, c(\tau_i) = k} w_i
$$

où $\tau_i$ est le type de la position $i$ et $w_i$ son poids dans le portefeuille. La même somme
prise sur la fonction de famille au lieu de $c$ — chaque sous-type d'ETF vers `ETF`,
`CROWDFUND_REAL_ESTATE` vers `CROWDFUND`, tout autre type vers lui-même — donne le poids de chaque
famille, le pendant de la vue du contenant.
Le badge de type suit le contenu : un badge *ETF actions* est bleu, comme un badge *Action*. La
manière dont le tableau de bord présente l'allocation par type est décrite dans le
[panneau Allocation](../../../user/dashboard/charts.md#allocation-panel).

Deux exceptions méritent chacune une phrase :

- **`ETF_MONETARY` se rattache à lui-même.** Un fonds monétaire n'a aucun type de base auquel se
  rattacher : la liquidité est un solde de compte, non un actif que l'on achète, donc ce n'est pas un
  type d'actif. `ETF` noierait le fonds parmi les fonds mixtes, et *Liquidité* n'est pas du tout un
  type d'actif — c'est le compartiment d'allocation dans lequel LibreFolio compte votre solde de
  trésorerie, séparément. Dans la vue du contenu, l'ETF monétaire constitue donc une classe à part,
  et son badge a une couleur qui lui est propre.
- **`CROWDFUND_REAL_ESTATE` a deux réponses.** Dans la vue du contenu, il contient de l'immobilier et
  appartient à la classe Immobilier ; dans les scénarios de stress, il subit le choc en tant que prêt
  qu'il est.

---

## 🌪️ Les types dans les scénarios de stress {: #types-in-stress-scenarios }

Un scénario de stress qui applique un choc au portefeuille par classe d'actifs traite chaque code
comme un **compartiment à part** — là, un sous-type n'est jamais replié dans sa classe de contenu.
Dans les valeurs par défaut des deux scénarios de classe d'actifs intégrés, *Equity crash* et
*Global risk-off*, chaque sous-type d'ETF subit exactement le choc du type de base qu'il détient,
tandis que l'`ETF` générique conserve un choc composite qui lui est propre, car son contenu n'est pas
précisé ; `ETF_MONETARY` ne subit aucun choc.

La seule exception délibérée est `CROWDFUND_REAL_ESTATE`, qui évolue comme `CROWDFUND` plutôt que
comme `REAL_ESTATE` : un prêt de financement participatif est illiquide et non valorisé au prix du
marché, et son risque est un défaut qui survient tardivement. Le raisonnement, et sa limite connue,
figurent sur la page [P2P / Crowdfunding](real-estate.md#in-stress-scenarios).

Chaque choc de compartiment de ces scénarios est modifiable, et un compartiment laissé non configuré
subit un choc nul — voir [Choc hypothétique](../../technical-analysis/risk-metrics/hypothetical-shock.md#what-you-did-not-configure).

---

## 🔗 Voir aussi

- 💸 **[Types de transactions](../transaction-types/index.md)** — Opérations qui affectent votre portefeuille
- 📅 **[Événements d'actifs](../asset-events/index.md)** — Opérations sur titres affectant les cours des actifs
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales par classe d'actifs
- 🧭 **[Allocation d'actifs](../../portfolio-theory/asset-allocation.md)** — Répartition du capital entre les classes d'actifs
- ⚡ **[Choc hypothétique](../../technical-analysis/risk-metrics/hypothetical-shock.md)** — Comment les compartiments par classe d'actifs subissent les chocs
