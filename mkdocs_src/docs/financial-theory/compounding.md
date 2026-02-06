# Compounding Frequencies

The **compounding frequency** determines how often accrued interest is added to the principal, which then earns interest itself.

LibreFolio supports the following frequencies for compound interest calculations:

- **`ANNUAL`**: Compounded once per year.
- **`SEMIANNUAL`**: Compounded twice per year.
- **`QUARTERLY`**: Compounded four times per year.
- **`MONTHLY`**: Compounded twelve times per year.
- **`DAILY`**: Compounded 365 times per year.
- **`CONTINUOUS`**: Compounded infinitely. The formula for continuous compounding is:

$$ A = P \times e^{rt} $$
