# 📅 Day Count Conventions

A **Day Count Convention** determines how interest accrues over time for a variety of financial instruments, such as bonds, loans, and mortgages. It defines two things:

1. How to calculate the number of days between two dates.
2. How to calculate the number of days in a year.

## 🔧 Usage in LibreFolio

Day count conventions are actively used by the **Scheduled Investment** asset source
provider (`backend/app/services/asset_source_providers/scheduled_investment.py`) for
synthetic yield calculations. The function `calculate_day_count_fraction()` in
`backend/app/utils/financial_math.py` implements all four conventions and returns a
`Decimal` time fraction used in interest accrual computations.

The default convention is **ACT/365**.

## 📅 ACT/365 (Actual/365)

- **Days**: The actual number of days between two dates.
- **Year**: Assumed to be 365 days.
- **Formula**: $t = \frac{\text{actual days}}{365}$
- **Usage**: Common in UK money markets and for some government bonds. **Default in LibreFolio.**

## 📅 ACT/360 (Actual/360)

- **Days**: The actual number of days between two dates.
- **Year**: Assumed to be 360 days.
- **Formula**: $t = \frac{\text{actual days}}{360}$
- **Usage**: Very common in US money markets and for commercial loans.

## 📐 30/360 (Bond Basis)

- **Days**: Calculated assuming every month has 30 days.
- **Year**: Assumed to be 360 days.
- **Formula**: $t = \frac{360(Y_2 - Y_1) + 30(M_2 - M_1) + (D_2 - D_1)}{360}$
- **Usage**: Standard for US corporate bonds and many municipal bonds.

## 📅 ACT/ACT (Actual/Actual)

- **Days**: The actual number of days between two dates.
- **Year**: The actual number of days in the year (365 or 366 for leap years).
- **Formula**: $t = \frac{\text{actual days}}{365 \text{ or } 366}$
- **Usage**: Standard for US Treasury bonds. Handles leap years correctly by calculating the fraction for each year separately.

!!! info "Why does this matter?"

    The difference between conventions can be significant for large principals or long
    durations. For example, 30 days on a €1M loan at 5%: ACT/365 gives €4,109.59 in
    interest, while ACT/360 gives €4,166.67 — a €57 difference from the same 30-day
    period.

:material-link: [Day Count Convention on Wikipedia](https://en.wikipedia.org/wiki/Day_count_convention){ target="_blank" }
