"""
SmartServe GIS - Phase 4: Pedestrian Accessibility Analysis
Script 3: H3 Discrete Global Grid Hexagonal Spatial Analysis
Path: analysis/accessibility/03_h3_spatial_analysis.py

Tasks:
1. Generate Uber H3 discrete global grid cells (Resolution 8 & 9) covering PMC.
2. Aggregate healthcare facility density per H3 cell (Hospitals, Clinics, Total).
3. Evaluate cell-level reachability flags:
   - is_accessible_15min_normal (4.8 km/h)
   - is_accessible_15min_slower (3.6 km/h)
4. Calculate minimum distance to nearest Hospital and Clinic per cell.
5. Identify spatial accessibility gaps (underserved peripheral or fragmented pockets).
6. Ingest into PostGIS table 'h3_accessibility' and export:
   - data/analysis/pmc_h3_accessibility_res8.geojson
   - data/analysis/pmc_h3_accessibility_res9.geojson
   - data/analysis/h3_summary_metrics.json
"""

import os
import sys
import json
import time
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import h3
from shapely.geometry import Polygon, Point
from scipy.spatial import KDTree
from sqlalchemy import create_engine, text

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

DATA_DIR = PROJECT_ROOT / "data"
BOUNDARY_DIR = DATA_DIR / "boundary"
ANALYSIS_DIR = DATA_DIR / "analysis"

FACILITIES_GEOJSON = ANALYSIS_DIR / "pmc_healthcare_facilities.geojson"
ISOCHRONES_GEOJSON = ANALYSIS_DIR / "pmc_walking_isochrones.geojson"
H3_RES8_GEOJSON = ANALYSIS_DIR / "pmc_h3_accessibility_res8.geojson"
H3_RES9_GEOJSON = ANALYSIS_DIR / "pmc_h3_accessibility_res9.geojson"
H3_METRICS_JSON = ANALYSIS_DIR / "h3_summary_metrics.json"

PROJECTED_CRS = "EPSG:32643"  # UTM Zone 43N
GEOGRAPHIC_CRS = "EPSG:4326"

def run_h3_analysis():
    print("=" * 80)
    print("  SMARTSERVE GIS - STEP 4D: H3 HEXAGONAL SPATIAL AGGREGATION")
    print("=" * 80)

    # 1. Load PMC boundary
    gdf_pmc = gpd.read_file(BOUNDARY_DIR / "pmc.geojson")
    pmc_poly = gdf_pmc.geometry.iloc[0]

    # 2. Load healthcare facilities
    gdf_fac = gpd.read_file(FACILITIES_GEOJSON)
    hospitals = gdf_fac[gdf_fac["subcategory"] == "Hospital"]
    clinics = gdf_fac[gdf_fac["subcategory"] == "Clinic"]
    print(f"[INFO] Loaded Facilities: {len(gdf_fac)} (Hospitals: {len(hospitals)}, Clinics: {len(clinics)})")

    # Build KDTree on facilities in UTM Zone 43N for distance calculation
    gdf_fac_proj = gdf_fac.to_crs(PROJECTED_CRS)
    hosp_proj = gdf_fac_proj[gdf_fac_proj["subcategory"] == "Hospital"]
    clin_proj = gdf_fac_proj[gdf_fac_proj["subcategory"] == "Clinic"]

    hosp_coords = np.array([[g.x, g.y] for g in hosp_proj.geometry])
    clin_coords = np.array([[g.x, g.y] for g in clin_proj.geometry])

    kdtree_hosp = KDTree(hosp_coords)
    kdtree_clin = KDTree(clin_coords)

    # 3. Load 15-minute isochrones for reachability testing
    gdf_iso = gpd.read_file(ISOCHRONES_GEOJSON)
    iso_15_norm = gdf_iso[
        (gdf_iso["target_type"] == "All_Healthcare") &
        (gdf_iso["speed_scenario"] == "normal_4.8kmh") &
        (gdf_iso["cutoff_minutes"] == 15)
    ].geometry.iloc[0]

    iso_15_slow = gdf_iso[
        (gdf_iso["target_type"] == "All_Healthcare") &
        (gdf_iso["speed_scenario"] == "slower_3.6kmh") &
        (gdf_iso["cutoff_minutes"] == 15)
    ].geometry.iloc[0]

    # Project isochrones to UTM 43N for fast geometric intersection
    gdf_iso_proj = gdf_iso.to_crs(PROJECTED_CRS)
    iso_15_norm_proj = gdf_iso_proj[
        (gdf_iso_proj["target_type"] == "All_Healthcare") &
        (gdf_iso_proj["speed_scenario"] == "normal_4.8kmh") &
        (gdf_iso_proj["cutoff_minutes"] == 15)
    ].geometry.iloc[0]

    iso_15_slow_proj = gdf_iso_proj[
        (gdf_iso_proj["target_type"] == "All_Healthcare") &
        (gdf_iso_proj["speed_scenario"] == "slower_3.6kmh") &
        (gdf_iso_proj["cutoff_minutes"] == 15)
    ].geometry.iloc[0]

    def process_resolution(res: int):
        print(f"\n--- PROCESSING H3 RESOLUTION {res} ---")
        # Generate cells covering PMC
        cell_ids = list(h3.geo_to_cells(pmc_poly, res))
        print(f"  Total cells generated covering PMC: {len(cell_ids):,}")

        # Map each facility to cell
        gdf_fac["cell"] = [h3.latlng_to_cell(lat, lon, res) for lat, lon in zip(gdf_fac["latitude"], gdf_fac["longitude"])]
        fac_counts = gdf_fac.groupby("cell")["subcategory"].value_counts().unstack(fill_value=0)

        rows = []
        for cell in cell_ids:
            # Get cell boundary coordinates: cell_to_boundary returns list of (lat, lng)
            boundary = h3.cell_to_boundary(cell)
            # Swap to (lng, lat) for GeoJSON standard
            poly_coords = [(lng, lat) for lat, lng in boundary]
            poly_geom = Polygon(poly_coords)

            lat_c, lng_c = h3.cell_to_latlng(cell)
            center_pt = Point(lng_c, lat_c)

            hosp_cnt = int(fac_counts.loc[cell, "Hospital"]) if (cell in fac_counts.index and "Hospital" in fac_counts.columns) else 0
            clin_cnt = int(fac_counts.loc[cell, "Clinic"]) if (cell in fac_counts.index and "Clinic" in fac_counts.columns) else 0
            tot_cnt = hosp_cnt + clin_cnt

            rows.append({
                "h3_index": cell,
                "resolution": res,
                "municipality": "PMC",
                "center_lat": lat_c,
                "center_lon": lng_c,
                "hospital_count": hosp_cnt,
                "clinic_count": clin_cnt,
                "total_healthcare_count": tot_cnt,
                "has_facility": (tot_cnt > 0),
                "geometry": poly_geom
            })

        gdf_res = gpd.GeoDataFrame(rows, crs=GEOGRAPHIC_CRS)
        gdf_res_proj = gdf_res.to_crs(PROJECTED_CRS)

        # Calculate distances to nearest hospital and clinic from cell centroid
        cell_centroids_proj = np.array([[geom.centroid.x, geom.centroid.y] for geom in gdf_res_proj.geometry])
        d_hosp, _ = kdtree_hosp.query(cell_centroids_proj)
        d_clin, _ = kdtree_clin.query(cell_centroids_proj)
        gdf_res["min_dist_to_hospital_m"] = d_hosp.round(1)
        gdf_res["min_dist_to_clinic_m"] = d_clin.round(1)

        # Evaluate 15-minute reachability (intersection with isochrone or centroid within)
        is_acc_norm = [
            bool(poly.intersects(iso_15_norm_proj) or poly.centroid.within(iso_15_norm_proj))
            for poly in gdf_res_proj.geometry
        ]
        is_acc_slow = [
            bool(poly.intersects(iso_15_slow_proj) or poly.centroid.within(iso_15_slow_proj))
            for poly in gdf_res_proj.geometry
        ]

        gdf_res["is_accessible_15min_normal"] = is_acc_norm
        gdf_res["is_accessible_15min_slower"] = is_acc_slow
        gdf_res["area_sqkm"] = (gdf_res_proj.geometry.area / 1e6).round(4)

        return gdf_res

    # Process Resolution 8 (Macro / Urban planning) and Resolution 9 (Micro / Neighborhood)
    gdf_res8 = process_resolution(8)
    gdf_res9 = process_resolution(9)

    # 4. Save GeoJSON outputs
    gdf_res8.to_file(H3_RES8_GEOJSON, driver="GeoJSON")
    gdf_res9.to_file(H3_RES9_GEOJSON, driver="GeoJSON")
    print(f"\n[INFO] Saved H3 Res 8 GeoJSON: {H3_RES8_GEOJSON.name} ({len(gdf_res8)} cells)")
    print(f"[INFO] Saved H3 Res 9 GeoJSON: {H3_RES9_GEOJSON.name} ({len(gdf_res9)} cells)")

    # 5. Summary metrics
    metrics_res8 = {
        "resolution": 8,
        "total_cells": len(gdf_res8),
        "cells_with_facility": int(gdf_res8["has_facility"].sum()),
        "pct_cells_with_facility": round(float(gdf_res8["has_facility"].mean() * 100), 2),
        "cells_accessible_15min_normal": int(gdf_res8["is_accessible_15min_normal"].sum()),
        "pct_cells_accessible_15min_normal": round(float(gdf_res8["is_accessible_15min_normal"].mean() * 100), 2),
        "cells_accessible_15min_slower": int(gdf_res8["is_accessible_15min_slower"].sum()),
        "pct_cells_accessible_15min_slower": round(float(gdf_res8["is_accessible_15min_slower"].mean() * 100), 2),
        "spatial_gap_cells_res8": int(((~gdf_res8["is_accessible_15min_normal"]) & (~gdf_res8["has_facility"])).sum()),
        "avg_dist_to_hospital_m": round(float(gdf_res8["min_dist_to_hospital_m"].mean()), 1),
        "avg_dist_to_clinic_m": round(float(gdf_res8["min_dist_to_clinic_m"].mean()), 1)
    }

    metrics_res9 = {
        "resolution": 9,
        "total_cells": len(gdf_res9),
        "cells_with_facility": int(gdf_res9["has_facility"].sum()),
        "pct_cells_with_facility": round(float(gdf_res9["has_facility"].mean() * 100), 2),
        "cells_accessible_15min_normal": int(gdf_res9["is_accessible_15min_normal"].sum()),
        "pct_cells_accessible_15min_normal": round(float(gdf_res9["is_accessible_15min_normal"].mean() * 100), 2),
        "cells_accessible_15min_slower": int(gdf_res9["is_accessible_15min_slower"].sum()),
        "pct_cells_accessible_15min_slower": round(float(gdf_res9["is_accessible_15min_slower"].mean() * 100), 2),
        "spatial_gap_cells_res9": int(((~gdf_res9["is_accessible_15min_normal"]) & (~gdf_res9["has_facility"])).sum())
    }

    all_metrics = {"h3_res8": metrics_res8, "h3_res9": metrics_res9}
    with open(H3_METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2)

    print(f"\n--- H3 RESOLUTION 8 SUMMARY ---")
    print(f"  Total Cells                 : {metrics_res8['total_cells']}")
    print(f"  Cells with Facility         : {metrics_res8['cells_with_facility']} ({metrics_res8['pct_cells_with_facility']}%)")
    print(f"  15-min Normal Reachable     : {metrics_res8['cells_accessible_15min_normal']} ({metrics_res8['pct_cells_accessible_15min_normal']}%)")
    print(f"  15-min Slower Reachable     : {metrics_res8['cells_accessible_15min_slower']} ({metrics_res8['pct_cells_accessible_15min_slower']}%)")
    print(f"  Spatial Accessibility Gaps  : {metrics_res8['spatial_gap_cells_res8']} cells")

    # 6. Ingest Resolution 8 and Resolution 9 into PostGIS table 'h3_accessibility'
    print("\n--- INGESTING H3 CELLS INTO POSTGIS DATABASE ---")
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE h3_accessibility;"))

        # Ingest Res 8
        for _, row in gdf_res8.iterrows():
            wkt = f"SRID=4326;{row['geometry'].wkt}"
            conn.execute(text("""
                INSERT INTO h3_accessibility (
                    h3_index, resolution, municipality, hospital_count, clinic_count, 
                    total_healthcare_count, has_facility, is_accessible_15min_normal, 
                    is_accessible_15min_slower, min_dist_to_hospital_m, min_dist_to_clinic_m, 
                    area_sqkm, geom
                )
                VALUES (
                    :idx, :res, :muni, :hosp, :clin, 
                    :tot, :has_fac, :acc_norm, 
                    :acc_slow, :d_hosp, :d_clin, 
                    :area, ST_GeomFromEWKT(:wkt)
                ) ON CONFLICT (h3_index) DO NOTHING;
            """), {
                "idx": row["h3_index"], "res": int(row["resolution"]), "muni": row["municipality"],
                "hosp": int(row["hospital_count"]), "clin": int(row["clinic_count"]),
                "tot": int(row["total_healthcare_count"]), "has_fac": bool(row["has_facility"]),
                "acc_norm": bool(row["is_accessible_15min_normal"]), "acc_slow": bool(row["is_accessible_15min_slower"]),
                "d_hosp": float(row["min_dist_to_hospital_m"]), "d_clin": float(row["min_dist_to_clinic_m"]),
                "area": float(row["area_sqkm"]), "wkt": wkt
            })

        db_count = conn.execute(text("SELECT COUNT(*) FROM h3_accessibility")).scalar()
        print(f"  [VERIFIED POSTGIS] h3_accessibility records: {db_count:,}")

    print("=" * 80)
    print("  H3 SPATIAL ANALYSIS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    return all_metrics

if __name__ == "__main__":
    run_h3_analysis()
