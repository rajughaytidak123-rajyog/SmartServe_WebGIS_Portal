"""
SmartServe GIS - Phase 4: Pedestrian Accessibility Analysis
Script 1: Pedestrian Walking Network Extraction & PostGIS Ingestion
Path: analysis/accessibility/01_extract_walking_network.py

Tasks:
1. Load or fetch the PMC pedestrian street network using OSMnx (network_type='walk').
2. Retain network topology and verify connected components.
3. Remove or repair invalid/isolated edges.
4. Calculate precise planar edge lengths in meters using UTM Zone 43N (EPSG:32643).
5. Calculate pedestrian travel times:
   - Normal walking speed: 4.8 km/h = 1.3333 m/s
   - Slower walking speed: 3.6 km/h = 1.0000 m/s
6. Load nodes and edges into PostGIS tables:
   - walking_network_nodes
   - walking_network_edges
7. Export GeoJSON / GraphML outputs for offline caching and fast visualization:
   - data/analysis/pmc_walking_network.graphml
   - data/analysis/pmc_walking_nodes.geojson
   - data/analysis/pmc_walking_edges.geojson
"""

import os
import sys
import time
from pathlib import Path
import geopandas as gpd
import pandas as pd
import networkx as nx
import osmnx as ox
from shapely.geometry import Point, LineString
from sqlalchemy import create_engine, text

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

DATA_DIR = PROJECT_ROOT / "data"
BOUNDARY_DIR = DATA_DIR / "boundary"
ANALYSIS_DIR = DATA_DIR / "analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_CACHE = ANALYSIS_DIR / "pmc_walking_network.graphml"
NODES_GEOJSON = ANALYSIS_DIR / "pmc_walking_nodes.geojson"
EDGES_GEOJSON = ANALYSIS_DIR / "pmc_walking_edges.geojson"

PROJECTED_CRS = "EPSG:32643"  # UTM Zone 43N
NORMAL_SPEED_MPS = 4.8 * 1000 / 3600  # 1.3333 m/s
SLOWER_SPEED_MPS = 3.6 * 1000 / 3600  # 1.0000 m/s

def extract_and_load_walking_network():
    print("=" * 80)
    print("  SMARTSERVE GIS - STEP 4A: PMC PEDESTRIAN WALKING NETWORK EXTRACTION")
    print("=" * 80)

    # 1. Load PMC boundary
    pmc_boundary_path = BOUNDARY_DIR / "pmc.geojson"
    gdf_pmc = gpd.read_file(pmc_boundary_path)
    pmc_polygon = gdf_pmc.geometry.iloc[0]

    # 2. Check cache or download via OSMnx
    if GRAPH_CACHE.exists() and GRAPH_CACHE.stat().st_size > 1000:
        print(f"[INFO] Loading cached walking graph from: {GRAPH_CACHE.name}...")
        t0 = time.time()
        G = ox.load_graphml(GRAPH_CACHE)
        print(f"[SUCCESS] Loaded in {time.time()-t0:.2f}s! Nodes: {len(G.nodes):,}, Edges: {len(G.edges):,}")
    else:
        print("[INFO] Fetching walking graph from Overpass API (network_type='walk')...")
        t0 = time.time()
        ox.settings.overpass_endpoint = "https://overpass-api.de/api/interpreter"
        ox.settings.requests_timeout = 180
        ox.settings.use_cache = True
        G = ox.graph_from_polygon(pmc_polygon, network_type="walk", simplify=True)
        print(f"[SUCCESS] Downloaded in {time.time()-t0:.2f}s! Nodes: {len(G.nodes):,}, Edges: {len(G.edges):,}")
        ox.save_graphml(G, GRAPH_CACHE)
        print(f"[INFO] Saved graph cache to: {GRAPH_CACHE.name}")

    # 3. Analyze connectivity and topological properties
    is_connected = nx.is_strongly_connected(G) if G.is_directed() else nx.is_connected(G)
    wcc = list(nx.weakly_connected_components(G))
    largest_wcc_size = len(max(wcc, key=len)) if wcc else 0
    print(f"\n--- TOPOLOGY & CONNECTIVITY ---")
    print(f"  Directed Graph                  : {G.is_directed()}")
    print(f"  Strongly Connected              : {is_connected}")
    print(f"  Weakly Connected Components     : {len(wcc):,}")
    print(f"  Largest Component Coverage      : {largest_wcc_size:,} nodes ({largest_wcc_size / len(G.nodes) * 100:.1f}%)")

    # 4. Convert to GeoDataFrames and calculate metric lengths in UTM Zone 43N
    print("\n--- CALCULATING METRIC LENGTHS & PEDESTRIAN TRAVEL TIMES ---")
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)

    # Reproject to UTM Zone 43N for precise metric lengths
    gdf_edges_proj = gdf_edges.to_crs(PROJECTED_CRS)
    gdf_edges["length_meters"] = gdf_edges_proj.geometry.length.round(2)

    # Calculate travel times in seconds
    gdf_edges["travel_time_normal_sec"] = (gdf_edges["length_meters"] / NORMAL_SPEED_MPS).round(1)
    gdf_edges["travel_time_slower_sec"] = (gdf_edges["length_meters"] / SLOWER_SPEED_MPS).round(1)

    total_network_km = gdf_edges["length_meters"].sum() / 1000
    print(f"  Total Walkable Network Length   : {total_network_km:,.1f} km")
    print(f"  Normal Walking Speed            : 4.8 km/h ({NORMAL_SPEED_MPS:.3f} m/s)")
    print(f"  Slower Walking Speed            : 3.6 km/h ({SLOWER_SPEED_MPS:.3f} m/s)")

    # 5. Export GeoJSON files for visualization
    print("\n--- EXPORTING VECTOR ARTIFACTS ---")
    # Reset index for clean attributes
    gdf_nodes_export = gdf_nodes.reset_index()
    gdf_nodes_export = gdf_nodes_export[["osmid", "y", "x", "geometry"]].rename(
        columns={"osmid": "node_id", "y": "latitude", "x": "longitude"}
    )
    gdf_nodes_export["municipality"] = "PMC"
    gdf_nodes_export.to_file(NODES_GEOJSON, driver="GeoJSON")
    print(f"  [SAVED] Nodes GeoJSON : {NODES_GEOJSON.name} ({len(gdf_nodes_export):,} points)")

    gdf_edges_export = gdf_edges.reset_index()
    # Normalize highway and name columns (some might be lists)
    def clean_col(val):
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        return str(val) if pd.notnull(val) else None

    gdf_edges_export["highway_clean"] = gdf_edges_export["highway"].apply(clean_col)
    gdf_edges_export["name_clean"] = gdf_edges_export["name"].apply(clean_col) if "name" in gdf_edges_export else "N/A"
    gdf_edges_export["oneway_clean"] = gdf_edges_export["oneway"].astype(bool) if "oneway" in gdf_edges_export else False
    gdf_edges_export["municipality"] = "PMC"

    cols_to_keep = [
        "u", "v", "key", "highway_clean", "name_clean", "oneway_clean",
        "length_meters", "travel_time_normal_sec", "travel_time_slower_sec",
        "municipality", "geometry"
    ]
    gdf_edges_export = gdf_edges_export[[c for c in cols_to_keep if c in gdf_edges_export.columns]].rename(
        columns={"highway_clean": "highway", "name_clean": "name", "oneway_clean": "oneway"}
    )
    gdf_edges_export.to_file(EDGES_GEOJSON, driver="GeoJSON")
    print(f"  [SAVED] Edges GeoJSON : {EDGES_GEOJSON.name} ({len(gdf_edges_export):,} segments)")

    # 6. Load into PostGIS tables
    print("\n--- INGESTING NETWORK INTO POSTGIS DATABASE ---")
    engine = create_engine(settings.database_url)

    with engine.begin() as conn:
        # Clear previous network entries if any
        conn.execute(text("TRUNCATE TABLE walking_network_edges, walking_network_nodes CASCADE;"))

        # Batch insert nodes
        print("  Inserting nodes into 'walking_network_nodes'...")
        nodes_records = []
        for _, row in gdf_nodes_export.iterrows():
            nodes_records.append({
                "node_id": int(row["node_id"]),
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "muni": "PMC",
                "wkt": f"SRID=4326;POINT({row['longitude']} {row['latitude']})"
            })

        # Insert in chunks of 5,000 for high efficiency
        chunk_size = 5000
        for i in range(0, len(nodes_records), chunk_size):
            chunk = nodes_records[i:i + chunk_size]
            conn.execute(text("""
                INSERT INTO walking_network_nodes (node_id, latitude, longitude, municipality, geom)
                VALUES (:node_id, :lat, :lon, :muni, ST_GeomFromEWKT(:wkt))
                ON CONFLICT (node_id) DO NOTHING;
            """), chunk)

        # Batch insert edges
        print("  Inserting edges into 'walking_network_edges'...")
        edges_records = []
        for _, row in gdf_edges_export.iterrows():
            geom_wkt = row["geometry"].wkt
            name_val = str(row["name"])[:250] if pd.notnull(row.get("name")) and str(row.get("name")).lower() != "nan" else None
            highway_val = str(row["highway"])[:60] if pd.notnull(row.get("highway")) and str(row.get("highway")).lower() != "nan" else None
            edges_records.append({
                "u": int(row["u"]),
                "v": int(row["v"]),
                "key": int(row.get("key", 0)),
                "highway": highway_val,
                "name": name_val,
                "oneway": bool(row.get("oneway", False)),
                "len_m": float(row["length_meters"]),
                "t_norm": float(row["travel_time_normal_sec"]),
                "t_slow": float(row["travel_time_slower_sec"]),
                "muni": "PMC",
                "wkt": f"SRID=4326;{geom_wkt}"
            })

        for i in range(0, len(edges_records), chunk_size):
            chunk = edges_records[i:i + chunk_size]
            conn.execute(text("""
                INSERT INTO walking_network_edges (
                    u, v, key, highway, name, oneway, length_meters, 
                    travel_time_normal_sec, travel_time_slower_sec, municipality, geom
                )
                VALUES (
                    :u, :v, :key, :highway, :name, :oneway, :len_m, 
                    :t_norm, :t_slow, :muni, ST_GeomFromEWKT(:wkt)
                );
            """), chunk)

        # Verify counts in PostGIS
        db_nodes_count = conn.execute(text("SELECT COUNT(*) FROM walking_network_nodes")).scalar()
        db_edges_count = conn.execute(text("SELECT COUNT(*) FROM walking_network_edges")).scalar()
        print(f"  [VERIFIED POSTGIS] walking_network_nodes count: {db_nodes_count:,}")
        print(f"  [VERIFIED POSTGIS] walking_network_edges count: {db_edges_count:,}")

    print("=" * 80)
    print("  WALKING NETWORK EXTRACTION & POSTGIS INGESTION COMPLETE!")
    print("=" * 80)
    return G, gdf_nodes_export, gdf_edges_export

if __name__ == "__main__":
    extract_and_load_walking_network()
