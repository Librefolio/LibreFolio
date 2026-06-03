# 🏦 Interactive Brokers (IBKR)

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## How to Export

1. Log in to [Interactive Brokers Client Portal](https://www.interactivebrokers.com) or Trader Workstation (TWS).
2. Go to **Reports → Activity → Flex Queries** or **Statements → Activity Statement**.
3. Select date range and export as **CSV**.

## Notes

- Supports standard IBKR activity reports (trades, dividends, fees, deposits, withdrawals).
- Multi-currency accounts are supported.
- Corporate actions (splits, mergers) may require manual adjustment.

## 🔗 Developer Reference

→ [IBKR Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
