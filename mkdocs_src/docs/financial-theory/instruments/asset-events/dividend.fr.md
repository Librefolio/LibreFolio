# 💰 Dividende

Un **dividende** est une distribution de liquidités versée par une société (ou un fonds) à ses actionnaires, représentant une part des bénéfices de l'entreprise.

---

## 📖 Définition

Les dividendes sont des paiements périodiques effectués à partir des bénéfices d'une société à ses actionnaires. Ils sont généralement versés trimestriellement (courant aux États-Unis) ou semestriellement/annuellement (courant en Europe). Les ETF distribuent également des dividendes collectés auprès de leurs positions sous-jacentes.

**Dates clés** du cycle de vie d'un dividende :

| Date | Signification |
|------|---------|
| **Date de déclaration**&nbsp; | Le conseil d'administration annonce le montant et les dates du dividende |
| **Date de détachement**&nbsp; | Premier jour de bourse où les acheteurs ne reçoivent PAS le dividende. Le cours de l'action chute généralement du montant du dividende à l'ouverture du marché. |
| **Date d'enregistrement**&nbsp; | La société vérifie qui détient les actions (généralement 1 à 2 jours après la date de détachement) |
| **Date de paiement**&nbsp; | Les liquidités sont déposées sur les comptes des actionnaires |

---

## 📉 Impact sur le prix du marché

À la **date de détachement**, le cours de l'action chute théoriquement du **montant exact du dividende**. Cela s'explique par le fait que les nouveaux acheteurs à cette date ne recevront pas le paiement à venir.

!!! example "Example"

    **Apple (AAPL)** s'échange à 180,00 $. Un dividende trimestriel de 0,25 $ se détache.

    - **Avant la clôture de la date de détachement** : 180,00 $
    - **Ouverture à la date de détachement** (théorique) : 179,75 $
    - **Différence** : −0,25 $ (= montant du dividende)

    En pratique, les forces du marché peuvent faire varier le prix d'ouverture réel, mais la bourse **ajuste le prix de référence** à la baisse de exactement 0,25 $.

---

## 📊 Effet sur le rendement total

Bien que le prix chute du montant du dividende, le **rendement total** (variation du prix + dividendes reçus) reste neutre au moment du paiement. Avec le temps, les dividendes réinvestis produisent un effet composé significatif.

$$
\text{Total Return} = \frac{P_{\text{end}} - P_{\text{start}} + \sum D_i}{P_{\text{start}}}
$$

Où $D_i$ représente chaque paiement de dividende reçu pendant la période de détention.

---

## 🔢 Rendement du dividende

Le **rendement du dividende** exprime le dividende annuel en pourcentage du cours actuel de l'action :

$$
\text{Dividend Yield} = \frac{\text{Annual Dividends per Share}}{\text{Current Price per Share}} \times 100\%
$$

!!! tip "Typical ranges"

    - Actions de croissance : 0–1 %
    - Sociétés matures : 2–4 %
    - Rendement élevé / REITs : 4–8 % +

---

## 🧮 Comment LibreFolio gère les dividendes

Dans LibreFolio, un événement `DIVIDEND` (et la transaction de portefeuille correspondante) est enregistré avec :

- **Date** : La date de détachement
- **Amount** : Le paiement en espèces par action
- **Currency** : La devise du paiement (ex: USD, EUR)

### La différence comptable : Dividende vs Intérêt
Il est crucial de distinguer une transaction de **Dividende** d'une transaction d'**Intérêt** au niveau de la base de données :

1. **Dividende (basé sur des actifs en actions)** : Dans le suivi de portefeuille en partie double, un dividende représente un flux de trésorerie entrant (`cash.amount > 0`) généré par la détention d'actions d'un actif spécifique. Le nombre d'actions détenues à la date de détachement reste constant — aucune action n'est ajoutée ou supprimée lors de ce versement en espèces. Ainsi, la transaction dans la base de données nécessite `quantity = 0` pour éviter un double comptage ou une inflation de votre solde d'actions. Toute information sur le nombre d'actions ayant généré le versement est traitée comme *informative* et est généralement stockée dans le champ de description.
2. **Intérêt (basé sur la dette/rendement)** : Un paiement d'intérêt représente le rendement d'une dette ou de dépôts de trésorerie (ex: comptes d'épargne ou coupons d'obligations). Contrairement aux dividendes, les intérêts ne nécessitent pas strictement l'existence d'un actif en actions sous-jacent (l'actif est optionnel).

Pour les **actifs dont le prix est indexé sur le marché** (Yahoo Finance, justETF), les événements de dividende sont informatifs — ils expliquent l'écart de prix à la date de détachement mais ne modifient pas le prix récupéré. Pour les actifs de type **investissement programmé**, ils font partie intégrante du modèle de prix.

---

## 🔗 Related

- 📅 **[Aperçu des événements d'actifs](index.md)** — Tous les types d'événements
- 💸 **[Types de transactions](../transaction-types/index.md)** — Comment les dividendes apparaissent dans les transactions du portefeuille
- 📈 **[Rendements et taux de croissance](../../fundamentals/returns.md)** — Rendement total incluant les dividendes
