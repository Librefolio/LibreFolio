# 📅 Conventions de calcul des jours

Une **convention de calcul des jours** détermine la manière dont les intérêts s'accumulent au fil du temps pour divers instruments financiers, tels que les obligations, les prêts et les hypothèques. Elle définit deux éléments :

1. Comment calculer le nombre de jours entre deux dates.
2. Comment calculer le nombre de jours dans une année.

## 🔧 Utilisation dans LibreFolio

Les conventions de calcul des jours sont activement utilisées par le fournisseur de source d'actifs **Scheduled Investment** (`backend/app/services/asset_source_providers/scheduled_investment.py`) pour les calculs de rendement synthétique. La fonction `calculate_day_count_fraction()` dans `backend/app/utils/financial_math.py` implémente les quatre conventions et retourne une fraction de temps `Decimal` utilisée dans les calculs d'accumulation d'intérêts.

La convention par défaut est **ACT/365**.

## 📅 ACT/365 (Actual/365)

- **Jours** : Le nombre réel de jours entre deux dates.
- **Année** : Considérée comme ayant 365 jours.
- **Formule** : $t = \frac{\text{jours réels}}{365}$
- **Utilisation** : Courante sur les marchés monétaires du Royaume-Uni et pour certaines obligations d'État. **Par défaut dans LibreFolio.**

## 📅 ACT/360 (Actual/360)

- **Jours** : Le nombre réel de jours entre deux dates.
- **Année** : Considérée comme ayant 360 jours.
- **Formule** : $t = \frac{\text{jours réels}}{360}$
- **Utilisation** : Très courante sur les marchés monétaires américains et pour les prêts commerciaux.

## 📐 30/360 (Bond Basis)

- **Jours** : Calculés en supposant que chaque mois compte 30 jours.
- **Année** : Considérée comme ayant 360 jours.
- **Formule** : $t = \frac{360(Y_2 - Y_1) + 30(M_2 - M_1) + (D_2 - D_1)}{360}$
- **Utilisation** : Standard pour les obligations d'entreprises américaines et de nombreuses obligations municipales.

## 📅 ACT/ACT (Actual/Actual)

- **Jours** : Le nombre réel de jours entre deux dates.
- **Année** : Le nombre réel de jours dans l'année (365 ou 366 pour les années bissextiles).
- **Formule** : $t = \frac{\text{jours réels}}{365 \text{ ou } 366}$
- **Utilisation** : Standard pour les obligations du Trésor américain. Gère correctement les années bissextiles en calculant la fraction pour chaque année séparément.

!!! info "Pourquoi est-ce important ?"

    La différence entre les conventions peut être significative pour des montants principaux élevés ou des durées longues. Par exemple, pour 30 jours sur un prêt de 1 million € à 5 % : ACT/365 donne 4 109,59 € d'intérêts, tandis qu'ACT/360 donne 4 166,67 € — soit une différence de 57 € pour la même période de 30 jours.

:material-link: [Convention de calcul des jours sur Wikipedia](https://en.wikipedia.org/wiki/Day_count_convention){ target="_blank" }
