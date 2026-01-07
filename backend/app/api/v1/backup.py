"""
Backup/Export API Endpoints (Placeholder).

These endpoints are placeholders for future functionality:
- Export portfolio data to JSON/CSV
- Restore data from backup

Status: 501 Not Implemented
"""
from enum import Enum
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

backup_router = APIRouter(
    prefix="/backup",
    tags=["Backup & Export"],
    )


# =============================================================================
# SCHEMAS
# =============================================================================

class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    SQLITE = "sqlite"  # Full database backup


class ExportScope(str, Enum):
    """What to include in export."""
    ALL = "all"
    TRANSACTIONS = "transactions"
    ASSETS = "assets"
    BROKERS = "brokers"
    SETTINGS = "settings"


class ExportRequest(BaseModel):
    """Request for data export."""
    format: ExportFormat = ExportFormat.JSON
    scope: List[ExportScope] = [ExportScope.ALL]
    include_price_history: bool = False  # Can be large
    broker_ids: Optional[List[int]] = None  # Filter by broker (None = all)


class ExportResponse(BaseModel):
    """Response with export file info."""
    download_url: str
    filename: str
    size_bytes: int
    expires_at: str  # ISO datetime


class RestoreRequest(BaseModel):
    """Request to restore from backup."""
    file_id: str  # UUID of uploaded backup file
    overwrite_existing: bool = False  # If true, replaces existing data


class RestoreResponse(BaseModel):
    """Response from restore operation."""
    success: bool
    restored_count: dict  # e.g., {"brokers": 2, "assets": 50, "transactions": 1000}
    warnings: List[str] = []


# =============================================================================
# ENDPOINTS
# =============================================================================

@backup_router.post("/export", response_model=ExportResponse)
async def export_data(request: ExportRequest):
    """
    Export portfolio data to file.

    **Supported Formats:**
    - `json`: Human-readable JSON file
    - `csv`: Multiple CSV files in ZIP archive
    - `sqlite`: Full SQLite database file

    **Scope Options:**
    - `all`: Export everything
    - `transactions`: Only transactions
    - `assets`: Only assets and metadata
    - `brokers`: Only broker definitions
    - `settings`: Only user settings

    **Note:** This endpoint is not yet implemented.
    """
    raise HTTPException(
        status_code=501,
        detail="Export functionality is not yet implemented. Coming soon!"
        )


@backup_router.post("/restore", response_model=RestoreResponse)
async def restore_data(request: RestoreRequest):
    """
    Restore portfolio data from backup file.

    **Important:**
    - If `overwrite_existing=False` (default), only imports new data
    - If `overwrite_existing=True`, replaces all existing data

    **Supported Formats:**
    - JSON export files created by `/export`
    - SQLite database files

    **Note:** This endpoint is not yet implemented.
    """
    raise HTTPException(
        status_code=501,
        detail="Restore functionality is not yet implemented. Coming soon!"
        )


@backup_router.get("/formats")
async def list_export_formats():
    """
    List available export formats.

    Returns information about each supported format.
    """
    return {
        "formats": [
            {
                "code": "json",
                "name": "JSON Export",
                "description": "Human-readable JSON file with all data",
                "extension": ".json",
                "available": False  # Not yet implemented
                },
            {
                "code": "csv",
                "name": "CSV Archive",
                "description": "ZIP file containing CSV files for each table",
                "extension": ".zip",
                "available": False
                },
            {
                "code": "sqlite",
                "name": "SQLite Database",
                "description": "Full database backup as SQLite file",
                "extension": ".db",
                "available": False
                }
            ]
        }


@backup_router.get("/status")
async def backup_status():
    """
    Get backup/export system status.

    Returns current implementation status.
    """
    return {
        "status": "placeholder",
        "message": "Backup/Export functionality is planned for a future release",
        "implemented_endpoints": [
            "/backup/formats",
            "/backup/status"
            ],
        "planned_endpoints": [
            "/backup/export",
            "/backup/restore"
            ]
        }
