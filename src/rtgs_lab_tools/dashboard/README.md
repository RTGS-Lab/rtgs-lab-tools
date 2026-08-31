# Sensor Pod Comparison Dashboard

  A Streamlit dashboard for comparing data across multiple Winter Turf sensor pods. Supports live DB
  extraction, CSV upload, and several statistical plot types.

  ## Prerequisites

  - `rtgs_lab_tools` installed (run `install.sh` first, or `uv sync`)
  - A `.env` file at the repo root with database credentials
  - UMN VPN active (required to reach `sensing-0.msi.umn.edu:5433`)

  ## Running

      uv run streamlit run dashboard.py

  Or without uv:

      python -m streamlit run dashboard.py

  ## Sidebar Controls

  ### Data Source

  **Extract Data** — pulls records from the database for the selected date range and node list.
  Progress and any errors appear below the button.

  **Upload CSV** — load an already-exported file instead of hitting the DB. Accepts both parsed CSVs
  (with a `device_name` column) and raw Particle-format CSVs (auto-detected and parsed).

  ### Advanced Settings

  Toggle the **Advanced Settings** checkbox to expose:

  | Setting | Description |
  |---|---|
  | Project name | Database project to query |
  | IQR spike removal | Replace per-device outliers with NaN before plotting |
  | IQR multiplier | Aggressiveness of spike removal (lower = stricter; default 3.0) |
  | Resample | Time-bucket the data before plotting (`None`, `1min` ... `1h`; default `15min`) |
  | Figure width / height | Plot dimensions in inches |
  | Reference node | The control pod used as the X-axis in scatter and residual plots |
  | Nodes | Edit nickname, color, and Particle hex ID per node; remove nodes; add new ones |

  Click **Save as Default** to persist your settings to `dashboard_config.json`. The file is loaded
  automatically on next launch.

  ## Sensors

  | Column | Label |
  |---|---|
  | `o2_pct` | O2 (%) |
  | `apogee_temp_c` | Apogee Temp (C) |
  | `co2_ppm` | CO2 (ppm) |
  | `soil_vwc_pct` | Soil VWC (%) |
  | `acclima_temp_c` | Acclima Soil Temp (C) |
  | `hedorah_temp_c` | Hedorah Temp (C) |

  ## Plot Types

  Select a **Parameter** and check the **Nodes** you want to include, then click a plot button.

  ### Time Series
  Line plot of the selected parameter over time, one line per node.

  ### Param-Param
  Scatter plots of each selected node vs. the reference/control node. Annotated with n, R2, Bias, and
   RMSE. Data is aligned to 1-hour buckets before comparing (devices transmit at different offsets,
  so finer grids rarely produce matching timestamps).

  ### Residuals
  Line plot of `(node - control)` over time for each non-control node.

  ### Bland-Altman
  Plots the difference `(node - control)` against the mean `(node + control) / 2`. Horizontal lines
  mark the bias and +/-1.96 sigma limits of agreement.

  ### Temperature Overlay
  One subplot per selected node, overlaying Apogee, Acclima soil, and Hedorah temperatures on a
  shared time axis.

  All plots have a **Download PNG** button (150 dpi).

  ## Plot Options

  Expand the **Plot Options** section to set a custom Y-axis label, Y-axis limits, and plot title
  before generating a chart.

  ## Default Nodes

  | Nickname | Device Name | Particle ID |
  |---|---|---|
  | Node 40 (V3) | WinterTurf_Type_A_40 | `e00fce681e37a01973a2a02e` |
  | Node 64 (V3) | WinterTurf_Type_A_64 | `e00fce6803efd010cc6e2a8e` |
  | Node 65 (Control) | WinterTurf_Type_A_65 | `e00fce68cf4d968d5f0bb856` |
  | Node 88 (V1) | WinterTurf_Type_A_88 | `e00fce681c40100f788039b6` |
  | Node 89 (V2) | WinterTurf_Type_A_89 | `e00fce68d7ecce60cbfa0453` |

  Node 65 is the default control/reference node.

  ## Configuration File

  Settings are saved to `dashboard_config.json` at the repo root. Delete the file to reset to
  defaults.
