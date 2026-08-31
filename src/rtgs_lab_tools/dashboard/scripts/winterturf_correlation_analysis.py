"""
Side-by-side correlation analysis for WinterTurf_Type_A devices 65, 88, and 89.

Produces:
  1. Time series panel  — all variables over time, one column per device
  2. Correlation heatmap — per-device Pearson correlation matrix
  3. Pairplot / scatter grid — cross-variable scatter with regression line, faceted by device
  4. Cross-device correlation — how each variable correlates across the three devices

Usage:
    # Run parse_winterturf_data.py first, then:
    python scripts/winterturf_correlation_analysis.py [--input PATH] [--output-dir PATH]
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_INPUT = DATA_DIR / "winterturf_clean.csv"
DEFAULT_OUTPUT_DIR = DATA_DIR / "winterturf_analysis"

DEVICES = ["WinterTurf_Type_A_65", "WinterTurf_Type_A_88", "WinterTurf_Type_A_89"]
DEVICE_COLORS = {
    "WinterTurf_Type_A_65": "#1f77b4",
    "WinterTurf_Type_A_88": "#ff7f0e",
    "WinterTurf_Type_A_89": "#2ca02c",
}

SENSOR_COLS = {
    "apogee_temp_c":  "Apogee Temp (C)",
    "acclima_temp_c": "Acclima Soil Temp (C)",
    "co2_ppm":        "CO2 (ppm)",
    "o2_pct":         "O2 (%)",
    "soil_vwc_pct":   "Soil Moisture VWC (%)",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["publish_time"])
    df = df[df["device_name"].isin(DEVICES)].copy()
    df = df.sort_values("publish_time").reset_index(drop=True)
    print(f"Loaded {len(df)} rows from {path}")
    for dev in DEVICES:
        n = (df["device_name"] == dev).sum()
        print(f"  {dev}: {n} records")
    return df


def resample_device(df: pd.DataFrame, freq: str = "15min") -> pd.DataFrame:
    """Resample each device to a regular grid and return a combined DataFrame."""
    frames = []
    for dev in DEVICES:
        sub = df[df["device_name"] == dev].set_index("publish_time")
        sub = sub[list(SENSOR_COLS.keys())].resample(freq).mean()
        sub["device_name"] = dev
        frames.append(sub.reset_index())
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Plot 1 — Time series panel
# ---------------------------------------------------------------------------

def plot_time_series(df: pd.DataFrame, output_dir: Path):
    n_vars = len(SENSOR_COLS)
    n_devs = len(DEVICES)

    fig, axes = plt.subplots(
        n_vars, n_devs,
        figsize=(6 * n_devs, 3 * n_vars),
        sharex="col",
        sharey="row",
    )
    fig.suptitle("WinterTurf Type A — Time Series (Mar 10 – Mar 31, 2026)", fontsize=14, y=1.01)

    for col_idx, dev in enumerate(DEVICES):
        sub = df[df["device_name"] == dev].sort_values("publish_time")
        color = DEVICE_COLORS[dev]
        axes[0, col_idx].set_title(dev.replace("WinterTurf_Type_A_", "Device "), fontsize=11)

        for row_idx, (col, label) in enumerate(SENSOR_COLS.items()):
            ax = axes[row_idx, col_idx]
            ax.plot(sub["publish_time"], sub[col], color=color, linewidth=0.8, alpha=0.85)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=7)
            if col_idx == 0:
                ax.set_ylabel(label, fontsize=9)

    fig.tight_layout()
    out = output_dir / "01_time_series.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Plot 1b — Overlaid time series (all devices on same axes per metric)
# ---------------------------------------------------------------------------

def plot_overlay_time_series(df_raw: pd.DataFrame, output_dir: Path):
    """Use raw (non-resampled) data so readings connect as continuous lines."""
    n_vars = len(SENSOR_COLS)
    fig, axes = plt.subplots(n_vars, 1, figsize=(14, 3.5 * n_vars), sharex=True)
    fig.suptitle("WinterTurf Type A — Overlaid Time Series (Mar 10 – Mar 31, 2026)", fontsize=14)

    for ax, (col, label) in zip(axes, SENSOR_COLS.items()):
        for dev in DEVICES:
            sub = (
                df_raw[df_raw["device_name"] == dev]
                .dropna(subset=[col])
                .sort_values("publish_time")
            )
            ax.plot(
                sub["publish_time"],
                sub[col],
                label=dev.replace("WinterTurf_Type_A_", "Device "),
                color=DEVICE_COLORS[dev],
                linewidth=0.9,
                alpha=0.85,
            )
        ax.set_ylabel(label, fontsize=10)
        ax.legend(loc="upper right", fontsize=8, framealpha=0.7)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))

    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)
    fig.tight_layout()
    out = output_dir / "01b_overlay_time_series.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Plot 2 — Per-device correlation heatmaps
# ---------------------------------------------------------------------------

def plot_correlation_heatmaps(df: pd.DataFrame, output_dir: Path):
    fig, axes = plt.subplots(1, len(DEVICES), figsize=(5.5 * len(DEVICES), 5))
    fig.suptitle("Pearson Correlation — Per Device", fontsize=13)

    labels = list(SENSOR_COLS.values())

    for ax, dev in zip(axes, DEVICES):
        sub = df[df["device_name"] == dev][list(SENSOR_COLS.keys())].dropna()
        corr = sub.corr(method="pearson")
        corr.columns = labels
        corr.index = labels

        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
        sns.heatmap(
            corr,
            ax=ax,
            annot=True,
            fmt=".2f",
            cmap="RdBu_r",
            vmin=-1,
            vmax=1,
            linewidths=0.5,
            mask=mask,
            cbar=ax == axes[-1],
        )
        ax.set_title(dev.replace("WinterTurf_Type_A_", "Device "), fontsize=10)
        ax.tick_params(axis="x", rotation=30, labelsize=8)
        ax.tick_params(axis="y", rotation=0, labelsize=8)

    fig.tight_layout()
    out = output_dir / "02_correlation_heatmaps.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Plot 3 — Scatter grid (pairplot) per device
# ---------------------------------------------------------------------------

def plot_scatter_grid(df: pd.DataFrame, output_dir: Path):
    cols = list(SENSOR_COLS.keys())
    labels = list(SENSOR_COLS.values())
    n = len(cols)

    for dev in DEVICES:
        sub = df[df["device_name"] == dev][cols].dropna()
        color = DEVICE_COLORS[dev]

        fig, axes = plt.subplots(n, n, figsize=(3.5 * n, 3.5 * n))
        fig.suptitle(
            f"Scatter Grid — {dev.replace('WinterTurf_Type_A_', 'Device ')}",
            fontsize=13,
        )

        for i, (col_y, label_y) in enumerate(zip(cols, labels)):
            for j, (col_x, label_x) in enumerate(zip(cols, labels)):
                ax = axes[i, j]
                if i == j:
                    ax.hist(sub[col_x].dropna(), bins=30, color=color, alpha=0.7, edgecolor="white")
                else:
                    valid = sub[[col_x, col_y]].dropna()
                    ax.scatter(valid[col_x], valid[col_y], s=4, alpha=0.4, color=color)
                    if len(valid) > 2:
                        slope, intercept, r, p, _ = stats.linregress(valid[col_x], valid[col_y])
                        x_line = np.linspace(valid[col_x].min(), valid[col_x].max(), 100)
                        ax.plot(x_line, slope * x_line + intercept, color="black", linewidth=1)
                        ax.set_title(f"r={r:.2f}", fontsize=7, pad=2)

                if i == n - 1:
                    ax.set_xlabel(label_x, fontsize=8)
                else:
                    ax.set_xlabel("")
                if j == 0:
                    ax.set_ylabel(label_y, fontsize=8)
                else:
                    ax.set_ylabel("")
                ax.tick_params(labelsize=7)

        fig.tight_layout()
        slug = dev.replace("WinterTurf_Type_A_", "")
        out = output_dir / f"03_scatter_grid_device_{slug}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Plot 4 — Cross-device correlation (variable vs variable across devices)
# ---------------------------------------------------------------------------

def plot_cross_device(df: pd.DataFrame, output_dir: Path):
    """
    For each pair of (variable, device-A vs device-B), align timestamps and
    scatter to show how the same measurement correlates across devices.
    """
    # Pivot to wide format: one column per (device, variable)
    wide = df.pivot_table(index="publish_time", columns="device_name", values=list(SENSOR_COLS.keys()))
    wide.columns = [f"{dev}_{col}" for col, dev in wide.columns]
    wide = wide.reset_index()

    device_pairs = [
        ("WinterTurf_Type_A_65", "WinterTurf_Type_A_88"),
        ("WinterTurf_Type_A_65", "WinterTurf_Type_A_89"),
        ("WinterTurf_Type_A_88", "WinterTurf_Type_A_89"),
    ]
    pair_labels = ["65 vs 88", "65 vs 89", "88 vs 89"]

    n_vars = len(SENSOR_COLS)
    n_pairs = len(device_pairs)

    fig, axes = plt.subplots(
        n_vars, n_pairs,
        figsize=(5 * n_pairs, 4 * n_vars),
    )
    fig.suptitle("Cross-Device Correlation — Same Variable, Different Devices", fontsize=13, y=1.01)

    for col_idx, ((dev_a, dev_b), pair_lbl) in enumerate(zip(device_pairs, pair_labels)):
        axes[0, col_idx].set_title(pair_lbl, fontsize=11)
        for row_idx, (col, label) in enumerate(SENSOR_COLS.items()):
            ax = axes[row_idx, col_idx]
            col_a = f"{dev_a}_{col}"
            col_b = f"{dev_b}_{col}"

            if col_a not in wide.columns or col_b not in wide.columns:
                ax.set_visible(False)
                continue

            valid = wide[[col_a, col_b]].dropna()
            ax.scatter(valid[col_a], valid[col_b], s=5, alpha=0.35, color="#555555")

            if len(valid) > 2:
                slope, intercept, r, p, _ = stats.linregress(valid[col_a], valid[col_b])
                x_line = np.linspace(valid[col_a].min(), valid[col_a].max(), 100)
                ax.plot(x_line, slope * x_line + intercept, color="crimson", linewidth=1.2)
                p_str = f"p<0.001" if p < 0.001 else f"p={p:.3f}"
                ax.set_title(f"{pair_lbl}  r={r:.2f}  {p_str}", fontsize=8)

            short_a = dev_a.replace("WinterTurf_Type_A_", "Dev ")
            short_b = dev_b.replace("WinterTurf_Type_A_", "Dev ")
            ax.set_xlabel(f"{short_a} — {label}", fontsize=8)
            ax.set_ylabel(f"{short_b} — {label}", fontsize=8)
            ax.tick_params(labelsize=7)

    fig.tight_layout()
    out = output_dir / "04_cross_device_correlation.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("CORRELATION SUMMARY")
    print("=" * 70)
    cols = list(SENSOR_COLS.keys())
    labels = list(SENSOR_COLS.values())

    for dev in DEVICES:
        sub = df[df["device_name"] == dev][cols].dropna()
        corr = sub.corr(method="pearson")
        print(f"\n--- {dev} (n={len(sub)}) ---")
        # Print only lower triangle pairs
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                r = corr.iloc[i, j]
                valid = sub[[cols[i], cols[j]]].dropna()
                if len(valid) > 2:
                    _, _, _, p, _ = stats.linregress(valid[cols[i]], valid[cols[j]])
                    p_str = "p<0.001" if p < 0.001 else f"p={p:.3f}"
                else:
                    p_str = "n/a"
                print(f"  {labels[i]:30s} x {labels[j]:30s}  r={r:+.3f}  {p_str}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="WinterTurf correlation analysis.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--resample",
        default="15min",
        help="Resample frequency for time alignment (default: 15min)",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    df_raw = load_data(args.input)
    df = resample_device(df_raw, freq=args.resample)

    print(f"\nGenerating plots in: {args.output_dir}")
    plot_time_series(df, args.output_dir)
    plot_overlay_time_series(df_raw, args.output_dir)
    plot_correlation_heatmaps(df, args.output_dir)
    plot_scatter_grid(df, args.output_dir)
    plot_cross_device(df, args.output_dir)
    print_summary(df)

    print(f"\nDone. All outputs saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
