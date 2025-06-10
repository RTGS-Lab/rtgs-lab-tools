"""Temperature conversion functions.

RTGS Lab, 2024
Migrated from rtgsET library
"""


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert temperature from Celsius to Fahrenheit.

    Args:
        celsius: Temperature in degrees Celsius

    Returns:
        Temperature in degrees Fahrenheit

    Note:
        Uses exact conversion formula: F = (C * 9/5) + 32
    """
    return (celsius * 9.0 / 5.0) + 32.0


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert temperature from Fahrenheit to Celsius.

    Args:
        fahrenheit: Temperature in degrees Fahrenheit

    Returns:
        Temperature in degrees Celsius

    Note:
        Uses exact conversion formula: C = (F - 32) * (5/9)
    """
    return (fahrenheit - 32.0) * (5.0 / 9.0)
