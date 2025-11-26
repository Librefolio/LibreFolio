# Tutorial: Track a P2P Loan

> 🚧 **Work in Progress**
>
> This tutorial will be completed once the frontend application is available.

This tutorial demonstrates how to track a scheduled-yield asset, such as a peer-to-peer (P2P) loan from a platform like Recrowd or Mintos.

## Steps

1.  **Create a Broker**: Set up a "broker" to represent the P2P platform (e.g., "Recrowd").
2.  **Create the Asset**: Define the loan as a new asset.
    -   **Valuation Model**: `SCHEDULED_YIELD`
    -   **Interest Schedule**: Provide the JSON schedule detailing the interest rates and periods.
3.  **Deposit Cash**: Add cash to your P2P platform account.
4.  **Record the BUY Transaction**: Record your initial investment in the loan.
5.  **View the Valuation**: Observe how the asset's value automatically increases over time based on the accrued interest calculated from the schedule.
