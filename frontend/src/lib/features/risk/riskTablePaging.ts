/**
 * The page sizes of every table of the risk and correlation surfaces (developer, 05/10 and 31/10/2026).
 *
 * «Nella tabella metti la paginazione se ci sono più di 5 righe», widened to every table of those surfaces, with «all» among
 * the sizes: a reader who does not want pages sets it to infinite, and the table remembers it (`DataTable`'s own storage, per
 * `storageKey`). `0` is `DataTable`'s «all». The bar appears only when there are more rows than the first size.
 */
export const RISK_PAGE_SIZE = 5;
export const RISK_PAGE_SIZES: number[] = [5, 10, 25, 0];
