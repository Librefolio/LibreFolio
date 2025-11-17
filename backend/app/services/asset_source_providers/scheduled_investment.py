"""
Scheduled Investment Provider.

This provider calculates synthetic values for scheduled-yield assets such as:
- Crowdfunding loans (P2P lending)
- Bonds with fixed interest schedules
- Any asset with predictable cash flows

The provider calculates values at runtime based on:
- Interest schedule from Asset.interest_schedule (JSON field)
- Current principal (face_value) calculated from transactions

Values are NOT stored in the database - they are calculated on-demand.

How it works:
1. Receives asset_id as identifier
2. Queries DB for:
   - Asset record (interest_schedule JSON)
   - All transactions for this asset
3. Calculates current principal from transactions:
   - BUY: increases principal
   - SELL: decreases principal
   - INTEREST: may include principal repayment (if negative)
4. Calculates accrued interest using schedule
5. Returns principal + accrued interest

Supports:
- Multiple day count conventions: ACT/365, ACT/360, ACT/ACT, 30/360
- Interest types: SIMPLE and COMPOUND
- Multiple compounding frequencies: DAILY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL, CONTINUOUS

Test support:
- provider_params can include "_transaction_override" to bypass DB queries
- Override should contain list of transaction dicts for testing

For detailed parameter structure documentation, see:
- backend.app.schemas.assets.ScheduledInvestmentSchedule
- backend.app.schemas.assets.InterestRatePeriod
- backend.app.schemas.assets.LateInterestConfig
"""
import logging
import json
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Transaction, TransactionType
from backend.app.db.session import get_session_generator
from backend.app.schemas.assets import (
    CurrentValueModel,
    HistoricalDataModel,
    PricePointModel,
    ScheduledInvestmentSchedule,
    CompoundingType,
    )
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.utils.financial_math import (
    calculate_day_count_fraction,
    calculate_simple_interest,
    calculate_compound_interest,
    find_active_period,
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
                "identifier": "1",  # asset_id
                "provider_params": {
                    "schedule": [
                        {
                            "start_date": "2025-01-01",
                            "end_date": "2025-12-31",
                            "annual_rate": "0.05",
                            "compounding": "SIMPLE",
                            "day_count": "ACT/365"
                            }
                        ],
                    "late_interest": None,
                    "_transaction_override": [
                        {
                            "type": "BUY",
                            "quantity": 1,
                            "price": "10000",
                            "trade_date": "2025-01-01"
                        }
                    ]
                    }
                }
            ]

    @property
    def supports_search(self) -> bool:
        """Search not applicable for scheduled investments."""
        return False

    async def _get_asset_from_db(self, asset_id: int, session: AsyncSession) -> Asset:
        """
        Retrieve asset record from database.

        Args:
            asset_id: Asset ID
            session: Database session

        Returns:
            Asset record

        Raises:
            AssetSourceError: If asset not found
        """
        result = await session.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise AssetSourceError(
                f"Asset not found: {asset_id}",
                error_code="ASSET_NOT_FOUND",
                details={"asset_id": asset_id}
            )

        return asset

    async def _get_transactions_from_db(
        self,
        asset_id: int,
        session: AsyncSession,
        up_to_date: Optional[date_type] = None
    ) -> list[Transaction]:
        """
        Retrieve all transactions for an asset from database.

        Args:
            asset_id: Asset ID
            session: Database session
            up_to_date: Optional date filter (inclusive)

        Returns:
            List of Transaction records
        """
        query = select(Transaction).where(Transaction.asset_id == asset_id)

        if up_to_date:
            # Use settlement_date if available, otherwise trade_date
            query = query.where(
                and_(
                    Transaction.trade_date <= up_to_date
                )
            )

        query = query.order_by(Transaction.trade_date, Transaction.id)

        result = await session.execute(query)
        return list(result.scalars().all())

    def _calculate_face_value_from_transactions(
        self,
        transactions: list[Transaction] | list[dict]
    ) -> Decimal:
        """
        Calculate current principal (face_value) from transactions.

        Logic:
        - BUY: increases principal (quantity * price)
        - SELL: decreases principal (quantity * price)
        - INTEREST: may include principal repayment (negative amount decreases principal)
        - Other transaction types don't affect principal

        Args:
            transactions: List of Transaction records or dicts (from override)

        Returns:
            Current principal amount
        """
        face_value = Decimal("0")

        for txn in transactions:
            # Handle both Transaction objects and dicts
            if isinstance(txn, dict):
                txn_type = txn.get("type")
                quantity = Decimal(str(txn.get("quantity", 0)))
                price = Decimal(str(txn.get("price", 0)))
            else:
                txn_type = txn.type
                quantity = txn.quantity
                price = txn.price if txn.price else Decimal("0")

            if txn_type == TransactionType.BUY or txn_type == "BUY":
                # Buy increases principal
                face_value += quantity * price
            elif txn_type == TransactionType.SELL or txn_type == "SELL":
                # Sell decreases principal
                face_value -= quantity * price
            elif txn_type == TransactionType.INTEREST or txn_type == "INTEREST":
                # Interest transactions with negative price represent principal repayment
                # Positive price is just interest income (doesn't affect principal)
                if price < 0:
                    face_value += price  # Negative price reduces principal

        return face_value

    async def get_current_value(
        self,
        identifier: str,
        provider_params: dict,
        ) -> CurrentValueModel:
        """
        Calculate current value for scheduled investment.

        Formula: value = principal + accrued_interest

        The principal (face_value) is calculated from transactions:
        - Sum of BUY transactions (quantity * price)
        - Minus SELL transactions (quantity * price)
        - Minus principal repayments (INTEREST with negative price)

        Args:
            identifier: Asset ID (as string)
            provider_params: Can include "_transaction_override" for testing

        Returns:
            CurrentValueModel with calculated value

        Raises:
            AssetSourceError: If calculation fails or asset not found
        """
        try:
            asset_id = int(identifier)

            # Initialize variables
            transactions = []
            schedule = None
            currency = "EUR"

            # Check for transaction override (for testing)
            transaction_override = provider_params.get("_transaction_override")

            if transaction_override:
                # Test mode: use provided transactions
                transactions = transaction_override

                # Remove _transaction_override from params before validation
                params_copy = {k: v for k, v in provider_params.items() if k != "_transaction_override"}

                # Validate and extract schedule
                schedule = self.validate_params(params_copy)
                currency = "EUR"  # Default for tests
            else:
                # Production mode: fetch from DB
                async for session in get_session_generator():
                    # Get asset record
                    asset = await self._get_asset_from_db(asset_id, session)

                    # Get transactions
                    transactions = await self._get_transactions_from_db(asset_id, session)

                    # Parse interest schedule from asset
                    if not asset.interest_schedule:
                        raise AssetSourceError(
                            f"Asset {asset_id} has no interest_schedule configured",
                            error_code="MISSING_SCHEDULE",
                            details={"asset_id": asset_id}
                        )

                    schedule_data = json.loads(asset.interest_schedule)
                    schedule = ScheduledInvestmentSchedule(**schedule_data)
                    currency = asset.currency
                    break  # Exit after first iteration

            if schedule is None:
                raise AssetSourceError(
                    "Failed to load schedule",
                    error_code="SCHEDULE_LOAD_ERROR",
                    details={"asset_id": asset_id}
                )

            # Calculate current principal from transactions
            face_value = self._calculate_face_value_from_transactions(transactions)

            # If no principal invested, return 0
            if face_value <= 0:
                return CurrentValueModel(
                    value=Decimal("0"),
                    currency=currency,
                    as_of_date=date_type.today(),
                    source=self.provider_name
                )

            # Calculate value for today
            target_date = date_type.today()
            total_value = self._calculate_value_for_date(schedule, face_value, target_date)

            return CurrentValueModel(
                value=total_value,
                currency=currency,
                as_of_date=target_date,
                source=self.provider_name
                )

        except AssetSourceError:
            raise
        except ValueError as e:
            raise AssetSourceError(
                f"Invalid asset ID: {identifier}",
                error_code="INVALID_IDENTIFIER",
                details={"error": str(e)}
            )
        except Exception as e:
            raise AssetSourceError(
                f"Failed to calculate current value for asset '{identifier}': {e}",
                error_code="CALCULATION_ERROR",
                details={"error": str(e)}
                )

    @property
    def supports_history(self) -> bool:
        """This provider supports historical data (calculated)."""
        return True

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
        For each date, calculates principal from transactions up to that date.

        Args:
            identifier: Asset ID (as string)
            provider_params: Can include "_transaction_override" for testing
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            HistoricalDataModel with prices list, currency, source

        Raises:
            AssetSourceError: If calculation fails
        """
        try:
            asset_id = int(identifier)

            # Initialize variables
            all_transactions = []
            schedule = None
            currency = "EUR"

            # Check for transaction override (for testing)
            transaction_override = provider_params.get("_transaction_override")

            if transaction_override:
                # Test mode: use provided transactions
                all_transactions = transaction_override

                # Remove _transaction_override from params before validation
                params_copy = {k: v for k, v in provider_params.items() if k != "_transaction_override"}

                schedule = self.validate_params(params_copy)
                currency = "EUR"
            else:
                # Production mode: fetch from DB
                async for session in get_session_generator():
                    asset = await self._get_asset_from_db(asset_id, session)
                    all_transactions = await self._get_transactions_from_db(
                        asset_id, session, up_to_date=end_date
                    )

                    if not asset.interest_schedule:
                        raise AssetSourceError(
                            f"Asset {asset_id} has no interest_schedule configured",
                            error_code="MISSING_SCHEDULE",
                            details={"asset_id": asset_id}
                        )

                    schedule_data = json.loads(asset.interest_schedule)
                    schedule = ScheduledInvestmentSchedule(**schedule_data)
                    currency = asset.currency
                    break

            if schedule is None:
                raise AssetSourceError(
                    "Failed to load schedule",
                    error_code="SCHEDULE_LOAD_ERROR",
                    details={"asset_id": asset_id}
                )

            # Calculate for each day in range
            prices = []
            current_date = start_date

            while current_date <= end_date:
                # Filter transactions up to current_date
                transactions_up_to_date = [
                    txn for txn in all_transactions
                    if (isinstance(txn, dict) and txn.get("trade_date") <= current_date.isoformat())
                    or (not isinstance(txn, dict) and txn.trade_date <= current_date)
                ]

                # Calculate face_value for this date
                face_value = self._calculate_face_value_from_transactions(transactions_up_to_date)

                # Calculate value
                if face_value <= 0:
                    value = Decimal("0")
                else:
                    value = self._calculate_value_for_date(schedule, face_value, current_date)

                prices.append(PricePointModel(
                    date=current_date,
                    close=value,
                    currency=currency
                    ))
                current_date += timedelta(days=1)

            return HistoricalDataModel(
                prices=prices,
                currency=currency,
                source=self.provider_name
                )

        except AssetSourceError:
            raise
        except ValueError as e:
            raise AssetSourceError(
                f"Invalid asset ID: {identifier}",
                error_code="INVALID_IDENTIFIER",
                details={"error": str(e)}
            )
        except Exception as e:
            raise AssetSourceError(
                f"Failed to calculate history: {e}",
                error_code="CALCULATION_ERROR",
                details={"error": str(e)}
                )

    @property
    def test_search_query(self) -> str | None:
        """Search not applicable for scheduled investments."""
        return None

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
        schedule: ScheduledInvestmentSchedule,
        face_value: Decimal,
        target_date: date_type,
        ) -> Decimal:
        """
        Calculate synthetic value for a specific date.

        Core calculation method used by both get_current_value() and get_history_value().

        Formula:
            value = principal + accrued_interest

        Where accrued_interest is calculated period-by-period using the appropriate:
        - Day count convention (ACT/365, ACT/360, 30/360, ACT/ACT)
        - Interest type (SIMPLE or COMPOUND)
        - Compounding frequency (if COMPOUND)

        Args:
            schedule: Validated ScheduledInvestmentSchedule with all periods
            face_value: Current principal amount
            target_date: Date to calculate value for

        Returns:
            Calculated value as Decimal

        Note:
            Handles multiple scenarios:
            - Before schedule starts: returns principal only
            - During schedule: calculates accrued interest
            - After maturity (grace period): continues with last rate
            - After grace period: applies late interest rate
        """
        # Extract schedule start date from first period
        if not schedule.schedule:
            return face_value  # No schedule = no interest

        schedule_start = schedule.schedule[0].start_date

        # Calculate maturity date from last period's end_date
        maturity_date = schedule.schedule[-1].end_date

        # Before investment starts: return only principal (no interest accrued yet)
        if target_date < schedule_start:
            return face_value

        # Calculate accrued interest from schedule start to target date
        # Process period by period to handle rate changes and different calculation methods
        total_interest = Decimal("0")
        current_date = schedule_start

        while current_date <= target_date:
            # Find the active period for this date
            period = find_active_period(
                schedule=schedule.schedule,
                target_date=current_date,
                maturity_date=maturity_date,
                late_interest=schedule.late_interest
            )

            if period is None:
                # No applicable period (shouldn't happen if schedule is valid)
                break

            # Calculate end date for this calculation segment
            # (either end of period or target_date, whichever comes first)
            segment_end = min(period.end_date, target_date)

            # Calculate time fraction using period's day count convention
            time_fraction = calculate_day_count_fraction(
                start_date=current_date,
                end_date=segment_end,
                convention=period.day_count
            )

            # Calculate interest for this segment based on compounding type
            if period.compounding == CompoundingType.SIMPLE:
                segment_interest = calculate_simple_interest(
                    principal=face_value,
                    annual_rate=period.annual_rate,
                    time_fraction=time_fraction
                )
            else:  # COMPOUND
                if period.compound_frequency is None:
                    raise ValueError("compound_frequency required for COMPOUND interest")
                segment_interest = calculate_compound_interest(
                    principal=face_value,
                    annual_rate=period.annual_rate,
                    time_fraction=time_fraction,
                    frequency=period.compound_frequency
                )

            total_interest += segment_interest

            # Move to next segment (day after segment_end)
            current_date = segment_end + timedelta(days=1)

            # If we've reached target_date, stop
            if segment_end >= target_date:
                break

        # Total value = principal + accumulated interest
        return face_value + total_interest

    def validate_params(self, provider_params: dict) -> ScheduledInvestmentSchedule:
        """
        Validate provider parameters for scheduled investment.

        Uses Pydantic ScheduledInvestmentSchedule model for validation.
        Automatically converts dict/JSON to Pydantic model.

        See backend.app.schemas.assets.ScheduledInvestmentSchedule for full documentation.

        Args:
            provider_params: Parameters dict (will be converted to ScheduledInvestmentSchedule)

        Returns:
            Validated ScheduledInvestmentSchedule instance

        Raises:
            AssetSourceError: If validation fails

        Example:
            params = {
                "schedule": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": "2025-12-31",
                        "annual_rate": 0.05,
                        "compounding": "SIMPLE",
                        "day_count": "ACT/365"
                    }
                ],
                "late_interest": {
                    "annual_rate": 0.12,
                    "grace_period_days": 30,
                    "compounding": "SIMPLE",
                    "day_count": "ACT/365"
                }
            }
            validated = provider.validate_params(params)
            # Returns ScheduledInvestmentSchedule instance with validated data
        """
        if not provider_params:
            raise AssetSourceError(
                "Provider params required for scheduled_investment",
                error_code="MISSING_PARAMS",
                details={"required": ["schedule"]}
                )

        try:
            # Convert dict to Pydantic model (automatic validation)
            return ScheduledInvestmentSchedule(**provider_params)
        except ValueError as e:
            raise AssetSourceError(
                f"Invalid provider params: {e}",
                error_code="INVALID_PARAMS",
                details={"error": str(e)}
                )
