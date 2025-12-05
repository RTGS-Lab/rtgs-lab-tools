# Planet Labs Imagery Indexing and Automatic Ordering System

## Overview
Create a system to index available Planet Labs imagery, track downloads, and automatically order new imagery on a weekly basis. Uses SQLite for dual indexing (available catalog + local downloads) with YAML configuration for ROI management.

## User Requirements
- **Two indexes**: Track both Planet Labs catalog availability and local downloads
- **Config file**: YAML configuration for multiple ROIs with search parameters
- **Automatic ordering**: Order new images when detected (weekly polling)
- **Storage**: SQLite database
- **No credits used**: Search polling is free, only orders use quota

## Architecture

### Database Schema (SQLite at ~/.rtgs_lab_tools/planet_index.db)
```sql
-- Track what's available in Planet Labs catalog
available_imagery: id (PK), roi_name, acquired, cloud_cover,
                   clear_confidence_percent, instrument, geometry,
                   first_detected, last_seen

-- Track what's been downloaded locally
downloaded_imagery: id (PK), roi_name, local_path, file_hash,
                    downloaded_at, product_bundle

-- Track Planet Orders API orders
orders: order_id (PK), order_url, roi_name, state, created_at,
        completed_at, num_scenes

-- Many-to-many: orders ↔ scenes
order_scenes: order_id, scene_id (composite PK)

-- ROI configurations (synced from YAML)
roi_configs: roi_name (PK), geometry, item_types, max_cloud_cover,
             auto_order, poll_enabled, product_bundle

-- Audit trail for operations
index_audit: id, timestamp, operation, roi_name, details, success
```

### Module Structure
```
src/rtgs_lab_tools/gridded_data/planet_index/
├── __init__.py           # Package exports
├── models.py             # SQLAlchemy ORM models
├── database.py           # PlanetIndexDB class (CRUD operations)
├── config.py             # PlanetIndexConfig (YAML parser)
├── indexer.py            # PlanetIndexer (search/index management)
├── orderer.py            # PlanetOrderer (Orders API management)
├── downloader.py         # PlanetDownloader (download management)
└── utils.py              # Shared utilities (pagination, filtering)
```

### YAML Configuration (~/.rtgs_lab_tools/planet_rois.yaml)
```yaml
defaults:
  item_types: [PSScene]
  instruments: [PSB.SD]
  max_cloud_cover: 0.05
  product_bundle: analytic_sr_udm2
  clip_to_roi: true
  auto_order: false

rois:
  wausau_2025:
    name: "Wausau Golf Course 2025"
    geometry: {...}  # Inline GeoJSON or geometry_file path
    poll_start_date: "2025-01-01"
    auto_order: true
    output_directory: "./data/planet/wausau_2025"
```

## Implementation Plan

### Phase 1: Foundation (Models & Database)
**Files to create:**
- `src/rtgs_lab_tools/gridded_data/planet_index/__init__.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/models.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/database.py`

**Key classes:**
- `AvailableImagery`, `DownloadedImagery`, `Order`, `OrderScene`, `ROIConfig`, `IndexAudit` (SQLAlchemy models)
- `PlanetIndexDB` class with methods:
  - `init_schema()` - Create tables
  - `upsert_imagery(scenes, roi_name)` - Add/update available imagery
  - `get_new_imagery(roi_name, since)` - Query new scenes since timestamp
  - `mark_downloaded(scene_id, roi_name, file_path, file_hash)` - Record download
  - `create_order(order_id, scene_ids, roi_name)` - Record order
  - `update_order_status(order_id, state)` - Update order state
  - `get_pending_orders()` - Get orders in queued/running state

**Pattern to follow:** `src/rtgs_lab_tools/core/database.py` (DatabaseManager class)

### Phase 2: Configuration Management
**Files to create:**
- `src/rtgs_lab_tools/gridded_data/planet_index/config.py`

**Key class:**
- `PlanetIndexConfig` with methods:
  - `__init__(config_path)` - Load YAML, validate structure
  - `get_roi_config(roi_name)` - Get config for specific ROI
  - `list_rois()` - List all configured ROIs
  - `sync_to_db(db)` - Sync ROI configs to roi_configs table
  - `create_template(output_path)` - Generate template YAML

**Integration:**
- Update `src/rtgs_lab_tools/core/config.py` to add `planet_index_db_path` and `planet_index_config_path` properties
- Add PyYAML to dependencies in `pyproject.toml`

### Phase 3: Indexing (Search & Catalog Management)
**Files to create:**
- `src/rtgs_lab_tools/gridded_data/planet_index/indexer.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/utils.py`

**Key functionality:**
- `PlanetIndexer` class:
  - `update_index(roi_name, start_date, end_date)` - Search Planet API and update database
  - `search_planet(roi_config, start_date, end_date)` - Execute search with pagination
  - `deduplicate_by_date(scenes)` - Keep best scene per date (by clear_confidence_percent)

**Utils functions:**
- `paginate_quick_search(session, request)` - Handle Planet API pagination (_links._next pattern)
- `filter_by_instrument(scenes, instruments)` - Filter scenes by instrument
- `deduplicate_by_date_and_quality(scenes)` - Sort and deduplicate

**Pattern to follow:** Extract and enhance search logic from `src/rtgs_lab_tools/gridded_data/planet.py:276-339` (quick_search function)

**Key enhancement:** Handle pagination that notebook shows but current code doesn't:
```python
next_url = search_result.json()['_links'].get('_next')
while next_url:
    next_response = session.get(next_url)
    features.extend(next_response.json()['features'])
    next_url = next_response.json()['_links'].get('_next')
```

### Phase 4: Order Management
**Files to create:**
- `src/rtgs_lab_tools/gridded_data/planet_index/orderer.py`

**Key class:**
- `PlanetOrderer` with methods:
  - `create_order(roi_name, scene_ids, dry_run)` - Create Planet Orders API order
  - `check_order_status(order_id)` - Poll order status
  - `poll_pending_orders()` - Check all pending orders
  - `auto_order_new_imagery(roi_name)` - Order all unordered scenes for ROI
  - `_split_into_batches(scene_ids, batch_size)` - Handle large orders

**Pattern to follow:** Reuse order logic from `src/rtgs_lab_tools/gridded_data/planet.py:128-170` (download_clipped_scenes order creation)

**Integration:** Query `available_imagery` for scenes not in `downloaded_imagery` and not in `order_scenes`

### Phase 5: Download Management
**Files to create:**
- `src/rtgs_lab_tools/gridded_data/planet_index/downloader.py`

**Key class:**
- `PlanetDownloader` with methods:
  - `download_order(order_id)` - Download all scenes from completed order
  - `verify_download(file_path)` - Calculate SHA-256 hash
  - `organize_file(file_path, roi_name, acquired_date)` - Move to organized directory (YYYY/MM/DD structure)

**Pattern to follow:**
- `src/rtgs_lab_tools/sensing_data/file_operations.py:20-33` (calculate_file_hash)
- `src/rtgs_lab_tools/gridded_data/planet.py:24-43` (download_file function)

### Phase 6: CLI Commands
**Files to modify:**
- `src/rtgs_lab_tools/gridded_data/cli.py` (add new command group)

**New commands to add:**
```python
@gridded_data_cli.group()
def planet_index(ctx):
    """Planet imagery indexing and ordering tools."""

# Commands:
@planet_index.command()
def init(...):
    """Initialize database and create config template."""

@planet_index.command()
def update(...):
    """Update imagery index from Planet API (search and catalog)."""

@planet_index.command()
def list_imagery(...):
    """List available imagery in index (with filters)."""

@planet_index.command()
def order(...):
    """Create Planet order for imagery (with --dry-run)."""

@planet_index.command()
def status(...):
    """Check status of Planet orders."""

@planet_index.command()
def download(...):
    """Download completed orders."""

@planet_index.command()
def stats(...):
    """Show index statistics."""

@planet_index.command()
def sync_config(...):
    """Sync ROI configs from YAML to database."""
```

**Pattern to follow:** Existing gridded_data CLI commands with `@add_common_options` and `@handle_common_errors` decorators

### Phase 7: Automation Scripts & Documentation
**Files to create:**
- `scripts/planet-index-weekly.sh` - Weekly automation script for cron
- `docs/planet-index-guide.md` - User guide

**Automation workflow:**
```bash
# Weekly cron job (runs Monday 2 AM):
rtgs gridded-data planet-index update --roi all
rtgs gridded-data planet-index order --roi <auto_order_rois> --auto
rtgs gridded-data planet-index status --download-ready
```

## Workflow

### Manual Workflow
1. `planet-index init --create-template` - Create config file
2. Edit `~/.rtgs_lab_tools/planet_rois.yaml` with ROIs
3. `planet-index sync-config` - Load ROIs into database
4. `planet-index update --roi wausau_2025` - Search and index
5. `planet-index list-imagery --roi wausau_2025 --not-ordered` - Review
6. `planet-index order --roi wausau_2025 --auto --dry-run` - Preview order
7. `planet-index order --roi wausau_2025 --auto` - Place order
8. `planet-index status --pending-only` - Check order status
9. `planet-index download --roi wausau_2025` - Download completed

### Automated Workflow
- Cron job runs weekly script
- Updates all ROI indexes (free search)
- Auto-orders for ROIs with `auto_order: true`
- Downloads any completed orders

## Critical Files

**Files to create:**
- `src/rtgs_lab_tools/gridded_data/planet_index/__init__.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/models.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/database.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/config.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/indexer.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/orderer.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/downloader.py`
- `src/rtgs_lab_tools/gridded_data/planet_index/utils.py`
- `scripts/planet-index-weekly.sh`

**Files to modify:**
- `src/rtgs_lab_tools/gridded_data/cli.py` - Add planet-index command group
- `src/rtgs_lab_tools/core/config.py` - Add database and config path properties
- `pyproject.toml` - Add pyyaml dependency

**Files to reference (patterns to follow):**
- `src/rtgs_lab_tools/gridded_data/planet.py` - Existing Planet API logic
- `src/rtgs_lab_tools/core/database.py` - Database manager pattern
- `src/rtgs_lab_tools/core/cli_utils.py` - CLI patterns and error handling
- `src/rtgs_lab_tools/sensing_data/file_operations.py` - File hashing and verification

## Key Features from Notebooks to Incorporate

1. **Duplicate Detection** (from Planet - Bulk Order.ipynb:276-296):
   - Check `downloaded_imagery` before ordering
   - Query existing files to avoid re-downloading

2. **Quality Filtering** (from Planet - Bulk Order.ipynb):
   - Sort by `clear_confidence_percent`
   - Keep one image per date (clearest)
   - Filter by instrument type and quality_category

3. **Two-Phase Workflow** (from both notebooks):
   - Phase 1: Search and order (save order URLs)
   - Phase 2: Download when ready
   - Separation allows batch management

4. **Pagination Support** (from Planet - Bulk Order.ipynb:132-140):
   - Follow `_links._next` pattern
   - Accumulate all results across pages

## Testing Strategy

1. **Unit tests** - Database operations, config parsing, deduplication logic
2. **Integration tests** - Planet API searches (with test ROI), order creation, downloads
3. **End-to-end test** - Full workflow for single ROI
4. **Performance test** - Index 1000+ scenes, query performance

## Success Criteria

✅ Can configure multiple ROIs in YAML
✅ Index tracks both available catalog and downloaded files separately
✅ Search polling works without using Planet credits
✅ Detects new imagery and orders automatically (if enabled)
✅ Downloads organize files by date (YYYY/MM/DD)
✅ Duplicate detection prevents re-ordering/downloading
✅ Weekly automation via cron works reliably
✅ All operations logged to PostgreSQL audit system
✅ CLI commands follow existing rtgs-lab-tools patterns
