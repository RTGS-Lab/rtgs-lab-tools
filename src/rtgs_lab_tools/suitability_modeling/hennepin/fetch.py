"""Download the public layers the Scoring Review V2 reads, clipped to Hennepin County + 1 mile.

URLs come from the spatial_data registry (download_url or service_url of each key). The registry's
own extractor reads a whole download into memory and pulls REST services statewide with no bbox;
NWI (4.14 GB state zip) and FEMA NFHL (national service) do not fit that, so this module streams
downloads to disk and queries services by the county envelope. Gap noted, not patched there.

Output, per registry key, under base.yaml public_root (not git):
    <key>/raw/<file>         the download as fetched (zip), or the REST pages as GeoJSON
    <key>/<key>.gpkg         features meeting county + 1 mile, EPSG:26915
    <key>/fetch.json         url, sha256 of raw and gpkg, feature counts, time

python -m rtgs_lab_tools.suitability_modeling.hennepin.fetch [--only key ...] [--force]
"""

import argparse
import hashlib
import json
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
import requests
import shapely

from ...spatial_data.registry.dataset_registry import get_dataset_config
from .context import CONFIG_DIR, load_config

BUFFER_M = 1609.34  # sheet: "Clip features by county boundary + 1 mile"
UA = {"User-Agent": "rtgs-lab-tools hennepin fetch (UMN RTGS Lab)"}

# registry key -> how to read it. layer: layer name inside the download (None = the only one);
# where: SQL filter applied after reading.
FETCH = {
    # every layer by its feature service: the Commons zips now hold compressed FileGDBs (CDF) that
    # GDAL's OpenFileGDB driver cannot read (dnr_native_plant_communities, 2026-11-10)
    "state_administered_lands": {}, "TNC_lands": {}, "usfws_national_realty_boundaries": {},
    "metro_conservation_corridors": {}, "dnr_native_plant_communities": {}, "MBS_sites": {},
    "WAN": {}, "conservation_opportunity_areas": {}, "rpbb_high_potential_zones": {},
    "important_bird_areas_public": {}, "audubon_migratory_stopover_water_mn": {"page": 100},
    "lakes_of_biological_significance": {}, "shallow_lakes_dnr_wildlife": {},
    "public_waters_basins_watercourses": {"also": {"watercourses": "service_url_watercourses"}},
    "nwi_wetlands": {"page": 250}, "fema_nfhl_flood_hazard_zones": {"page": 50},
    "watersheds": {}, "water_table_aquifer_vulnerability": {},
    # Met Council service answers HTTP 500 to feature queries (23 region-wide polygons); its zip reads
    "land_use_2025": {"download": True},
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _pages_sha(raw_dir):
    h = hashlib.sha256()
    for p in sorted(raw_dir.glob("page*.geojson")):
        h.update(p.read_bytes())
    return h.hexdigest()


def county_area(config):
    c = pyogrio.read_dataframe(config["paths"]["county"]).to_crs(26915)
    return shapely.buffer(c.geometry.union_all(), BUFFER_M)


def _get(url, params=None, stream=False, tries=4, post=False):
    for i in range(tries):
        try:
            if post:  # long OBJECTID lists overflow GET URLs (HTTP 404/500 on NWI, NFHL, Audubon)
                r = requests.post(url, data=params, headers=UA, timeout=300)
            else:
                r = requests.get(url, params=params, headers=UA, timeout=180, stream=stream)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + f".part{time.time_ns()}")
    with _get(url, stream=True) as r, open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    tmp.replace(dest)
    return dest


def rest_pages(url, area, raw_dir, page):
    """Query a FeatureServer/MapServer layer by the area's envelope, page by page."""
    env = gpd.GeoSeries([area], crs=26915).to_crs(4326).total_bounds
    params = {"where": "1=1", "geometry": ",".join(f"{v:.6f}" for v in env),
              "geometryType": "esriGeometryEnvelope", "inSR": 4326,
              "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "outSR": 26915,
              "f": "geojson", "returnGeometry": "true"}
    ids = _get(f"{url}/query", {**params, "returnIdsOnly": "true", "f": "json"}).json()
    oids = sorted(ids.get("objectIds") or [])
    oid_field = ids.get("objectIdFieldName", "OBJECTID")
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for i in range(0, len(oids), page):
        chunk = oids[i:i + page]
        q = {k: v for k, v in params.items() if k not in ("geometry", "geometryType", "inSR",
                                                          "spatialRel")}
        q["where"] = f"{oid_field} IN ({','.join(map(str, chunk))})"
        body = _get(f"{url}/query", q, post=True).content
        p = raw_dir / f"page{i // page:04d}.geojson"
        p.write_bytes(body)
        g = gpd.read_file(p)
        frames.append(g)
    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=26915), oids
    g = pd.concat(frames, ignore_index=True)
    g = gpd.GeoDataFrame(g, geometry="geometry", crs=frames[0].crs or 26915)
    if g.crs is None or g.crs.to_epsg() != 26915:
        # GeoJSON is lon/lat by spec; some servers honour outSR, some do not
        g = g.set_crs(4326, allow_override=True) if abs(g.total_bounds[0]) <= 180 else g
        g = g.to_crs(26915)
    return g, oids


def read_zip(zpath, layer, area):
    """Pick the vector file inside the zip and read the features meeting the area."""
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        out = zpath.parent / zpath.stem
        if not out.exists():
            z.extractall(out)
    cands = [n for n in names if n.lower().endswith((".gpkg", ".shp"))]
    gdbs = sorted({n.split(".gdb/")[0] + ".gdb" for n in names if ".gdb/" in n})
    src = out / (cands[0] if cands else gdbs[0])
    layers = [x[0] for x in pyogrio.list_layers(src)]
    if layer is None or layer not in layers:
        if layer is not None:
            raise ValueError(f"{zpath.name}: layer {layer!r} not in {layers}")
        poly = [x[0] for x in pyogrio.list_layers(src) if x[1] and "Polygon" in str(x[1])]
        layer = poly[0] if len(poly) == 1 else layers[0]
    crs = pyogrio.read_info(src, layer=layer)["crs"]
    bbox = tuple(gpd.GeoSeries([area], crs=26915).to_crs(crs).total_bounds)
    g = pyogrio.read_dataframe(src, layer=layer, bbox=bbox, force_2d=True)
    return g.to_crs(26915), str(src), layer, layers


def fetch(key, root, area, force=False):
    spec = FETCH[key]
    cfg = get_dataset_config(key)
    if cfg is None:
        raise KeyError(key)
    d = root / key
    meta_path = d / "fetch.json"
    if meta_path.exists() and not force:
        return json.loads(meta_path.read_text())
    started = time.strftime("%F %T")
    meta = {"key": key, "registry_url": cfg.get("url"), "started": started}
    if not spec.get("download"):
        url = cfg["service_url"]
        g, oids = rest_pages(url, area, d / "raw", spec.get("page", 1000))
        meta.update({"service_url": url, "ids_in_envelope": len(oids),
                     "raw_sha256": _pages_sha(d / "raw")})
        for name, field in (spec.get("also") or {}).items():
            g2, o2 = rest_pages(cfg[field], area, d / f"raw_{name}", spec.get("page", 1000))
            g2 = g2[shapely.intersects(shapely.make_valid(g2.geometry.to_numpy()), area)]
            p2 = d / f"{key}_{name}.gpkg"
            pyogrio.write_dataframe(g2.reset_index(drop=True), p2, layer=f"{key}_{name}")
            meta[name] = {"service_url": cfg[field], "features": len(g2), "gpkg": str(p2),
                          "gpkg_sha256": sha256(p2), "raw_sha256": _pages_sha(d / f"raw_{name}")}
    else:
        url = cfg["download_url"]
        z = download(url, d / "raw" / url.rstrip("/").split("/")[-1])
        g, src, layer, layers = read_zip(z, spec.get("layer"), area)
        meta.update({"download_url": url, "raw_file": str(z), "raw_sha256": sha256(z),
                     "raw_bytes": z.stat().st_size, "source": src, "layer": layer,
                     "layers_in_file": layers})
    g = g[g.geometry.notna() & ~g.geometry.is_empty]
    keep = shapely.intersects(shapely.make_valid(g.geometry.to_numpy()), area)
    g = g[keep].reset_index(drop=True)
    out = d / f"{key}.gpkg"
    tmp = d / f"{key}.tmp{time.time_ns()}.gpkg"
    pyogrio.write_dataframe(g, tmp, layer=key)
    tmp.replace(out)
    meta.update({"gpkg": str(out), "gpkg_sha256": sha256(out), "features": len(g),
                 "fields": [c for c in g.columns if c != "geometry"], "finished": time.strftime("%F %T")})
    meta_path.write_text(json.dumps(meta, indent=1))
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    config = load_config()
    root = Path(config["public_root"])
    area = county_area(config)
    for key in a.only or FETCH:
        t = time.time()
        try:
            m = fetch(key, root, area, a.force)
            print(f"{key}\t{m['features']}\t{round(time.time() - t, 1)}s", flush=True)
        except Exception as e:  # noqa: BLE001 - report every layer, fail at the end
            print(f"{key}\tFAILED\t{type(e).__name__}: {e}", flush=True)


if __name__ == "__main__":
    main()
