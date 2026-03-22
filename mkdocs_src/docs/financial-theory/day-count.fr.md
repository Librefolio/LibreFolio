# 📅 Conventions de décompte des jours

Une **convention de décompte des jours** détermine la manière dont les intérêts s'accumulent dans le temps pour divers instruments financiers, tels que les obligations, les prêts et les hypothèques. Elle définit deux éléments :

1. Comment calculer le nombre de jours entre deux dates.
2. Comment calculer le nombre de jours dans une année.

## 🔧 Utilisation dans LibreFolio

Les conventions de décompte des jours sont activement utilisées par le fournisseur de source d'actifs `ScheduledInvestment` pour les calculs de **rendement synthétique**. La fonction `calculate_day_count_fraction()` dans `backend/app/utils/financial_math.py` implémente les quatre conventions et renvoie une fraction de temps `Decimal` utilisée dans les calculs d'accumulation d'intérêts.

La convention par défaut est **ACT/365**.

## 📅 ACT/365 (Réel/365)

- **Jours** : Le nombre réel de jours entre deux dates.
- **Année** : Suppose 365 jours.
- **Formule** : $t = \frac{\text{jours réels}}{365}$
- **Utilisation** : Courante sur les marchés monétaires britanniques et pour certaines obligations d'État. **Par défaut dans LibreFolio.**

## 📅 ACT/360 (Réel/360)

- **Jours** : Le nombre réel de jours entre deux dates.
- **Année** : Suppose 360 jours.
- **Formule** : $t = \frac{\text{jours réels}}{360}$
- **Utilisation** : Très courante sur les marchés monétaires américains et pour les prêts commerciaux.

## 📐 30/360 (Base obligataire)

- **Jours** : Calculés en supposant que chaque mois compte 30 jours.
- **Année** : Suppose 360 jours.
- **Formule** : $t = \frac{360(Y_2 - Y_1) + 30(M_2 - M_1) + (D_2 - D_1)}{360}$
- **Utilisation** : Normale pour les obligations corporatives américaines et de nombreuses obligations municipales.

## 📅 ACT/ACT (Réel/Réel)

- **Jours** : Le nombre réel de jours entre deux dates.
- **Année** : Le nombre réel de jours dans l'année (365 ou 366 pour les années bissextiles).
- **Formule** : $t = \frac{\text{jours réels}}{365 \text{ ou } 366}$
- **Utilisation** : Normale pour les obligations du Trésor américain. Gère **précisément** les années bissextiles en calculant la fraction séparément pour chaque année.

!!! info "Pourquoi est-ce important ?"
    La différence entre les conventions peut être significative pour des **montants élevés** ou des durées longues. Par exemple, pour 30 jours sur un prêt de 1 M€ à 5 % : ACT/365 donne 4 109,59 € d'intérêts, tandis qu'ACT/360 donne 4 166,67 € — une différence de 57 € sur la même période de 30 jours.

:material-link: [Day Count Convention sur Wikipédia](https://en.wikipedia.org/wiki/Day_count_convention){ target="_blank" }
