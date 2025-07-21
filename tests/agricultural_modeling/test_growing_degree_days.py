"""Tests for growing degree days calculations."""

import pytest

from rtgs_lab_tools.agricultural_modeling.growing_degree_days import (
    calculate_corn_heat_units,
    calculate_gdd_modified,
    calculate_gdd_original,
)


class TestCalculateGddOriginal:
    """Test the original GDD calculation method."""

    def test_normal_range(self):
        """Test GDD calculation in normal temperature range."""
        result = calculate_gdd_original(10.0, 20.0, 8.0, 30.0)
        expected = 15.0 - 8.0  # (10+20)/2 - 8
        assert result == expected

    def test_too_cold(self):
        """Test GDD calculation when temperature is too cold."""
        result = calculate_gdd_original(2.0, 6.0, 8.0, 30.0)
        assert result == 0.0

    def test_too_warm(self):
        """Test GDD calculation when temperature is too warm."""
        result = calculate_gdd_original(25.0, 35.0, 8.0, 30.0)
        expected = 30.0 - 8.0  # capped at upper threshold
        assert result == expected

    def test_edge_case_base_temp(self):
        """Test GDD calculation at base temperature."""
        result = calculate_gdd_original(6.0, 10.0, 8.0, 30.0)
        expected = 8.0 - 8.0  # (6+10)/2 - 8
        assert result == expected

    def test_edge_case_upper_temp(self):
        """Test GDD calculation at upper temperature."""
        result = calculate_gdd_original(28.0, 32.0, 8.0, 30.0)
        expected = 30.0 - 8.0  # capped at upper threshold
        assert result == expected


class TestCalculateGddModified:
    """Test the modified GDD calculation method."""

    def test_normal_range(self):
        """Test modified GDD calculation in normal temperature range."""
        result = calculate_gdd_modified(10.0, 20.0, 8.0, 30.0)
        expected = (10.0 + 20.0) / 2.0 - 8.0
        assert result == expected

    def test_min_temp_too_cold(self):
        """Test modified GDD when min temperature is too cold."""
        result = calculate_gdd_modified(5.0, 20.0, 8.0, 30.0)
        expected = (8.0 + 20.0) / 2.0 - 8.0  # min temp adjusted to base
        assert result == expected

    def test_max_temp_too_warm(self):
        """Test modified GDD when max temperature is too warm."""
        result = calculate_gdd_modified(10.0, 35.0, 8.0, 30.0)
        expected = (10.0 + 30.0) / 2.0 - 8.0  # max temp adjusted to upper
        assert result == expected

    def test_both_temps_adjusted(self):
        """Test modified GDD when both temperatures need adjustment."""
        result = calculate_gdd_modified(5.0, 35.0, 8.0, 30.0)
        expected = (8.0 + 30.0) / 2.0 - 8.0  # both temps adjusted
        assert result == expected

    def test_both_temps_too_cold(self):
        """Test modified GDD when both temperatures are too cold."""
        result = calculate_gdd_modified(2.0, 6.0, 8.0, 30.0)
        expected = (8.0 + 8.0) / 2.0 - 8.0  # both adjusted to base
        assert result == expected


class TestCalculateCornHeatUnits:
    """Test the corn heat units calculation."""

    def test_normal_temperatures(self):
        """Test CHU calculation with normal temperatures."""
        result = calculate_corn_heat_units(15.0, 25.0, 10.0)
        expected = (
            1.8 * (15.0 - 4.4) + 3.33 * (25.0 - 10.0) - 0.084 * (25.0 - 10.0) ** 2.0
        ) / 2.0
        assert abs(result - expected) < 0.001

    def test_default_base_temp(self):
        """Test CHU calculation with default base temperature."""
        result = calculate_corn_heat_units(15.0, 25.0)
        expected = (
            1.8 * (15.0 - 4.4) + 3.33 * (25.0 - 10.0) - 0.084 * (25.0 - 10.0) ** 2.0
        ) / 2.0
        assert abs(result - expected) < 0.001

    def test_cold_temperatures(self):
        """Test CHU calculation with cold temperatures."""
        result = calculate_corn_heat_units(5.0, 12.0, 10.0)
        expected = (
            1.8 * (5.0 - 4.4) + 3.33 * (12.0 - 10.0) - 0.084 * (12.0 - 10.0) ** 2.0
        ) / 2.0
        assert abs(result - expected) < 0.001

    def test_high_temperatures(self):
        """Test CHU calculation with high temperatures."""
        result = calculate_corn_heat_units(20.0, 35.0, 10.0)
        expected = (
            1.8 * (20.0 - 4.4) + 3.33 * (35.0 - 10.0) - 0.084 * (35.0 - 10.0) ** 2.0
        ) / 2.0
        assert abs(result - expected) < 0.001

    def test_negative_result(self):
        """Test CHU calculation that might result in negative values."""
        result = calculate_corn_heat_units(2.0, 8.0, 10.0)
        # Should handle negative results as per the formula
        expected = (
            1.8 * (2.0 - 4.4) + 3.33 * (8.0 - 10.0) - 0.084 * (8.0 - 10.0) ** 2.0
        ) / 2.0
        assert abs(result - expected) < 0.001
