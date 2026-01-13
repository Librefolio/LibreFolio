# Interest Types

LibreFolio supports both **Simple** and **Compound** interest calculations.

## Simple Interest

Simple interest is calculated only on the principal amount.

**Formula:**

$$ I = P \times r \times t $$

Where:
-   $I$ = Interest
-   $P$ = Principal
-   $r$ = Annual Interest Rate
-   $t$ = Time (in years, calculated using the Day Count Convention)

## Compound Interest

Compound interest is calculated on the principal amount plus the accumulated interest from previous periods.

**Formula:**

$$ A = P \times (1 + \frac{r}{n})^{n \times t} $$

Where:
-   $A$ = Final Amount (Principal + Interest)
-   $P$ = Principal
-   $r$ = Annual Interest Rate
-   $n$ = Number of compounding periods per year
-   $t$ = Time (in years)
