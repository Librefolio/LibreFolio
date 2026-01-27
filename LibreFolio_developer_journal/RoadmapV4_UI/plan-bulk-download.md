# Piano Implementazione Bulk Download

**Data**: 26 Gennaio 2026  
**Status**: 📋 PLANNED  
**Priorità**: Media  
**Dipendenze**: Nessuna  

---

## Problema

Attualmente il download multiplo dalla selezione tabella scarica i file singolarmente perché:
- `GET /api/v1/uploads/file/{file_id}` - accetta solo 1 file
- `GET /api/v1/brokers/import/files/{file_id}/download` - accetta solo 1 file

Questo crea una pessima UX quando l'utente seleziona N file e ne scarica N separatamente.

---

## Soluzione Proposta

### Nuovi Endpoint

#### 1. Uploads Bulk Download
```
POST /api/v1/uploads/bulk-download
```

**Body**:
```json
{
  "file_ids": ["uuid1", "uuid2", "uuid3"],
  "archive_name": "my-files",
  "format": "zip"  // "zip" | "tar" | "tar.gz"
}
```

**Response**: `application/octet-stream` (file binario)

**Headers Response**:
```
Content-Type: application/zip
Content-Disposition: attachment; filename="my-files.zip"
```

#### 2. BRIM Bulk Download
```
POST /api/v1/brokers/import/bulk-download
```

**Body**:
```json
{
  "file_ids": ["uuid1", "uuid2", "uuid3"],
  "archive_name": "broker-reports",
  "format": "zip"
}
```

**Response**: Identica struttura

---

## Architettura

### Nuovo Service Condiviso

**File**: `backend/app/services/archive_service.py`

```python
"""
Archive creation service for bulk file downloads.
Supports zip, tar, and tar.gz formats.
"""

import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import List, Literal, Tuple
from fastapi.responses import StreamingResponse
import asyncio
from concurrent.futures import ThreadPoolExecutor

ArchiveFormat = Literal["zip", "tar", "tar.gz"]

class ArchiveService:
    """Service for creating downloadable archives from multiple files."""
    
    SUPPORTED_FORMATS = {"zip", "tar", "tar.gz"}
    
    @staticmethod
    def get_content_type(format: ArchiveFormat) -> str:
        """Get MIME type for archive format."""
        return {
            "zip": "application/zip",
            "tar": "application/x-tar",
            "tar.gz": "application/gzip"
        }[format]
    
    @staticmethod
    def get_extension(format: ArchiveFormat) -> str:
        """Get file extension for archive format."""
        return {
            "zip": ".zip",
            "tar": ".tar",
            "tar.gz": ".tar.gz"
        }[format]
    
    @staticmethod
    def create_archive_sync(
        files: List[Tuple[Path, str]],  # (path, name_in_archive)
        format: ArchiveFormat,
        output_path: Path
    ) -> None:
        """
        Create archive synchronously (run in executor).
        
        Args:
            files: List of (file_path, archive_name) tuples
            format: Archive format
            output_path: Where to save the archive
        """
        if format == "zip":
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path, archive_name in files:
                    zf.write(file_path, archive_name)
        elif format == "tar":
            with tarfile.open(output_path, 'w') as tf:
                for file_path, archive_name in files:
                    tf.add(file_path, archive_name)
        elif format == "tar.gz":
            with tarfile.open(output_path, 'w:gz') as tf:
                for file_path, archive_name in files:
                    tf.add(file_path, archive_name)
    
    @classmethod
    async def create_streaming_archive(
        cls,
        files: List[Tuple[Path, str]],
        format: ArchiveFormat,
        archive_name: str
    ) -> StreamingResponse:
        """
        Create archive and return as streaming response.
        Archive is deleted after streaming completes.
        
        Args:
            files: List of (file_path, archive_name) tuples
            format: Archive format (zip, tar, tar.gz)
            archive_name: Base name for the archive file
            
        Returns:
            StreamingResponse with the archive content
        """
        # Create temp file for archive
        extension = cls.get_extension(format)
        temp_dir = tempfile.mkdtemp()
        archive_path = Path(temp_dir) / f"{archive_name}{extension}"
        
        # Create archive in executor (non-blocking)
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(
                executor,
                cls.create_archive_sync,
                files,
                format,
                archive_path
            )
        
        # Stream and cleanup
        async def iterfile():
            try:
                with open(archive_path, 'rb') as f:
                    while chunk := f.read(65536):  # 64KB chunks
                        yield chunk
            finally:
                # Cleanup temp files
                archive_path.unlink(missing_ok=True)
                Path(temp_dir).rmdir()
        
        return StreamingResponse(
            iterfile(),
            media_type=cls.get_content_type(format),
            headers={
                "Content-Disposition": f'attachment; filename="{archive_name}{extension}"'
            }
        )
```

---

## Dipendenze Python

### Già Incluse in Python Standard Library
- `zipfile` - Per creare archivi ZIP
- `tarfile` - Per creare archivi TAR e TAR.GZ
- `tempfile` - Per file temporanei

### Nessuna Nuova Dipendenza Richiesta ✅

Python fornisce tutto ciò che serve nella standard library. Non è necessario aggiungere dipendenze a `Pipfile`.

---

## Schema Request/Response

**File**: `backend/app/schemas/common.py` (o nuovo file)

```python
from pydantic import BaseModel, field_validator
from typing import List, Literal

class BulkDownloadRequest(BaseModel):
    """Request body for bulk download endpoints."""
    file_ids: List[str]
    archive_name: str = "download"
    format: Literal["zip", "tar", "tar.gz"] = "zip"
    
    @field_validator('file_ids')
    @classmethod
    def validate_file_ids(cls, v):
        if len(v) == 0:
            raise ValueError("At least one file_id is required")
        if len(v) > 100:
            raise ValueError("Maximum 100 files per download")
        return v
    
    @field_validator('archive_name')
    @classmethod
    def validate_archive_name(cls, v):
        # Sanitize filename
        import re
        sanitized = re.sub(r'[^\w\-]', '_', v)
        return sanitized[:100]  # Max 100 chars
```

---

## Endpoint Implementation

### Uploads Bulk Download

**File**: `backend/app/api/v1/uploads.py`

```python
@router.post("/bulk-download")
async def bulk_download(
    request: BulkDownloadRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Download multiple files as a compressed archive.
    
    Supports formats: zip, tar, tar.gz
    Maximum 100 files per request.
    """
    # Collect valid files
    files: List[Tuple[Path, str]] = []
    for file_id in request.file_ids:
        file_path = get_upload_path(file_id)
        if not file_path:
            continue  # Skip missing files
        
        info = get_upload_info(file_id)
        filename = info.original_name if info else file_path.name
        files.append((file_path, filename))
    
    if not files:
        raise HTTPException(status_code=404, detail="No valid files found")
    
    return await ArchiveService.create_streaming_archive(
        files=files,
        format=request.format,
        archive_name=request.archive_name
    )
```

### BRIM Bulk Download

**File**: `backend/app/api/v1/brokers.py`

```python
@brim_router.post("/bulk-download")
async def brim_bulk_download(
    request: BulkDownloadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Download multiple BRIM files as a compressed archive.
    
    Only files the user has access to (via broker permissions) are included.
    """
    broker_service = BrokerService(session)
    files: List[Tuple[Path, str]] = []
    
    for file_id in request.file_ids:
        file_info = brim_provider.get_file_info(file_id)
        if not file_info:
            continue
        
        # Check access
        if file_info.target_broker_id and not current_user.is_superuser:
            role = await broker_service._check_user_access(
                file_info.target_broker_id, current_user.id
            )
            if role is None:
                continue  # Skip files without access
        
        file_path = brim_provider.get_file_path(file_id)
        if file_path and file_path.exists():
            files.append((file_path, file_info.filename))
    
    if not files:
        raise HTTPException(status_code=404, detail="No accessible files found")
    
    return await ArchiveService.create_streaming_archive(
        files=files,
        format=request.format,
        archive_name=request.archive_name
    )
```

---

## Frontend Integration

### Requisiti UX

Quando l'utente seleziona file e clicca "Download":

1. **Mostra modal di conferma** simile a quello della delete
2. **Lista file selezionati** (se 1 file: mostrata aperta, se >1: collassabile)
3. **Selettore formato compressione**:
   - `Singoli file` - scarica ciascun file separatamente
   - `ZIP` - compressione standard (~30-50% riduzione)
   - `TAR` - nessuna compressione, solo raggruppamento
   - `7-Zip` - massima compressione (~50-70% riduzione)
4. **Due pulsanti**: "Annulla" | "Scarica (xx KB)"
5. **Stima dimensione**: 
   - Singoli/TAR: somma size_bytes
   - ZIP: size_bytes * 0.6 (stima)
   - 7-Zip: size_bytes * 0.4 (stima)

### Schema aggiornato Backend

```typescript
// Request
{
  "file_ids": ["uuid1", "uuid2"],
  "archive_name": "download",
  "format": "zip" | "tar" | "tar.gz" | "7z" | "individual"
}

// Response per format="individual": 
// 404 Not Implemented (frontend gestisce download singoli)
```

### Componente Modal

**File**: `frontend/src/lib/components/files/DownloadModal.svelte`

```svelte
<script lang="ts">
  interface Props {
    files: Array<{ id: string; name: string; size_bytes: number }>;
    onConfirm: (format: DownloadFormat) => void;
    onCancel: () => void;
  }
  
  type DownloadFormat = 'individual' | 'zip' | 'tar' | '7z';
  
  let selectedFormat: DownloadFormat = $state('zip');
  
  const compressionRatios = {
    individual: 1.0,
    tar: 1.0,
    zip: 0.6,
    '7z': 0.4
  };
  
  let estimatedSize = $derived(() => {
    const totalBytes = files.reduce((sum, f) => sum + f.size_bytes, 0);
    return Math.round(totalBytes * compressionRatios[selectedFormat]);
  });
  
  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  }
</script>

<!-- Modal UI con lista file, selector formato, bottoni -->
```

### File API Helper

**File**: `frontend/src/lib/api/downloads.ts`

```typescript
export type DownloadFormat = 'individual' | 'zip' | 'tar' | '7z';

export async function downloadFiles(
  fileIds: string[],
  archiveName: string,
  format: DownloadFormat,
  type: 'static' | 'brim'
): Promise<void> {
  if (format === 'individual') {
    // Download each file individually with delay
    for (let i = 0; i < fileIds.length; i++) {
      setTimeout(() => {
        const url = type === 'static' 
          ? `/api/v1/uploads/file/${fileIds[i]}?download=true`
          : `/api/v1/brokers/import/files/${fileIds[i]}/download`;
        const a = document.createElement('a');
        a.href = url;
        a.download = '';
        a.click();
      }, i * 300); // 300ms delay between downloads
    }
    return;
  }
  
  // Bulk download
  const endpoint = type === 'static' 
    ? '/api/v1/uploads/bulk-download'
    : '/api/v1/brokers/import/bulk-download';
    
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_ids: fileIds, archive_name: archiveName, format })
  });
  
  if (!response.ok) throw new Error('Download failed');
  
  const blob = await response.blob();
  const ext = format === '7z' ? '7z' : format;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${archiveName}.${ext}`;
  a.click();
  URL.revokeObjectURL(url);
}
```

### Integrazione DataTable Actions

Modificare `FilesTable.svelte` per aprire il modal invece di scaricare direttamente.

---

## Analisi Compressibilità (Future Enhancement)

### Idea: Pre-calcolo in Upload

Durante l'upload, il backend potrebbe:
1. Analizzare i primi N KB del file
2. Calcolare entropia/compressibilità stimata
3. Salvare nel JSON metadata: `"compression_ratio_estimate": 0.45`

**Pro**: Stime più accurate nel frontend
**Contro**: Overhead in upload, complessità

**Raccomandazione**: Rimandare a futuro enhancement. Per ora usare stime statiche per tipo MIME:
- Text/CSV: 0.3 (molto comprimibile)
- JSON: 0.35
- Images: 0.95 (già compressi)
- Unknown: 0.6 (media)

---

## Architettura Storage Unificata (Future Refactor)

### Problema Attuale

I due sottosistemi (uploads e BRIM) hanno codice duplicato per:
- Salvataggio file su disco
- Creazione JSON metadata
- Lettura/parsing metadata

### Soluzione Proposta

Creare `backend/app/services/file_storage_service.py`:

```python
class FileStorageService:
    """
    Unified file storage service for uploads and BRIM.
    Handles file + metadata JSON pairs.
    """
    
    async def save_file(
        self,
        stream: BinaryIO,
        original_name: str,
        base_path: Path,
        common_metadata: dict,
        specific_metadata: dict
    ) -> str:
        """
        Save file and create associated JSON.
        
        Args:
            stream: File binary stream
            original_name: Original filename
            base_path: Directory to save files
            common_metadata: Shared fields (size, content_type, uploaded_at, etc)
            specific_metadata: Type-specific fields under 'details' key
            
        Returns:
            Generated file UUID
        """
        file_id = str(uuid.uuid4())
        extension = Path(original_name).suffix
        
        # Save binary file
        file_path = base_path / f"{file_id}{extension}"
        with open(file_path, 'wb') as f:
            while chunk := stream.read(65536):
                f.write(chunk)
        
        # Create metadata JSON
        metadata = {
            "file_id": file_id,
            "original_name": original_name,
            "stored_name": file_path.name,
            "size_bytes": file_path.stat().st_size,
            "uploaded_at": datetime.utcnow().isoformat(),
            **common_metadata,
            "details": specific_metadata
        }
        
        json_path = base_path / f"{file_id}.json"
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return file_id
```

**Struttura JSON Unificata**:
```json
{
  "file_id": "uuid",
  "original_name": "report.csv",
  "stored_name": "uuid.csv",
  "size_bytes": 12345,
  "uploaded_at": "2026-01-26T12:00:00Z",
  "content_type": "text/csv",
  "details": {
    // Per uploads:
    "uploaded_by_user_id": 1
    
    // Per BRIM:
    "target_broker_id": 5,
    "status": "parsed",
    "compatible_plugins": ["broker_generic_csv"]
  }
}
```

**Raccomandazione**: Implementare questo refactor insieme o subito dopo il bulk download, per evitare duplicazioni future.

---

## Dipendenze Python

### Per ZIP e TAR - Standard Library ✅
- `zipfile` - Per creare archivi ZIP
- `tarfile` - Per creare archivi TAR e TAR.GZ
- `tempfile` - Per file temporanei

### Per 7-Zip - Nuova Dipendenza
```
py7zr>=0.20.0
```

Da aggiungere a `Pipfile`:
```toml
[packages]
py7zr = "*"
```

---

## Test Plan

### API Tests

**File**: `backend/test_scripts/test_api/test_uploads_api.py`

```python
class TestBulkDownload:
    async def test_bulk_download_zip(self, test_server):
        """BD-001: Download multiple files as ZIP."""
        
    async def test_bulk_download_tar_gz(self, test_server):
        """BD-002: Download as tar.gz."""
    
    async def test_bulk_download_7z(self, test_server):
        """BD-003: Download as 7z."""
        
    async def test_bulk_download_empty_list(self, test_server):
        """BD-004: 400 for empty file list."""
        
    async def test_bulk_download_max_files(self, test_server):
        """BD-005: 400 when exceeding 100 files."""
        
    async def test_bulk_download_skips_missing(self, test_server):
        """BD-006: Skips missing files, downloads available ones."""
```

**File**: `backend/test_scripts/test_api/test_brim_api.py`

```python
class TestBRIMBulkDownload:
    async def test_bulk_download_respects_permissions(self, test_server):
        """BD-007: Only downloads files user has access to."""
        
    async def test_bulk_download_broker_files(self, test_server):
        """BD-008: Downloads broker files as archive."""
```

---

## Timeline Stimata

| Task | Stima |
|------|-------|
| ArchiveService (con 7z) | 1.5h |
| Schema BulkDownloadRequest | 30m |
| Uploads endpoint | 1h |
| BRIM endpoint | 1h |
| DownloadModal.svelte | 2h |
| downloads.ts helper | 30m |
| Integrazione FilesTable | 1h |
| Tests backend | 1.5h |
| **Totale** | **9h** |

---

## Checklist

### Backend
- [ ] Aggiungere `py7zr` a Pipfile
- [ ] Creare `backend/app/services/archive_service.py`
- [ ] Aggiungere `BulkDownloadRequest` schema
- [ ] Implementare `POST /api/v1/uploads/bulk-download`
- [ ] Implementare `POST /api/v1/brokers/import/bulk-download`
- [ ] Scrivere test API

### Frontend
- [ ] Creare `DownloadModal.svelte`
- [ ] Creare `frontend/src/lib/api/downloads.ts`
- [ ] Aggiornare FilesTable per usare modal
- [ ] Aggiungere traduzioni (it, en, fr, es)

### Future Enhancement
- [ ] FileStorageService unificato
- [ ] Pre-calcolo compression ratio in upload
