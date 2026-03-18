"""Winter cereal cold hardiness (LT50) simulation model.

Independent Python implementation of the Winter Cereal Survival Model (WCSM)
based on the equations published in:

    Byrns, B.M., Greer, K.J., & Fowler, D.B. (2020). Modeling winter survival
    in cereals: An interactive tool. Crop Science, 60, 2408-2419.
    https://doi.org/10.1002/csc2.20246

The model estimates daily changes in cold hardiness (LT50) based on
phenological development, acclimation, dehardening, and damage due to
low-temperature stress. It uses environmental and genetic parameters to
simulate how winter cereals respond to crown temperature over time.

Mathematical formulas are drawn from the following published sources:
    - Formula 2 (Acclimation): Fowler & Limin (2004); Fowler et al. (1999)
    - Formula 4 (Threshold temp): Fowler (2008)
    - Formula 5 (Degree days): Byrns et al. (2020), Table 2
    - Formula 7 (Vernalization): Porter & Gawith (1999)
    - Formula 8 (Photoperiod): Fowler et al. (2014)
    - Formula 10 (Dehardening): Fowler & Limin (2004)
    - Formula 11 (Respiration): Bergjord et al. (2008)
    - Formula 12 (LT stress): Fowler et al. (2014)
    - VRT sigmoid: Limin & Fowler (2002)

Cultivar parameters are from Table 1 and the coefficient files distributed
with the WCSM interactive tool (University of Saskatchewan).

This implementation was validated to machine precision (max |diff| ~ 1e-14)
against the original R implementation by Byrns et al. (GPL-3 licensed,
https://github.com/byrn-baker/wcsm-usask) using R's deSolve package with
Euler integration.

RTGS Lab, 2026
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── Cultivar presets ────────────────────────────────────────────────────────
# From input_coefficients_ddfln.csv in the WCSM Shiny app (USask).
# Columns: name, LT50c, vernReq, minDD, photoCoeff, photoCritical, type, origin
CULTIVAR_PRESETS: Dict[str, Dict[str, Any]] = {
    "Norstar": {
        "LT50c": -24.0,
        "vernReq": 49,
        "minDD": None,
        "photoCoeff": 50,
        "photoCritical": 13.5,
        "type": "Winter Wheat",
        "origin": "Western Canada",
    },
    "Cougar": {
        "LT50c": -28.3,
        "vernReq": 49,
        "minDD": None,
        "photoCoeff": 50,
        "photoCritical": 13.5,
        "type": "Winter rye",
        "origin": "Western Canada",
    },
    "CDC Falcon": {
        "LT50c": -22.6,
        "vernReq": 49,
        "minDD": None,
        "photoCoeff": 50,
        "photoCritical": 13.5,
        "type": "Winter Wheat",
        "origin": "Western Canada",
    },
    "Kharkov": {
        "LT50c": -20.3,
        "vernReq": 49,
        "minDD": None,
        "photoCoeff": 50,
        "photoCritical": 13.5,
        "type": "Winter Wheat",
        "origin": "Russia",
    },
    "Jagger": {
        "LT50c": -20.0,
        "vernReq": 49,
        "minDD": None,
        "photoCoeff": 50,
        "photoCritical": 13.5,
        "type": "Winter Wheat",
        "origin": "Kansas",
    },
    "Dicktoo": {
        "LT50c": -17.5,
        "vernReq": 0,
        "minDD": 325,
        "photoCoeff": 60,
        "photoCritical": 13.5,
        "type": "Facultative Barley",
        "origin": "North Dakota",
    },
    "Gazelle": {
        "LT50c": -11.6,
        "vernReq": 0,
        "minDD": 350,
        "photoCoeff": 53,
        "photoCritical": 13.5,
        "type": "Spring rye",
        "origin": "Western Canada",
    },
    "Sisler": {
        "LT50c": -7.5,
        "vernReq": 0,
        "minDD": 325,
        "photoCoeff": 0,
        "photoCritical": 13.5,
        "type": "Spring Barley",
        "origin": "Western Canada",
    },
}


def get_cultivar_names() -> List[str]:
    """Return sorted list of available cultivar preset names."""
    return sorted(CULTIVAR_PRESETS.keys())


def get_cultivar_parameters(name: str) -> Dict[str, Any]:
    """Return parameters for a named cultivar preset.

    Args:
        name: Cultivar name (case-sensitive).

    Returns:
        Dict with keys: LT50c, vernReq, minDD, photoCoeff, photoCritical,
        type, origin.

    Raises:
        KeyError: If cultivar name is not found.
    """
    if name not in CULTIVAR_PRESETS:
        available = ", ".join(get_cultivar_names())
        raise KeyError(f"Unknown cultivar '{name}'. Available: {available}")
    return dict(CULTIVAR_PRESETS[name])


# ── Initial state ───────────────────────────────────────────────────────────

INITIAL_STATE: Dict[str, float] = {
    "LT50raw": -3.0,
    "minLT50": -3.0,
    "dehardAmt": 0.0,
    "dehardAmtStress": 0.0,
    "mflnFraction": 0.0,
    "photoReqFraction": 0.0,
    "accAmt": 0.0,
    "vernDays": 0.0,
    "vernProg": 0.0,
    "respProg": 0.0,
}


# ── Model core ──────────────────────────────────────────────────────────────


class WinterInjuryModel:
    """Winter cereal cold hardiness simulation.

    Simulates the daily evolution of LT50 (temperature at which 50% of plants
    are killed) for winter cereals using an Euler integration of coupled
    phenological and hardiness equations.

    Args:
        parameters: Dict with keys minDD, photoCoeff, photoCritical, vernReq,
            initLT50, LT50c.
        daylengths: 0-indexed sequence of daily daylength values (hours).
        crown_temps: 0-indexed sequence of daily crown temperature values (C).
    """

    def __init__(
        self,
        parameters: Dict[str, float],
        daylengths: Any,
        crown_temps: Any,
    ):
        self.params = parameters
        self.daylengths = np.asarray(daylengths, dtype=float)
        self.crown_temps = np.asarray(crown_temps, dtype=float)

    def _delay(self, t: int, d: int) -> np.ndarray:
        """Return crown temps over a trailing window (R DELAY equivalent)."""
        r_t = t + 1
        start = max(0, r_t - d - 1)
        return self.crown_temps[start : r_t]

    def model_step(
        self, t: int, Y: Dict[str, float]
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Compute one Euler step of the winter injury model.

        Args:
            t: Current timestep (0-based).
            Y: Current state variables.

        Returns:
            (derivatives, diagnostics) tuple of dicts.
        """
        # Unpack state
        vernDays = Y["vernDays"]
        dehardAmt = Y["dehardAmt"]
        dehardAmtStress = Y["dehardAmtStress"]
        accAmt = Y["accAmt"]
        respProg = Y["respProg"]
        LT50raw = Y["LT50raw"]
        photoReqFraction = Y["photoReqFraction"]
        minLT50 = Y["minLT50"]
        mflnFraction = Y["mflnFraction"]
        vernProg = Y["vernProg"]

        # Unpack parameters
        minDD = self.params["minDD"]
        photoCoeff = self.params["photoCoeff"]
        photoCritical = self.params["photoCritical"]
        vernReq = self.params["vernReq"]
        initLT50 = self.params["initLT50"]
        LT50c = self.params["LT50c"]

        # Environmental inputs
        crownTemp = float(self.crown_temps[t])
        daylength = float(self.daylengths[t])

        fiveDayTemp = self._delay(t, 10)
        fiveDayTempMean = float(np.mean(fiveDayTemp))
        if len(fiveDayTemp) < 2:
            fiveDayTempSD = float("nan")
        else:
            fiveDayTempSD = float(np.std(fiveDayTemp, ddof=1))

        # Developmental progress
        photoProg = min(photoReqFraction, 1.0) if photoCoeff > 0 else 0.0
        LT50 = min(initLT50, LT50raw)
        vernSaturation = min(vernDays / vernReq, 1.0) if vernReq > 0 else 1.0

        # Threshold induction temperature [Formula 4]
        thresholdTemp = 3.7214 - 0.4011 * LT50c
        LT50DamageAdj = LT50c - dehardAmtStress

        # Min LT50 tracking
        LT50MinFlow = (LT50 - minLT50) if LT50 < minLT50 else 0.0

        # Degree-day requirement [Formula 5]
        DDReq = max(minDD, (0.95 * minDD - 340) * (crownTemp - 2) + minDD)
        mflnFlow = max(crownTemp, 0.0) / DDReq

        # Vernalization rate [Formula 7]
        if crownTemp > -1.3 and crownTemp < 10:
            vernRate = 1.0
        elif crownTemp >= 10 and crownTemp < 12:
            vernRate = 0.364 * (
                3.313 * (crownTemp + 1.3) ** 0.423
                - (crownTemp + 1.3) ** 0.846
            )
        else:
            vernRate = 0.0

        # VRT progress [Formula 4]
        VRProg = min(min(min(1.0, mflnFraction), photoProg), vernSaturation)
        VRFactor = 1.0 / (1.0 + np.exp(80.0 * (VRProg - 0.9)))

        # Respiration stress [Formula 11]
        if (
            fiveDayTempMean < 1.5
            and fiveDayTempMean > -1
            and fiveDayTempSD < 0.75
        ):
            respFlow = 0.54 * (np.exp(0.84 + 0.051 * crownTemp) - 2) / 1.85
        else:
            respFlow = 0.0

        # Dehardening [Formula 10]
        dehardRate = 5.05 / (
            1.0 + np.exp(4.35 - 0.28 * min(crownTemp, thresholdTemp))
        )
        if respFlow > 0:
            dehardFlow = 0.0
        elif crownTemp > thresholdTemp and LT50 < initLT50:
            dehardFlow = dehardRate
        elif crownTemp > initLT50 and LT50 < initLT50:
            dehardFlow = dehardRate * (1.0 - VRFactor)
        else:
            dehardFlow = 0.0

        # LT stress [Formula 12]
        if (
            LT50 < crownTemp
            and (minLT50 / 2.0) > crownTemp
            and (LT50 - dehardAmtStress < initLT50)
            and crownTemp < initLT50
        ):
            LTStressFlow = abs(
                (minLT50 - crownTemp)
                / np.exp(-0.654 * (minLT50 - crownTemp) - 3.74)
            )
        else:
            LTStressFlow = 0.0

        # Photoperiod [Formula 8]
        if crownTemp > 0 and respFlow == 0:
            photoFactor = abs(
                (
                    3.5
                    / (
                        1.0
                        + np.exp(
                            0.504 * (daylength - photoCritical)
                            - 0.321 * (crownTemp - 13.242)
                        )
                    )
                )
                - 3.5
            )
        else:
            photoFactor = 0.0
        photoFlow = photoFactor / (3.25 * photoCoeff) if photoCoeff > 0 else 0.0

        # Acclimation [Formula 2]
        accRate = max(
            0.0, 0.014 * (thresholdTemp - crownTemp) * (LT50 - LT50DamageAdj)
        )
        if respFlow > 0:
            accFlow = 0.0
        elif LTStressFlow == 0:
            accFlow = VRFactor * accRate
        else:
            accFlow = 0.0

        derivatives = {
            "dLT50raw": respFlow + LTStressFlow + dehardFlow - accFlow,
            "dminLT50": LT50MinFlow,
            "ddehardAmt": -dehardFlow,
            "ddehardAmtStress": -respFlow - LTStressFlow,
            "dmflnFraction": mflnFlow,
            "dphotoReqFraction": photoFlow,
            "daccAmt": accFlow,
            "dvernDays": vernRate,
            "dvernProg": vernRate / vernReq if vernReq else 0.0,
            "drespProg": respFlow,
        }

        diagnostics = {
            "vernSaturation": vernSaturation,
            "respiration": respFlow,
            "daylength": daylength,
            "temperature": crownTemp,
        }

        return derivatives, diagnostics


# ── Simulation runner ───────────────────────────────────────────────────────


def run_simulation(
    parameters: Dict[str, float],
    crown_temps: List[float],
    daylengths: List[float],
) -> List[Dict[str, float]]:
    """Run a full-season Euler simulation of the winter injury model.

    Args:
        parameters: Model parameters dict with keys minDD, photoCoeff,
            photoCritical, vernReq, initLT50, LT50c.
        crown_temps: Daily crown temperatures (C), 0-indexed.
        daylengths: Daily daylengths (hours), 0-indexed.

    Returns:
        List of dicts, one per timestep (including initial state at index 0).
        Each dict contains all state variables plus diagnostics.
    """
    n = min(len(crown_temps), len(daylengths))
    model = WinterInjuryModel(parameters, daylengths[:n], crown_temps[:n])

    Y = dict(INITIAL_STATE)
    records = [{"time": 0, **Y}]

    for t in range(n):
        d, diag = model.model_step(t, Y)
        Y = {k: Y[k] + d["d" + k] for k in Y}
        records.append(
            {
                "time": t + 1,
                **Y,
                "LT50": min(Y["LT50raw"], parameters["initLT50"]),
                "temperature": diag["temperature"],
                "daylength": diag["daylength"],
                "respiration": diag["respiration"],
                "vernSaturation": diag["vernSaturation"],
            }
        )

    return records


def load_csv_column(path: str, column: str) -> List[float]:
    """Load a single numeric column from a CSV file.

    Args:
        path: Path to CSV file.
        column: Column header name.

    Returns:
        List of float values.

    Raises:
        FileNotFoundError: If file does not exist.
        KeyError: If column is not found in the CSV.
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {path}")

    values: List[float] = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        if column not in (reader.fieldnames or []):
            raise KeyError(
                f"Column '{column}' not found in {path}. "
                f"Available: {reader.fieldnames}"
            )
        for row in reader:
            values.append(float(row[column]))
    return values
