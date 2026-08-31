#!/usr/bin/env python3
"""
Sensor Pod Comparison Dashboard
================================
Drop this file in the repo root and run:

    python -m streamlit run dashboard.py

Requirements:
  - rtgs_lab_tools installed  (run install.sh first)
  - .env file at repo root with DB credentials
  - UMN VPN active to reach sensing-0.msi.umn.edu:5433
"""

import copy
import io
import json
import traceback
from datetime import date, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "dashboard_config.json"


def _load_saved_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return copy.deepcopy(DEFAULT_CONFIG)


def _save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pod Comparison Dashboard",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

[data-testid="stSidebar"] {
    background: #141820 !important;
    border-right: 1px solid #2a3348;
}
[data-testid="stSidebar"] * { font-family: 'IBM Plex Sans', sans-serif; }

.stApp { background-color: #0d0f14; }

/* Extra top padding fixes title/sidebar-arrow overlap */
.block-container { padding-top: 2.8rem !important; padding-bottom: 2rem; }

h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #e2e8f0 !important;
    letter-spacing: -0.01em;
}
h1 { font-size: 1.45rem !important; margin-bottom: 0.1rem !important; }

.stButton > button[kind="primary"] {
    background: #4af0b0 !important;
    color: #0d0f14 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.04em !important;
    border: none !important;
    border-radius: 6px !important;
}
.stButton > button[kind="primary"]:hover { background: #32d898 !important; }

.stButton > button[kind="secondary"] {
    background: #1c2230 !important;
    color: #e2e8f0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.78rem !important;
    border: 1px solid #2a3348 !important;
    border-radius: 6px !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #4af0b0 !important; color: #4af0b0 !important;
}

[data-testid="metric-container"] {
    background: #141820;
    border: 1px solid #2a3348;
    border-radius: 8px;
    padding: 0.75rem 1rem !important;
}

.stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
    background: #1c2230 !important;
    border: 1px solid #2a3348 !important;
    color: #e2e8f0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.82rem !important;
    border-radius: 5px !important;
}

hr { border-color: #2a3348 !important; }
.stSuccess { background: rgba(74,240,176,0.08) !important; border-left: 3px solid #4af0b0 !important; }
.stInfo    { background: rgba(74,156,240,0.08) !important; border-left: 3px solid #4a9cf0 !important; }

/* Hide unrendered Material icon text (font not loading in local env) */
span.material-symbols-rounded,
span.material-symbols-outlined,
span.material-symbols-sharp { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  LOAD REPO TOOLS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading rtgs_lab_tools…")
def _load_tools():
    try:
        from rtgs_lab_tools.sensing_data import extract_data
        from rtgs_lab_tools.core.database import DatabaseManager
        from rtgs_lab_tools.core.config import Config

        import importlib.util
        script_path = Path(__file__).parent / "scripts" / "parse_winterturf_data.py"
        spec = importlib.util.spec_from_file_location("parse_wt", script_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        return dict(ok=True, extract_data=extract_data,
                    DatabaseManager=DatabaseManager, Config=Config,
                    parse_file=mod.parse_file, parse_module=mod)
    except Exception as exc:
        return dict(ok=False, error=str(exc), tb=traceback.format_exc())


tools = _load_tools()


# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
SENSOR_COLS = ["o2_pct", "apogee_temp_c", "co2_ppm", "soil_vwc_pct", "acclima_temp_c", "hedorah_temp_c"]
SENSOR_LABELS = {
    "o2_pct":          "O₂ (%)",
    "apogee_temp_c":   "Apogee Temp (°C)",
    "co2_ppm":         "CO₂ (ppm)",
    "soil_vwc_pct":    "Soil VWC (%)",
    "acclima_temp_c":  "Acclima Soil Temp (°C)",
    "hedorah_temp_c":  "Hedorah Temp (°C)",
}

TEMP_OVERLAY_SERIES = [
    ("apogee_temp_c",  "Apogee",        "#f0d44a"),
    ("acclima_temp_c", "Acclima Soil",  "#4af0b0"),
    ("hedorah_temp_c", "Hedorah",       "#c084fc"),
]
DEFAULT_COLORS   = ["#4af0b0", "#4a9cf0", "#f07a4a", "#c084fc", "#f0d44a", "#f07a9c", "#4af0d4"]
RESAMPLE_OPTIONS = ["None", "1min", "5min", "15min", "30min", "1h"]

# ─────────────────────────────────────────────────────────────────────────────
#  DEFAULT CONFIG
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "project":   "Winter Turf - v3",
    "days_back": 7,
    "resample":  "15min",
    "fig_w":     13,
    "fig_h":     5,
    "ctrl_device": "WinterTurf_Type_A_65",
    "cleaning": {
        "iqr_filter":     True,
        "iqr_multiplier": 3.0,
    },
    "nodes": [
        {
            "node_id":     "e00fce681e37a01973a2a02e",
            "device_name": "WinterTurf_Type_A_40",
            "nickname":    "Node 40 (V3)",
            "color":       "#9467bd",
        },
        {
            "node_id":     "e00fce6803efd010cc6e2a8e",
            "device_name": "WinterTurf_Type_A_64",
            "nickname":    "Node 64 (V3)",
            "color":       "#8c564b",
        },
        {
            "node_id":     "e00fce68cf4d968d5f0bb856",
            "device_name": "WinterTurf_Type_A_65",
            "nickname":    "Node 65 (Control)",
            "color":       "#1f77b4",
        },
        {
            "node_id":     "e00fce681c40100f788039b6",
            "device_name": "WinterTurf_Type_A_88",
            "nickname":    "Node 88 (V1)",
            "color":       "#ff7f0e",
        },
        {
            "node_id":     "e00fce68d7ecce60cbfa0453",
            "device_name": "WinterTurf_Type_A_89",
            "nickname":    "Node 89 (V2)",
            "color":       "#2ca02c",
        },
    ],
}

PLOT_STYLE = {
    "figure.facecolor":  "#141820",
    "axes.facecolor":    "#1c2230",
    "axes.edgecolor":    "#2a3348",
    "axes.labelcolor":   "#e2e8f0",
    "axes.titlecolor":   "#e2e8f0",
    "xtick.color":       "#6b7a99",
    "ytick.color":       "#6b7a99",
    "text.color":        "#e2e8f0",
    "grid.color":        "#2a3348",
    "grid.linestyle":    "--",
    "grid.alpha":        0.55,
    "legend.facecolor":  "#0d0f14",
    "legend.edgecolor":  "#2a3348",
    "font.family":       "monospace",
    "font.size":         10,
}


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "cfg" not in st.session_state:
    st.session_state.cfg = _load_saved_config()
for _k, _v in [("raw_path", None), ("clean_df", None), ("extract_log", "")]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def parse_device_map(text: str) -> dict:
    """Parse 'DeviceName: Nickname' lines → {device_name: nickname}."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            name, nick = line.split(":", 1)
            result[name.strip()] = nick.strip()
        else:
            result[line] = line
    return result


def device_map_to_text(d: dict) -> str:
    lines = []
    for name, nick in d.items():
        lines.append(f"{name}: {nick}" if name != nick else name)
    return "\n".join(lines)


def do_extract(project, start, end, node_ids, cfg_nodes=None):
    output_dir = "data/dashboard_output"
    try:
        # Patch the parser's DEVICE_MAP so any nodes added via the UI are recognised
        parse_mod = tools.get("parse_module")
        if parse_mod and cfg_nodes:
            for node in cfg_nodes:
                parse_mod.DEVICE_MAP.setdefault(
                    node["node_id"], node["device_name"]
                )

        results = tools["extract_data"](
            project=project,
            start_date=str(start),
            end_date=str(end),
            node_ids=node_ids or None,
            output_dir=output_dir,
            output_format="csv",
        )
        if not results.get("success"):
            return f"Extraction failed: {results}"

        raw_path = Path(results["output_file"])
        st.session_state.raw_path = raw_path

        df = tools["parse_file"](raw_path)
        # Strip timezone — matplotlib DateFormatter needs naive timestamps
        df["publish_time"] = pd.to_datetime(df["publish_time"]).dt.tz_localize(None)
        df = df.sort_values("publish_time")
        st.session_state.clean_df = df

        n = results.get("records_extracted", len(df))
        return f"✓  {n:,} records → {raw_path.name}"
    except Exception as exc:
        return f"✗  {exc}\n\n{traceback.format_exc()}"


def apply_iqr_filter(df: pd.DataFrame, multiplier: float) -> pd.DataFrame:
    df = df.copy()
    cols = [c for c in SENSOR_COLS if c in df.columns]
    for dev in df["device_name"].unique():
        mask = df["device_name"] == dev
        for col in cols:
            s = df.loc[mask, col]
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            df.loc[mask, col] = s.where((s >= q1 - multiplier * iqr) & (s <= q3 + multiplier * iqr))
    return df


def fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf.read()


def save_and_download(fig, fname: str):
    png = fig_to_png(fig)
    st.download_button(f"⬇  Download  {fname}", data=png,
                       file_name=fname, mime="image/png", key=f"dl_{fname}")


# ─────────────────────────────────────────────────────────────────────────────
#  PLOTTING
# ─────────────────────────────────────────────────────────────────────────────
def _apply_style():
    plt.rcParams.update(PLOT_STYLE)


def plot_timeseries(df, param, devices, colors, labels, y_label,
                    y_min, y_max, title, fig_size, resample):
    _apply_style()
    fig, ax = plt.subplots(figsize=fig_size)

    for dev in devices:
        sub = (df[df["device_name"] == dev]
               .set_index("publish_time")[param]
               .sort_index()
               .dropna())
        if sub.empty:
            continue
        if resample:
            # dropna after resample so isolated buckets connect as a line
            # rather than rendering as scattered dots.
            sub = sub.resample(resample).mean().dropna()
        ax.plot(sub.index, sub.values,
                label=labels.get(dev, dev),
                color=colors.get(dev) or None,
                linewidth=1.5)

    ax.set_xlabel("Time (UTC)", fontsize=10)
    ax.set_ylabel(y_label or SENSOR_LABELS.get(param, param), fontsize=10)
    if title:
        ax.set_title(title, fontsize=11, pad=10)
    # Single set_ylim call — two separate calls each reset the other bound.
    ax.set_ylim(
        bottom=float(y_min) if y_min is not None else None,
        top=float(y_max) if y_max is not None else None,
    )
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=6, maxticks=12))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(
        ax.xaxis.get_major_locator()
    ))
    fig.autofmt_xdate(rotation=30)
    ax.grid(True)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    return fig


def _aligned_pair(df, param, dev_a, dev_b, grid):
    """Resample both devices to the same grid and inner-join on time.

    Devices transmit at different offsets so fine grids (15min) rarely produce
    matching bucket timestamps. Use 1h as a minimum alignment resolution so
    the inner join always finds overlapping rows.
    """
    align_grid = "1h"
    s_a = (df[df["device_name"] == dev_a]
           .set_index("publish_time")[param]
           .sort_index().resample(align_grid).mean())
    s_b = (df[df["device_name"] == dev_b]
           .set_index("publish_time")[param]
           .sort_index().resample(align_grid).mean())
    merged = pd.concat([s_a.rename("a"), s_b.rename("b")], axis=1).dropna()
    return merged


def plot_param_param(df, param, devices, ctrl_dev, colors, labels,
                     y_label, y_min, y_max, resample):
    # Ensure ctrl_dev is always included as the X-axis reference
    all_devs    = devices if ctrl_dev in devices else [ctrl_dev] + list(devices)
    comparisons = [d for d in all_devs if d != ctrl_dev]
    if not comparisons:
        return None

    grid = resample if resample else "15min"
    _apply_style()
    ncols = min(len(comparisons), 3)
    nrows = (len(comparisons) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(5.5 * ncols, 5.2 * nrows),
                             squeeze=False)
    ax_label = y_label or SENSOR_LABELS.get(param, param)

    for idx, dev in enumerate(comparisons):
        ax = axes[idx // ncols][idx % ncols]
        merged = _aligned_pair(df, param, ctrl_dev, dev, grid)
        merged.columns = ["ctrl", "dev"]

        if merged.empty:
            ax.text(0.5, 0.5, "No overlapping data\n(check device names match)",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#6b7a99", fontsize=9)
            ax.set_title(labels.get(dev, dev), fontsize=10)
            continue

        lo  = min(merged["ctrl"].min(), merged["dev"].min())
        hi  = max(merged["ctrl"].max(), merged["dev"].max())
        pad = (hi - lo) * 0.06
        ref = [lo - pad, hi + pad]

        ax.plot(ref, ref, color="#6b7a99", lw=1.2, ls=":", label="1:1", zorder=1)
        ax.scatter(merged["ctrl"], merged["dev"],
                   color=colors.get(dev, DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]),
                   s=14, alpha=0.65, zorder=2)

        if y_min is not None or y_max is not None:
            lo2 = float(y_min) if y_min is not None else lo - pad
            hi2 = float(y_max) if y_max is not None else hi + pad
            ax.set_xlim(lo2, hi2); ax.set_ylim(lo2, hi2)
        else:
            ax.set_xlim(lo - pad, hi + pad)
            ax.set_ylim(lo - pad, hi + pad)

        if len(merged) > 2:
            r2   = np.corrcoef(merged["ctrl"], merged["dev"])[0, 1] ** 2
            bias = (merged["dev"] - merged["ctrl"]).mean()
            rmse = np.sqrt(((merged["dev"] - merged["ctrl"]) ** 2).mean())
            ax.text(0.04, 0.97,
                    f"n={len(merged):,}\nR²={r2:.4f}\nBias={bias:+.3f}\nRMSE={rmse:.3f}",
                    transform=ax.transAxes, fontsize=8.5, va="top", color="#e2e8f0",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#0d0f14",
                              edgecolor="#2a3348", alpha=0.85))

        ax.set_xlabel(f"{labels.get(ctrl_dev, ctrl_dev)}  —  {ax_label}", fontsize=9)
        ax.set_ylabel(f"{labels.get(dev, dev)}  —  {ax_label}", fontsize=9)
        ax.set_title(labels.get(dev, dev), fontsize=10,
                     color=colors.get(dev, "#e2e8f0"))
        ax.legend(fontsize=8)
        ax.grid(True)

    for idx in range(len(comparisons), nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    fig.suptitle(f"Parameter–Parameter  ·  {ax_label}", fontsize=11, y=1.01)
    fig.tight_layout()
    return fig


def plot_residuals(df, param, devices, ctrl_dev, colors, labels,
                   y_label, resample):
    _apply_style()
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax_label = y_label or SENSOR_LABELS.get(param, param)

    for dev in devices:
        if dev == ctrl_dev:
            continue
        merged = _aligned_pair(df, param, ctrl_dev, dev, resample)
        if merged.empty:
            continue
        resid = merged["b"] - merged["a"]
        ax.plot(resid.index, resid.values,
                label=labels.get(dev, dev),
                color=colors.get(dev), linewidth=1.3)

    ax.axhline(0, color="#6b7a99", lw=1, ls=":", zorder=0)
    ax.set_xlabel("Time (UTC)", fontsize=10)
    ax.set_ylabel(f"Residual  ({ax_label})", fontsize=10)
    ax.set_title(f"Residuals Over Time  ·  Design − Control  ·  {ax_label}", fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    fig.autofmt_xdate(rotation=30)
    ax.grid(True)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


def plot_bland_altman(df, param, devices, ctrl_dev, colors, labels,
                      y_label, resample):
    comparisons = [d for d in devices if d != ctrl_dev]
    if not comparisons:
        return None

    grid = resample if resample else "15min"
    _apply_style()
    ncols = min(len(comparisons), 3)
    nrows = (len(comparisons) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(5.5 * ncols, 5.2 * nrows),
                             squeeze=False)
    ax_label = y_label or SENSOR_LABELS.get(param, param)

    for idx, dev in enumerate(comparisons):
        ax = axes[idx // ncols][idx % ncols]
        merged = _aligned_pair(df, param, ctrl_dev, dev, grid)
        merged.columns = ["ctrl", "dev"]

        if merged.empty:
            ax.text(0.5, 0.5, "No overlapping data", ha="center",
                    va="center", transform=ax.transAxes, color="#6b7a99")
            continue

        means = (merged["ctrl"] + merged["dev"]) / 2
        diffs = merged["dev"] - merged["ctrl"]
        bias  = diffs.mean()
        sd    = diffs.std()
        color = colors.get(dev, DEFAULT_COLORS[idx % len(DEFAULT_COLORS)])

        ax.scatter(means, diffs, color=color, s=14, alpha=0.6, zorder=2)
        ax.axhline(bias,             color="#4af0b0", lw=1.3, ls="--",
                   label=f"Bias  {bias:+.3f}", zorder=3)
        ax.axhline(bias + 1.96 * sd, color="#f07a4a", lw=1, ls=":",
                   label=f"+1.96σ  {bias + 1.96*sd:+.3f}", zorder=3)
        ax.axhline(bias - 1.96 * sd, color="#f07a4a", lw=1, ls=":",
                   label=f"−1.96σ  {bias - 1.96*sd:+.3f}", zorder=3)
        ax.axhline(0, color="#6b7a99", lw=0.8, ls=":", zorder=1)

        ax.set_xlabel(f"Mean  ({ax_label})", fontsize=9)
        ax.set_ylabel(f"Difference  ({ax_label})", fontsize=9)
        ax.set_title(labels.get(dev, dev), fontsize=10, color=color)
        ax.legend(fontsize=8)
        ax.grid(True)

    for idx in range(len(comparisons), nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    fig.suptitle(f"Bland–Altman  ·  {ax_label}", fontsize=11, y=1.01)
    fig.tight_layout()
    return fig


def plot_temp_overlay(df, devices, labels, resample, fig_size):
    """One subplot per device; each subplot overlays Apogee, Acclima, and Hedorah temps."""
    series = [(col, lbl, clr) for col, lbl, clr in TEMP_OVERLAY_SERIES if col in df.columns]
    if not series:
        return None

    _apply_style()
    ncols = min(len(devices), 3)
    nrows = (len(devices) + ncols - 1) // ncols
    subplot_w = max(fig_size[0] / ncols, 5.5)
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(subplot_w * ncols, fig_size[1] * nrows),
                             squeeze=False)

    for idx, dev in enumerate(devices):
        ax = axes[idx // ncols][idx % ncols]
        sub_df = df[df["device_name"] == dev].set_index("publish_time").sort_index()

        plotted = 0
        for col, lbl, clr in series:
            if col not in sub_df.columns:
                continue
            s = sub_df[col].dropna()
            if s.empty:
                continue
            if resample:
                s = s.resample(resample).mean().dropna()
            ax.plot(s.index, s.values, label=lbl, color=clr, linewidth=1.5)
            plotted += 1

        if plotted == 0:
            ax.text(0.5, 0.5, "No temperature data", ha="center", va="center",
                    transform=ax.transAxes, color="#6b7a99", fontsize=9)

        ax.set_title(labels.get(dev, dev), fontsize=10)
        ax.set_xlabel("Time (UTC)", fontsize=9)
        ax.set_ylabel("Temperature (°C)", fontsize=9)
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(
            ax.xaxis.get_major_locator()
        ))
        ax.grid(True)
        ax.legend(fontsize=8, loc="best")

    for idx in range(len(devices), nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    fig.autofmt_xdate(rotation=30)
    fig.suptitle("Temperature Sensor Overlay  ·  Apogee / Acclima / Hedorah", fontsize=11, y=1.01)
    fig.tight_layout()
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
if not tools["ok"]:
    st.error(f"**Failed to load rtgs_lab_tools**\n\n{tools['error']}")
    with st.expander("Traceback"):
        st.code(tools.get("tb", ""))
    st.info("Make sure you ran `install.sh` and are running from the repo root.")
    st.stop()

with st.sidebar:
    st.markdown("## ⬡ Pod Dashboard")
    st.caption("Sensor Pod Comparison Tool · RTGS Lab")
    st.divider()

    cfg = st.session_state.cfg

    # ── Date Range ───────────────────────────────────────────
    st.markdown("**Date Range**")
    col_a, col_b = st.columns(2)
    start_date = col_a.date_input(
        "Start", value=date.today() - timedelta(days=cfg["days_back"])
    )
    end_date = col_b.date_input("End", value=date.today())

    # ── Extract ───────────────────────────────────────────────
    if st.button("EXTRACT DATA", use_container_width=True, type="primary"):
        node_ids = [n["node_id"] for n in cfg["nodes"]]
        with st.spinner("Extracting and parsing…"):
            msg = do_extract(cfg["project"], start_date, end_date, node_ids, cfg["nodes"])
        st.session_state.extract_log = msg

    if st.session_state.extract_log:
        log = st.session_state.extract_log
        (st.success if "✓" in log else st.error)(log)

    # ── Upload CSV ────────────────────────────────────────────
    st.divider()
    st.caption("or load an existing CSV")
    uploaded = st.file_uploader("upload", type=["csv"], label_visibility="collapsed")
    if uploaded:
        try:
            import os, tempfile
            # Save to temp file so parse_file (which takes a Path) can read it
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as _tmp:
                _tmp.write(uploaded.read())
                _tmp_path = Path(_tmp.name)
            try:
                df_up = pd.read_csv(_tmp_path, parse_dates=["publish_time"])
                if "device_name" not in df_up.columns and "message" in df_up.columns:
                    # Raw Particle CSV — parse it
                    df_up = tools["parse_file"](_tmp_path)
                    st.info("Detected raw Particle CSV — parsed automatically.")
            finally:
                os.unlink(_tmp_path)
            df_up["publish_time"] = pd.to_datetime(df_up["publish_time"]).dt.tz_localize(None)
            df_up = df_up.sort_values("publish_time")
            st.session_state.clean_df = df_up
            st.success(f"Loaded {len(df_up):,} rows from {uploaded.name}")
        except Exception as exc:
            st.error(str(exc))

    # ── Advanced Settings ─────────────────────────────────────
    st.divider()
    _show_adv = st.checkbox("Advanced Settings", value=False, key="show_adv")
    if _show_adv:
        st.markdown("**Project**")
        cfg["project"] = st.text_input(
            "Project name", value=cfg["project"], key="adv_project",
            label_visibility="collapsed",
        )

        st.markdown("**Data Cleaning**")
        if "cleaning" not in cfg:
            cfg["cleaning"] = copy.deepcopy(DEFAULT_CONFIG["cleaning"])
        cfg["cleaning"]["iqr_filter"] = st.checkbox(
            "IQR spike removal", value=cfg["cleaning"]["iqr_filter"], key="adv_iqr",
            help="Replace per-device outliers with NaN before plotting",
        )
        if cfg["cleaning"]["iqr_filter"]:
            cfg["cleaning"]["iqr_multiplier"] = st.slider(
                "IQR multiplier", min_value=1.0, max_value=6.0,
                value=float(cfg["cleaning"]["iqr_multiplier"]),
                step=0.5, key="adv_iqr_mult",
                help="Lower = more aggressive removal. 3.0 is a good default.",
            )

        st.markdown("**Graph Settings**")
        _rs_cur = cfg["resample"] if cfg["resample"] else "None"
        _rs_idx = RESAMPLE_OPTIONS.index(_rs_cur) if _rs_cur in RESAMPLE_OPTIONS else RESAMPLE_OPTIONS.index("15min")
        _rs = st.selectbox("Resample", RESAMPLE_OPTIONS, index=_rs_idx, key="adv_resample")
        cfg["resample"] = None if _rs == "None" else _rs

        _wc, _hc = st.columns(2)
        cfg["fig_w"] = _wc.slider("Width (in)",  6, 20, cfg["fig_w"], key="adv_fw")
        cfg["fig_h"] = _hc.slider("Height (in)", 3, 12, cfg["fig_h"], key="adv_fh")

        st.markdown("**Control / Reference Node**")
        _dev_nicks   = [n["nickname"]    for n in cfg["nodes"]]
        _nick_to_dev = {n["nickname"]: n["device_name"] for n in cfg["nodes"]}
        _dev_to_nick = {n["device_name"]: n["nickname"] for n in cfg["nodes"]}
        _ctrl_nick   = _dev_to_nick.get(cfg["ctrl_device"], _dev_nicks[0])
        _ctrl_idx    = _dev_nicks.index(_ctrl_nick) if _ctrl_nick in _dev_nicks else 0
        _sel_ctrl    = st.selectbox("Reference", _dev_nicks, index=_ctrl_idx,
                                    key="adv_ctrl", label_visibility="collapsed")
        cfg["ctrl_device"] = _nick_to_dev[_sel_ctrl]

        st.markdown("**Nodes**")
        for _i, _node in enumerate(cfg["nodes"]):
            st.markdown(f"*{_node['nickname']}*")
            _na, _nb, _nc = st.columns([3, 1, 1])
            _node["nickname"] = _na.text_input(
                "Nickname", value=_node["nickname"], key=f"adv_nick_{_i}",
                label_visibility="collapsed",
            )
            _node["color"] = _nb.color_picker(
                "Color", value=_node["color"], key=f"adv_color_{_i}",
                label_visibility="collapsed",
            )
            if _nc.button("Remove", key=f"adv_rm_{_i}"):
                cfg["nodes"].pop(_i)
                st.rerun()
            _node["node_id"] = st.text_input(
                "Node ID", value=_node["node_id"], key=f"adv_nodeid_{_i}",
            )

        st.markdown("**Add Node**")
        with st.form("add_node_form", clear_on_submit=True):
            _new_id    = st.text_input("Node ID (hex)", placeholder="e00fce68...")
            _new_nick  = st.text_input("Nickname",      placeholder="Node 99 (V4)")
            _new_color = st.color_picker("Color", value="#4af0b0")
            if st.form_submit_button("Add"):
                if _new_id.strip() and _new_nick.strip():
                    _slug = (
                        _new_nick.strip()
                        .replace(" ", "_").replace("(", "").replace(")", "")
                        .replace("/", "_").replace("-", "_")
                    )
                    cfg["nodes"].append({
                        "node_id":     _new_id.strip(),
                        "device_name": f"Device_{_slug}",
                        "nickname":    _new_nick.strip(),
                        "color":       _new_color,
                    })
                    st.rerun()
                else:
                    st.warning("Node ID and Nickname are required.")

        st.divider()
        if st.button("Save as Default", use_container_width=True):
            _save_config(cfg)
            st.success("Saved to dashboard_config.json")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────
cfg = st.session_state.cfg

st.markdown("# ⬡  Sensor Pod Comparison Dashboard")
st.caption(f"RTGS Lab  ·  {cfg['project']}")

if st.session_state.clean_df is None:
    st.info(
        "👈  **Get started:**  Pick a date range and click **Extract Data** in the sidebar.  "
        "You can also upload an already-parsed CSV."
    )
    st.stop()

df = st.session_state.clean_df

# Apply IQR spike removal if enabled
_cl = cfg.get("cleaning", {})
if _cl.get("iqr_filter", False):
    df = apply_iqr_filter(df, _cl.get("iqr_multiplier", 3.0))

# ─────────────────────────────────────────────────────────────────────────────
#  DATA SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📋  Data Summary", expanded=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Records", f"{len(df):,}")
    m2.metric("Devices",       df["device_name"].nunique())
    m3.metric("Start",         str(df["publish_time"].min())[:16])
    m4.metric("End",           str(df["publish_time"].max())[:16])
    if st.checkbox("Show raw data table"):
        st.dataframe(df.head(100), use_container_width=True, height=220)


# ─────────────────────────────────────────────────────────────────────────────
#  PARAMETER + NODE SELECTION
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
available_params = [c for c in SENSOR_COLS if c in df.columns]
devices_in_data  = set(df["device_name"].dropna().unique())

pc, nc = st.columns([2, 3])

with pc:
    selected_param = st.selectbox(
        "**Parameter**",
        available_params,
        format_func=lambda x: SENSOR_LABELS.get(x, x),
    )

with nc:
    st.markdown("**Nodes to include**")
    node_cols = st.columns(len(cfg["nodes"]))
    selected_devices = []
    for _i, _node in enumerate(cfg["nodes"]):
        _dev = _node["device_name"]
        _disabled = _dev not in devices_in_data
        _checked = node_cols[_i].checkbox(
            _node["nickname"],
            value=(not _disabled),
            disabled=_disabled,
            key=f"chk_{_dev}",
            help=None if not _disabled else "Not found in loaded data",
        )
        if _checked and not _disabled:
            selected_devices.append(_dev)

# Build labels/colors from config (nicknames & colors are set in Advanced Settings)
custom_labels = {n["device_name"]: n["nickname"] for n in cfg["nodes"]}
custom_colors = {n["device_name"]: n["color"]    for n in cfg["nodes"]}
ctrl_device   = cfg["ctrl_device"]
resample      = cfg["resample"]
fig_size      = (cfg["fig_w"], cfg["fig_h"])

# ── Optional plot tweaks ───────────────────────────────────────────────────
with st.expander("Plot Options"):
    y_label_in = st.text_input(
        "Y-axis label", value="",
        placeholder=SENSOR_LABELS.get(selected_param, selected_param),
    )
    ym1, ym2 = st.columns(2)
    y_min_str = ym1.text_input("Y min", value="", placeholder="auto")
    y_max_str = ym2.text_input("Y max", value="", placeholder="auto")
    y_min = float(y_min_str) if y_min_str.strip() else None
    y_max = float(y_max_str) if y_max_str.strip() else None
    plot_title = st.text_input("Plot title", value="", placeholder="Optional")


# ─────────────────────────────────────────────────────────────────────────────
#  PLOT BUTTONS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Generate Plots")

b1, b2, b3, b4 = st.columns(4)

if b1.button("Time Series", use_container_width=True, type="primary"):
    if not selected_devices:
        st.warning("Select at least one node.")
    else:
        with st.spinner("Rendering time series…"):
            fig = plot_timeseries(
                df, selected_param, selected_devices,
                custom_colors, custom_labels,
                y_label_in or None, y_min, y_max,
                plot_title or None, fig_size, resample,
            )
        st.pyplot(fig, use_container_width=True)
        fname = f"timeseries_{selected_param}_{date.today()}.png"
        save_and_download(fig, fname)
        plt.close(fig)

if b2.button("Param-Param", use_container_width=True, type="primary"):
    if len(selected_devices) < 2:
        st.warning("Select at least two nodes.")
    else:
        with st.spinner("Rendering scatter plots…"):
            fig = plot_param_param(
                df, selected_param, selected_devices, ctrl_device,
                custom_colors, custom_labels,
                y_label_in or None, y_min, y_max, resample,
            )
        if fig:
            st.pyplot(fig, use_container_width=True)
            fname = f"param_param_{selected_param}_{date.today()}.png"
            save_and_download(fig, fname)
            plt.close(fig)
        else:
            st.warning("No non-control nodes to compare.")

if b3.button("Residuals", use_container_width=True, type="primary"):
    if len(selected_devices) < 2:
        st.warning("Select at least two nodes.")
    else:
        with st.spinner("Rendering residuals…"):
            fig = plot_residuals(
                df, selected_param, selected_devices, ctrl_device,
                custom_colors, custom_labels, y_label_in or None, resample,
            )
        st.pyplot(fig, use_container_width=True)
        fname = f"residuals_{selected_param}_{date.today()}.png"
        save_and_download(fig, fname)
        plt.close(fig)

if b4.button("Bland-Altman", use_container_width=True, type="primary"):
    if len(selected_devices) < 2:
        st.warning("Select at least two nodes.")
    else:
        with st.spinner("Rendering Bland–Altman…"):
            fig = plot_bland_altman(
                df, selected_param, selected_devices, ctrl_device,
                custom_colors, custom_labels, y_label_in or None, resample,
            )
        if fig:
            st.pyplot(fig, use_container_width=True)
            fname = f"bland_altman_{selected_param}_{date.today()}.png"
            save_and_download(fig, fname)
            plt.close(fig)
        else:
            st.warning("No non-control nodes to compare.")


st.markdown("---")
st.markdown("### Temperature Overlay")
st.caption("Overlays Apogee temp, Acclima soil temp, and Hedorah temp on a shared time axis — one panel per selected node.")

if st.button("Temp Overlay", use_container_width=True, type="primary", key="btn_temp_overlay"):
    if not selected_devices:
        st.warning("Select at least one node.")
    else:
        with st.spinner("Rendering temperature overlay…"):
            fig = plot_temp_overlay(
                df, selected_devices, custom_labels, resample, fig_size,
            )
        if fig:
            st.pyplot(fig, use_container_width=True)
            fname = f"temp_overlay_{date.today()}.png"
            save_and_download(fig, fname)
            plt.close(fig)
        else:
            st.warning("No temperature columns found in the loaded data.")


# ─────────────────────────────────────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "⬡  Pod Comparison Dashboard  ·  RTGS Lab  ·  "
    "Run `python -m streamlit run dashboard.py` from repo root  ·  "
    "Requires UMN VPN for DB access"
)
