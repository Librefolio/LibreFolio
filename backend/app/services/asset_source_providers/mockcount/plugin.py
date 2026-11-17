"""``mockcount``: mockprov's answers, counted at the call boundary like a provider that calls out (project 76, U4).

For the tests of the call limits only (the consultant's rule 3): ``mockprov`` is not counted, since a limit on it would be
an instance setting of the shared test backend and stop every test that uses it. ``mockcount`` belongs to the one suite
or spec that sets its limits. Test-only: withheld outside test mode, like every double. No network.

Its fields are the five core call limits only, given at registration: none of mockprov's own (its ``api_key`` and its
alias variable are mockprov's), no group.
"""

from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.platform.provider_registry import register_provider


@register_provider(AssetProviderRegistry)
class MockCountProvider(MockProvider):
    """mockprov's answers under the code ``mockcount``, counted at the boundary. FOR TESTING ONLY."""

    test_only = True
    calls_external_service = True
    settings_fields = ()
    settings_groups = ()

    @property
    def provider_code(self) -> str:
        return "mockcount"

    @property
    def provider_name(self) -> str:
        return "Mock Counted Provider"
