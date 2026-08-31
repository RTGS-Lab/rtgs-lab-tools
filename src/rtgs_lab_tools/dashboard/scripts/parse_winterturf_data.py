"""
Parse raw WinterTurf CSV data into a clean, analysis-ready CSV.

Extracts from data/v2 events:
  - apogee_temp_c  : Apogee O2 sensor temperature (°C)
  - co2_ppm        : Hedorah CO2 (ppm)
  - o2_pct         : Apogee O2 oxygen percentage (%)
  - soil_vwc_pct   : Acclima soil VWC (%) — averaged across all positions
  - acclima_temp_c : Acclima soil temperature (°C) — averaged across all positions

Usage:
    python scripts/parse_winterturf_data.py [--input PATH] [--output PATH]
"""

import argparse
import json
from pathlib import Path

import pandas as pd

DEVICE_MAP = {
    "e00fce68cf4d968d5f0bb856": "WinterTurf_Type_A_65",
    "e00fce681c40100f788039b6": "WinterTurf_Type_A_88",
    "e00fce68d7ecce60cbfa0453": "WinterTurf_Type_A_89",
}

DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_INPUT = next(
    iter(sorted(DATA_DIR.glob("Winter_Turf_v3_2026_03_10*.csv"), reverse=True)), None
)
DEFAULT_OUTPUT = DATA_DIR / "winterturf_clean.csv"


def parse_message(message: str) -> dict:
    """Extract sensor values from a data/v2 JSON message string."""
    try:
        payload = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return {}

    devices = payload.get("Data", {}).get("Devices", [])

    result = {}
    soil_vwc = []
    acclima_temps = []

    for device_entry in devices:
        for sensor_name, sensor_data in device_entry.items():
            if not isinstance(sensor_data, dict):
                continue

            if sensor_name == "Apogee O2":
                result["o2_pct"] = sensor_data.get("Oxygen_%")
                result["apogee_temp_c"] = sensor_data.get("Temperature")

            elif sensor_name == "Hedorah":
                result["co2_ppm"] = sensor_data.get("CO2")

            elif sensor_name == "Acclima Soil":
                vwc = sensor_data.get("VWC")
                temp = sensor_data.get("Temperature")
                if vwc is not None:
                    soil_vwc.append(vwc)
                if temp is not None:
                    acclima_temps.append(temp)

    if soil_vwc:
        result["soil_vwc_pct"] = sum(soil_vwc) / len(soil_vwc)
    if acclima_temps:
        result["acclima_temp_c"] = sum(acclima_temps) / len(acclima_temps)

    return result


def parse_file(input_path: Path) -> pd.DataFrame:
    print(f"Reading: {input_path}")
    df = pd.read_csv(input_path, low_memory=False)

    # Keep only data/v2 events
    df = df[df["event"] == "data/v2"].copy()
    print(f"  data/v2 rows: {len(df)}")

    # Keep only our three devices
    df = df[df["node_id"].isin(DEVICE_MAP)].copy()
    print(f"  rows after device filter: {len(df)}")

    df["publish_time"] = pd.to_datetime(df["publish_time"])
    df["device_name"] = df["node_id"].map(DEVICE_MAP)

    # Parse sensor values from each message
    parsed = df["message"].apply(parse_message)
    parsed_df = pd.DataFrame(parsed.tolist())

    result = pd.concat(
        [
            df[["publish_time", "node_id", "device_name"]].reset_index(drop=True),
            parsed_df.reset_index(drop=True),
        ],
        axis=1,
    )

    # Drop rows with no useful sensor data
    sensor_cols = ["apogee_temp_c", "acclima_temp_c", "co2_ppm", "o2_pct", "soil_vwc_pct"]
    result = result.dropna(subset=sensor_cols, how="all")
    result = result.sort_values("publish_time").reset_index(drop=True)

    return result


def main():
    parser = argparse.ArgumentParser(description="Parse WinterTurf raw CSV data.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to raw CSV file (default: latest Winter_Turf_v3_2026_03_10 file)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for clean output CSV (default: data/winterturf_clean.csv)",
    )
    args = parser.parse_args()

    if args.input is None:
        raise FileNotFoundError(f"No input file found in {DATA_DIR}")

    df = parse_file(args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    print(f"\nSaved {len(df)} rows to: {args.output}")
    print("\nColumn summary:")
    summary_cols = ["device_name", "apogee_temp_c", "acclima_temp_c", "co2_ppm", "o2_pct", "soil_vwc_pct"]
    print(df[summary_cols].groupby("device_name").describe().round(2).to_string())


if __name__ == "__main__":
    main()
