"""
Test AssetMetadataService utility methods.

Tests parse/serialize, diff computation, and partial update PATCH semantics
for asset classification metadata.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.assets import ClassificationParamsModel, PatchAssetMetadataRequest
from backend.app.services.asset_metadata import AssetMetadataService


def test_parse_classification_params_valid_json():
    """Test parsing valid JSON to ClassificationParamsModel."""
    json_str = '{"investment_type":"stock","sector":"Technology"}'
    parsed = AssetMetadataService.parse_classification_params(json_str)

    assert isinstance(parsed, ClassificationParamsModel)
    assert parsed.investment_type == "stock"
    assert parsed.sector == "Technology"


def test_parse_classification_params_none():
    """Test parsing None returns None."""
    result = AssetMetadataService.parse_classification_params(None)
    assert result is None


def test_serialize_classification_params():
    """Test serializing ClassificationParamsModel to JSON."""
    model = ClassificationParamsModel(
        investment_type="stock",
        sector="Technology"
        )

    serialized = AssetMetadataService.serialize_classification_params(model)
    assert isinstance(serialized, str)

    # Parse back to verify structure
    data = json.loads(serialized)
    assert data["investment_type"] == "stock"
    assert data["sector"] == "Technology"


def test_serialize_classification_params_none():
    """Test serializing None returns None."""
    result = AssetMetadataService.serialize_classification_params(None)
    assert result is None


def test_compute_metadata_diff():
    """Test computing differences between two ClassificationParamsModel instances."""
    old = ClassificationParamsModel(investment_type="stock", sector="Energy")
    new = ClassificationParamsModel(investment_type="etf", sector="Technology")

    changes = AssetMetadataService.compute_metadata_diff(old, new)
    fields = {c.field for c in changes}

    assert "investment_type" in fields
    assert "sector" in fields
    assert len(changes) == 2


def test_apply_partial_update_absent_fields_ignored():
    """Test that absent fields in patch are ignored (PATCH semantics)."""
    current = ClassificationParamsModel(
        investment_type="stock",
        sector="Technology"
        )

    # Patch only updates short_description, other fields should remain
    patch = PatchAssetMetadataRequest(
        short_description="New description"
        )

    updated = AssetMetadataService.apply_partial_update(current, patch)
    assert updated.investment_type == "stock"  # Unchanged
    assert updated.sector == "Technology"  # Unchanged
    assert updated.short_description == "New description"  # Updated


def test_apply_partial_update_null_clears_field():
    """Test that null in patch clears the field (PATCH semantics)."""
    current = ClassificationParamsModel(
        investment_type="stock",
        short_description="Original",
        sector="Technology"
        )

    # Explicitly set sector to None to clear it
    patch = PatchAssetMetadataRequest(
        sector=None
        )

    updated = AssetMetadataService.apply_partial_update(current, patch)
    assert updated.sector is None  # Cleared
    assert updated.short_description == "Original"  # Unchanged


def test_apply_partial_update_geographic_area_full_replace():
    """Test that geographic_area is fully replaced (no merge)."""
    current = ClassificationParamsModel(
        investment_type="stock",
        geographic_area={"USA": Decimal("0.6"), "ITA": Decimal("0.4")},
        sector="Technology"
        )

    # Replace entire geographic_area
    patch = PatchAssetMetadataRequest(
        geographic_area={"USA": Decimal("0.7"), "FRA": Decimal("0.3")}
        )

    updated = AssetMetadataService.apply_partial_update(current, patch)
    assert updated.geographic_area == {
        "USA": Decimal("0.7000"),
        "FRA": Decimal("0.3000")
        }
    # ITA is removed (full replace, not merge)
    assert "ITA" not in updated.geographic_area
    assert updated.sector == "Technology"  # Unchanged


def test_apply_partial_update_invalid_geo_area_raises():
    """Test that invalid geographic_area raises ValueError."""
    current = ClassificationParamsModel(investment_type="stock")
    patch = PatchAssetMetadataRequest(
        geographic_area={"INVALID": Decimal("1.0")}
        )

    with pytest.raises(ValueError):
        AssetMetadataService.apply_partial_update(current, patch)


def test_merge_provider_metadata():
    """Test merging provider-fetched metadata with current metadata."""
    current = ClassificationParamsModel(
        investment_type="stock",
        short_description="User description"
        )

    provider_data = {
        "investment_type": "etf",  # Provider overrides
        "sector": "Technology"  # Provider adds new field
        }

    merged = AssetMetadataService.merge_provider_metadata(current, provider_data)
    assert merged.investment_type == "etf"  # Provider wins
    assert merged.sector == "Technology"  # Added by provider
    assert merged.short_description == "User description"  # Unchanged
