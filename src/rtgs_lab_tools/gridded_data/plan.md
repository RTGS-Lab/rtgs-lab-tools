# Planet Labs Imagery Indexing and Automatic Ordering System

## Overview
Create a system to index available Planet Labs imagery, track downloads, and automatically order new imagery on a weekly basis. Uses SQLite for dual indexing (available catalog + local downloads) with YAML configuration for ROI management.

**Architecture:** This system will live in a **separate repository** on MSI HPC, utilizing the existing `rtgs-lab-tools` search and download functions as a library dependency.

## User Requirements
- **Two indexes**: Track both Planet Labs catalog availability and local downloads
- **Config file**: YAML configuration for multiple ROIs with search parameters
- **Automatic ordering**: Order new images when detected (weekly polling)
- **Storage**: SQLite database (in separate MSI repo)
- **No credits used**: Search polling is free, only orders use quota
- **Deployment**: Runs on MSI HPC with weekly cron automation

## Repository Architecture

### Repository 1: `rtgs-lab-tools` (this repo)
**Role:** Python library providing Planet API tools
**Provides:**
- `rtgs gridded-data planet-search` - Search Planet catalog (existing)
- `rtgs gridded-data download-clipped-scenes` - Download imagery (existing)
- Planet API authentication and session management
- No indexing logic, database, or automation scripts

**Location:** Installable Python package (pip install from git or PyPI)

### Repository 2: `msi-planet-index` (new, separate repo on MSI HPC)
**Role:** MSI-specific automation, indexing, and data storage
**Contains:**
- SQLite database: `planet_index.db`
- YAML configuration: `planet_rois.yaml`
- Downloaded imagery: `data/{roi_name}/`
- Python scripts for indexing and automation
- Weekly cron scripts
- MSI-specific deployment configs

**Dependencies:** Imports `rtgs-lab-tools` as a library

---

## Database Schema (SQLite in MSI repo)

### Schema Location
`planet_index.db` in the MSI repo root

### Tables
```sql
-- Track what's available in Planet Labs catalog (from search results)
available_imagery:
    id TEXT PRIMARY KEY,              -- Scene ID (e.g., "20170201_162101_0e0d")
    roi_name TEXT NOT NULL,
    acquired TEXT NOT NULL,           -- ISO timestamp
    date_acquired TEXT NOT NULL,      -- YYYY-MM-DD
    cloud_cover REAL,
    clear_confidence_percent REAL,
    clear_percent REAL,
    instrument TEXT,
    item_type TEXT,
    satellite_id TEXT,
    quality_category TEXT,
    published TEXT,
    updated TEXT,
    geometry TEXT,                    -- GeoJSON geometry as text
    first_detected TEXT,              -- When we first saw it in catalog
    last_seen TEXT                    -- Last time we saw it in catalog

-- Track what's been downloaded locally (multiple files per scene)
downloaded_files:
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id TEXT NOT NULL,           -- Foreign key to available_imagery.id
    roi_name TEXT NOT NULL,
    file_path TEXT NOT NULL,          -- Relative path from repo root
    file_type TEXT NOT NULL,          -- 'metadata_json', 'sr_tif', 'metadata_xml', 'udm2_tif'
    file_hash TEXT,                   -- SHA-256 hash for verification
    file_size INTEGER,                -- Bytes
    downloaded_at TEXT NOT NULL       -- ISO timestamp

-- Track Planet Orders API orders
orders:
    order_id TEXT PRIMARY KEY,        -- Planet order ID
    order_url TEXT,
    roi_name TEXT NOT NULL,
    state TEXT,                       -- 'queued', 'running', 'success', 'failed'
    created_at TEXT NOT NULL,
    completed_at TEXT,
    num_scenes INTEGER

-- Many-to-many: orders ↔ scenes
order_scenes:
    order_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    PRIMARY KEY (order_id, scene_id)

-- ROI configurations (synced from YAML)
roi_configs:
    roi_name TEXT PRIMARY KEY,
    geometry TEXT,                    -- GeoJSON as text
    item_types TEXT,                  -- JSON array
    asset_filter TEXT,                -- Asset types to download
    auto_order INTEGER,               -- Boolean (0/1)
    poll_enabled INTEGER,             -- Boolean (0/1)
    output_directory TEXT

-- Audit trail for operations
index_audit:
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    operation TEXT NOT NULL,          -- 'search', 'order', 'download', 'sync_config'
    roi_name TEXT,
    details TEXT,                     -- JSON details
    success INTEGER                   -- Boolean (0/1)
```

### Indexes
```sql
CREATE INDEX idx_available_imagery_roi ON available_imagery(roi_name);
CREATE INDEX idx_available_imagery_date ON available_imagery(date_acquired);
CREATE INDEX idx_downloaded_files_scene ON downloaded_files(scene_id);
CREATE INDEX idx_downloaded_files_roi ON downloaded_files(roi_name);
CREATE INDEX idx_order_scenes_scene ON order_scenes(scene_id);
```

---

## MSI Repository Structure
```
msi-planet-index/
├── planet_index.db                   # SQLite database
├── planet_rois.yaml                  # ROI configurations
├── data/                             # Downloaded imagery
│   ├── Course_01A/                   # One directory per ROI
│   │   ├── 20170201_162101_0e0d_metadata.json
│   │   ├── 20170201_162101_0e0d_3B_AnalyticMS_SR_clip.tif
│   │   ├── 20170201_162101_0e0d_3B_AnalyticMS_metadata_clip.xml
│   │   ├── 20170201_162101_0e0d_3B_udm2_clip.tif
│   │   └── ...
│   └── Course_01B/
├── scripts/
│   ├── index_manager.py              # Core indexing logic
│   ├── update_index.py               # Search and update catalog index
│   ├── order_imagery.py              # Create orders for new scenes
│   ├── download_orders.py            # Download completed orders
│   ├── sync_config.py                # Sync YAML to database
│   └── weekly_cron.sh                # Weekly automation script
├── config/
│   └── example_roi.yaml              # Template configuration
├── requirements.txt                  # Python dependencies (includes rtgs-lab-tools)
├── README.md
└── docs/
    └── setup_guide.md
```

### YAML Configuration (planet_rois.yaml in MSI repo)
```yaml
defaults:
  item_types: [PSScene]
  asset_filter: [analytic_sr, udm2]  # Only geometry and asset filters
  clip_to_roi: true
  auto_order: false

rois:
  Course_01A:
    name: "Golf Course 01A"
    geometry_file: "config/Course_01A_Outline.geojson"  # Path relative to repo
    auto_order: true
    output_directory: "data/Course_01A"

  Course_01B:
    name: "Golf Course 01B"
    geometry_file: "config/Course_01B_Outline.geojson"
    auto_order: true
    output_directory: "data/Course_01B"
```

## Implementation Plan

### rtgs-lab-tools: No Changes Needed
The existing `rtgs-lab-tools` package already provides the necessary functions:
- ✅ `planet_search()` - Search Planet catalog with filters
- ✅ `download_clipped_scenes()` - Download imagery via Orders API
- ✅ Planet API session management and authentication

**No implementation work required in this repository.**

---

### MSI Repository (`msi-planet-index`): Implementation Phases

### Phase 1: Repository Setup & Database Schema
**Files to create in MSI repo:**
- `planet_index.db` - SQLite database (empty initially)
- `scripts/init_database.py` - Database initialization script
- `scripts/models.py` - SQLAlchemy ORM models
- `requirements.txt` - Dependencies (rtgs-lab-tools, sqlalchemy, pyyaml)
- `README.md` - Setup and usage documentation

**Database initialization:**
```python
# scripts/init_database.py
# Creates all tables with proper schema
# Creates indexes for performance
# Can be run multiple times (idempotent)
```

**SQLAlchemy Models:**
- `AvailableImagery` - Catalog index
- `DownloadedFile` - Downloaded file tracking
- `Order` - Planet order tracking
- `OrderScene` - Order-scene relationship
- `ROIConfig` - ROI configurations
- `IndexAudit` - Audit trail

### Phase 2: Configuration Management
**Files to create:**
- `planet_rois.yaml` - Main configuration file
- `config/` - Directory for ROI geometry files
- `scripts/config_manager.py` - YAML parser and validator
- `scripts/sync_config.py` - Sync YAML to database

**Key functions:**
```python
# scripts/config_manager.py
def load_config(config_path) -> dict
def validate_config(config) -> bool
def get_roi_config(config, roi_name) -> dict
def list_rois(config) -> list

# scripts/sync_config.py
def sync_rois_to_database(config_path, db_path)
```

### Phase 3: Index Update (Search Integration)
**Files to create:**
- `scripts/index_manager.py` - Core indexing logic
- `scripts/update_index.py` - CLI script to update index

**Key workflow:**
```python
# scripts/update_index.py
1. Load ROI configs from database
2. For each ROI:
   a. Call rtgs_lab_tools.planet_search() to get search results
   b. Parse CSV results
   c. Upsert scenes into available_imagery table
   d. Mark first_detected and last_seen timestamps
   e. Log operation to index_audit
```

**Integration with rtgs-lab-tools:**
```python
from rtgs_lab_tools.gridded_data.planet import planet_search

# Use existing search function
results_csv = planet_search(
    source="PSScene",
    roi=roi_geometry_file,
    start_date=start_date,
    end_date=end_date,
    out_dir=temp_dir
)

# Parse CSV and insert into database
import pandas as pd
df = pd.read_csv(results_csv)
for _, row in df.iterrows():
    upsert_scene_to_db(row)
```

### Phase 4: Order Management
**Files to create:**
- `scripts/order_manager.py` - Order creation and tracking
- `scripts/order_imagery.py` - CLI script to create orders

**Key workflow:**
```python
# scripts/order_imagery.py
1. Query available_imagery for scenes not yet ordered/downloaded
2. Group scenes by ROI
3. For auto_order ROIs:
   a. Create order via Planet Orders API
   b. Record order in orders table
   c. Link scenes in order_scenes table
   d. Log operation to index_audit
```

**Key functions:**
```python
def get_unordered_scenes(db, roi_name) -> list
def create_planet_order(roi_name, scene_ids) -> order_id
def track_order(db, order_id, roi_name, scene_ids)
def check_order_status(order_id) -> state
def poll_pending_orders(db)
```

### Phase 5: Download Management
**Files to create:**
- `scripts/download_manager.py` - Download coordination
- `scripts/download_orders.py` - CLI script to download completed orders

**Key workflow:**
```python
# scripts/download_orders.py
1. Query orders table for completed orders
2. For each completed order:
   a. Download scenes using rtgs_lab_tools.download_clipped_scenes()
   b. Verify downloaded files (check existence, hash)
   c. Record each file in downloaded_files table
   d. Move files to proper ROI directory
   e. Log operation to index_audit
```

**Integration with rtgs-lab-tools:**
```python
from rtgs_lab_tools.gridded_data.planet import download_clipped_scenes

# Use existing download function
download_clipped_scenes(
    source="PSScene",
    roi=roi_geometry_file,
    out_dir=f"data/{roi_name}",
    meta_file=scene_ids_csv,  # CSV with scene IDs from order
    confirmed=True
)

# Then track files in database
for file_path in downloaded_files:
    record_downloaded_file(db, scene_id, file_path, file_type, file_hash)
```

### Phase 6: Weekly Automation Script
**Files to create:**
- `scripts/weekly_cron.sh` - Main automation script
- `scripts/run_weekly_update.py` - Python wrapper with error handling

**Cron workflow:**
```bash
#!/bin/bash
# scripts/weekly_cron.sh

cd /path/to/msi-planet-index

# 1. Sync config (in case YAML changed)
python scripts/sync_config.py

# 2. Update index for all ROIs (free search)
python scripts/update_index.py --all

# 3. Create orders for new imagery (auto_order ROIs only)
python scripts/order_imagery.py --auto-only

# 4. Check pending orders and download completed ones
python scripts/download_orders.py --completed-only

# 5. Send summary email/notification
python scripts/send_summary.py
```

**Crontab entry:**
```
# Run every Monday at 2 AM
0 2 * * 1 /path/to/msi-planet-index/scripts/weekly_cron.sh >> /path/to/logs/weekly_cron.log 2>&1
```

### Phase 7: Utilities & Documentation
**Files to create:**
- `scripts/query_index.py` - Query database for analysis
- `scripts/stats.py` - Generate statistics reports
- `scripts/verify_downloads.py` - Verify file integrity
- `docs/setup_guide.md` - MSI setup instructions
- `docs/usage_guide.md` - How to use the system
- `docs/schema_diagram.md` - Database schema documentation

## Workflow

### Initial Setup (One-time)
1. **On MSI:** Clone `msi-planet-index` repo
2. **On MSI:** Install dependencies: `pip install -r requirements.txt`
3. **On MSI:** Initialize database: `python scripts/init_database.py`
4. **On MSI:** Edit `planet_rois.yaml` with ROI configurations
5. **On MSI:** Sync config to database: `python scripts/sync_config.py`
6. **On MSI:** Set up cron job for weekly automation

### Manual Workflow (for testing or one-off updates)
1. **Update index for specific ROI:**
   ```bash
   python scripts/update_index.py --roi Course_01A
   ```

2. **Review new imagery available:**
   ```bash
   python scripts/query_index.py --roi Course_01A --not-downloaded
   ```

3. **Create order (dry-run first):**
   ```bash
   python scripts/order_imagery.py --roi Course_01A --dry-run
   python scripts/order_imagery.py --roi Course_01A
   ```

4. **Check order status:**
   ```bash
   python scripts/order_imagery.py --check-status
   ```

5. **Download completed orders:**
   ```bash
   python scripts/download_orders.py --completed-only
   ```

### Automated Workflow (Weekly Cron)
**Runs every Monday at 2 AM:**
1. Sync YAML config to database (handles config changes)
2. Update index for all ROIs (free Planet API search)
3. Create orders for new imagery (only for `auto_order: true` ROIs)
4. Check pending orders and download completed ones
5. Send summary notification/email

**No manual intervention needed** - system runs autonomously

## Critical Files Summary

### In `rtgs-lab-tools` (this repo)
**No changes required** - existing Planet API functions are sufficient:
- ✅ `src/rtgs_lab_tools/gridded_data/planet.py` - Search and download functions
- ✅ `src/rtgs_lab_tools/gridded_data/cli.py` - CLI for planet-search and download-clipped-scenes

### In `msi-planet-index` (new MSI repo)
**Files to create:**

**Configuration & Data:**
- `planet_index.db` - SQLite database
- `planet_rois.yaml` - ROI configurations
- `data/` - Downloaded imagery directory

**Python Scripts:**
- `scripts/init_database.py` - Database initialization
- `scripts/models.py` - SQLAlchemy ORM models
- `scripts/config_manager.py` - YAML parser and validator
- `scripts/sync_config.py` - Sync YAML to database
- `scripts/index_manager.py` - Core indexing logic
- `scripts/update_index.py` - Update catalog index
- `scripts/order_manager.py` - Order creation and tracking
- `scripts/order_imagery.py` - Create orders CLI
- `scripts/download_manager.py` - Download coordination
- `scripts/download_orders.py` - Download completed orders
- `scripts/query_index.py` - Query database
- `scripts/stats.py` - Generate statistics
- `scripts/verify_downloads.py` - Verify file integrity
- `scripts/send_summary.py` - Email notifications

**Automation:**
- `scripts/weekly_cron.sh` - Weekly automation script
- `scripts/run_weekly_update.py` - Python wrapper with error handling

**Documentation:**
- `README.md` - Main documentation
- `requirements.txt` - Python dependencies
- `docs/setup_guide.md` - MSI setup instructions
- `docs/usage_guide.md` - How to use the system
- `docs/schema_diagram.md` - Database schema documentation
- `config/example_roi.yaml` - Template configuration

**Files to reference (patterns to follow from rtgs-lab-tools):**
- `src/rtgs_lab_tools/gridded_data/planet.py` - Planet API integration patterns
- `src/rtgs_lab_tools/core/database.py` - Database connection patterns
- `src/rtgs_lab_tools/sensing_data/file_operations.py` - File hashing and verification

## Key Implementation Details

### 1. Duplicate Detection
**Before ordering:**
- Query `downloaded_files` table for scene_id
- Query `order_scenes` table for pending/active orders
- Only order scenes that are neither downloaded nor already ordered

**Before downloading:**
- Check if files already exist in `data/{roi_name}/`
- Verify file hashes if files exist
- Skip download if valid files already present

### 2. Data Mapping from Search Results to Database
**CSV columns → available_imagery table:**
```python
csv_to_db_mapping = {
    'id': 'id',
    'acquired': 'acquired',
    'date_acquired': 'date_acquired',
    'cloud_cover': 'cloud_cover',
    'clear_confidence_percent': 'clear_confidence_percent',
    'clear_percent': 'clear_percent',
    'instrument': 'instrument',
    'item_type': 'item_type',
    'satellite_id': 'satellite_id',
    'quality_category': 'quality_category',
    'published': 'published',
    'updated': 'updated'
}
```

### 3. File Type Tracking
**Per scene, track 4 files:**
```python
file_types = {
    'metadata_json': f'{scene_id}_metadata.json',
    'sr_tif': f'{scene_id}_3B_AnalyticMS_SR_clip.tif',
    'metadata_xml': f'{scene_id}_3B_AnalyticMS_metadata_clip.xml',
    'udm2_tif': f'{scene_id}_3B_udm2_clip.tif'
}
```

### 4. Two-Phase Workflow
**Phase 1: Search and Order**
- Weekly search updates `available_imagery` table (free)
- Identify new scenes (not in `downloaded_files` or `order_scenes`)
- Create Planet orders and record in `orders` table
- Save order URLs for tracking

**Phase 2: Download When Ready**
- Poll pending orders for completion
- When order completes, download all scenes
- Record each file in `downloaded_files` table
- Verify file integrity with hashes

### 5. Filtering Strategy (Based on Requirements)
**Only use:**
- ✅ Geometry filter (ROI boundary)
- ✅ Asset filter (analytic_sr, udm2)

**Do NOT use:**
- ❌ Quality category filter
- ❌ Cloud cover filter (optional - can be added to YAML config if needed)
- ❌ Date filter (optional - can be configured per ROI)

Keep system flexible for future filter additions via YAML config.

## Testing Strategy

**Phase 1 Testing (Database & Config):**
- Test database initialization and schema creation
- Test YAML parsing and validation
- Test config sync to database

**Phase 2 Testing (Index Updates):**
- Test search result CSV parsing
- Test upsert logic (handles duplicates correctly)
- Test timestamp tracking (first_detected, last_seen)

**Phase 3 Testing (Orders & Downloads):**
- Test order creation with rtgs-lab-tools integration
- Test download with rtgs-lab-tools integration
- Test file tracking and hash verification
- Test duplicate prevention logic

**Phase 4 Testing (Automation):**
- Test weekly cron script end-to-end
- Test error handling and logging
- Test with multiple ROIs

## Success Criteria

✅ Can configure multiple ROIs in YAML
✅ Index tracks both available catalog and downloaded files separately
✅ Search polling works without using Planet credits (free searches)
✅ Detects new imagery and orders automatically (for auto_order ROIs)
✅ Downloads organize files by ROI name (data/{roi_name}/)
✅ Duplicate detection prevents re-ordering/downloading same scenes
✅ Weekly automation via cron works reliably on MSI HPC
✅ All operations logged to index_audit table
✅ System uses rtgs-lab-tools as a library dependency
✅ Database and scripts live in separate MSI repo
✅ Minimal filtering (geometry + assets only) for maximum flexibility

---

## Quick Reference Summary

### Two-Repository Architecture

**`rtgs-lab-tools` (this repo):**
- Provides Planet API search and download functions
- No changes needed - existing functionality is sufficient
- Installed as a library dependency

**`msi-planet-index` (new MSI repo):**
- SQLite database for indexing
- Python scripts for automation
- Downloaded imagery storage
- Weekly cron jobs
- YAML configuration

### Core Workflow

```
Weekly Cron (Monday 2 AM)
├─> Search Planet catalog (free) → Update available_imagery table
├─> Identify new scenes → Create orders (for auto_order ROIs)
├─> Check pending orders → Download completed
└─> Log everything to index_audit
```

### Key Database Tables

1. **available_imagery** - Planet catalog index from search results
2. **downloaded_files** - Local file tracking (4 files per scene)
3. **orders** - Planet Orders API tracking
4. **order_scenes** - Order-to-scene relationships
5. **roi_configs** - ROI configurations from YAML
6. **index_audit** - Operation logging

### Actual File Structure (from search results)

**Search result CSV columns:**
- `id`, `acquired`, `date_acquired`, `cloud_cover`, `clear_confidence_percent`
- `instrument`, `item_type`, `satellite_id`, `quality_category`

**Downloaded files per scene (4 files):**
- `{scene_id}_metadata.json`
- `{scene_id}_3B_AnalyticMS_SR_clip.tif`
- `{scene_id}_3B_AnalyticMS_metadata_clip.xml`
- `{scene_id}_3B_udm2_clip.tif`

**Storage pattern:**
- `data/{roi_name}/{scene_files}` (flat directory per ROI)
