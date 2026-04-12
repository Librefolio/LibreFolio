# 💰 Dividende

Un **dividende** est une distribution de liquidités versée par une société (ou un fonds) à ses actionnaires, représentant une part des bénéfices de l'entreprise.

---

## 📖 Définition

Les dividendes sont des paiements périodiques effectués à partir des bénéfices d'une société vers ses actionnaires. Ils sont généralement versés trimestriellement (courant aux États-Unis) ou semestriellement/annuellement (courant en Europe). Les ETF distribuent également les dividendes collectés auprès de leurs positions sous-jacentes.

**Dates clés** du cycle de vie d'un dividende :

| Date | Signification |
|------|---------|
| **Date de déclaration** | Le conseil d'administration annonce le montant et les dates du dividende |
| **Date de détachement** | Premier jour de bourse où les acheteurs ne reçoivent PAS le dividende. Le cours de l'action baisse généralement du montant du dividende à l'ouverture du marché. |
| **Date d'enregistrement** | La société vérifie qui détient les actions (généralement 1 à 2 jours après la date de détachement) |
| **Date de paiement** | Les liquidités sont déposées sur les comptes des actionnaires |

---

## 📉 Impact sur le prix du marché

À la **date de détachement**, le cours de l'action baisse théoriquement du **montant exact du dividende**. Cela s'explique par le fait que les nouveaux acheteurs à cette date ne recevront pas le paiement à venir.

!!! example "Exemple"

    **Apple (AAPL)** s'échange à 180,00 $. Un dividende trimestriel de 0,25 $ est détaché.

    - **Avant la clôture de la date de détachement** : 180,00 $
    - **Ouverture à la date de détachement** (théorique) : 179,75 $
    - **Différence** : −0,25 $ (= montant du dividende)

    En pratique, les forces du marché peuvent faire varier le prix d'ouverture réel, mais la bourse **ajuste le prix de référence** à la baisse d'exactement 0,25 $.

---

## 📊 Effet sur le rendement total

Bien que le prix baisse du montant du dividende, le **rendement total** (variation du prix + dividendes reçus) reste neutre au moment du paiement. Avec le temps, les dividendes réinvestis produisent un effet composé significatif.

$$
\text{Rendement Total} = \frac{P_{\text{end}} - P_{\text{start}} + \sum D_i}{P_{\text{start}}}
$$

Où $D_i$ représente chaque paiement de dividende reçu pendant la période de détention.

---

## 🔢 Rendement du dividende

Le **rendement du dividende** exprime le dividende annuel en pourcentage du cours actuel de l'action :

$$
\text{Rendement du Dividende} = \frac{\text{Dividendes annuels par action}}{\text{Cours actuel par action}} \times 100\%
$$

!!! tip "Fourchettes typiques"

    - Actions de croissance : 0–1 %
    - Sociétés matures : 2–4 %
    - Haut rendement / REITs : 4–8%+

---

## 🧮 Comment LibreFolio gère les dividendes

Dans LibreFolio, un événement `DIVIDEND` est enregistré avec :

- **Date** : La date de détachement
- **Amount** : Le paiement en espèces par action
- **Currency** : La devise du paiement (ex: USD, EUR)

Pour les **actifs dont le prix est indexé sur le marché** (Yahoo Finance, justETF), les événements de dividendes sont informatifs — ils expliquent l'écart de prix à la date de détachement mais ne modifient pas le prix récupéré. Pour les actifs de type **Scheduled Investment**, ils font partie intégrante du modèle de prix.

---

## 🔗 Liens connexes

- 📅 **[Aperçu des événements d'actifs](index.md)** — Tous les types d'événements
- 💸 **[Types de transactions](../transaction-types/index.md)** — Comment les dividendes apparaissent dans les transactions du portefeuille
- 📈 **[Rendements et taux de croissance](../../fundamentals/returns.md)** — Rendement total incluant les dividendes
