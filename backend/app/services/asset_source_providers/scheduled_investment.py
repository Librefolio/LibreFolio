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
"""
import logging
from datetime import date as date_type, timedelta
from decimal import Decimal

from backend.app.schemas.assets import CurrentValueModel, HistoricalDataModel, PricePointModel
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

    def validate_params(self, provider_params: dict | None) -> dict:
        """
        Validate provider parameters for scheduled investment.

        Required params:
        - face_value: Starting amount at day 0 (string or number)
        - currency: ISO 4217 currency code
        - interest_schedule: List of rate periods
        - maturity_date: Maturity date (ISO format)

        Optional params:
        - late_interest: {rate, grace_period_days}
        - schedule_start_date: Override start date (defaults to first period start)

        Args:
            provider_params: Parameters dict

        Returns:
            Validated and normalized params

        Raises:
            AssetSourceError: If validation fails
        """
        if not provider_params:
            raise AssetSourceError(
                "Provider params required for scheduled_investment",
                error_code="MISSING_PARAMS",
                details={"required": ["face_value", "currency", "interest_schedule", "maturity_date"]}
                )

        # Check required fields
        required = ["face_value", "currency", "interest_schedule", "maturity_date"]
        missing = [f for f in required if f not in provider_params]

        if missing:
            raise AssetSourceError(
                f"Missing required params: {', '.join(missing)}",
                error_code="MISSING_PARAMS",
                details={"missing": missing}
                )

        # Validate face_value
        try:
            face_value = Decimal(str(provider_params["face_value"]))
            if face_value <= 0:
                raise ValueError("face_value must be positive")
        except Exception as e:
            raise AssetSourceError(
                f"Invalid face_value: {e}",
                error_code="INVALID_PARAMS",
                details={"field": "face_value", "value": provider_params.get("face_value")}
                )

        # Validate interest_schedule
        schedule = provider_params["interest_schedule"]
        if not isinstance(schedule, list) or len(schedule) == 0:
            raise AssetSourceError(
                "interest_schedule must be a non-empty list",
                error_code="INVALID_PARAMS",
                details={"field": "interest_schedule"}
                )

        # Validate maturity_date
        try:
            if isinstance(provider_params["maturity_date"], str):
                maturity_date = date_type.fromisoformat(provider_params["maturity_date"])
            else:
                maturity_date = provider_params["maturity_date"]
        except Exception as e:
            raise AssetSourceError(
                f"Invalid maturity_date: {e}",
                error_code="INVALID_PARAMS",
                details={"field": "maturity_date", "value": provider_params.get("maturity_date")}
                )

        return provider_params

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
            provider_params: Required parameters (see validate_params)

        Returns:
            CurrentValueModel with calculated value

        Raises:
            AssetSourceError: If calculation fails
        """
        try:
            # Validate params
            params = self.validate_params(provider_params)

            # Extract params
            face_value = Decimal(str(params["face_value"]))
            currency = params["currency"]
            schedule = params["interest_schedule"]
            maturity_date_str = params["maturity_date"]
            late_interest = params.get("late_interest")

            # Parse maturity date
            if isinstance(maturity_date_str, str):
                maturity_date = date_type.fromisoformat(maturity_date_str)
            else:
                maturity_date = maturity_date_str

            # Get schedule start date
            first_period = schedule[0]
            schedule_start_raw = first_period["start_date"]

            if isinstance(schedule_start_raw, str):
                schedule_start = date_type.fromisoformat(schedule_start_raw)
            else:
                schedule_start = schedule_start_raw

            # Calculate for today
            target_date = date_type.today()

            # Before schedule starts: return face value
            if target_date < schedule_start:
                return {
                    "value": face_value,
                    "currency": currency,
                    "as_of_date": target_date,
                    "source": self.provider_name
                    }

            # Calculate accrued interest
            accrued = calculate_accrued_interest(
                face_value=face_value,
                start_date=schedule_start,
                end_date=target_date,
                schedule=schedule,
                maturity_date=maturity_date,
                late_interest=late_interest
                )

            # Total value
            total_value = face_value + accrued
            return CurrentValueModel(
                value=total_value,
                currency=currency,
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
            provider_params: Required parameters (see validate_params)
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        Returns:
            HistoricalDataModel with prices list, currency, source

        Raises:
            AssetSourceError: If calculation fails
        """
        try:
            # Validate params
            params = self.validate_params(provider_params)

            # Extract params
            face_value = Decimal(str(params["face_value"]))
            currency = params["currency"]
            schedule = params["interest_schedule"]
            maturity_date_str = params["maturity_date"]
            late_interest = params.get("late_interest")

            # Parse maturity date
            if isinstance(maturity_date_str, str):
                maturity_date = date_type.fromisoformat(maturity_date_str)
            else:
                maturity_date = maturity_date_str

            # Get schedule start date
            first_period = schedule[0]
            schedule_start_raw = first_period["start_date"]

            if isinstance(schedule_start_raw, str):
                schedule_start = date_type.fromisoformat(schedule_start_raw)
            else:
                schedule_start = schedule_start_raw

            # Calculate for each day in range
            prices = []
            current_date = start_date

            while current_date <= end_date:
                # Before schedule starts: use face value
                if current_date < schedule_start:
                    value = face_value
                else:
                    # Calculate accrued interest
                    accrued = calculate_accrued_interest(
                        face_value=face_value,
                        start_date=schedule_start,
                        end_date=current_date,
                        schedule=schedule,
                        maturity_date=maturity_date,
                        late_interest=late_interest
                        )
                    value = face_value + accrued
                prices.append(PricePointModel(date=current_date, close=value, currency=currency))
                current_date += timedelta(days=1)

            return HistoricalDataModel(prices=prices, currency=currency, source=self.provider_name)

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
