"""Tests for crop parameters database."""

import pytest

from rtgs_lab_tools.agricultural_modeling.crop_parameters import (
    get_crop_names,
    get_crop_parameters,
    get_crop_status,
)


class TestGetCropParameters:
    """Test the crop parameters retrieval function."""

    def test_get_all_crops(self):
        """Test getting all crop parameters."""
        crops = get_crop_parameters()
        assert isinstance(crops, dict)
        assert len(crops) > 0
        assert "corn" in crops
        assert "soybeans" in crops
        assert "wheat" in crops

    def test_get_specific_crop(self):
        """Test getting parameters for a specific crop."""
        corn_params = get_crop_parameters("corn")
        assert isinstance(corn_params, dict)
        assert "tBase" in corn_params
        assert "tUpper" in corn_params
        assert "status" in corn_params
        assert "verifiedBy" in corn_params
        assert "reference" in corn_params

    def test_corn_parameters(self):
        """Test specific corn parameters."""
        corn_params = get_crop_parameters("corn")
        assert corn_params["tBase"] == 10.0
        assert corn_params["tUpper"] == 30.0
        assert corn_params["status"] == "verified"

    def test_wheat_parameters(self):
        """Test specific wheat parameters."""
        wheat_params = get_crop_parameters("wheat")
        assert wheat_params["tBase"] == 0.0
        assert wheat_params["tUpper"] == 35.0
        assert wheat_params["status"] == "verified"

    def test_potatoes_parameters(self):
        """Test specific potatoes parameters."""
        potatoes_params = get_crop_parameters("potatoes")
        assert potatoes_params["tBase"] == 7.0
        assert potatoes_params["tUpper"] == 36.0
        assert potatoes_params["status"] == "verified"

    def test_invalid_crop(self):
        """Test getting parameters for non-existent crop."""
        with pytest.raises(KeyError) as excinfo:
            get_crop_parameters("nonexistent_crop")
        assert "not found in database" in str(excinfo.value)
        assert "Available crops:" in str(excinfo.value)

    def test_case_sensitivity(self):
        """Test that crop names are case sensitive."""
        with pytest.raises(KeyError):
            get_crop_parameters("CORN")  # Should be lowercase
        with pytest.raises(KeyError):
            get_crop_parameters("Corn")  # Should be lowercase

    def test_all_crops_have_required_fields(self):
        """Test that all crops have required parameter fields."""
        required_fields = ["tBase", "tUpper", "status", "verifiedBy", "reference"]
        crops = get_crop_parameters()

        for crop_name, crop_params in crops.items():
            for field in required_fields:
                assert (
                    field in crop_params
                ), f"Crop '{crop_name}' missing field '{field}'"

    def test_temperature_values_are_numeric(self):
        """Test that temperature values are numeric."""
        crops = get_crop_parameters()

        for crop_name, crop_params in crops.items():
            assert isinstance(
                crop_params["tBase"], (int, float)
            ), f"tBase for {crop_name} is not numeric"
            assert isinstance(
                crop_params["tUpper"], (int, float)
            ), f"tUpper for {crop_name} is not numeric"
            assert (
                crop_params["tBase"] < crop_params["tUpper"]
            ), f"tBase >= tUpper for {crop_name}"


class TestGetCropNames:
    """Test the crop names retrieval function."""

    def test_get_crop_names(self):
        """Test getting sorted list of crop names."""
        names = get_crop_names()
        assert isinstance(names, list)
        assert len(names) > 0
        assert "corn" in names
        assert "soybeans" in names
        assert "wheat" in names

    def test_names_are_sorted(self):
        """Test that crop names are returned in sorted order."""
        names = get_crop_names()
        assert names == sorted(names)

    def test_names_match_parameters(self):
        """Test that names match keys in parameters dictionary."""
        names = get_crop_names()
        crops = get_crop_parameters()
        assert set(names) == set(crops.keys())


class TestGetCropStatus:
    """Test the crop status retrieval function."""

    def test_get_crop_status(self):
        """Test getting verification status for all crops."""
        status = get_crop_status()
        assert isinstance(status, dict)
        assert len(status) > 0

    def test_status_values(self):
        """Test that status values are valid."""
        status = get_crop_status()
        valid_statuses = ["verified", "pending"]

        for crop_name, crop_status in status.items():
            assert (
                crop_status in valid_statuses
            ), f"Invalid status '{crop_status}' for {crop_name}"

    def test_status_matches_parameters(self):
        """Test that status matches the full parameters."""
        status = get_crop_status()
        crops = get_crop_parameters()

        for crop_name in crops.keys():
            assert status[crop_name] == crops[crop_name]["status"]

    def test_verified_crops_exist(self):
        """Test that there are verified crops in the database."""
        status = get_crop_status()
        verified_crops = [name for name, stat in status.items() if stat == "verified"]
        assert len(verified_crops) > 0, "No verified crops found"

    def test_corn_is_verified(self):
        """Test that corn is verified."""
        status = get_crop_status()
        assert status["corn"] == "verified"
