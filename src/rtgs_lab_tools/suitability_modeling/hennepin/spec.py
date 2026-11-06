"""The v1 model as run: categories, within-category weights, divisors.

Source: Hennepin_suitability_analysis@94770eb
00_suitability_model_open_source_master/src/suitability/aggregation/overall.py, verified against
full_parcels_ranked_final_v1.csv (B. Landers, 2024-11-21) by baseline.py.
"""

# key, label, weight in Overall_Value, column name in the v1 table
CATEGORIES = [
    ("SC", "Spatial Context", 0.30, "Spatial_Context"),
    ("HQ", "Habitat Quality and Diversity", 0.25, "Habitat_Quality"),
    ("SZ", "Size", 0.15, "Size"),
    ("WP", "Wildlife and Plant Conservation", 0.15, "Wildlife_Plant"),
    ("RC", "Risk of Conversion", 0.10, "Risk_of_Conserv"),
    ("WR", "Water Resources", 0.05, "Water_Res"),
]

# field, label, category, within-category weight, divisor
INPUTS = [
    ("PA_Value", "Protected Areas Nearby", "SC", 0.50, 3),
    ("NS_Value", "Natural Spaces Nearby", "SC", 0.35, 3),
    ("QR_Value", "Habitat Quality Ranking", "HQ", 0.45, 4),
    ("QC_Value", "Adjacent to Quality Community", "HQ", 0.10, 1),
    ("Lvl3_Value", "Habitat Diversity", "HQ", 0.45, 1),
    ("Size_Value", "Parcel Size", "SZ", 1.00, 1),
    ("WAN_Value", "Wildlife Action Network Rank", "WP", 0.16, 1),
    ("Bird_Value", "Important Bird Area", "WP", 0.16, 1),
    ("Bee_Value", "Pollinator (Bee) Habitat", "WP", 0.16, 2),
    ("ROD_Value", "Risk of Development", "RC", 1.00, 1),
    ("SB_Value", "Shoreland Buffer Area", "WR", 0.15, 1),
    ("FP_Value", "Floodplain Within Site", "WR", 0.20, 2),
    ("HCWI_Value", "Hennepin County Wetland Inventory Area", "WR", 0.20, 1),
    ("HW_Value", "Headwater Area", "WR", 0.15, 1),
    ("GW_Value", "Groundwater Recharge, 1996-2010", "WR", 0.15, 5),
    ("Cont_Value", "Groundwater Contamination Susceptibility", "WR", 0.15, 3),
]

CATEGORY_COLUMNS = {key: col for key, _, _, col in CATEGORIES}
CATEGORY_WEIGHTS = {key: w for key, _, w, _ in CATEGORIES}
