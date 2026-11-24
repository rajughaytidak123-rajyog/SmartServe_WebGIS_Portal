"""
SmartServe GIS - Phase 4: Pedestrian Accessibility Analysis
Script 5: Comparative Scenario Analysis & Visualization Generation
Path: analysis/accessibility/05_compare_scenarios.py

Tasks:
1. Aggregate and benchmark all accessibility scenarios:
   - Normal walking speed (4.8 km/h) vs Slower walking speed (3.6 km/h)
   - Hospitals (409) vs Clinics (336) vs All Healthcare (745)
   - 5-min, 10-min, and 15-min cutoffs
2. Ingest structured benchmark records into PostGIS table 'accessibility_summary'.
3. Generate high-resolution analytical comparison charts and maps:
   - analysis/accessibility/maps/isochrone_coverage_comparison.png
   - analysis/accessibility/maps/population_access_breakdown.png
   - analysis/accessibility/maps/pmc_accessibility_isochrones_map.png
   - analysis/accessibility/maps/pmc_h3_accessibility_gap_map.png
4. Output Markdown summary comparison table.
"""

import os
import sys
import json
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sqlalchemy import create_engine, text

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

DATA_DIR = PROJECT_ROOT / "data"
BOUNDARY_DIR = DATA_DIR / "boundary"
ANALYSIS_DIR = DATA_DIR / "analysis"
MAPS_DIR = PROJECT_ROOT / "analysis" / "accessibility" / "maps"
MAPS_DIR.mkdir(parents=True, exist_ok=True)

ISO_METRICS_JSON = ANALYSIS_DIR / "isochrone_summary_metrics.json"
H3_METRICS_JSON = ANALYSIS_DIR / "h3_summary_metrics.json"
POP_METRICS_JSON = ANALYSIS_DIR / "population_accessibility_summary.json"
FACILITIES_GEOJSON = ANALYSIS_DIR / "pmc_healthcare_facilities.geojson"
ISOCHRONES_GEOJSON = ANALYSIS_DIR / "pmc_walking_isochrones.geojson"
H3_GEOJSON = ANALYSIS_DIR / "pmc_h3_accessibility_res8.geojson"

def run_scenario_comparison():
    print("=" * 80)
    print("  SMARTSERVE GIS - STEP 4F: COMPARATIVE SCENARIO BENCHMARKING & CHARTS")
    print("=" * 80)

    # 1. Load metrics
    with open(ISO_METRICS_JSON, "r", encoding="utf-8") as f:
        iso_metrics = json.load(f)
    with open(H3_METRICS_JSON, "r", encoding="utf-8") as f:
        h3_metrics = json.load(f)
    with open(POP_METRICS_JSON, "r", encoding="utf-8") as f:
        pop_metrics = json.load(f)

    # 2. Ingest into PostGIS 'accessibility_summary' table
    print("\n--- INGESTING BENCHMARKED SCENARIOS INTO POSTGIS ---")
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE accessibility_summary;"))

        for m in iso_metrics:
            scenario_id = f"{m['target_type'].lower()}_{m['speed_scenario']}_{m['cutoff_minutes']}min"
            h3_total = h3_metrics["h3_res8"]["total_cells"]
            h3_acc = h3_metrics["h3_res8"]["cells_accessible_15min_normal"] if "normal" in m["speed_scenario"] else h3_metrics["h3_res8"]["cells_accessible_15min_slower"]
            h3_pct = round((h3_acc / h3_total) * 100, 2)

            pop_acc = pop_metrics["scenarios"]["normal_4.8kmh_15min"]["accessible_population"] if "normal" in m["speed_scenario"] else pop_metrics["scenarios"]["slower_3.6kmh_15min"]["accessible_population"]

            conn.execute(text("""
                INSERT INTO accessibility_summary (
                    scenario_id, facility_type, walking_speed_kmh, cutoff_minutes, 
                    cutoff_distance_m, facilities_evaluated, accessible_area_sqkm, 
                    pct_pmc_area_accessible, accessible_h3_cells_res8, total_h3_cells_res8, 
                    pct_h3_cells_accessible, estimated_accessible_population, notes
                )
                VALUES (
                    :scen_id, :target, :speed, :cutoff, 
                    :dist, :fac_cnt, :area, 
                    :cov_pct, :h3_acc, :h3_tot, 
                    :h3_pct, :pop_acc, :notes
                )
                ON CONFLICT (scenario_id) DO UPDATE SET 
                    accessible_area_sqkm = EXCLUDED.accessible_area_sqkm,
                    pct_pmc_area_accessible = EXCLUDED.pct_pmc_area_accessible;
            """), {
                "scen_id": scenario_id,
                "target": m["target_type"],
                "speed": m["speed_kmh"],
                "cutoff": m["cutoff_minutes"],
                "dist": m["cutoff_distance_m"],
                "fac_cnt": m["facility_count"],
                "area": m["network_area_sqkm"],
                "cov_pct": m["network_coverage_pct"],
                "h3_acc": h3_acc,
                "h3_tot": h3_total,
                "h3_pct": h3_pct,
                "pop_acc": pop_acc if m["cutoff_minutes"] == 15 else None,
                "notes": f"Network-derived shortest path isochrone. Tortuosity efficiency: {m['network_to_euclidean_efficiency_pct']}%"
            })

        db_cnt = conn.execute(text("SELECT COUNT(*) FROM accessibility_summary")).scalar()
        print(f"  [VERIFIED POSTGIS] accessibility_summary rows: {db_cnt}")

    # 3. Generate Analytical Figures
    print("\n--- GENERATING PUBLICATION-QUALITY COMPARISON CHARTS & MAPS ---")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Chart 1: Accessible Area across Cutoffs and Speeds
    df_iso = pd.DataFrame(iso_metrics)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)

    # Filter 15-minute comparison
    sub_15 = df_iso[df_iso["cutoff_minutes"] == 15]
    x = np.arange(len(sub_15["target_type"].unique()))
    width = 0.35

    normal_vals = sub_15[sub_15["speed_scenario"] == "normal_4.8kmh"]["network_area_sqkm"].values
    slower_vals = sub_15[sub_15["speed_scenario"] == "slower_3.6kmh"]["network_area_sqkm"].values
    labels = sub_15["target_type"].unique()

    rects1 = ax.bar(x - width/2, normal_vals, width, label="Normal Speed (4.8 km/h - 1,200m)", color="#2563eb")
    rects2 = ax.bar(x + width/2, slower_vals, width, label="Slower Speed (3.6 km/h - 900m)", color="#f59e0b")

    ax.set_ylabel("Accessible Service Area (sq km)", fontsize=12, fontweight="bold")
    ax.set_title("15-Minute Pedestrian Accessibility Coverage in Pune (PMC Area: 251 km²)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold")
    ax.legend(frameon=True, fontsize=10)
    ax.set_ylim(0, 260)

    # Add data labels
    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h:.1f} km²\n({h/251.02*100:.1f}%)", xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")
    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f"{h:.1f} km²\n({h/251.02*100:.1f}%)", xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")

    chart1_path = MAPS_DIR / "isochrone_coverage_comparison.png"
    plt.tight_layout()
    plt.savefig(chart1_path)
    plt.close()
    print(f"  [CHART SAVED] {chart1_path.name}")

    # Chart 2: Population Coverage Breakdown
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=150)
    p_norm = [pop_metrics["scenarios"]["normal_4.8kmh_15min"]["accessible_population"],
              pop_metrics["scenarios"]["normal_4.8kmh_15min"]["unserved_population"]]
    p_slow = [pop_metrics["scenarios"]["slower_3.6kmh_15min"]["accessible_population"],
              pop_metrics["scenarios"]["slower_3.6kmh_15min"]["unserved_population"]]
    colors = ["#10b981", "#ef4444"]

    ax1.pie(p_norm, labels=[f"Within 15 Min\n{p_norm[0]:,}", f"Beyond 15 Min\n{p_norm[1]:,}"],
            autopct="%1.1f%%", startangle=140, colors=colors, explode=(0.05, 0),
            textprops={"fontsize": 10, "fontweight": "bold"})
    ax1.set_title("Normal Walking Speed (4.8 km/h)\nBaseline Population: 3.99 Million", fontsize=11, fontweight="bold")

    ax2.pie(p_slow, labels=[f"Within 15 Min\n{p_slow[0]:,}", f"Beyond 15 Min\n{p_slow[1]:,}"],
            autopct="%1.1f%%", startangle=140, colors=colors, explode=(0.05, 0),
            textprops={"fontsize": 10, "fontweight": "bold"})
    ax2.set_title("Slower Walking Speed (3.6 km/h)\nVulnerable & Elderly Population", fontsize=11, fontweight="bold")

    chart2_path = MAPS_DIR / "population_access_breakdown.png"
    plt.tight_layout()
    plt.savefig(chart2_path)
    plt.close()
    print(f"  [CHART SAVED] {chart2_path.name}")

    # Map 1: Spatial Map of Isochrones and Facilities
    gdf_pmc = gpd.read_file(BOUNDARY_DIR / "pmc.geojson")
    gdf_fac = gpd.read_file(FACILITIES_GEOJSON)
    gdf_iso = gpd.read_file(ISOCHRONES_GEOJSON)

    fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
    gdf_pmc.plot(ax=ax, color="#f8fafc", edgecolor="#334155", linewidth=1.5, zorder=1)

    # 15 min normal isochrone
    iso_15_all = gdf_iso[
        (gdf_iso["target_type"] == "All_Healthcare") &
        (gdf_iso["speed_scenario"] == "normal_4.8kmh") &
        (gdf_iso["cutoff_minutes"] == 15)
    ]
    iso_10_all = gdf_iso[
        (gdf_iso["target_type"] == "All_Healthcare") &
        (gdf_iso["speed_scenario"] == "normal_4.8kmh") &
        (gdf_iso["cutoff_minutes"] == 10)
    ]
    iso_5_all = gdf_iso[
        (gdf_iso["target_type"] == "All_Healthcare") &
        (gdf_iso["speed_scenario"] == "normal_4.8kmh") &
        (gdf_iso["cutoff_minutes"] == 5)
    ]

    iso_15_all.plot(ax=ax, color="#bfdbfe", alpha=0.6, edgecolor="#3b82f6", linewidth=0.8, zorder=2)
    iso_10_all.plot(ax=ax, color="#93c5fd", alpha=0.7, edgecolor="#2563eb", linewidth=0.8, zorder=3)
    iso_5_all.plot(ax=ax, color="#60a5fa", alpha=0.8, edgecolor="#1d4ed8", linewidth=0.8, zorder=4)

    # Plot hospitals and clinics
    hosp = gdf_fac[gdf_fac["subcategory"] == "Hospital"]
    clin = gdf_fac[gdf_fac["subcategory"] == "Clinic"]

    clin.plot(ax=ax, color="#10b981", markersize=8, alpha=0.7, zorder=5, label=f"Clinics ({len(clin)})")
    hosp.plot(ax=ax, color="#ef4444", markersize=14, alpha=0.9, zorder=6, label=f"Hospitals ({len(hosp)})")

    ax.set_title("Pune Municipal Corporation (PMC)\nPedestrian Walking Accessibility to Healthcare (5, 10, 15 Minutes)", fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="lower left", frameon=True, fontsize=10)
    ax.set_axis_off()

    map1_path = MAPS_DIR / "pmc_accessibility_isochrones_map.png"
    plt.tight_layout()
    plt.savefig(map1_path)
    plt.close()
    print(f"  [MAP SAVED] {map1_path.name}")

    # Map 2: H3 Hexagonal Accessibility Gap Map
    gdf_h3 = gpd.read_file(H3_GEOJSON)
    fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
    gdf_pmc.plot(ax=ax, color="none", edgecolor="#1e293b", linewidth=1.5, zorder=3)

    # Color cells by reachability
    gdf_h3["color"] = np.where(gdf_h3["is_accessible_15min_normal"], "#86efac", "#fca5a5")
    gdf_h3.plot(ax=ax, color=gdf_h3["color"], edgecolor="#94a3b8", linewidth=0.3, alpha=0.8, zorder=2)

    hosp.plot(ax=ax, color="#dc2626", markersize=10, alpha=0.8, zorder=4, label="Hospitals")

    patch_acc = mpatches.Patch(color="#86efac", label="Accessible within 15 Min (Normal)")
    patch_gap = mpatches.Patch(color="#fca5a5", label="Accessibility Gap (> 15 Min Walk)")
    ax.legend(handles=[patch_acc, patch_gap], loc="lower left", frameon=True, fontsize=10)

    ax.set_title("PMC Healthcare Accessibility Gaps (Uber H3 Resolution 8 Hexagonal Grid)", fontsize=13, fontweight="bold", pad=12)
    ax.set_axis_off()

    map2_path = MAPS_DIR / "pmc_h3_accessibility_gap_map.png"
    plt.tight_layout()
    plt.savefig(map2_path)
    plt.close()
    print(f"  [MAP SAVED] {map2_path.name}")

    print("=" * 80)
    print("  COMPARATIVE SCENARIO BENCHMARKING COMPLETED!")
    print("=" * 80)

if __name__ == "__main__":
    run_scenario_comparison()
