"""
SmartServe GIS - Phase 1: Spatial Data Engineering
Script 1: Validate Geometries, CRS, Attributes, and Duplicates
Path: analysis/data_engineering/01_validate_geometries_and_crs.py

Tasks:
1. Validate geometry validity (shapely.is_valid) across all 20 service subcategories and boundaries.
2. Verify native Coordinate Reference System (CRS) for all datasets.
3. Check attribute completeness (null values, data types, value distributions).
4. Detect duplicate OSM IDs and exact coordinate duplicates.
5. Compute projected coordinates in UTM Zone 43N (EPSG:32643) for planar metric calculations.
6. Export structured JSON report to data/analysis/data_validation_report.json.
"""

import os
import sys
import json
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Paths
DATA_DIR = PROJECT_ROOT / "data"
CLEANED_DIR = DATA_DIR / "cleaned"
FINAL_DIR = DATA_DIR / "final"
BOUNDARY_DIR = DATA_DIR / "boundary"
ANALYSIS_OUT_DIR = DATA_DIR / "analysis"
ANALYSIS_OUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECTED_CRS = "EPSG:32643"  # WGS 84 / UTM Zone 43N (Pune: ~73.85 E, 18.52 N)
EXPECTED_CRS = "EPSG:4326"

def validate_all_datasets():
    print("=" * 80)
    print("  SMARTSERVE GIS - SPATIAL DATA ENGINEERING: VALIDATION & AUDIT")
    print("=" * 80)
    print(f"[INFO] Storage/Exchange CRS Expected : {EXPECTED_CRS}")
    print(f"[INFO] Planar Projected CRS Target  : {PROJECTED_CRS} (UTM Zone 43N)")

    report = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "projected_crs": PROJECTED_CRS,
        "boundaries_validation": {},
        "services_master_validation": {},
        "subcategories_validation": [],
        "overall_summary": {}
    }

    # -------------------------------------------------------------------------
    # 1. VALIDATE MUNICIPAL BOUNDARIES
    # -------------------------------------------------------------------------
    print("\n--- 1. AUDITING MUNICIPAL BOUNDARY DATASETS ---")
    boundary_files = {
        "pmc": BOUNDARY_DIR / "pmc.geojson",
        "pcmc": BOUNDARY_DIR / "pcmc.geojson",
        "combined": BOUNDARY_DIR / "pmc_pcmc_combined.geojson",
        "study_area": BOUNDARY_DIR / "study_area.geojson"
    }

    for name, path in boundary_files.items():
        if not path.exists():
            print(f"[ERROR] Boundary file not found: {path}")
            continue

        gdf_b = gpd.read_file(path)
        geom_valid = gdf_b.geometry.is_valid.all()
        geom_types = list(gdf_b.geometry.geom_type.unique())
        crs_str = str(gdf_b.crs)

        # Reproject to UTM Zone 43N for metric area calculation
        gdf_proj = gdf_b.to_crs(PROJECTED_CRS)
        area_sqkm = float(gdf_proj.geometry.area.sum() / 1e6)
        bounds = [round(b, 6) for b in gdf_b.total_bounds]

        report["boundaries_validation"][name] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "feature_count": len(gdf_b),
            "native_crs": crs_str,
            "crs_valid": (crs_str == EXPECTED_CRS),
            "all_geometries_valid": bool(geom_valid),
            "geometry_types": geom_types,
            "bounding_box_wsen": bounds,
            "projected_area_sqkm_utm43n": round(area_sqkm, 2)
        }

        print(f"  [BOUNDARY] {name.upper():<12} | Features: {len(gdf_b)} | CRS: {crs_str:<10} | Valid: {geom_valid!s:<5} | Area: {area_sqkm:8.2f} km²")

    # -------------------------------------------------------------------------
    # 2. VALIDATE CONSOLIDATED MASTER DATASET (data/final/all_services.geojson)
    # -------------------------------------------------------------------------
    print("\n--- 2. AUDITING MASTER SERVICES DATASET ---")
    master_path = FINAL_DIR / "all_services.geojson"
    gdf_master = gpd.read_file(master_path)

    total_records = len(gdf_master)
    crs_str = str(gdf_master.crs)
    all_valid = gdf_master.geometry.is_valid.all()
    all_points = (gdf_master.geometry.geom_type == "Point").all()

    # Attribute completeness check
    required_cols = ["id", "name", "category", "subcategory", "latitude", "longitude", "municipality"]
    missing_counts = {col: int(gdf_master[col].isnull().sum()) for col in required_cols if col in gdf_master.columns}

    # Duplicate check on osm_id (excluding None/empty)
    osm_ids = gdf_master["osm_id"].dropna()
    osm_duplicates = int(osm_ids.duplicated().sum())

    # Exact coordinate duplicate check
    coords = list(zip(gdf_master.geometry.x, gdf_master.geometry.y))
    coord_duplicates = len(coords) - len(set(coords))

    # Municipality counts
    muni_counts = gdf_master["municipality"].value_counts().to_dict()

    # Reproject to UTM Zone 43N to verify reprojection behavior
    gdf_proj = gdf_master.to_crs(PROJECTED_CRS)
    gdf_master["utm_x"] = gdf_proj.geometry.x.round(2)
    gdf_master["utm_y"] = gdf_proj.geometry.y.round(2)

    report["services_master_validation"] = {
        "file": str(master_path.relative_to(PROJECT_ROOT)),
        "total_records": total_records,
        "native_crs": crs_str,
        "all_geometries_valid": bool(all_valid),
        "all_geometry_type_point": bool(all_points),
        "missing_attributes": missing_counts,
        "duplicate_osm_ids": osm_duplicates,
        "duplicate_coordinate_pairs": coord_duplicates,
        "municipality_breakdown": muni_counts,
        "utm_zone_43n_x_range": [float(gdf_proj.geometry.x.min()), float(gdf_proj.geometry.x.max())],
        "utm_zone_43n_y_range": [float(gdf_proj.geometry.y.min()), float(gdf_proj.geometry.y.max())]
    }

    print(f"  [MASTER] Total Records      : {total_records}")
    print(f"  [MASTER] Native CRS         : {crs_str} (Match Expected: {crs_str == EXPECTED_CRS})")
    print(f"  [MASTER] All Geoms Valid    : {all_valid}")
    print(f"  [MASTER] Duplicate OSM IDs  : {osm_duplicates}")
    print(f"  [MASTER] Duplicate Coords   : {coord_duplicates} (Acceptable: co-located multi-speciality clinics / bank branches in commercial complexes)")
    print(f"  [MASTER] Municipality Count : {muni_counts}")

    # -------------------------------------------------------------------------
    # 3. AUDIT ALL 20 CLEANED SUBCATEGORY FILES
    # -------------------------------------------------------------------------
    print("\n--- 3. AUDITING ALL 20 CLEANED SUBCATEGORY LAYERS ---")
    cleaned_geojson_files = sorted(list(CLEANED_DIR.glob("*.geojson")))

    subcat_total = 0
    for geojson_file in cleaned_geojson_files:
        gdf_sub = gpd.read_file(geojson_file)
        subcat_total += len(gdf_sub)
        is_valid = gdf_sub.geometry.is_valid.all()
        categories = list(gdf_sub["category"].unique()) if "category" in gdf_sub else []
        subcats = list(gdf_sub["subcategory"].unique()) if "subcategory" in gdf_sub else []
        pmc_c = int((gdf_sub["municipality"] == "PMC").sum()) if "municipality" in gdf_sub else 0
        pcmc_c = int((gdf_sub["municipality"] == "PCMC").sum()) if "municipality" in gdf_sub else 0

        info = {
            "file": geojson_file.name,
            "count": len(gdf_sub),
            "category": categories[0] if categories else "N/A",
            "subcategory": subcats[0] if subcats else "N/A",
            "is_valid": bool(is_valid),
            "pmc_count": pmc_c,
            "pcmc_count": pcmc_c
        }
        report["subcategories_validation"].append(info)
        print(f"  - {geojson_file.name:<25} | Count: {len(gdf_sub):4d} | Valid: {is_valid!s:<5} | PMC: {pmc_c:4d} | PCMC: {pcmc_c:4d}")

    # Overall Summary
    report["overall_summary"] = {
        "total_subcategory_records": subcat_total,
        "total_master_records": total_records,
        "master_equals_subcategories": (subcat_total == total_records),
        "validation_passed": bool(all_valid and (crs_str == EXPECTED_CRS))
    }

    # Save to data/analysis/data_validation_report.json
    out_report_path = ANALYSIS_OUT_DIR / "data_validation_report.json"
    with open(out_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[SUCCESS] Validation report written to: {out_report_path}")
    print("=" * 80)
    return report

if __name__ == "__main__":
    validate_all_datasets()
