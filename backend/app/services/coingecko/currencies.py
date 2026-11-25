"""The currencies a CoinGecko price may be asked in, for an asset of LibreFolio (project 76, A3).

CoinGecko prices a coin in 63 «vs currencies» (``/simple/supported_vs_currencies``): national currencies, a dozen
cryptocurrencies, gold and silver, the IMF's XDR, and fractions of a bitcoin. An asset's currency is a currency
LibreFolio knows: an active ISO 4217 code. So the choice is the national ones only, without metals and XDR, fixed here
and checked by a test against the recorded list (``fixtures/coingecko/supported_vs_currencies.json``).
"""

#: CoinGecko's national vs currencies that are active ISO 4217 codes, uppercase, sorted (45; ``VEF`` is retired).
VS_CURRENCIES: tuple[str, ...] = (
    "AED", "ARS", "AUD", "BDT", "BHD", "BMD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK", "DKK", "EUR", "GBP",
    "GEL", "HKD", "HUF", "IDR", "ILS", "INR", "JPY", "KRW", "KWD", "LKR", "MMK", "MXN", "MYR", "NGN", "NOK",
    "NZD", "PHP", "PKR", "PLN", "RUB", "SAR", "SEK", "SGD", "THB", "TRY", "TWD", "UAH", "USD", "VND", "ZAR",
)  # fmt: skip

#: The currency an asset gets when nothing else says (the plan, A3): the euro.
DEFAULT_VS_CURRENCY = "EUR"
