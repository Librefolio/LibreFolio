# 🏁 Règlement à Échéance

Un événement de **règlement à échéance** marque la fin d'un instrument financier à terme fixe — l'émetteur restitue le principal (valeur nominale) à l'investisseur, et aucun calcul de prix ultérieur n'est effectué.

---

## 📖 Définition

L'échéance est la date à laquelle un instrument de dette (obligation, titre de créance, certificat de dépôt, prêt à terme) atteint sa fin contractuelle. À cette date :

1. Le **principal** (valeur nominale / valeur au pair) est restitué à l'investisseur
2. Tout **paiement d'intérêts final** est effectué (le cas échéant)
3. L'instrument **cesse d'exister** — plus aucune valorisation ni transaction n'est effectuée

### Instruments avec dates d'échéance

| Instrument | Échéance typique | Règlement |
|------------|-----------------|------------|
| **Bons du Trésor** | 4 semaines – 1 an | Valeur nominale à l'échéance |
| **Obligations d'État** | 2 – 30 ans | Valeur nominale + coupon final |
| **Obligations d'entreprise** | 1 – 30 ans | Valeur nominale + coupon final |
| **Certificats de dépôt** | 1 mois – 5 ans | Principal + intérêts courus |
| **Dépôts à terme** | 1 mois – 5 ans | Principal + intérêts |
| **Prêts P2P** | 1 – 5 ans | Principal restant |

---

## 📉 Impact sur le prix du marché

À mesure qu'une obligation approche de son échéance, son prix de marché converge vers la **valeur nominale** (au pair), qu'elle ait été négociée avec une prime ou une décote :

$$
\lim_{d \to \text{échéance}} P(d) = \text{Valeur Nominale}
$$

Ce phénomène est appelé **pull to par** :

- **Obligations avec prime** (prix > pair) : Le prix diminue progressivement vers le pair
- **Obligations avec décote** (prix < pair) : Le prix augmente progressivement vers le pair

!!! example "Exemple : Échéance d'une obligation d'État"

    Une obligation d'État à 10 ans avec une valeur nominale de 1 000 € et un coupon annuel de 3 % :

    - **À l'émission** (2015) : Prix = 1 000 € (au pair)
    - **À mi-parcours** (2020) : Prix = 1 050 € (prime, car les taux du marché ont chuté)
    - **Près de l'échéance** (2024) : Prix = 1 005 € (convergence vers le pair)
    - **À l'échéance** (2025-01-15) : L'investisseur reçoit :
    - 1 000 € (restitution de la valeur nominale)
    - 30 € (coupon annuel final)
    - Total : 1 030 €

!!! example "Exemple : Obligation à coupon zéro"

    Une obligation à coupon zéro avec une valeur nominale de 1 000 $ achetée à 850 $ :

    - **À l'achat** : Prix = 850 $ (décote)
    - **À l'échéance** : L'investisseur reçoit 1 000 $
    - **Rendement implicite** : 150 $ (1 000 $ − 850 $)
    - Aucun paiement d'intérêts intermédiaire — tout le rendement provient du règlement à l'échéance

---

## 📊 Après l'échéance

Une fois qu'un événement de règlement à échéance est enregistré dans LibreFolio :

- La **série de prix** de l'actif s'arrête à la date d'échéance
- Le montant du règlement représente le **dernier point de donnée**
- L'actif peut rester dans le système pour analyse historique mais ne recevra plus de nouvelles données de prix

---

## 🧮 Comment LibreFolio gère le règlement à échéance

Dans LibreFolio, un événement `MATURITY_SETTLEMENT` est enregistré avec :

- **Date** : La date d'échéance
- **Montant** : La valeur nominale / le montant du principal restitué
- **Devise** : La devise du règlement
- **Notes** : Description optionnelle (ex: "Obligation du Trésor 10Y arrivée à échéance")

Pour le fournisseur **Scheduled Investment**, la date d'échéance est configurée dans les paramètres du fournisseur. La formule de calcul du prix reconnaît qu'aucun cumul supplémentaire n'a lieu après l'échéance :

$$
\text{price}(d) = \begin{cases}
\text{initial\\_value} + \text{accrued}(d) - \Sigma\text{INT} + \Sigma\text{ADJ} & \text{if } d < \text{maturity} \\
\text{settlement\\_amount} & \text{if } d \geq \text{maturity}
\end{cases}
$$

---

## 🔗 Liens connexes

- 📅 **[Aperçu des événements d'actifs](index.md)** — Tous les types d'événements
- 📈 **[Intérêts](interest.md)** — Paiements de coupons périodiques avant l'échéance
- 📆 **[Conventions de comptage des jours](../../fundamentals/day-count.md)** — Comment le cumul est calculé entre les dates de coupon
- 📊 **[Ajustement de prix](price-adjustment.md)** — Changements de valeur non monétaires avant l'échéance
