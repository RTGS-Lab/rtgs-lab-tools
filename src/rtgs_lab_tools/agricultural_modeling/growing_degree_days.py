"""Growing Degree Day (GDD) calculation functions.

RTGS Lab, 2024
Migrated from rtgsET library
"""


def calculate_gdd_original(
    t_min: float, t_max: float, t_base: float, t_upper: float
) -> float:
    """Calculate Growing Degree Days using McMaster & Wilhelm Method 1.

    Args:
        t_min: Minimum daily temperature
        t_max: Maximum daily temperature
        t_base: Base temperature threshold
        t_upper: Upper temperature threshold

    Returns:
        Growing degree days for the day

    Reference:
        McMaster, G. & Wilhelm, W. Growing degree-days: one equation,
        two interpretations (1997)
    """
    # Calculate average temperature
    t_avg = (t_max + t_min) / 2.0

    # Too cold, gdd = 0
    if t_avg < t_base:
        return 0.0

    # Too warm, cap at upper threshold
    if t_avg > t_upper:
        return t_upper - t_base

    # Normal range
    return t_avg - t_base


def calculate_gdd_modified(
    t_min: float, t_max: float, t_base: float, t_upper: float
) -> float:
    """Calculate Growing Degree Days using McMaster & Wilhelm Method 2.

    Args:
        t_min: Minimum daily temperature
        t_max: Maximum daily temperature
        t_base: Base temperature threshold
        t_upper: Upper temperature threshold

    Returns:
        Growing degree days for the day

    Reference:
        McMaster, G. & Wilhelm, W. Growing degree-days: one equation,
        two interpretations (1997)
    """
    # Adjust tMax and tMin to be within [tBase, tUpper] range
    t_max_adj = max(min(t_max, t_upper), t_base)
    t_min_adj = max(min(t_min, t_upper), t_base)

    # Calculate GDD from adjusted temperatures
    return (t_min_adj + t_max_adj) / 2.0 - t_base


# Unimlemented methods for GDD calculation
# #
# def calcImproved(header, df):

#     """
#     from Ritchie, J. & NeSmith, D. Temperature and crop development. Modeling plant and soil systems, 5–29 (1991)

#     parameters:

#         tHourly - hourly temperature
#         tBase - base temperature
#         tUpper - upper threshold temperature
#         tOpt - optimum temperature

#     """

#     # Calculate daily GDD
#     df['gddImp'] = ''

#     # Calculate cumulative GDD
#     df['cumGddImp'] = ''

#     return df


# #
# # Zhou & Wang Nonlinear method
# #

# def calcBetaDist(header, df):

#     """
#     from Zhou, G & Wang, Q. A new nonlinear method for calculating growing degree days (2018)

#     parameters:

#         tHourly - hourly temperature
#         tBase - base temperature
#         tUpper - upper threshold temperature
#         tOpt - optimum temperature

#     """

#     # Calculate daily GDD
#     df['gddBeta'] = ''

#     # Calculate cumulative GDD
#     df['cumGddBeta'] = ''

#     return df

# #
# #
# #


def calculate_corn_heat_units(
    t_min: float, t_max: float, t_base: float = 10.0
) -> float:
    """Calculate Corn Heat Units (CHU).

    Args:
        t_min: Minimum daily temperature in Celsius
        t_max: Maximum daily temperature in Celsius
        t_base: Base temperature (default 10.0°C for corn)

    Returns:
        Corn Heat Units for the day

    Note:
        CHU is a temperature-based index used to estimate if weather
        is warm enough to grow corn.

    Formula:
        CHU = (1.8 * (t_min - 4.4) + 3.33 * (t_max - t_base) - 0.084 * (t_max - t_base)^2) / 2

    Reference:
        Corn Heat Units calculator - Farmwest
        https://farmwest.com/climate/calculator-information/chu/
    """
    chu = (
        1.8 * (t_min - 4.4) + 3.33 * (t_max - t_base) - 0.084 * (t_max - t_base) ** 2.0
    ) / 2.0
    return chu
