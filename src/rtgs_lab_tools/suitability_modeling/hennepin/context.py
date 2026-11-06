"""Paths, v1 table, parcel geometry, file hashes. One object every change reads from."""

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely
import yaml

CONFIG_DIR = Path(__file__).parent / "config"


def load_config():
    base = yaml.safe_load((CONFIG_DIR / "base.yaml").read_text())
    changes = {}
    for f in sorted((CONFIG_DIR / "changes").glob("*.yaml")):
        entry = yaml.safe_load(f.read_text())
        changes[entry["id"]] = entry
    base["changes"] = changes
    return base


def resolve(path, delivered_root):
    return str(path).replace("${DELIVERED}", str(delivered_root))


@dataclass
class Context:
    gdb: str
    delivered: dict
    table: pd.DataFrame
    parcels: gpd.GeoDataFrame
    centroids: gpd.GeoSeries = field(init=False)
    parcels_valid: np.ndarray = field(init=False)

    def __post_init__(self):
        self.centroids = self.parcels.geometry.centroid
        self.parcels_valid = shapely.make_valid(self.parcels.geometry.to_numpy())


def load_table(config):
    return pd.read_csv(config["paths"]["v1_csv"], dtype={"PID": str})


def load_context(config, delivered_root):
    table = load_table(config)
    geo = pyogrio.read_dataframe(config["paths"]["v1_shp"], columns=["PID"], force_2d=True)
    geo = geo.set_crs(26915, allow_override=True)
    if not (geo.PID.to_numpy() == table.PID.to_numpy()).all():
        raise ValueError("v1 shapefile and csv row order differ")
    delivered = {k: resolve(v, delivered_root) for k, v in config["delivered"].items()}
    return Context(config["paths"]["gdb"], delivered, table, geo)


def sha256_path(path):
    """File: sha256 of bytes. Directory (a .gdb): sha256 of its sorted member hashes."""
    p = Path(path)
    if p.is_dir():
        digest = hashlib.sha256()
        for member in sorted(x for x in p.rglob("*") if x.is_file()):
            digest.update(member.name.encode())
            digest.update(sha256_path(member).encode())
        return digest.hexdigest()
    digest = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_date(path):
    return pd.Timestamp(os.path.getmtime(path), unit="s").strftime("%Y-%m-%d")
