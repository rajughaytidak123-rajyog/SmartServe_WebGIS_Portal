"""
SmartServe GIS - Phase 4: Pedestrian Accessibility Analysis
Script 2: Network-Based Walking Accessibility & Multi-Interval Isochrones
Path: analysis/accessibility/02_walking_accessibility_isochrones.py

Tasks:
1. Load PMC boundary polygon and healthcare facilities (Hospitals: 409, Clinics: 336).
2. Load walkable network and map facilities to nearest network vertices.
3. Compute actual walking-network travel times and distances:
   - Normal walking speed: 4.8 km/h (1.3333 m/s) -> 5 min (400m), 10 min (800m), 15 min (1200m)
   - Slower walking speed: 3.6 km/h (1.0000 m/s) -> 5 min (300m), 10 min (600m), 15 min (900m)
4. Evaluate network shortest paths using multi-source Dijkstra traversal.
5. Generate accurate walking isochrones (subgraph buffer hulls) clipped to PMC boundary.
6. Compare network isochrones against Euclidean circular buffers to document network tortuosity.
7. Save isochrones into PostGIS table 'accessibility_isochrones' and export GeoJSON:
   - data/analysis/pmc_walking_isochrones.geojson
   - data/analysis/isochrone_summary_metrics.json
"""

import os
import sys
import json
import time
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import networkx as nx
import osmnx as ox
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
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

GRAPH_CACHE = ANALYSIS_DIR / "pmc_walking_network.graphml"
FACILITIES_GEOJSON = ANALYSIS_DIR / "pmc_healthcare_facilities.geojson"
ISOCHRONES_GEOJSON = ANALYSIS_DIR / "pmc_walking_isochrones.geojson"
METRICS_JSON = ANALYSIS_DIR / "isochrone_summary_metrics.json"

PROJECTED_CRS = "EPSG:32643"  # UTM Zone 43N
GEOGRAPHIC_CRS = "EPSG:4326"

# Scenarios Configuration
SCENARIOS = [
    {
        "speed_scenario": "normal_4.8kmh",
        "speed_kmh": 4.8,
        "speed_mps": 4.8 * 1000 / 3600,  # 1.3333 m/s
        "cutoffs": [
            {"minutes": 5, "distance_m": 400.0},
            {"minutes": 10, "distance_m": 800.0},
            {"minutes": 15, "distance_m": 1200.0}
        ]
    },
    {
        "speed_scenario": "slower_3.6kmh",
        "speed_kmh": 3.6,
        "speed_mps": 3.6 * 1000 / 3600,  # 1.0000 m/s
        "cutoffs": [
            {"minutes": 5, "distance_m": 300.0},
            {"minutes": 10, "distance_m": 600.0},
            {"minutes": 15, "distance_m": 900.0}
        ]
    }
]

def generate_isochrones():
    print("=" * 80)
    print("  SMARTSERVE GIS - STEP 4B & 4C: PEDESTRIAN WALKING ISOCHRONE ANALYSIS")
    print("=" * 80)

    # 1. Load PMC boundary
    gdf_pmc = gpd.read_file(BOUNDARY_DIR / "pmc.geojson")
    gdf_pmc_proj = gdf_pmc.to_crs(PROJECTED_CRS)
    pmc_poly_proj = gdf_pmc_proj.geometry.iloc[0]
    pmc_total_area_sqkm = pmc_poly_proj.area / 1e6
    print(f"[INFO] PMC Boundary Area: {pmc_total_area_sqkm:.2f} km² (Projected UTM Zone 43N)")

    # 2. Load healthcare facilities
    gdf_facilities = gpd.read_file(FACILITIES_GEOJSON)
    gdf_fac_proj = gdf_facilities.to_crs(PROJECTED_CRS)
    print(f"[INFO] Loaded Facilities: {len(gdf_facilities)} total ({sum(gdf_facilities['subcategory']=='Hospital')} Hospitals, {sum(gdf_facilities['subcategory']=='Clinic')} Clinics)")

    # 3. Load walking graph
    print(f"[INFO] Loading walking network graph...")
    G = ox.load_graphml(GRAPH_CACHE)
    # Project graph to UTM Zone 43N for metric calculations
    G_proj = ox.project_graph(G, to_crs=PROJECTED_CRS)
    print(f"[INFO] Projected graph to {PROJECTED_CRS}: {len(G_proj.nodes):,} nodes, {len(G_proj.edges):,} edges")

    # Build KDTree on projected nodes for nearest node lookup
    nodes_proj, edges_proj = ox.graph_to_gdfs(G_proj)
    node_coords = np.array([[geom.x, geom.y] for geom in nodes_proj.geometry])
    node_ids = list(nodes_proj.index)
    kdtree = KDTree(node_coords)

    # 4. Map facilities to nearest network nodes
    fac_coords = np.array([[geom.x, geom.y] for geom in gdf_fac_proj.geometry])
    distances, indices = kdtree.query(fac_coords)
    gdf_fac_proj["nearest_node"] = [node_ids[idx] for idx in indices]
    gdf_fac_proj["snap_distance_m"] = distances.round(2)
    print(f"[INFO] Facilities snapped to network. Max snap distance: {distances.max():.1f}m, Median: {np.median(distances):.1f}m")

    # Define facility subsets
    target_groups = {
        "Hospital": gdf_fac_proj[gdf_fac_proj["subcategory"] == "Hospital"],
        "Clinic": gdf_fac_proj[gdf_fac_proj["subcategory"] == "Clinic"],
        "All_Healthcare": gdf_fac_proj
    }

    isochrone_results = []
    comparison_metrics = []

    # 5. Compute network isochrones for each scenario and cutoff
    edge_buffer_m = 65.0  # Buffer around reachable street centerlines

    for scenario in SCENARIOS:
        scenario_name = scenario["speed_scenario"]
        speed_kmh = scenario["speed_kmh"]
        print(f"\n--- SCENARIO: {scenario_name.upper()} ({speed_kmh} km/h) ---")

        for cutoff in scenario["cutoffs"]:
            minutes = cutoff["minutes"]
            dist_m = cutoff["distance_m"]
            print(f"\n  >> Calculating {minutes}-minute isochrone (Network distance limit: {dist_m}m)...")

            for group_name, gdf_group in target_groups.items():
                start_nodes = set(gdf_group["nearest_node"].unique())
                num_facilities = len(gdf_group)

                t0 = time.time()
                # Multi-source Dijkstra: shortest paths up to dist_m
                reachable_node_dists = nx.multi_source_dijkstra_path_length(
                    G_proj, sources=start_nodes, cutoff=dist_m, weight="length"
                )
                reachable_nodes = set(reachable_node_dists.keys())

                # Get subgraph of reachable nodes and incident edges
                sub_edges = edges_proj[
                    edges_proj.index.get_level_values("u").isin(reachable_nodes) &
                    edges_proj.index.get_level_values("v").isin(reachable_nodes)
                ]

                # Create polygon from buffered network edges and nodes
                polys = []
                if not sub_edges.empty:
                    polys.append(sub_edges.geometry.buffer(edge_buffer_m).unary_union)
                sub_nodes = nodes_proj.loc[list(reachable_nodes)]
                if not sub_nodes.empty:
                    polys.append(sub_nodes.geometry.buffer(edge_buffer_m).unary_union)

                if polys:
                    isochrone_union = unary_union(polys)
                    # Clip strictly to PMC municipal boundary
                    isochrone_clipped = isochrone_union.intersection(pmc_poly_proj)
                else:
                    isochrone_clipped = Polygon()

                if isochrone_clipped.is_empty:
                    area_sqkm = 0.0
                    cov_pct = 0.0
                    geom_4326 = MultiPolygon()
                else:
                    area_sqkm = round(isochrone_clipped.area / 1e6, 2)
                    cov_pct = round((area_sqkm / pmc_total_area_sqkm) * 100, 2)
                    # Convert to MultiPolygon in EPSG:4326
                    gdf_temp = gpd.GeoDataFrame(geometry=[isochrone_clipped], crs=PROJECTED_CRS).to_crs(GEOGRAPHIC_CRS)
                    geom_wgs = gdf_temp.geometry.iloc[0]
                    if geom_wgs.geom_type == "Polygon":
                        geom_4326 = MultiPolygon([geom_wgs])
                    else:
                        geom_4326 = geom_wgs

                # Circular Euclidean buffer for direct comparison
                euclidean_union = unary_union(gdf_group.geometry.buffer(dist_m)).intersection(pmc_poly_proj)
                euclidean_area_sqkm = round(euclidean_union.area / 1e6, 2)
                euclidean_cov_pct = round((euclidean_area_sqkm / pmc_total_area_sqkm) * 100, 2)
                network_efficiency = round((area_sqkm / euclidean_area_sqkm * 100), 1) if euclidean_area_sqkm > 0 else 0

                print(f"     [{group_name:<14}] {minutes:2d} min | Reachable Nodes: {len(reachable_nodes):5d} | Network Area: {area_sqkm:6.2f} km² ({cov_pct:5.1f}%) | Euclidean Area: {euclidean_area_sqkm:6.2f} km² ({euclidean_cov_pct:5.1f}%) | Path Tortuosity Efficiency: {network_efficiency}%")

                isochrone_results.append({
                    "target_type": group_name,
                    "speed_scenario": scenario_name,
                    "speed_kmh": speed_kmh,
                    "cutoff_minutes": minutes,
                    "cutoff_distance_m": dist_m,
                    "facility_count": num_facilities,
                    "area_sqkm": area_sqkm,
                    "coverage_pct_pmc": cov_pct,
                    "municipality": "PMC",
                    "geometry": geom_4326
                })

                comparison_metrics.append({
                    "target_type": group_name,
                    "speed_scenario": scenario_name,
                    "speed_kmh": speed_kmh,
                    "cutoff_minutes": minutes,
                    "cutoff_distance_m": dist_m,
                    "facility_count": num_facilities,
                    "network_area_sqkm": area_sqkm,
                    "network_coverage_pct": cov_pct,
                    "euclidean_area_sqkm": euclidean_area_sqkm,
                    "euclidean_coverage_pct": euclidean_cov_pct,
                    "network_to_euclidean_efficiency_pct": network_efficiency,
                    "reachable_network_nodes": len(reachable_nodes)
                })

    # 6. Save GeoJSON output
    gdf_isochrones = gpd.GeoDataFrame(isochrone_results, crs=GEOGRAPHIC_CRS)
    gdf_isochrones.to_file(ISOCHRONES_GEOJSON, driver="GeoJSON")
    print(f"\n[INFO] Saved isochrones GeoJSON: {ISOCHRONES_GEOJSON} ({len(gdf_isochrones)} polygons)")

    # 7. Save metrics JSON
    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(comparison_metrics, f, indent=2)
    print(f"[INFO] Saved metrics JSON: {METRICS_JSON}")

    # 8. Load into PostGIS table 'accessibility_isochrones'
    print("\n--- INGESTING ISOCHRONES INTO POSTGIS DATABASE ---")
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE accessibility_isochrones;"))

        for _, row in gdf_isochrones.iterrows():
            wkt = f"SRID=4326;{row['geometry'].wkt}"
            conn.execute(text("""
                INSERT INTO accessibility_isochrones (
                    target_type, speed_scenario, speed_kmh, cutoff_minutes, 
                    cutoff_distance_m, facility_count, area_sqkm, coverage_pct_pmc, 
                    municipality, geom
                )
                VALUES (
                    :target, :scenario, :speed, :cutoff, 
                    :dist, :fac_cnt, :area, :cov, 
                    :muni, ST_Multi(ST_GeomFromEWKT(:wkt))
                );
            """), {
                "target": row["target_type"],
                "scenario": row["speed_scenario"],
                "speed": row["speed_kmh"],
                "cutoff": int(row["cutoff_minutes"]),
                "dist": float(row["cutoff_distance_m"]),
                "fac_cnt": int(row["facility_count"]),
                "area": float(row["area_sqkm"]),
                "cov": float(row["coverage_pct_pmc"]),
                "muni": row["municipality"],
                "wkt": wkt
            })

        db_count = conn.execute(text("SELECT COUNT(*) FROM accessibility_isochrones")).scalar()
        print(f"  [VERIFIED POSTGIS] accessibility_isochrones records: {db_count}")

    print("=" * 80)
    print("  PEDESTRIAN ISOCHRONE ANALYSIS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    return comparison_metrics

if __name__ == "__main__":
    generate_isochrones()
