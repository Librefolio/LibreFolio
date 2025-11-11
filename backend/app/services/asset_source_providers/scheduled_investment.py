"""
Scheduled Investment Provider.

This provider calculates synthetic values for scheduled-yield assets such as:
- Crowdfunding loans (P2P lending)
- Bonds with fixed interest schedules
- Any asset with predictable cash flows

The provider calculates values at runtime based on:
- Face value (principal)
- Interest schedule (rate periods)
- Maturity date
- Late interest (optional)

Values are NOT stored in the database - they are calculated on-demand.

Day count convention: ACT/365 (actual days / 365)
Interest type: SIMPLE (not compound)

For detailed parameter structure documentation, see:
- backend.app.schemas.assets.ScheduledInvestmentParams
- backend.app.schemas.assets.InterestRatePeriod
- backend.app.schemas.assets.LateInterestConfig

Note:
    All methods accept dict/JSON which is automatically converted to Pydantic models.
    Use ScheduledInvestmentParams(**dict_data) or .parse_raw(json_str) for manual conversion.
"""
import logging
from datetime import date as date_type, timedelta
from decimal import Decimal

from backend.app.schemas.assets import (
    CurrentValueModel,
    HistoricalDataModel,
    PricePointModel,
    ScheduledInvestmentParams,
    )
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.utils.financial_math import (
    calculate_accrued_interest,
    )

logger = logging.getLogger(__name__)


@register_provider(AssetProviderRegistry)
class ScheduledInvestmentProvider(AssetSourceProvider):
    """
    Provider for scheduled-yield assets (loans, bonds).

    Calculates synthetic values based on interest schedules.
    No external API calls - all calculations are local.
    """

    @property
    def provider_code(self) -> str:
        return "scheduled_investment"

    @property
    def provider_name(self) -> str:
        return "Scheduled Investment Calculator"

    @property
    def test_cases(self) -> list[dict]:
        """Test cases for scheduled investment provider."""
        return [
            {
                "identifier": "TEST-LOAN-001",
                "provider_params": {
                    "face_value": "10000",
                    "currency": "EUR",
                    "interest_schedule": [
                        {
                            "start_date": "2025-01-01",
                            "end_date": "2025-12-31",
                            "rate": "0.05"
                            }
                        ],
                    "maturity_date": "2025-12-31",
                    "late_interest": None
                    }
                }
            ]

    @property
    def supports_history(self) -> bool:
        """This provider supports historical data (calculated)."""
        return True

    @property
    def supports_search(self) -> bool:
        """Search not applicable for scheduled investments."""
        return False

    @property
    def test_search_query(self) -> str | None:
        """Search not applicable for scheduled investments."""
        return None

    def validate_params(self, provider_params: dict) -> ScheduledInvestmentParams:
        """
        Validate provider parameters for scheduled investment.

        Uses Pydantic ScheduledInvestmentParams model for validation.
        Automatically converts dict/JSON to Pydantic model.

        See backend.app.schemas.assets.ScheduledInvestmentParams for full documentation.

        Args:
            provider_params: Parameters dict (will be converted to ScheduledInvestmentParams)

        Returns:
            Validated ScheduledInvestmentParams instance

        Raises:
            AssetSourceError: If validation fails

        Example:
            params = {
                "face_value": "10000",
                "currency": "EUR",
                "interest_schedule": [
                    {"start_date": "2025-01-01", "end_date": "2025-12-31", "rate": "0.05"}
                ],
                "maturity_date": "2025-12-31",
                "late_interest": {"rate": "0.12", "grace_period_days": 30}
            }
            validated = provider.validate_params(params)
            # Returns ScheduledInvestmentParams instance with validated data
        """
        if not provider_params:
            raise AssetSourceError(
                "Provider params required for scheduled_investment",
                error_code="MISSING_PARAMS",
                details={"required": ["face_value", "currency", "interest_schedule", "maturity_date"]}
                )

        try:
            # Convert dict to Pydantic model (automatic validation)
            return ScheduledInvestmentParams(**provider_params)
        except ValueError as e:
            raise AssetSourceError(
                f"Invalid provider params: {e}",
                error_code="INVALID_PARAMS",
                details={"error": str(e)}
                )

    async def get_current_value(
        self,
        identifier: str,
        provider_params: dict,
        ) -> CurrentValueModel:
        """
        Calculate current value for scheduled investment.

        Formula: value = face_value + accrued_interest

        Args:
            identifier: Asset identifier (for logging), not used in calculation.
            provider_params: Required parameters (see ScheduledInvestmentParams schema)

        Returns:
            CurrentValueModel with calculated value

        Raises:
            AssetSourceError: If calculation fails
        """
        try:
            # Validate params and convert to Pydantic model
            params = self.validate_params(provider_params)

            # Calculate for today using validated params
            target_date = date_type.today()
            total_value = self._calculate_value_for_date(params, target_date)

            return CurrentValueModel(
                value=total_value,
                currency=params.currency,
                as_of_date=target_date,
                source=self.provider_name
                )

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to calculate current value for asset '{identifier}': {e}",
                error_code="CALCULATION_ERROR",
                details={"error": str(e)}
                )

    async def get_history_value(
        self,
        identifier: str,
        provider_params: dict,
        start_date: date_type,
        end_date: date_type,
        ) -> HistoricalDataModel:
        """
        Calculate historical values for scheduled investment.

        Generates daily values for requested date range.

        Args:
            identifier: Asset identifier (for logging)
            provider_params: Required parameters (see ScheduledInvestmentParams schema)
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            HistoricalDataModel with prices list, currency, source

        Raises:
            AssetSourceError: If calculation fails
        """
        try:
            # Validate params and convert to Pydantic model
            params = self.validate_params(provider_params)

            # Calculate for each day in range using validated params
            prices = []
            current_date = start_date

            while current_date <= end_date:
                value = self._calculate_value_for_date(params, current_date)
                prices.append(PricePointModel(
                    date=current_date,
                    close=value,
                    currency=params.currency
                    ))
                current_date += timedelta(days=1)

            return HistoricalDataModel(
                prices=prices,
                currency=params.currency,
                source=self.provider_name
                )

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to calculate history: {e}",
                error_code="CALCULATION_ERROR",
                details={"error": str(e)}
                )

    async def search(self, query: str) -> list[dict]:
        """
        Search not applicable for scheduled investments.

        Scheduled investments are configured manually with specific parameters.
        """
        raise AssetSourceError(
            "Search not supported for scheduled_investment provider",
            error_code="NOT_SUPPORTED",
            details={"message": "Scheduled investments require manual configuration"}
            )

    def _calculate_value_for_date(
        self,
        params: ScheduledInvestmentParams,
        target_date: date_type,
        ) -> Decimal:
        """
        Calculate synthetic value for a specific date.

        Core calculation method used by both get_current_value() and get_history_value().

        Formula:
            value = face_value + accrued_interest

        Where accrued_interest is calculated from schedule start to target_date
        using SIMPLE interest with ACT/365 day count convention.

        Args:
            params: Validated ScheduledInvestmentParams (contains all needed data)
            target_date: Date to calculate value for

        Returns:
            Calculated value as Decimal

        Note:
            This method delegates to financial_math.calculate_accrued_interest()
            for the actual interest calculation, ensuring consistency across
            the application.

        TODO (Step 03):
            - Check if loan repaid via transactions
            - Subtract dividend payments from value
        """
        # Extract schedule start date from first period
        # All Pydantic validation is already done, safe to access
        schedule_start = params.interest_schedule[0].start_date

        # Before investment starts: return only principal (no interest accrued yet)
        # Example: If schedule starts Jan 1st but we query Dec 15th, return face_value
        if target_date < schedule_start:
            return params.face_value

        # Calculate accrued interest from schedule start to target date
        # This handles:
        # - Multiple rate periods (e.g., 5% year 1, 6% year 2)
        # - Rate changes mid-period
        # - Grace periods after maturity
        # - Late interest penalties
        accrued = calculate_accrued_interest(
            face_value=params.face_value,
            start_date=schedule_start,
            end_date=target_date,
            schedule=params.interest_schedule,
            maturity_date=params.maturity_date,
            late_interest=params.late_interest
            )

        # Total value = principal + accumulated interest
        # This is an ESTIMATE for portfolio valuation
        # Actual profit = sale_price - purchase_price (realized via transactions)
        return params.face_value + accrued
