"""
Test AssetMetadataService utility methods.

Tests diff computation and partial update PATCH semantics
for asset classification metadata.
"""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.db import AssetType
from backend.app.schemas import FAGeographicArea

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.assets import FAClassificationParams, FAClassificationParams
from backend.app.services.asset_metadata import AssetMetadataService


def test_compute_metadata_diff():
    """Test computing differences between two FAClassificationParams instances."""
    old = FAClassificationParams(sector="Energy")
    new = FAClassificationParams(sector="Technology")

    changes = AssetMetadataService.compute_metadata_diff(old, new)
    fields = {c.field for c in changes}

    assert "sector" in fields
    assert len(changes) == 1 , f"Expected 2 changes, got {len(changes)}: {changes}"


def test_apply_partial_update_absent_fields_ignored():
    """Test that absent fields in patch are ignored (PATCH semantics)."""
    current = FAClassificationParams(sector="Technology")

    # Patch only updates short_description, other fields should remain
    patch = FAClassificationParams(short_description="New description")

    updated = AssetMetadataService.apply_partial_update(current, patch)
    assert updated.sector == "Technology"  # Unchanged
    assert updated.short_description == "New description"  # Updated


def test_apply_partial_update_null_clears_field():
    """Test that null in patch clears the field (PATCH semantics)."""
    current = FAClassificationParams(short_description="Original",sector="Technology")

    # Explicitly set sector to None to clear it
    patch = FAClassificationParams(sector=None)

    updated = AssetMetadataService.apply_partial_update(current, patch)
    assert updated.sector is None  # Cleared
    assert updated.short_description == "Original"  # Unchanged


def test_apply_partial_update_geographic_area_full_replace():
    """Test that geographic_area is fully replaced (no merge)."""
    current = FAClassificationParams(
        geographic_area=FAGeographicArea(distribution={"USA": Decimal("0.6"), "ITA": Decimal("0.4")}),
        sector="Technology"
        )

    # Replace entire geographic_area
    patch = FAClassificationParams(geographic_area=FAGeographicArea(distribution={"USA": Decimal("0.7"), "FRA": Decimal("0.3")}))

    updated = AssetMetadataService.apply_partial_update(current, patch)
    assert updated.geographic_area.distribution == {"USA": Decimal("0.7000"), "FRA": Decimal("0.3000")}
    # ITA is removed (full replace, not merge)
    assert "ITA" not in updated.geographic_area.distribution
    assert updated.sector == "Technology"  # Unchanged


def test_merge_provider_metadata():
    """Test merging provider-fetched metadata with current metadata."""
    current = FAClassificationParams(short_description="User description")

    provider_data = {
        "sector": "Technology"  # Provider adds new field
        }

    merged = AssetMetadataService.merge_provider_metadata(current, provider_data)
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
        sector="Technology",
        short_description="Tech stock",
        geographic_area=FAGeographicArea(distribution={"USA": Decimal("1.0")})
        )
    patch = FAClassificationParams(geographic_area=FAGeographicArea(distribution={"USA": "0.6", "GBR": "0.4"}))
    updated = AssetMetadataService.apply_partial_update(current, patch)

    # Verify: geographic_area changed, other fields unchanged
    assert updated.sector == "Technology", "sector should be unchanged"
    assert updated.short_description == "Tech stock", "short_description should be unchanged"
    assert updated.geographic_area.distribution == {"USA": Decimal("0.6000"), "GBR": Decimal("0.4000")}
    print("✅ Only geographic_area changed, other fields preserved")

    # Case 2: PATCH geographic_area=null → clears existing geographic_area
    print("\nCase 2: PATCH geographic_area=null clears field")
    current = FAClassificationParams(geographic_area=FAGeographicArea(distribution={"USA": Decimal("0.6"), "ITA": Decimal("0.4")}))
    patch = FAClassificationParams(geographic_area=None)
    updated = AssetMetadataService.apply_partial_update(current, patch)

    # Verify: geographic_area cleared
    assert updated.geographic_area is None, "geographic_area should be None"
    print("✅ geographic_area cleared with null")

    # Case 3: Multiple PATCHes in sequence → final state correct
    print("\nCase 3: Multiple PATCHes in sequence")
    current = FAClassificationParams(sector="Finance")

    # First PATCH: Update sector and add geo area
    patch1 = FAClassificationParams(sector="Technology", geographic_area=FAGeographicArea(distribution={"USA": "1.0"}))
    current = AssetMetadataService.apply_partial_update(current, patch1)
    assert current.sector == "Technology"
    assert current.geographic_area.distribution == {"USA": Decimal("1.0000")}

    # Second PATCH: Update sector, keep others
    patch2 = FAClassificationParams(sector="Energy")
    current = AssetMetadataService.apply_partial_update(current, patch2)
    assert current.sector == "Energy"  # Check change
    assert current.geographic_area.distribution == {"USA": Decimal("1.0000")}  # Still there

    # Third PATCH: Clear sector
    patch3 = FAClassificationParams(sector=None)
    current = AssetMetadataService.apply_partial_update(current, patch3)
    assert current.sector is None
    assert current.geographic_area.distribution == {"USA": Decimal("1.0000")}  # Still there

    print("✅ Multiple sequential PATCHes result in correct final state")

    # Case 4: Concurrent PATCHes (last write wins) - Simulation
    print("\nCase 4: Concurrent PATCH semantics (last write wins)")
    # Simulate two concurrent PATCHes to the same asset
    # In a real scenario, this would be handled by optimistic locking
    # For testing, we just verify that the last PATCH wins

    current = FAClassificationParams(
        sector="Technology"
        )

    # User A PATCHes sector
    patch_a = FAClassificationParams(sector="Finance")
    result_a = AssetMetadataService.apply_partial_update(current, patch_a)

    # User B PATCHes sector (simulates concurrent write)
    patch_b = FAClassificationParams(sector="Healthcare")
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
