"""One CoinGecko account, what its plugins share: the SDK behind one door (``sdk``) and its currencies (``currencies``).

Two plugins read the account of the settings group ``coingecko``: the price provider and the enricher of the profile. A
plugin never imports another, so what both need lives here, in the core, once: above all the rule that the key never
leaves (``sdk``). It knows the source, as the group does: the exception to «shared helpers are generic», because the
account is one. It cannot sit in ``plugin_settings/groups/``, which imports only the fields: the SDK's errors are the
asset family's, whose base imports the groups.
"""
