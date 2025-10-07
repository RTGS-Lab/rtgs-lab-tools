# GeoParquet Selection - Decision Matrix

**Why GeoParquet as Standardized Output Format?**

## File Size Comparison (Real Dataset: protected_areas)

| Format | File Size | Relative Size |
|--------|-----------|---------------|
| **GeoParquet** | **2.9 MB** | **1.0×** ✅ |
| GeoPackage | 8 MB | 2.8× |
| Shapefile | 12 MB | 4.1× |
| GeoJSON | 45 MB | 15.5× |

**Result: 50-75% smaller than alternatives**

---

## Key Criteria Comparison

| Criteria | GeoParquet | Shapefile | GeoPackage | GeoJSON |
|----------|------------|-----------|------------|---------|
| **File Size** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Very Good | ⭐⭐ Poor |
| **Read Speed** | ⭐⭐⭐⭐⭐ Columnar | ⭐⭐⭐ Sequential | ⭐⭐⭐⭐ Indexed | ⭐⭐ Text parsing |
| **Compression** | ⭐⭐⭐⭐⭐ Built-in | ⭐⭐ Limited | ⭐⭐⭐⭐ Optional | ⭐ None |
| **Column Names** | ✅ Unlimited | ❌ 10 chars max | ✅ Unlimited | ✅ Unlimited |
| **Cloud-Native** | ⭐⭐⭐⭐⭐ Optimized | ⭐⭐ Poor | ⭐⭐⭐ Good | ⭐⭐⭐ Good |
| **GIS Support** | ⭐⭐⭐ Emerging | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐⭐ Native |

---

## Overall Scores

| Format | Performance | Storage | Future-Proof | **Total** |
|--------|-------------|---------|--------------|-----------|
| **GeoParquet** | 9/10 | 10/10 | 10/10 | **29/30** ✅ |
| GeoPackage | 8/10 | 8/10 | 7/10 | **23/30** |
| Shapefile | 7/10 | 6/10 | 4/10 | **17/30** |
| GeoJSON | 6/10 | 4/10 | 6/10 | **16/30** |

---

## Why GeoParquet Wins

✅ **50% smaller files** (2.9 MB vs 12 MB Shapefile)
✅ **Columnar storage** - read only needed columns
✅ **Built-in compression** (Snappy)
✅ **Cloud-optimized** for S3/GCS streaming
✅ **No attribute limits** (Shapefile has 10 char names)
✅ **Apache Arrow ecosystem** (Polars, DuckDB)
✅ **Future-proof** - Apache Foundation standard

**Tradeoff:** Limited desktop GIS support (but Shapefile export available as fallback)

---

## Implementation

```python
# Primary format: GeoParquet
gdf.to_parquet(output_path, compression='snappy')

# Fallback: Shapefile for legacy GIS tools
gdf.to_file(output_path, driver='ESRI Shapefile')
```