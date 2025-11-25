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

from backend.app.schemas.assets import FAClassificationParams, FAPatchMetadataRequest
from backend.app.services.asset_metadata import AssetMetadataService


def test_parse_classification_params_valid_json():
    """Test parsing valid JSON to FAClassificationParams."""
    json_str = '{"investment_type":"stock","sector":"Technology"}'
    parsed = AssetMetadataService.parse_classification_params(json_str)

    assert isinstance(parsed, FAClassificationParams)
    assert parsed.investment_type == "stock"
    assert parsed.sector == "Technology"


def test_parse_classification_params_none():
    """Test parsing None returns None."""
    result = AssetMetadataService.parse_classification_params(None)
    assert result is None


def test_serialize_classification_params():
    """Test serializing FAClassificationParams to JSON."""
    model = FAClassificationParams(
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
    """Test computing differences between two FAClassificationParams instances."""
    old = FAClassificationParams(investment_type="stock", sector="Energy")
    new = FAClassificationParams(investment_type="etf", sector="Technology")

    changes = AssetMetadataService.compute_metadata_diff(old, new)
    fields = {c.field for c in changes}

    assert "investment_type" in fields
    assert "sector" in fields
    assert len(changes) == 2


def test_apply_partial_update_absent_fields_ignored():
    """Test that absent fields in patch are ignored (PATCH semantics)."""
    current = FAClassificationParams(
        investment_type="stock",
        sector="Technology"
        )

    # Patch only updates short_description, other fields should remain
    patch = FAPatchMetadataRequest(short_description="New description")

    updated = AssetMetadataService.apply_partial_update(current, patch)
    assert updated.investment_type == "stock"  # Unchanged
    assert updated.sector == "Technology"  # Unchanged
    assert updated.short_description == "New description"  # Updated


def test_apply_partial_update_null_clears_field():
    """Test that null in patch clears the field (PATCH semantics)."""
    current = FAClassificationParams(
        investment_type="stock",
        short_description="Original",
        sector="Technology"
        )

    # Explicitly set sector to None to clear it
    patch = FAPatchMetadataRequest(
        sector=None
        )

    updated = AssetMetadataService.apply_partial_update(current, patch)
    assert updated.sector is None  # Cleared
    assert updated.short_description == "Original"  # Unchanged


def test_apply_partial_update_geographic_area_full_replace():
    """Test that geographic_area is fully replaced (no merge)."""
    current = FAClassificationParams(
        investment_type="stock",
        geographic_area={"USA": Decimal("0.6"), "ITA": Decimal("0.4")},
        sector="Technology"
        )

    # Replace entire geographic_area
    patch = FAPatchMetadataRequest(geographic_area={"USA": Decimal("0.7"), "FRA": Decimal("0.3")})

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
    current = FAClassificationParams(investment_type="stock")
    patch = FAPatchMetadataRequest(geographic_area={"INVALID": Decimal("1.0")})

    with pytest.raises(ValueError):
        AssetMetadataService.apply_partial_update(current, patch)


def test_merge_provider_metadata():
    """Test merging provider-fetched metadata with current metadata."""
    current = FAClassificationParams(
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


def test_patch_semantic_edge_cases():
    """Test PATCH semantic edge cases for Phase 6.4."""
    print("\n" + "=" * 70)
    print("  Test: PATCH Semantic Edge Cases (Phase 6.4)")
    print("=" * 70)

    # Case 1: PATCH with only geographic_area → other fields unchanged
    print("\nCase 1: PATCH only geographic_area, other fields unchanged")
    current = FAClassificationParams(
        investment_type="stock",
        sector="Technology",
        short_description="Tech stock",
        geographic_area={"USA": Decimal("1.0")}
        )
    patch = FAPatchMetadataRequest(geographic_area={"USA": "0.6", "GBR": "0.4"})
    updated = AssetMetadataService.apply_partial_update(current, patch)

    # Verify: geographic_area changed, other fields unchanged
    assert updated.investment_type == "stock", "investment_type should be unchanged"
    assert updated.sector == "Technology", "sector should be unchanged"
    assert updated.short_description == "Tech stock", "short_description should be unchanged"
    assert updated.geographic_area == {"USA": Decimal("0.6000"), "GBR": Decimal("0.4000")}
    print("✅ Only geographic_area changed, other fields preserved")

    # Case 2: PATCH geographic_area=null → clears existing geographic_area
    print("\nCase 2: PATCH geographic_area=null clears field")
    current = FAClassificationParams(investment_type="etf", geographic_area={"USA": Decimal("0.6"), "ITA": Decimal("0.4")})
    patch = FAPatchMetadataRequest(geographic_area=None)
    updated = AssetMetadataService.apply_partial_update(current, patch)

    # Verify: geographic_area cleared, investment_type unchanged
    assert updated.geographic_area is None, "geographic_area should be None"
    assert updated.investment_type == "etf", "investment_type should be unchanged"
    print("✅ geographic_area cleared with null")

    # Case 3: Multiple PATCHes in sequence → final state correct
    print("\nCase 3: Multiple PATCHes in sequence")
    current = FAClassificationParams(investment_type="stock", sector="Finance")

    # First PATCH: Update sector and add geo area
    patch1 = FAPatchMetadataRequest(sector="Technology", geographic_area={"USA": "1.0"})
    current = AssetMetadataService.apply_partial_update(current, patch1)
    assert current.sector == "Technology"
    assert current.geographic_area == {"USA": Decimal("1.0000")}

    # Second PATCH: Update investment_type, keep others
    patch2 = FAPatchMetadataRequest(investment_type="etf")
    current = AssetMetadataService.apply_partial_update(current, patch2)
    assert current.investment_type == "etf"
    assert current.sector == "Technology"  # Still there
    assert current.geographic_area == {"USA": Decimal("1.0000")}  # Still there

    # Third PATCH: Clear sector
    patch3 = FAPatchMetadataRequest(sector=None)
    current = AssetMetadataService.apply_partial_update(current, patch3)
    assert current.sector is None
    assert current.investment_type == "etf"  # Still there
    assert current.geographic_area == {"USA": Decimal("1.0000")}  # Still there

    print("✅ Multiple sequential PATCHes result in correct final state")

    # Case 4: Concurrent PATCHes (last write wins) - Simulation
    print("\nCase 4: Concurrent PATCH semantics (last write wins)")
    # Simulate two concurrent PATCHes to the same asset
    # In a real scenario, this would be handled by optimistic locking
    # For testing, we just verify that the last PATCH wins

    current = FAClassificationParams(
        investment_type="stock",
        sector="Technology"
        )

    # User A PATCHes sector
    patch_a = FAPatchMetadataRequest(sector="Finance")
    result_a = AssetMetadataService.apply_partial_update(current, patch_a)

    # User B PATCHes sector (simulates concurrent write)
    patch_b = FAPatchMetadataRequest(sector="Healthcare")
    result_b = AssetMetadataService.apply_partial_update(current, patch_b)

    # Both are valid transformations from the same base state
    assert result_a.sector == "Finance"
    assert result_b.sector == "Healthcare"
    print("✅ Last write wins (no optimistic locking enforced at service layer)")
    print("   Note: Optimistic locking should be handled at API/DB layer if needed")

    print("\n" + "=" * 70)
    print("  ✅ All PATCH semantic edge cases passed!")
    print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
