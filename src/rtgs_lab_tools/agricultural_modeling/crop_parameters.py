"""Crop parameter database for agricultural research.

RTGS Lab, 2024
Migrated from rtgsET library
"""

from typing import Dict, List, Optional


def get_crop_parameters(crop: Optional[str] = None) -> Dict:
    """Get growing degree day parameters for agricultural crops.

    Args:
        crop: Name of the crop. If None, returns all crop parameters.

    Returns:
        Dictionary containing crop parameters including:
        - tBase: Base temperature for GDD calculations
        - tUpper: Upper threshold temperature
        - status: Verification status of parameters
        - verifiedBy: Person who verified the parameters
        - reference: Scientific reference for the parameters

    Raises:
        KeyError: If specified crop is not found in database
    """
    crops = {
        "corn": {
            "tBase": 10.0,
            "tUpper": 30.0,
            "status": "verified",
            "verifiedBy": "Samikshya Subedi",
            "reference": "Darby, H. M., & Lauer, J. G. (2002). Harvest date and hybrid influence on corn forage yield, quality, and preservation. Agronomy Journal, 94(3), 559–566.",
        },
        "sweet-corn": {
            "tBase": 10.0,
            "tUpper": 30.0,
            "status": "verified",
            "verifiedBy": "Samikshya Subedi",
            "reference": "NOTE: Need a reference.",
        },
        "soybeans": {
            "tBase": 10.0,
            "tUpper": 30.0,
            "status": "verified",
            "verifiedBy": "Samikshya Subedi",
            "reference": "S.N., Edey. (1977). Growing degree-days and crop production in Canada. In Publication Agriculture Canada (Canada). no. 1635.",
        },
        "potatoes": {
            "tBase": 7.0,
            "tUpper": 36.0,
            "status": "verified",
            "verifiedBy": "Samikshya Subedi",
            "reference": "Sands, P. J., Hackett, C., & Nix, H. A. (1979). A model of the development and bulking of potatoes (Solanum tuberosum L.) I. Derivation from well-managed field Crop. Field  Crop Research, 2, 309–331.",
        },
        "sugarbeets": {
            "tBase": 1.1,
            "tUpper": 30.0,
            "status": "verified",
            "verifiedBy": "",
            "reference": "Baskerville, G. L., & Emin, P. (1969). Rapid estimation of heat accumulation from maximum and minimum temperatures. Ecology, 50(3), 514–517.",
        },
        "wheat": {
            "tBase": 0.0,
            "tUpper": 35.0,
            "status": "verified",
            "verifiedBy": "Samikshya Subedi",
            "reference": "Baur, 1984",
        },
        "barley": {
            "tBase": 5.5,
            "tUpper": 30.0,
            "status": "pending",
            "verifiedBy": "",
            "reference": "NOTE: Need a reference and to validate parameters!",
        },
        "edible-beans": {
            "tBase": 5.0,
            "tUpper": 30.0,
            "status": "verified",
            "verifiedBy": "Samikshya Subedi",
            "reference": "NOTE: Need a reference and to validate parameters!",
        },
        "alfalfa": {
            "tBase": 5.5,
            "tUpper": 43.0,
            "status": "verified",
            "verifiedBy": "Samikshya Subedi",
            "reference": "Sharratt, B. S., Sheaffer, C. C., & Baker, D. G. (1989). Base temperature for the application of the growing-degree-day model to field-grown alfalfa. Field  Crop Research, 21(2), 95–102. https://doi.org/https://doi.org/10.1016/0378-4290(89)90045-2",
        },
        "peas": {
            "tBase": 5.0,
            "tUpper": 35.0,
            "status": "pending",
            "verifiedBy": "",
            "reference": "NOTE: Need to check tUpper value!  S.N., Edey. (1977). Growing degree-days and crop production in Canada. In Publication Agriculture Canada (Canada). no. 1635.",
        },
    }

    if crop is None:
        return crops

    if crop not in crops:
        raise KeyError(
            f"Crop '{crop}' not found in database. Available crops: {list(crops.keys())}"
        )

    return crops[crop]


def get_crop_names() -> List[str]:
    """Get a sorted list of available crop names.

    Returns:
        Sorted list of crop names available in the database
    """
    return sorted(get_crop_parameters().keys())


def get_crop_status() -> Dict[str, str]:
    """Get verification status for all crops.

    Returns:
        Dictionary mapping crop names to their verification status
    """
    crops = get_crop_parameters()
    return {name: crop["status"] for name, crop in crops.items()}
