"""Tests for UID decoding utilities."""

import pytest

from rtgs_lab_tools.device_configuration.uid_decoding import (
    decode_both_configs,
    decode_sensor_configuration_uid,
    decode_system_configuration_uid,
    format_sensor_config,
    format_system_config,
    parse_uid,
)


class TestDecodeSystemConfigurationUid:
    """Test the system configuration UID decoding function."""

    def test_decode_basic_system_config(self):
        """Test decoding a basic system configuration UID."""
        # Create a test UID with known values
        # log_period=300 (0x012C), backhaul_count=1, power_save_mode=2,
        # logging_mode=2, num_aux_talons=1, num_i2c_talons=1, num_sdi12_talons=1
        # 0x012C1A55 = 19439189
        uid = 0x012C1A55

        config = decode_system_configuration_uid(uid)

        assert config["log_period"] == 300
        assert config["backhaul_count"] == 1
        assert config["power_save_mode"] == 2
        assert config["logging_mode"] == 2
        assert config["num_aux_talons"] == 1
        assert config["num_i2c_talons"] == 1
        assert config["num_sdi12_talons"] == 1

    def test_decode_zero_uid(self):
        """Test decoding a zero UID."""
        uid = 0
        config = decode_system_configuration_uid(uid)

        for key in config:
            assert config[key] == 0

    def test_decode_max_values(self):
        """Test decoding with maximum possible values."""
        # Set all bits to maximum for their respective fields
        uid = 0xFFFFFFFF
        config = decode_system_configuration_uid(uid)

        assert config["log_period"] == 0xFFFF  # 16 bits
        assert config["backhaul_count"] == 0xF  # 4 bits
        assert config["power_save_mode"] == 0x3  # 2 bits
        assert config["logging_mode"] == 0x3  # 2 bits
        assert config["num_aux_talons"] == 0x3  # 2 bits
        assert config["num_i2c_talons"] == 0x3  # 2 bits
        assert config["num_sdi12_talons"] == 0x3  # 2 bits

    def test_decode_system_config_bit_masks(self):
        """Test specific bit mask operations."""
        # Test with specific bit patterns
        uid = 0x12345678
        config = decode_system_configuration_uid(uid)

        # Verify bit extraction
        assert config["log_period"] == (0x12345678 >> 16) & 0xFFFF
        assert config["backhaul_count"] == (0x12345678 >> 12) & 0xF
        assert config["power_save_mode"] == (0x12345678 >> 10) & 0x3
        assert config["logging_mode"] == (0x12345678 >> 8) & 0x3
        assert config["num_aux_talons"] == (0x12345678 >> 6) & 0x3
        assert config["num_i2c_talons"] == (0x12345678 >> 4) & 0x3
        assert config["num_sdi12_talons"] == (0x12345678 >> 2) & 0x3


class TestDecodeSensorConfigurationUid:
    """Test the sensor configuration UID decoding function."""

    def test_decode_basic_sensor_config(self):
        """Test decoding a basic sensor configuration UID."""
        # Create a test UID with known values
        # num_et=0, num_haar=0, num_soil=1, num_apogee_solar=0,
        # num_co2=0, num_o2=0, num_pressure=0
        # 0x00100000 = 1048576
        uid = 0x00100000

        config = decode_sensor_configuration_uid(uid)

        assert config["num_et"] == 0
        assert config["num_haar"] == 0
        assert config["num_soil"] == 1
        assert config["num_apogee_solar"] == 0
        assert config["num_co2"] == 0
        assert config["num_o2"] == 0
        assert config["num_pressure"] == 0

    def test_decode_zero_sensor_uid(self):
        """Test decoding a zero sensor UID."""
        uid = 0
        config = decode_sensor_configuration_uid(uid)

        for key in config:
            assert config[key] == 0

    def test_decode_max_sensor_values(self):
        """Test decoding with maximum possible sensor values."""
        # Set all bits to maximum for their respective fields
        uid = 0xFFFFFFFF
        config = decode_sensor_configuration_uid(uid)

        assert config["num_et"] == 0xF  # 4 bits
        assert config["num_haar"] == 0xF  # 4 bits
        assert config["num_soil"] == 0xF  # 4 bits
        assert config["num_apogee_solar"] == 0xF  # 4 bits
        assert config["num_co2"] == 0xF  # 4 bits
        assert config["num_o2"] == 0xF  # 4 bits
        assert config["num_pressure"] == 0xF  # 4 bits

    def test_decode_sensor_config_bit_masks(self):
        """Test specific bit mask operations for sensor config."""
        # Test with specific bit patterns
        uid = 0x12345678
        config = decode_sensor_configuration_uid(uid)

        # Verify bit extraction
        assert config["num_et"] == (0x12345678 >> 28) & 0xF
        assert config["num_haar"] == (0x12345678 >> 24) & 0xF
        assert config["num_soil"] == (0x12345678 >> 20) & 0xF
        assert config["num_apogee_solar"] == (0x12345678 >> 16) & 0xF
        assert config["num_co2"] == (0x12345678 >> 12) & 0xF
        assert config["num_o2"] == (0x12345678 >> 8) & 0xF
        assert config["num_pressure"] == (0x12345678 >> 4) & 0xF


class TestFormatSystemConfig:
    """Test the system configuration formatting function."""

    def test_format_system_config_basic(self):
        """Test formatting a basic system configuration."""
        uid = 0x012C1A55  # Known values from earlier test

        formatted = format_system_config(uid)

        assert "System Configuration UID:" in formatted
        assert "0x012C1A55" in formatted
        assert "19667541" in formatted
        assert "Log Period:           300" in formatted
        assert "Backhaul Count:       1" in formatted
        assert "Power Save Mode:      2" in formatted
        assert "Logging Mode:         2" in formatted
        assert "Num Aux Talons:       1" in formatted
        assert "Num I2C Talons:       1" in formatted
        assert "Num SDI12 Talons:     1" in formatted

    def test_format_system_config_zero(self):
        """Test formatting a zero system configuration."""
        uid = 0

        formatted = format_system_config(uid)

        assert "System Configuration UID:" in formatted
        assert "0x00000000" in formatted
        assert "(0)" in formatted
        assert "Log Period:           0" in formatted
        assert "Backhaul Count:       0" in formatted


class TestFormatSensorConfig:
    """Test the sensor configuration formatting function."""

    def test_format_sensor_config_basic(self):
        """Test formatting a basic sensor configuration."""
        uid = 0x00100000  # Known values from earlier test

        formatted = format_sensor_config(uid)

        assert "Sensor Configuration UID:" in formatted
        assert "0x00100000" in formatted
        assert "1048576" in formatted
        assert "Num ET Sensors:       0" in formatted
        assert "Num Haar Sensors:     0" in formatted
        assert "Num Soil Sensors:     1" in formatted
        assert "Num Apogee Solar:     0" in formatted
        assert "Num CO2 Sensors:      0" in formatted
        assert "Num O2 Sensors:       0" in formatted
        assert "Num Pressure Sensors: 0" in formatted

    def test_format_sensor_config_zero(self):
        """Test formatting a zero sensor configuration."""
        uid = 0

        formatted = format_sensor_config(uid)

        assert "Sensor Configuration UID:" in formatted
        assert "0x00000000" in formatted
        assert "(0)" in formatted
        assert "Num ET Sensors:       0" in formatted
        assert "Num Haar Sensors:     0" in formatted


class TestParseUid:
    """Test the UID parsing function."""

    def test_parse_decimal_uid(self):
        """Test parsing decimal UID."""
        result = parse_uid("123456")
        assert result == 123456

    def test_parse_hexadecimal_uid(self):
        """Test parsing hexadecimal UID."""
        result = parse_uid("0x1E240")
        assert result == 123456

    def test_parse_hexadecimal_uppercase(self):
        """Test parsing uppercase hexadecimal UID."""
        result = parse_uid("0X1E240")
        assert result == 123456

    def test_parse_hexadecimal_mixed_case(self):
        """Test parsing mixed case hexadecimal UID."""
        result = parse_uid("0xaBcDeF")
        assert result == 0xABCDEF

    def test_parse_uid_zero(self):
        """Test parsing zero UID."""
        assert parse_uid("0") == 0
        assert parse_uid("0x0") == 0

    def test_parse_uid_invalid_format(self):
        """Test parsing invalid UID format."""
        with pytest.raises(ValueError) as excinfo:
            parse_uid("invalid")
        assert "Invalid UID format" in str(excinfo.value)

    def test_parse_uid_invalid_hex(self):
        """Test parsing invalid hexadecimal UID."""
        with pytest.raises(ValueError) as excinfo:
            parse_uid("0xGHIJ")
        assert "Invalid UID format" in str(excinfo.value)

    def test_parse_uid_empty_string(self):
        """Test parsing empty string."""
        with pytest.raises(ValueError) as excinfo:
            parse_uid("")
        assert "Invalid UID format" in str(excinfo.value)

    def test_parse_uid_none(self):
        """Test parsing None value."""
        with pytest.raises(AttributeError):
            parse_uid(None)


class TestDecodeBothConfigs:
    """Test the combined configuration decoding function."""

    def test_decode_both_configs(self):
        """Test decoding both system and sensor configurations."""
        system_uid = 0x012C1A55
        sensor_uid = 0x00100000

        result = decode_both_configs(system_uid, sensor_uid)

        assert "System Configuration UID:" in result
        assert "Sensor Configuration UID:" in result
        assert "0x012C1A55" in result
        assert "0x00100000" in result
        assert "Log Period:           300" in result
        assert "Num Soil Sensors:     1" in result

    def test_decode_both_configs_zero(self):
        """Test decoding both configurations with zero values."""
        system_uid = 0
        sensor_uid = 0

        result = decode_both_configs(system_uid, sensor_uid)

        assert "System Configuration UID:" in result
        assert "Sensor Configuration UID:" in result
        assert "0x00000000" in result
        assert result.count("0x00000000") == 2  # Should appear twice

    def test_decode_both_configs_formatting(self):
        """Test that both configurations are properly separated."""
        system_uid = 0x012C1A55
        sensor_uid = 0x00100000

        result = decode_both_configs(system_uid, sensor_uid)

        # Should have two sections separated by double newline
        sections = result.split("\n\n")
        assert len(sections) == 2
        assert "System Configuration UID:" in sections[0]
        assert "Sensor Configuration UID:" in sections[1]
