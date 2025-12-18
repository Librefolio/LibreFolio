"""
Test for FAGeographicArea integration with FAClassificationParams.

Tests serialization, deserialization, and round-trip compatibility
using Pydantic's native JSON methods.
"""
import json
from decimal import Decimal

from backend.app.schemas.assets import FAClassificationParams, FAGeographicArea, FASectorArea


def test_classification_params_with_geographic_area():
    """Test FAClassificationParams creation with FAGeographicArea."""
    geo = FAGeographicArea(distribution={"USA": Decimal("0.6"), "DEU": Decimal("0.4")})
    params = FAClassificationParams(
        short_description="Test Company",
        geographic_area=geo,
        sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
        )

    assert params.geographic_area is not None
    assert params.geographic_area.distribution["USA"] == Decimal("0.6000")
    assert params.geographic_area.distribution["DEU"] == Decimal("0.4000")


def test_serialize_classification_params():
    """Test serialization to JSON with FAGeographicArea."""
    geo = FAGeographicArea(distribution={"USA": Decimal("0.7"), "GBR": Decimal("0.3")})
    params = FAClassificationParams(
        geographic_area=geo,
        sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
        )

    json_str = params.model_dump_json(exclude_none=True)
    data = json.loads(json_str)

    # Check structure (now nested with "distribution" key)
    assert "geographic_area" in data
    assert isinstance(data["geographic_area"], dict)
    assert "distribution" in data["geographic_area"]
    assert "USA" in data["geographic_area"]["distribution"]


def test_deserialize_classification_params():
    """Test deserialization from JSON with nested FAGeographicArea."""
    # New format: nested with "distribution" key
    json_str = '{"geographic_area":{"distribution":{"USA":"0.6000","ITA":"0.4000"}},"sector_area":{"distribution":{"Technology":"1.0000"}}}'

    params = FAClassificationParams.model_validate_json(json_str)

    assert params is not None
    assert params.geographic_area is not None
    assert isinstance(params.geographic_area, FAGeographicArea)
    assert params.geographic_area.distribution["USA"] == Decimal("0.6000")
    assert params.geographic_area.distribution["ITA"] == Decimal("0.4000")


def test_round_trip_serialization():
    """Test round-trip: serialize → deserialize → serialize."""
    # Create original
    geo = FAGeographicArea(distribution={"USA": Decimal("0.5"), "FRA": Decimal("0.5")})
    original = FAClassificationParams(
        geographic_area=geo,
        sector_area=FASectorArea(distribution={"Financials": Decimal("1.0")})
        )

    # Serialize
    json_str1 = original.model_dump_json(exclude_none=True)

    # Deserialize
    parsed = FAClassificationParams.model_validate_json(json_str1)

    # Serialize again
    json_str2 = parsed.model_dump_json(exclude_none=True)

    # Compare
    data1 = json.loads(json_str1)
    data2 = json.loads(json_str2)

    assert data1 == data2


def test_none_geographic_area():
    """Test that None geographic_area works correctly."""
    params = FAClassificationParams(
        sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
        )

    json_str = params.model_dump_json(exclude_none=True)
    data = json.loads(json_str)

    assert "geographic_area" not in data  # Should be excluded

    # Deserialize
    parsed = FAClassificationParams.model_validate_json(json_str)
    assert parsed.geographic_area is None
