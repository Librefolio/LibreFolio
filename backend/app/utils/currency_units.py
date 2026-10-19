"""Quote currencies a price provider reports in a minor unit.

Yahoo Finance quotes London lines in pence and says so with the currency ``GBp``. The schemas accept a currency code
whatever its case: the prices are stored as ``GBP`` with their numbers unchanged, pence read as pounds, until the
asset's quote base (``quote_base_quantity``, "Units per single price") divides them back. The portfolio data-quality
report reads this table so that a currency stored as ``GBp`` is never suggested as ``GBP`` (``NON_ISO_CURRENCY``,
E-19b): pence relabelled as pounds would count 100 times.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

#: A provider's code for a minor unit, exactly as reported (the case is what tells ``GBp`` from ``GBP``), and how many
#: of its units make one unit of the currency the schemas fold it to.
MINOR_UNIT_FACTORS: Mapping[str, int] = MappingProxyType({"GBp": 100})


def minor_unit_factor(reported_currency: str | None) -> int | None:
    """The factor of ``reported_currency`` when a provider reports a minor unit with it (``"GBp"`` gives 100), else
    None."""
    if not reported_currency:
        return None
    return MINOR_UNIT_FACTORS.get(reported_currency.strip())
