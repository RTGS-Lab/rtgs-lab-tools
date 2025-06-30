"""Distance and speed conversion functions.

RTGS Lab, 2024
Migrated from rtgsET library
"""

from math import pi


def degrees_to_radians(degrees: float) -> float:
    """Convert angle from degrees to radians.

    Args:
        degrees: Angle in degrees

    Returns:
        Angle in radians

    Note:
        π radians = 180 degrees
    """
    return pi * (degrees / 180.0)


def feet_to_meters(feet: float) -> float:
    """Convert distance from feet to meters.

    Args:
        feet: Distance in feet

    Returns:
        Distance in meters

    Note:
        By definition, 1 ft = 0.3048 m (exact conversion)
    """
    return feet * 0.3048


def meters_per_second_to_miles_per_hour(ms: float) -> float:
    """Convert speed from meters per second to miles per hour.

    Args:
        ms: Speed in meters per second

    Returns:
        Speed in miles per hour

    Note:
        Conversion factor: 1 m/s = 2.236936 mph
    """
    return ms * 2.236936


def miles_per_hour_to_meters_per_second(mph: float) -> float:
    """Convert speed from miles per hour to meters per second.

    Args:
        mph: Speed in miles per hour

    Returns:
        Speed in meters per second

    Note:
        Conversion factor: 1 mph = 0.447040 m/s
    """
    return mph * 0.447040
