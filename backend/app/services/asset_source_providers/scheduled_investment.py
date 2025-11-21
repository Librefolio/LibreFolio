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
- backend.app.schemas.assets.FAScheduledInvestmentSchedule
- backend.app.schemas.assets.FAInterestRatePeriod
- backend.app.schemas.assets.FALateInterestConfig
"""
import json
import logging
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Transaction, TransactionType
from backend.app.db.session import get_session_generator
from backend.app.schemas.assets import (
    FACurrentValue,
    FAHistoricalData,
    FAPricePoint,
    FAScheduledInvestmentSchedule,
    CompoundingType,
    FAInterestRatePeriod,  # added for synthetic periods
    )
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.utils.financial_math import (
    calculate_day_count_fraction,
    calculate_simple_interest,
    calculate_compound_interest,
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
        ) -> FACurrentValue:
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
            FACurrentValue with calculated value

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
                    schedule = FAScheduledInvestmentSchedule(**schedule_data)
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
                return FACurrentValue(
                    value=Decimal("0"),
                    currency=currency,
                    as_of_date=date_type.today(),
                    source=self.provider_name
                    )

            # Calculate value for today
            target_date = date_type.today()
            total_value = self._calculate_value_for_date(schedule, face_value, target_date)

            return FACurrentValue(
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
        ) -> FAHistoricalData:
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
            FAHistoricalData with prices list, currency, source

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
                    schedule = FAScheduledInvestmentSchedule(**schedule_data)
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

                prices.append(FAPricePoint(
                    date=current_date,
                    close=value,
                    currency=currency
                    ))
                current_date += timedelta(days=1)

            return FAHistoricalData(
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
        schedule: FAScheduledInvestmentSchedule,
        face_value: Decimal,
        target_date: date_type,
        ) -> Decimal:
        """Period-based synthetic value calculation.

        Replaces previous day-by-day loop to avoid O(days) complexity and infinite loops.

        Steps:
          1. If target_date before first period start -> return principal.
          2. Collect real periods truncated to target_date.
          3. If after maturity, append synthetic grace / late periods as needed.
          4. Sum interest per period using appropriate method.
          5. Return principal + total interest.

        Synthetic periods:
          * Grace period: (maturity+1 .. min(grace_end, target_date)) with last scheduled rate.
          * Late period: (grace_end+1 .. target_date) with late_interest config.
        """
        if not schedule.schedule:
            return face_value

        first_start = schedule.schedule[0].start_date
        maturity_date = schedule.schedule[-1].end_date

        if target_date < first_start:
            return face_value

        periods_to_process: list[FAInterestRatePeriod] = []

        # 1. Real scheduled periods (truncate to target_date)
        for p in schedule.schedule:
            if p.start_date > target_date:
                break
            eff_start = p.start_date
            eff_end = p.end_date if p.end_date <= target_date else target_date
            if eff_end >= eff_start:
                periods_to_process.append(
                    FAInterestRatePeriod(
                        start_date=eff_start,
                        end_date=eff_end,
                        annual_rate=p.annual_rate,
                        compounding=p.compounding,
                        compound_frequency=p.compound_frequency,
                        day_count=p.day_count,
                        )
                    )

        # 2. Post-maturity synthetic periods
        if target_date > maturity_date and schedule.late_interest:
            li = schedule.late_interest
            grace_end = maturity_date + timedelta(days=li.grace_period_days)
            last_rate_period = schedule.schedule[-1]
            # Grace segment (only if target_date >= maturity+1 and grace_days > 0)
            grace_start = maturity_date + timedelta(days=1)
            if grace_start <= target_date and li.grace_period_days > 0:
                grace_segment_end = min(grace_end, target_date)
                if grace_segment_end >= grace_start:
                    periods_to_process.append(
                        FAInterestRatePeriod(
                            start_date=grace_start,
                            end_date=grace_segment_end,
                            annual_rate=last_rate_period.annual_rate,
                            compounding=last_rate_period.compounding,
                            compound_frequency=last_rate_period.compound_frequency,
                            day_count=last_rate_period.day_count,
                            )
                        )
            # Late segment (after grace_end)
            late_start = grace_end + timedelta(days=1)
            if target_date >= late_start:
                late_end = target_date
                if late_end >= late_start:
                    periods_to_process.append(
                        FAInterestRatePeriod(
                            start_date=late_start,
                            end_date=late_end,
                            annual_rate=li.annual_rate,
                            compounding=li.compounding,
                            compound_frequency=li.compound_frequency,
                            day_count=li.day_count,
                            )
                        )

        total_interest = Decimal("0")
        for period in periods_to_process:
            # day count fraction inclusive of start/end
            time_fraction = calculate_day_count_fraction(
                start_date=period.start_date,
                end_date=period.end_date,
                convention=period.day_count,
                )
            if time_fraction <= 0:
                continue  # defensive, shouldn't happen
            if period.compounding == CompoundingType.SIMPLE:
                segment_interest = calculate_simple_interest(
                    principal=face_value,
                    annual_rate=period.annual_rate,
                    time_fraction=time_fraction,
                    )
            else:
                if period.compound_frequency is None:
                    raise ValueError("compound_frequency required for COMPOUND interest")
                segment_interest = calculate_compound_interest(
                    principal=face_value,
                    annual_rate=period.annual_rate,
                    time_fraction=time_fraction,
                    frequency=period.compound_frequency,
                    )
            total_interest += segment_interest

        return face_value + total_interest

    def validate_params(self, provider_params: dict) -> FAScheduledInvestmentSchedule:
        """
        Validate provider parameters for scheduled investment.

        Uses Pydantic FAScheduledInvestmentSchedule model for validation.
        Automatically converts dict/JSON to Pydantic model.

        See backend.app.schemas.assets.FAScheduledInvestmentSchedule for full documentation.

        Args:
            provider_params: Parameters dict (will be converted to FAScheduledInvestmentSchedule)

        Returns:
            Validated FAScheduledInvestmentSchedule instance

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
            # Returns FAScheduledInvestmentSchedule instance with validated data
        """
        if not provider_params:
            raise AssetSourceError(
                "Provider params required for scheduled_investment",
                error_code="MISSING_PARAMS",
                details={"required": ["schedule"]}
                )

        try:
            # Convert dict to Pydantic model (automatic validation)
            return FAScheduledInvestmentSchedule(**provider_params)
        except ValueError as e:
            raise AssetSourceError(
                f"Invalid provider params: {e}",
                error_code="INVALID_PARAMS",
                details={"error": str(e)}
                )

    async def fetch_asset_metadata(
        self,
        identifier: str,
        provider_params: dict | None = None,
        ) -> dict | None:
        """
        Fetch asset metadata (NOT SUPPORTED for synthetic scheduled investment).

        Scheduled investment is a synthetic provider that calculates
        values from interest schedules. No external metadata available.

        Returns:
            None (metadata not supported)
        """
        # Synthetic provider - no external metadata
        return None
