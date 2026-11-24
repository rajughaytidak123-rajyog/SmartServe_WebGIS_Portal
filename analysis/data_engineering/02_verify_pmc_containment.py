"""
SmartServe GIS - Phase 1: Spatial Data Engineering
Script 2: Verify PMC Containment & Extract Healthcare Destination Facilities
Path: analysis/data_engineering/02_verify_pmc_containment.py

Tasks:
1. Perform spatial Point-in-Polygon (PIP) intersection against official PMC & PCMC polygons.
2. Verify that all 3,536 (or 3,541 in DB) PMC POIs fall strictly within the PMC boundary.
3. Verify municipality classification consistency (spatial geometry vs tabular attribute).
4. Extract the primary healthcare facilities (Hospitals & Clinics) for PMC pedestrian accessibility analysis.
5. Save analytical GeoJSON datasets in data/analysis/ without modifying original clean datasets:
   - data/analysis/pmc_healthcare_facilities.geojson (Hospitals & Clinics in PMC)
   - data/analysis/pmc_all_services.geojson (All 3,536+ PMC POIs with projected UTM coordinates)
6. Output a verification report to data/analysis/pmc_containment_report.json.
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
BOUNDARY_DIR = DATA_DIR / "boundary"
FINAL_DIR = DATA_DIR / "final"
ANALYSIS_OUT_DIR = DATA_DIR / "analysis"
ANALYSIS_OUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECTED_CRS = "EPSG:32643"  # UTM Zone 43N

def verify_containment_and_extract_targets():
    print("=" * 80)
    print("  SMARTSERVE GIS - SPATIAL DATA ENGINEERING: PMC CONTAINMENT AUDIT")
    print("=" * 80)

    # 1. Load boundaries
    pmc_boundary_path = BOUNDARY_DIR / "pmc.geojson"
    pcmc_boundary_path = BOUNDARY_DIR / "pcmc.geojson"

    gdf_pmc = gpd.read_file(pmc_boundary_path)
    gdf_pcmc = gpd.read_file(pcmc_boundary_path)

    pmc_polygon = gdf_pmc.unary_union
    pcmc_polygon = gdf_pcmc.unary_union

    print(f"[INFO] Loaded PMC boundary: {len(gdf_pmc)} polygon(s), valid={gdf_pmc.geometry.is_valid.all()}")
    print(f"[INFO] Loaded PCMC boundary: {len(gdf_pcmc)} polygon(s), valid={gdf_pcmc.geometry.is_valid.all()}")

    # 2. Load master services GeoJSON
    master_path = FINAL_DIR / "all_services.geojson"
    gdf_services = gpd.read_file(master_path)
    print(f"[INFO] Loaded master services: {len(gdf_services)} POIs")

    # 3. Spatial Point-in-Polygon (PIP) Containment Check
    # Check intersection / containment against PMC polygon
    in_pmc_mask = gdf_services.geometry.within(pmc_polygon)
    in_pcmc_mask = gdf_services.geometry.within(pcmc_polygon)

    attr_pmc_mask = (gdf_services["municipality"] == "PMC")
    attr_pcmc_mask = (gdf_services["municipality"] == "PCMC")

    pmc_spatial_count = int(in_pmc_mask.sum())
    pcmc_spatial_count = int(in_pcmc_mask.sum())
    pmc_attr_count = int(attr_pmc_mask.sum())
    pcmc_attr_count = int(attr_pcmc_mask.sum())

    # Check alignment between spatial location and attribute classification
    pmc_mismatches = gdf_services[attr_pmc_mask & (~in_pmc_mask)]
    pcmc_mismatches = gdf_services[attr_pcmc_mask & (~in_pcmc_mask)]

    print(f"\n--- MUNICIPALITY CLASSIFICATION VS SPATIAL CONTAINMENT ---")
    print(f"  PMC Attribute Count   : {pmc_attr_count}")
    print(f"  PMC Spatial PIP Count : {pmc_spatial_count}")
    print(f"  PMC Mismatches (Within 0m buffer): {len(pmc_mismatches)}")
    print(f"  PCMC Attribute Count  : {pcmc_attr_count}")
    print(f"  PCMC Spatial PIP Count: {pcmc_spatial_count}")
    print(f"  PCMC Mismatches       : {len(pcmc_mismatches)}")

    # 4. Filter PMC POIs
    gdf_pmc_services = gdf_services[attr_pmc_mask].copy()

    # Add projected coordinates (UTM Zone 43N) in meters
    gdf_pmc_proj = gdf_pmc_services.to_crs(PROJECTED_CRS)
    gdf_pmc_services["utm_x"] = gdf_pmc_proj.geometry.x.round(2)
    gdf_pmc_services["utm_y"] = gdf_pmc_proj.geometry.y.round(2)

    # 5. Extract Primary Healthcare Facilities (Hospitals & Clinics) for Walking Accessibility Analysis
    # NOTE: Pharmacies and all other services remain in the portal and in pmc_all_services!
    healthcare_subcats = ["Hospital", "Clinic"]
    gdf_pmc_healthcare = gdf_pmc_services[
        (gdf_pmc_services["category"] == "Healthcare") &
        (gdf_pmc_services["subcategory"].isin(healthcare_subcats))
    ].copy()

    hospital_count = int((gdf_pmc_healthcare["subcategory"] == "Hospital").sum())
    clinic_count = int((gdf_pmc_healthcare["subcategory"] == "Clinic").sum())
    total_healthcare = len(gdf_pmc_healthcare)

    print(f"\n--- PMC PRIMARY HEALTHCARE EXTRACTION FOR ACCESSIBILITY ---")
    print(f"  PMC Hospitals          : {hospital_count}")
    print(f"  PMC Clinics            : {clinic_count}")
    print(f"  Total Accessibility POIs: {total_healthcare}")

    # 6. Save analytical datasets in data/analysis/
    out_all_pmc = ANALYSIS_OUT_DIR / "pmc_all_services.geojson"
    out_healthcare = ANALYSIS_OUT_DIR / "pmc_healthcare_facilities.geojson"

    gdf_pmc_services.to_file(out_all_pmc, driver="GeoJSON")
    gdf_pmc_healthcare.to_file(out_healthcare, driver="GeoJSON")

    print(f"\n[INFO] Saved PMC all services layer    : {out_all_pmc} ({len(gdf_pmc_services)} features)")
    print(f"[INFO] Saved PMC healthcare facilities : {out_healthcare} ({len(gdf_pmc_healthcare)} features)")

    # 7. Generate structured containment report
    report = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "total_pois_in_master": len(gdf_services),
        "pmc_containment": {
            "attribute_tagged_pmc": pmc_attr_count,
            "spatially_within_pmc": pmc_spatial_count,
            "strictly_contained": (len(pmc_mismatches) == 0),
            "mismatch_count": len(pmc_mismatches)
        },
        "pcmc_containment": {
            "attribute_tagged_pcmc": pcmc_attr_count,
            "spatially_within_pcmc": pcmc_spatial_count,
            "strictly_contained": (len(pcmc_mismatches) == 0),
            "mismatch_count": len(pcmc_mismatches)
        },
        "pmc_service_categories_breakdown": gdf_pmc_services["category"].value_counts().to_dict(),
        "pmc_service_subcategories_breakdown": gdf_pmc_services["subcategory"].value_counts().to_dict(),
        "accessibility_study_targets": {
            "target_municipality": "PMC",
            "study_area_sqkm_utm43n": round(float(gdf_pmc.to_crs(PROJECTED_CRS).geometry.area.sum() / 1e6), 2),
            "hospitals": hospital_count,
            "clinics": clinic_count,
            "total_primary_healthcare_destinations": total_healthcare,
            "retained_categories_in_portal": list(gdf_pmc_services["category"].unique())
        }
    }

    report_path = ANALYSIS_OUT_DIR / "pmc_containment_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[SUCCESS] Containment audit written to : {report_path}")
    print("=" * 80)
    return report

if __name__ == "__main__":
    verify_containment_and_extract_targets()
