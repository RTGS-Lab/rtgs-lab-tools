"""
Test script for spatial_data configuration modes.

This script verifies that the configuration system works correctly
for different operational modes (built-in, local, hybrid).
"""

import logging
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from rtgs_lab_tools.spatial_data.config import SpatialDataConfig, DataConfig, DatabaseConfig
from rtgs_lab_tools.spatial_data.registry.dataset_registry import list_datasets_by_mode

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_built_in_mode():
    """Test built-in mode configuration."""
    logger.info("=" * 60)
    logger.info("Testing Built-in Mode")
    logger.info("=" * 60)

    config = SpatialDataConfig(
        mode="built-in",
        data=DataConfig(sources=["mn_geospatial"]),
        database=DatabaseConfig(logging_enabled=True)
    )

    logger.info(f"Mode: {config.mode}")
    logger.info(f"Database logging: {config.database.logging_enabled}")

    # List datasets
    datasets = list_datasets_by_mode(mode="built-in")
    logger.info(f"Found {len(datasets)} built-in datasets")

    # Show first few
    for name in list(datasets.keys())[:5]:
        logger.info(f"  - {name}: {datasets[name].get('description', 'No description')[:50]}...")

    logger.info("✓ Built-in mode test passed")
    return True


def test_local_mode():
    """Test local mode configuration (without actual local files)."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Local Mode (Config Only)")
    logger.info("=" * 60)

    # Create a test data directory
    test_data_dir = Path(__file__).parent / "test_data"
    test_data_dir.mkdir(exist_ok=True)

    config = SpatialDataConfig(
        mode="local",
        data=DataConfig(
            local_directory=str(test_data_dir),
            cache_directory=".rtgs_cache"
        ),
        database=DatabaseConfig(logging_enabled=False)
    )

    logger.info(f"Mode: {config.mode}")
    logger.info(f"Local directory: {config.data.local_directory}")
    logger.info(f"Database logging: {config.database.logging_enabled}")

    # Validate config
    try:
        config.validate()
        logger.info("✓ Local mode configuration is valid")
    except Exception as e:
        logger.error(f"✗ Local mode validation failed: {e}")
        return False

    # List datasets (should be empty since no files)
    datasets = list_datasets_by_mode(
        mode="local",
        local_directory=test_data_dir
    )
    logger.info(f"Found {len(datasets)} local datasets (expected 0 for empty directory)")

    logger.info("✓ Local mode test passed")
    return True


def test_hybrid_mode():
    """Test hybrid mode configuration."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Hybrid Mode (Config Only)")
    logger.info("=" * 60)

    test_data_dir = Path(__file__).parent / "test_data"
    test_data_dir.mkdir(exist_ok=True)

    config = SpatialDataConfig(
        mode="hybrid",
        data=DataConfig(
            local_directory=str(test_data_dir),
            sources=["mn_geospatial"],
            local_prefix="local"
        ),
        database=DatabaseConfig(logging_enabled=True)
    )

    logger.info(f"Mode: {config.mode}")
    logger.info(f"Local directory: {config.data.local_directory}")
    logger.info(f"Local prefix: {config.data.local_prefix}")
    logger.info(f"Database logging: {config.database.logging_enabled}")

    # Validate config
    try:
        config.validate()
        logger.info("✓ Hybrid mode configuration is valid")
    except Exception as e:
        logger.error(f"✗ Hybrid mode validation failed: {e}")
        return False

    # List datasets (should include built-in)
    datasets = list_datasets_by_mode(
        mode="hybrid",
        local_directory=test_data_dir,
        local_prefix="local"
    )
    logger.info(f"Found {len(datasets)} datasets (built-in + local)")

    # Check for built-in datasets
    built_in_count = sum(1 for d in datasets.values() if d.get("source") != "local")
    logger.info(f"  - Built-in datasets: {built_in_count}")
    logger.info(f"  - Local datasets: {len(datasets) - built_in_count}")

    logger.info("✓ Hybrid mode test passed")
    return True


def test_config_file_creation():
    """Test saving and loading configuration files."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Configuration File I/O")
    logger.info("=" * 60)

    test_config_path = Path(__file__).parent / "test_config.yaml"

    # Create config
    config = SpatialDataConfig(
        mode="local",
        data=DataConfig(
            local_directory="./test_data",
            cache_directory=".rtgs_cache"
        ),
        database=DatabaseConfig(logging_enabled=False)
    )

    # Save to file
    config.to_yaml(test_config_path)
    logger.info(f"✓ Configuration saved to {test_config_path}")

    # Load from file
    loaded_config = SpatialDataConfig.from_yaml(test_config_path)
    logger.info(f"✓ Configuration loaded from {test_config_path}")

    # Verify
    assert loaded_config.mode == config.mode
    assert loaded_config.data.local_directory == config.data.local_directory
    assert loaded_config.database.logging_enabled == config.database.logging_enabled

    logger.info("✓ Configuration file I/O test passed")

    # Clean up
    test_config_path.unlink()

    return True


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Spatial Data Configuration System Tests")
    logger.info("=" * 60)
    logger.info("")

    tests = [
        test_built_in_mode,
        test_local_mode,
        test_hybrid_mode,
        test_config_file_creation,
    ]

    results = []
    for test_func in tests:
        try:
            success = test_func()
            results.append((test_func.__name__, success))
        except Exception as e:
            logger.error(f"Test {test_func.__name__} raised exception: {e}", exc_info=True)
            results.append((test_func.__name__, False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        logger.info(f"{status}: {test_name}")

    logger.info("")
    logger.info(f"Results: {passed}/{total} tests passed")

    # Clean up test directory
    test_data_dir = Path(__file__).parent / "test_data"
    if test_data_dir.exists():
        test_data_dir.rmdir()

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
