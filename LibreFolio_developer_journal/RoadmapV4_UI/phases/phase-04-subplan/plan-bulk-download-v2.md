# Piano Bulk Download - v2

> **Data**: 26-01-2026  
> **Stato**: TODO  
> **Priorità**: Media  
> **Dipendenze**: Nessuna bloccante

## Obiettivo

Implementare il download multiplo di file (sia da static uploads che da broker reports) con supporto per:

- Download singoli file separati
- Download come archivio (tar, zip, 7z)
- Modal di selezione formato con preview dimensione

---

## Fase 1: Backend - Service Comune per Archivi

### 1.1 Dipendenze Python

Verifica dipendenze già presenti in Python standard library:

- `tarfile` - per .tar (built-in)
- `zipfile` - per .zip (built-in)
- `py7zr` - per .7z (**da aggiungere al Pipfile**)

```bash
pipenv install py7zr
```

### 1.2 Nuovo Service: `archive_service.py`

**File**: `backend/app/services/archive_service.py`

```python
"""
Archive Service - Common service for creating downloadable archives
"""
from pathlib import Path
from typing import List, Tuple, Literal, BinaryIO
import tarfile
import zipfile
import tempfile
import os

# Optional 7z support
try:
    import py7zr
    HAS_7Z = True
except ImportError:
    HAS_7Z = False

ArchiveFormat = Literal["none", "tar", "zip", "7z"]

class ArchiveService:
    """Service for creating archives from multiple files."""
    
    COMPRESSION_RATIOS = {
        "none": 1.0,   # No compression
        "tar": 1.0,    # No compression (just bundling)
        "zip": 0.6,    # ~40% compression for typical files
        "7z": 0.4,     # ~60% compression
    }
    
    @staticmethod
    def get_available_formats() -> List[str]:
        """Return list of available archive formats."""
        formats = ["none", "tar", "zip"]
        if HAS_7Z:
            formats.append("7z")
        return formats
    
    @staticmethod
    def estimate_size(total_bytes: int, format: ArchiveFormat) -> int:
        """Estimate archive size based on format compression ratio."""
        if format == "none":
            return total_bytes
        ratio = ArchiveService.COMPRESSION_RATIOS.get(format, 1.0)
        return int(total_bytes * ratio)
    
    @staticmethod
    def create_archive(
        files: List[Tuple[Path, str]],  # (source_path, archive_name)
        format: ArchiveFormat,
        archive_name: str
    ) -> Tuple[Path, str]:
        """
        Create an archive from multiple files.
        
        Args:
            files: List of (source_path, name_in_archive) tuples
            format: Archive format (tar, zip, 7z)
            archive_name: Base name for the archive (without extension)
            
        Returns:
            Tuple of (archive_path, content_type)
        """
        if format == "none":
            raise ValueError("Use direct download for single files")
            
        # Create temp file for archive
        suffix = f".{format}" if format != "tar" else ".tar"
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix, 
            delete=False,
            prefix=f"{archive_name}_"
        )
        temp_path = Path(temp_file.name)
        temp_file.close()
        
        try:
            if format == "tar":
                with tarfile.open(temp_path, "w") as tar:
                    for source, name in files:
                        tar.add(source, arcname=name)
                return temp_path, "application/x-tar"
                
            elif format == "zip":
                with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for source, name in files:
                        zf.write(source, arcname=name)
                return temp_path, "application/zip"
                
            elif format == "7z":
                if not HAS_7Z:
                    raise ValueError("7z format not available")
                with py7zr.SevenZipFile(temp_path, "w") as sz:
                    for source, name in files:
                        sz.write(source, arcname=name)
                return temp_path, "application/x-7z-compressed"
                
            else:
                raise ValueError(f"Unknown format: {format}")
                
        except Exception:
            # Cleanup on error
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    @staticmethod
    def cleanup_archive(archive_path: Path) -> None:
        """Delete temporary archive file."""
        if archive_path.exists():
            archive_path.unlink()
```

---

## Fase 2: Backend - Endpoint Bulk Download Uploads

### 2.1 Schema Request/Response

**File**: `backend/app/schemas/uploads.py` (aggiungere)

```python
from pydantic import BaseModel
from typing import List, Literal

class BulkDownloadRequest(BaseModel):
    """Request for bulk download."""
    file_ids: List[str]
    format: Literal["none", "tar", "zip", "7z"] = "zip"
    archive_name: str = "download"

class BulkDownloadInfo(BaseModel):
    """Info about bulk download before execution."""
    file_count: int
    total_bytes: int
    estimated_archive_bytes: int
    available_formats: List[str]
```

### 2.2 Endpoint: POST `/api/v1/uploads/bulk-download`

**File**: `backend/app/api/v1/uploads.py` (aggiungere)

```python
from fastapi.responses import FileResponse
from backend.app.services.archive_service import ArchiveService

@router.post("/bulk-download/info", response_model=BulkDownloadInfo)
async def bulk_download_info(
    request: BulkDownloadRequest,
    current_user: User = Depends(get_current_user),
):
    """Get info about bulk download (size estimates)."""
    files = []
    total_bytes = 0
    
    for file_id in request.file_ids:
        file_info = uploads_service.get_file(file_id, current_user.id)
        if file_info:
            files.append(file_info)
            total_bytes += file_info.size_bytes
    
    return BulkDownloadInfo(
        file_count=len(files),
        total_bytes=total_bytes,
        estimated_archive_bytes=ArchiveService.estimate_size(total_bytes, request.format),
        available_formats=ArchiveService.get_available_formats(),
    )

@router.post("/bulk-download")
async def bulk_download(
    background_tasks: BackgroundTasks,
    request: BulkDownloadRequest,
    current_user: User = Depends(get_current_user),
):
    """Download multiple files as archive or individually."""
    # Collect files
    files_to_download = []
    for file_id in request.file_ids:
        file_info = uploads_service.get_file(file_id, current_user.id)
        if not file_info:
            raise HTTPException(404, f"File not found: {file_id}")
        files_to_download.append((
            Path(file_info.stored_path),
            file_info.original_name
        ))
    
    if len(files_to_download) == 0:
        raise HTTPException(400, "No files to download")
    
    # Single file or "none" format - direct download
    if len(files_to_download) == 1 or request.format == "none":
        # Return first file (frontend handles multiple requests for "none")
        source, name = files_to_download[0]
        return FileResponse(
            source,
            filename=name,
            media_type="application/octet-stream"
        )
    
    # Create archive
    archive_path, content_type = ArchiveService.create_archive(
        files_to_download,
        request.format,
        request.archive_name
    )
    
    # Schedule cleanup after response
    background_tasks.add_task(ArchiveService.cleanup_archive, archive_path)
    
    extension = {"tar": ".tar", "zip": ".zip", "7z": ".7z"}[request.format]
    return FileResponse(
        archive_path,
        filename=f"{request.archive_name}{extension}",
        media_type=content_type
    )
```

---

## Fase 3: Backend - Endpoint Bulk Download BRIM

### 3.1 Schema (riusa da uploads o crea specifico)

Riusa `BulkDownloadRequest` e `BulkDownloadInfo` da uploads.

### 3.2 Endpoint: POST `/api/v1/brokers/import/bulk-download`

**File**: `backend/app/api/v1/brokers.py` (aggiungere al brim_router)

```python
@brim_router.post("/bulk-download/info", response_model=BulkDownloadInfo)
async def brim_bulk_download_info(
    request: BulkDownloadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """Get info about BRIM bulk download."""
    total_bytes = 0
    file_count = 0
    
    for file_id in request.file_ids:
        file_info = brim_provider.get_file_info(file_id)
        if file_info:
            # Verify access
            if file_info.target_broker_id:
                broker_service = BrokerService(session)
                role = await broker_service.get_user_role(
                    file_info.target_broker_id, current_user.id
                )
                if role is None and not current_user.is_superuser:
                    continue
            total_bytes += file_info.size_bytes or 0
            file_count += 1
    
    return BulkDownloadInfo(
        file_count=file_count,
        total_bytes=total_bytes,
        estimated_archive_bytes=ArchiveService.estimate_size(total_bytes, request.format),
        available_formats=ArchiveService.get_available_formats(),
    )

@brim_router.post("/bulk-download")
async def brim_bulk_download(
    background_tasks: BackgroundTasks,
    request: BulkDownloadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """Download multiple BRIM files as archive."""
    files_to_download = []
    broker_service = BrokerService(session)
    
    for file_id in request.file_ids:
        file_info = brim_provider.get_file_info(file_id)
        if not file_info:
            raise HTTPException(404, f"File not found: {file_id}")
        
        # Verify access
        if file_info.target_broker_id:
            role = await broker_service.get_user_role(
                file_info.target_broker_id, current_user.id
            )
            if role is None and not current_user.is_superuser:
                raise HTTPException(403, f"Access denied to file: {file_id}")
        
        file_path = brim_provider.get_file_path(file_id)
        if file_path and file_path.exists():
            files_to_download.append((file_path, file_info.filename))
    
    if not files_to_download:
        raise HTTPException(400, "No accessible files to download")
    
    # Single file or "none" - direct download
    if len(files_to_download) == 1 or request.format == "none":
        source, name = files_to_download[0]
        return FileResponse(source, filename=name)
    
    # Create archive
    archive_path, content_type = ArchiveService.create_archive(
        files_to_download, request.format, request.archive_name
    )
    
    background_tasks.add_task(ArchiveService.cleanup_archive, archive_path)
    
    extension = {"tar": ".tar", "zip": ".zip", "7z": ".7z"}[request.format]
    return FileResponse(
        archive_path,
        filename=f"{request.archive_name}{extension}",
        media_type=content_type
    )
```

---

## Fase 4: Backend - Test API

### 4.1 Test Uploads Bulk Download

**File**: `backend/test_scripts/test_api/test_uploads_api.py` (aggiungere)

```python
class TestBulkDownload:
    """Test bulk download functionality."""
    
    @pytest.mark.asyncio
    async def test_bulk_download_info(self, test_server):
        """Test getting bulk download info."""
        # Upload 2 files, then get info
        ...
    
    @pytest.mark.asyncio  
    async def test_bulk_download_zip(self, test_server):
        """Test downloading as ZIP archive."""
        ...
    
    @pytest.mark.asyncio
    async def test_bulk_download_tar(self, test_server):
        """Test downloading as TAR archive."""
        ...
    
    @pytest.mark.asyncio
    async def test_bulk_download_single_file(self, test_server):
        """Test bulk download with single file returns direct file."""
        ...
    
    @pytest.mark.asyncio
    async def test_bulk_download_none_format(self, test_server):
        """Test 'none' format returns first file."""
        ...
```

### 4.2 Test BRIM Bulk Download

**File**: `backend/test_scripts/test_api/test_brim_api.py` (aggiungere)

```python
class TestBRIMBulkDownload:
    """Test BRIM bulk download with access control."""
    
    @pytest.mark.asyncio
    async def test_bulk_download_own_files(self, test_server):
        """User can bulk download own broker files."""
        ...
    
    @pytest.mark.asyncio
    async def test_bulk_download_access_denied(self, test_server):
        """User cannot download files from inaccessible broker."""
        ...
```

---

## Fase 5: Frontend - Modal Download Multiplo

### 5.1 Componente: `BulkDownloadModal.svelte`

**File**: `frontend/src/lib/components/ui/BulkDownloadModal.svelte`

Features:

- Lista file selezionati (foldable se >1, aperta se ==1)
- Selettore formato: "Singoli file", "TAR", "ZIP", "7ZIP"
- Mostra dimensione stimata: "Scarica (xx KB)"
- Bottoni: "Annulla" | "Scarica"

```svelte
<script lang="ts">
    import { t } from '$lib/i18n';
    import { api } from '$lib/api';
    import { X, ChevronDown, ChevronUp, Download, Archive } from 'lucide-svelte';
    import { fade, scale } from 'svelte/transition';

    interface FileInfo {
        id: string;
        name: string;
        size: number;
    }

    interface Props {
        files: FileInfo[];
        endpoint: 'uploads' | 'brim';
        onClose: () => void;
        onDownload: () => void;
    }

    let { files, endpoint, onClose, onDownload }: Props = $props();

    let format = $state<'none' | 'tar' | 'zip' | '7z'>('zip');
    let archiveName = $state('download');
    let showFileList = $state(files.length === 1);
    let loading = $state(false);

    const totalBytes = $derived(files.reduce((sum, f) => sum + f.size, 0));
    
    const compressionRatios = { none: 1.0, tar: 1.0, zip: 0.6, '7z': 0.4 };
    const estimatedBytes = $derived(
        format === 'none' ? totalBytes : Math.round(totalBytes * compressionRatios[format])
    );

    function formatBytes(bytes: number): string {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    async function handleDownload() {
        loading = true;
        try {
            const baseUrl = endpoint === 'uploads' 
                ? '/uploads/bulk-download'
                : '/brokers/import/bulk-download';

            if (format === 'none') {
                // Download each file separately
                for (const file of files) {
                    const singleEndpoint = endpoint === 'uploads'
                        ? `/uploads/${file.id}?download=true`
                        : `/brokers/import/files/${file.id}/download`;
                    
                    // Trigger download
                    const link = document.createElement('a');
                    link.href = `/api/v1${singleEndpoint}`;
                    link.download = file.name;
                    link.click();
                }
            } else {
                // Download as archive
                const response = await api.postBlob(baseUrl, {
                    file_ids: files.map(f => f.id),
                    format,
                    archive_name: archiveName,
                });
                
                // Trigger download
                const url = URL.createObjectURL(response);
                const link = document.createElement('a');
                link.href = url;
                link.download = `${archiveName}.${format}`;
                link.click();
                URL.revokeObjectURL(url);
            }
            
            onDownload();
            onClose();
        } catch (e) {
            console.error('Download failed:', e);
        } finally {
            loading = false;
        }
    }
</script>

{#if true}
<div class="modal-backdrop" transition:fade={{ duration: 150 }}>
    <div class="modal" transition:scale={{ duration: 150, start: 0.95 }}>
        <header class="modal-header">
            <h3><Archive size={20} /> {$t('downloads.bulkTitle') || 'Download Files'}</h3>
            <button class="close-btn" onclick={onClose}><X size={20} /></button>
        </header>

        <div class="modal-body">
            <!-- File list -->
            <div class="file-section">
                <button 
                    class="file-toggle"
                    onclick={() => showFileList = !showFileList}
                >
                    <span>{files.length} {files.length === 1 ? 'file' : 'files'} ({formatBytes(totalBytes)})</span>
                    {#if files.length > 1}
                        {#if showFileList}<ChevronUp size={16} />{:else}<ChevronDown size={16} />{/if}
                    {/if}
                </button>
                
                {#if showFileList}
                    <ul class="file-list" transition:fade={{ duration: 100 }}>
                        {#each files as file}
                            <li>{file.name} <span class="file-size">({formatBytes(file.size)})</span></li>
                        {/each}
                    </ul>
                {/if}
            </div>

            <!-- Format selector -->
            <div class="format-section">
                <label>{$t('downloads.format') || 'Format'}</label>
                <select bind:value={format}>
                    <option value="none">{$t('downloads.singleFiles') || 'Single files (no archive)'}</option>
                    <option value="tar">TAR (no compression)</option>
                    <option value="zip">ZIP</option>
                    <option value="7z">7-Zip</option>
                </select>
            </div>

            <!-- Archive name (only for archives) -->
            {#if format !== 'none'}
                <div class="name-section">
                    <label>{$t('downloads.archiveName') || 'Archive name'}</label>
                    <input type="text" bind:value={archiveName} placeholder="download" />
                </div>
            {/if}
        </div>

        <footer class="modal-footer">
            <button class="btn btn-secondary" onclick={onClose}>
                {$t('common.cancel') || 'Cancel'}
            </button>
            <button class="btn btn-primary" onclick={handleDownload} disabled={loading}>
                <Download size={16} />
                {$t('downloads.download') || 'Download'} ({formatBytes(estimatedBytes)})
            </button>
        </footer>
    </div>
</div>
{/if}

<style>
    /* Modal styles - similar to ConfirmModal */
    .modal-backdrop { /* ... */ }
    .modal { /* ... */ }
    /* ... */
</style>
```

### 5.2 Integrazione in FilesTable/DataTable

Modificare l'azione "Download" quando ci sono selezioni multiple:

```typescript
function handleBulkDownload() {
    const selectedFiles = getSelectedFiles();
    if (selectedFiles.length === 0) return;
    
    showBulkDownloadModal = true;
    bulkDownloadFiles = selectedFiles.map(f => ({
        id: f.id || f.file_id,
        name: f.original_name || f.filename,
        size: f.size_bytes
    }));
}
```

### 5.3 Settings - Formato Download Default

Il formato di download di default deve essere configurabile sia a livello globale (admin) che personale (utente).

#### Backend - Nuovi campi settings

**GlobalSettings** (admin):

```python
default_download_format: Literal["none", "tar", "zip", "7z"] = "zip"
```

**UserSettings** (utente):

```python
download_format: Literal["none", "tar", "zip", "7z"] | None = None  # None = usa globale
```

#### Logica di risoluzione

1. Se `user_settings.download_format` è valorizzato → usa quello
2. Altrimenti → usa `global_settings.default_download_format`
3. Il "Restore defaults" nel profilo utente resetta a `None` (quindi usa globale)

#### Frontend - BulkDownloadModal

```typescript
// Nel componente BulkDownloadModal
import { userSettings } from '$lib/stores/settings';

// Inizializza formato dal setting utente (che già include fallback a globale)
let format = $state<'none' | 'tar' | 'zip' | '7z'>(
    $userSettings?.download_format || 'zip'
);
```

#### Frontend - Settings Pages

**GlobalSettingsTab.svelte**:

- Aggiungere selettore "Default download format" con opzioni: Single files, TAR, ZIP, 7-Zip

**UserSettingsTab.svelte** (o ProfileSettings):

- Aggiungere selettore "Download format" con opzioni + "Use default (from admin)"
- Mostrare valore corrente globale come hint

### 5.4 Traduzioni

**File**: `frontend/src/lib/i18n/locales/*.ts`

```typescript
// Aggiungere in ogni locale
downloads: {
    bulkTitle: "Download Files",
    format: "Format",
    singleFiles: "Single files (no archive)",
    archiveName: "Archive name",
    download: "Download",
    defaultFormat: "Default download format",
    useDefault: "Use default",
}
```

---

## Fase 6: Refactor Storage Service (Opzionale)

> **Nota**: Questa fase è opzionale e può essere implementata in seguito per unificare la gestione dei file tra uploads e BRIM.

### 6.1 Service Comune per File Storage

Creare un service comune che gestisca:

- Salvataggio file con metadata JSON
- Campi comuni (id, filename, size, uploaded_at, user_id)
- Campi specifici in sotto-oggetti

Questo permetterà di:

- Condividere logica tra uploads e BRIM
- Aggiungere nuovi campi comuni facilmente
- Mantenere separazione per campi specifici

---

## Checklist Implementazione

### Backend

- [ ] Aggiungere `py7zr` a Pipfile
- [ ] Creare `archive_service.py`
- [ ] Aggiungere schema `BulkDownloadRequest/Info`
- [ ] Endpoint POST `/uploads/bulk-download/info`
- [ ] Endpoint POST `/uploads/bulk-download`
- [ ] Endpoint POST `/brokers/import/bulk-download/info`
- [ ] Endpoint POST `/brokers/import/bulk-download`
- [ ] Aggiungere `default_download_format` a GlobalSettings
- [ ] Aggiungere `download_format` a UserSettings

### Test Backend

- [ ] Test bulk download uploads (zip, tar, single, none)
- [ ] Test bulk download BRIM con access control
- [ ] Test dimensione stimata
- [ ] Test settings download format

### Frontend

- [ ] Componente `BulkDownloadModal.svelte`
- [ ] Integrazione in FilesTable (upload section)
- [ ] Integrazione in FilesTable (BRIM section)
- [ ] Setting globale in GlobalSettingsTab
- [ ] Setting utente in UserSettings/Profile
- [ ] Traduzioni it/en/es/fr
- [ ] Aggiungere `api.postBlob()` se non esiste

### Documentazione

- [ ] Aggiornare API docs con nuovi endpoint
- [ ] Aggiornare README se necessario

---

## Timeline Stimata

| Fase       | Descrizione               | Stima    |
|------------|---------------------------|----------|
| 1          | Archive Service           | 1h       |
| 2          | Endpoint Uploads          | 1h       |
| 3          | Endpoint BRIM             | 1h       |
| 4          | Test Backend              | 1h       |
| 5          | Frontend Modal + Settings | 3h       |
| 6          | Refactor (opz)            | 2h       |
| **Totale** |                           | **7-9h** |
