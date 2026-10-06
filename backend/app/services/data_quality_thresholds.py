"""Project-wide data-quality thresholds.

One place for the numbers that decide when source data stops being "normal" and becomes a
data-quality problem, so every consumer — the portfolio's data-quality banner, the risk engine,
the asset eligibility check — agrees on them, and changing one of them changes it everywhere
(developer's decision of 24/09/2026).

Calendar days, not trading days: a quote carried over a weekend or a holiday is ordinary, and the
thresholds are chosen so that it never counts as a problem on its own.
"""

from decimal import Decimal

STALE_PRICE_THRESHOLD_DAYS = 7
"""A price older than this, in calendar days, is stale.

Up to this age a carried-forward price is ordinary — weekends, holidays, an instrument quoted on
its own market calendar. Beyond it the price no longer describes the asset, and the result that
uses it is degraded.
"""

TRANSACTION_IMPLIED_GRACE_DAYS = 14
"""Days after the first acquisition during which a missing market price is a normal placement lag
(e.g. a BTP bought at issue) rather than a data-quality problem."""

RISK_MIN_OBSERVATIONS = 20
"""The fewest return observations the statistical risk analytics accept.

Below it correlation, historical VaR/CVaR, risk contribution and beta refuse to compute, so an asset
with fewer quotes than this in a period cannot take part in a risk analysis of that period.
"""

REPLAY_EXCLUDED_WEIGHT_WARNING_SHARE = 0.5
"""Share of the portfolio's value beyond which a historical replay warns that it describes only a
minority of the portfolio (developer's decision of 24/09/2026).

The excluded share counts as idle cash, so the replayed loss is the loss of the covered part, not an
estimate for the whole portfolio.
"""

QUANTITY_DUST_THRESHOLD = Decimal("0.00001")
"""An open quantity at or below this is residue of the recorded transactions, not a position.

Some instruments redeemed in tranches (a crowdfunding loan bought back in parts) leave a tiny
non-zero quantity after the position is economically closed, because each tranche is rounded on
its own. The portfolio's holdings and the asset list's "held now" flags both read positions through
this threshold, so an asset is "held now" exactly when the portfolio would list it as a holding.
"""
