# Day Count Conventions

A **Day Count Convention** determines how interest accrues over time for a variety of financial instruments, such as bonds, loans, and mortgages. It defines two things:

1. How to calculate the number of days between two dates.
2. How to calculate the number of days in a year.

LibreFolio supports the following conventions:

## ACT/365 (Actual/365)

- **Days**: The actual number of days between two dates.
- **Year**: Assumed to be 365 days.
- **Usage**: Common in UK money markets and for some government bonds.

## ACT/360 (Actual/360)

- **Days**: The actual number of days between two dates.
- **Year**: Assumed to be 360 days.
- **Usage**: Very common in US money markets and for commercial loans.

## 30/360 (Bond Basis)

- **Days**: Calculated assuming every month has 30 days.
- **Year**: Assumed to be 360 days.
- **Usage**: Standard for US corporate bonds and many municipal bonds.

## ACT/ACT (Actual/Actual)

- **Days**: The actual number of days between two dates.
- **Year**: The actual number of days in the year (365 or 366 for leap years).
- **Usage**: Standard for US Treasury bonds.
