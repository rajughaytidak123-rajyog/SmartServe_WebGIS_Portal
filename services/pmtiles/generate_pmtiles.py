"""
SmartServe GIS - Cloud-Native PMTiles Archive Generator
Generates PMTiles v3 single-file vector tile archives directly from PostGIS.
Produces:
  1. data/pmtiles/pmc_services.pmtiles (POIs across all 9 categories & 20 subcategories)
  2. data/pmtiles/pmc_isochrones.pmtiles (Walking isochrones for 5, 10, 15 min catchments)
  3. data/pmtiles/pmc_h3.pmtiles (H3 hexagonal cells with reachability & gap metrics)
"""

import os
import sys
import math
import time
import json
import gzip
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Ensure pmtiles imports
from pmtiles.writer import Writer
from pmtiles.reader import Reader, MmapSource
from pmtiles.tile import zxy_to_tileid, TileType, Compression

# -----------------------------------------------------------------------------
# Configuration & Database Connection
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "smartserve_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", os.getenv("DB_PASS", "postgres"))

OUTPUT_DIR = PROJECT_ROOT / "data" / "pmtiles"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# PMC Geographic Bounding Box (WGS84 EPSG:4326)
BBOX = {
    "min_lon": 73.74,
    "min_lat": 18.42,
    "max_lon": 73.98,
    "max_lat": 18.62,
    "center_lon": 73.8567,
    "center_lat": 18.5204
}

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def deg2num(lat_deg, lon_deg, zoom):
    """Convert WGS84 coordinates to tile (x, y) numbers."""
    lat_rad = math.radians(lat_deg)
    n = 1 << zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

# -----------------------------------------------------------------------------
# PostGIS MVT Tile Generators (Native 3857 with Pre-Indexed Temp Tables)
# -----------------------------------------------------------------------------
def prep_services_table(cur):
    cur.execute("DROP TABLE IF EXISTS temp_services_3857;")
    cur.execute("""
        CREATE TEMP TABLE temp_services_3857 AS
        SELECT id, name, category, subcategory, municipality, address, phone,
               ST_Transform(geom, 3857) AS geom_3857
        FROM services
        WHERE geom IS NOT NULL;
    """)
    cur.execute("CREATE INDEX ON temp_services_3857 USING GIST (geom_3857);")

def query_services_mvt(cur, z, x, y):
    sql = """
    WITH bounds AS (SELECT ST_TileEnvelope(%s, %s, %s) AS geom_3857),
    mvtgeom AS (
        SELECT s.id, s.name, s.category, s.subcategory, s.municipality, s.address, s.phone,
               ST_AsMVTGeom(s.geom_3857, bounds.geom_3857, 4096, 64, true) AS geom
        FROM temp_services_3857 s, bounds
        WHERE s.geom_3857 && bounds.geom_3857
          AND ST_Intersects(s.geom_3857, bounds.geom_3857)
    )
    SELECT ST_AsMVT(mvtgeom.*, 'services', 4096, 'geom') FROM mvtgeom;
    """
    cur.execute(sql, (z, x, y))
    res = cur.fetchone()
    return bytes(res[0]) if res and res[0] else b""

def prep_isochrones_table(cur):
    cur.execute("DROP TABLE IF EXISTS temp_isochrones_3857;")
    cur.execute("""
        CREATE TEMP TABLE temp_isochrones_3857 AS
        SELECT id, target_type, speed_scenario, speed_kmh, cutoff_minutes, area_sqkm, coverage_pct_pmc,
               ST_Transform(geom, 3857) AS geom_3857
        FROM accessibility_isochrones
        WHERE geom IS NOT NULL;
    """)
    cur.execute("CREATE INDEX ON temp_isochrones_3857 USING GIST (geom_3857);")

def query_isochrones_mvt(cur, z, x, y):
    sql = """
    WITH bounds AS (SELECT ST_TileEnvelope(%s, %s, %s) AS geom_3857),
    mvtgeom AS (
        SELECT i.id, i.target_type, i.speed_scenario, i.speed_kmh, i.cutoff_minutes, i.area_sqkm, i.coverage_pct_pmc,
               ST_AsMVTGeom(i.geom_3857, bounds.geom_3857, 4096, 64, true) AS geom
        FROM temp_isochrones_3857 i, bounds
        WHERE i.geom_3857 && bounds.geom_3857
          AND ST_Intersects(i.geom_3857, bounds.geom_3857)
    )
    SELECT ST_AsMVT(mvtgeom.*, 'isochrones', 4096, 'geom') FROM mvtgeom;
    """
    cur.execute(sql, (z, x, y))
    res = cur.fetchone()
    return bytes(res[0]) if res and res[0] else b""

def prep_h3_table(cur):
    cur.execute("DROP TABLE IF EXISTS temp_h3_3857;")
    cur.execute("""
        CREATE TEMP TABLE temp_h3_3857 AS
        SELECT h3_index, resolution, municipality, hospital_count, clinic_count, total_healthcare_count,
               has_facility, is_accessible_15min_normal, is_accessible_15min_slower,
               min_dist_to_hospital_m, min_dist_to_clinic_m,
               ST_Transform(geom, 3857) AS geom_3857
        FROM h3_accessibility
        WHERE geom IS NOT NULL;
    """)
    cur.execute("CREATE INDEX ON temp_h3_3857 USING GIST (geom_3857);")

def query_h3_mvt(cur, z, x, y):
    sql = """
    WITH bounds AS (SELECT ST_TileEnvelope(%s, %s, %s) AS geom_3857),
    mvtgeom AS (
        SELECT h.h3_index, h.resolution, h.hospital_count, h.clinic_count, h.is_accessible_15min_normal,
               h.min_dist_to_hospital_m, h.min_dist_to_clinic_m,
               ST_AsMVTGeom(h.geom_3857, bounds.geom_3857, 4096, 64, true) AS geom
        FROM temp_h3_3857 h, bounds
        WHERE h.geom_3857 && bounds.geom_3857
          AND ST_Intersects(h.geom_3857, bounds.geom_3857)
    )
    SELECT ST_AsMVT(mvtgeom.*, 'h3_accessibility', 4096, 'geom') FROM mvtgeom;
    """
    cur.execute(sql, (z, x, y))
    res = cur.fetchone()
    return bytes(res[0]) if res and res[0] else b""

# -------------------------------------------------------------
# PMTiles Builder Engine
# -------------------------------------------------------------
def build_pmtiles_archive(name, prep_func, query_func, min_zoom, max_zoom, vector_layers_meta, force=False):
    output_path = OUTPUT_DIR / f"{name}.pmtiles"
    if not force and output_path.exists() and os.path.getsize(output_path) > 1024:
        print(f"\n[INFO] PMTiles Archive '{output_path.name}' already exists ({os.path.getsize(output_path)/1024:.1f} KB). Verifying existing archive...", flush=True)
        verify_archive(output_path)
        return output_path

    print(f"\n[INFO] ===================================================================", flush=True)
    print(f"[INFO] Building PMTiles Archive: {output_path.name}", flush=True)
    print(f"[INFO] Zoom range: {min_zoom} -> {max_zoom} | BBox: Pune PMC", flush=True)
    print(f"[INFO] ===================================================================", flush=True)

    t0 = time.time()
    conn = get_db_connection()
    cur = conn.cursor()

    # Pre-compute transformed indexed geometries
    print(f"[INFO] Pre-indexing geometries in native EPSG:3857 for {name}...", flush=True)
    prep_func(cur)

    total_tiles = 0
    non_empty_tiles = 0

    with open(output_path, "wb") as f:
        writer = Writer(f)

        for z in range(min_zoom, max_zoom + 1):
            x_min, y_min = deg2num(BBOX["max_lat"], BBOX["min_lon"], z)
            x_max, y_max = deg2num(BBOX["min_lat"], BBOX["max_lon"], z)

            x_start, x_end = min(x_min, x_max), max(x_min, x_max)
            y_start, y_end = min(y_min, y_max), max(y_min, y_max)

            z_tiles = 0
            z_non_empty = 0

            for x in range(x_start, x_end + 1):
                for y in range(y_start, y_end + 1):
                    total_tiles += 1
                    z_tiles += 1
                    mvt_bytes = query_func(cur, z, x, y)
                    if mvt_bytes and len(mvt_bytes) > 0:
                        compressed = gzip.compress(mvt_bytes, mtime=0)
                        tid = zxy_to_tileid(z, x, y)
                        writer.write_tile(tid, compressed)
                        non_empty_tiles += 1
                        z_non_empty += 1

            print(f"  └─ Zoom {z:2d}: {z_non_empty:4d} non-empty / {z_tiles:4d} total tiles", flush=True)

        header = {
            "tile_type": TileType.MVT,
            "tile_compression": Compression.GZIP,
            "min_lon_e7": int(BBOX["min_lon"] * 1e7),
            "min_lat_e7": int(BBOX["min_lat"] * 1e7),
            "max_lon_e7": int(BBOX["max_lon"] * 1e7),
            "max_lat_e7": int(BBOX["max_lat"] * 1e7),
            "center_lon_e7": int(BBOX["center_lon"] * 1e7),
            "center_lat_e7": int(BBOX["center_lat"] * 1e7),
            "center_zoom": min_zoom
        }

        metadata = {
            "name": name,
            "description": f"SmartServe GIS Vector Archive for {name} (Pune PMC)",
            "attribution": "SmartServe WebGIS Portal / OpenStreetMap Contributors",
            "format": "pbf",
            "vector_layers": vector_layers_meta
        }

        print(f"[INFO] Finalizing PMTiles v3 directory header and metadata...", flush=True)
        writer.finalize(header, metadata)

    cur.close()
    conn.close()

    elapsed = time.time() - t0
    file_size_kb = os.path.getsize(output_path) / 1024

    print(f"[SUCCESS] Generated: {output_path.name}", flush=True)
    print(f"  ├─ File size      : {file_size_kb:.1f} KB", flush=True)
    print(f"  ├─ Addressed tiles: {non_empty_tiles} non-empty tiles", flush=True)
    print(f"  └─ Generation time: {elapsed:.2f} seconds", flush=True)

    # Verify PMTiles integrity with Reader
    verify_archive(output_path)
    return output_path

def verify_archive(path):
    """Read back header and root directory to verify PMTiles validity."""
    with open(path, "rb") as f:
        reader = Reader(MmapSource(f))
        header = reader.header()
        meta = reader.metadata()
        print(f"[VERIFY] Header Check for {path.name}:", flush=True)
        print(f"  ├─ Spec Version : {header.get('version', 3)}", flush=True)
        print(f"  ├─ Tile Type    : {header['tile_type'].name}", flush=True)
        print(f"  ├─ Compression  : {header['tile_compression'].name}", flush=True)
        print(f"  ├─ Min/Max Zoom : Z{header['min_zoom']} - Z{header['max_zoom']}", flush=True)
        print(f"  ├─ Tile Entries : {header['tile_entries_count']}", flush=True)
        print(f"  └─ Root Length  : {header['root_length']} bytes", flush=True)

def main():
    print("=" * 70, flush=True)
    print("  SMARTSERVE GIS - CLOUD-NATIVE PMTILES ARCHIVE BUILDER", flush=True)
    print("  PostGIS Native MVT to PMTiles v3 Serverless Single-File Datasets", flush=True)
    print("=" * 70, flush=True)

    # 1. Services POI Archive (Zoom 10 - 16)
    services_meta = [{
        "id": "services",
        "description": "Multi-category POIs for Pune Municipal Corporation",
        "fields": {
            "id": "Number",
            "name": "String",
            "category": "String",
            "subcategory": "String",
            "municipality": "String",
            "address": "String",
            "phone": "String"
        }
    }]
    build_pmtiles_archive("pmc_services", prep_services_table, query_services_mvt, min_zoom=10, max_zoom=16, vector_layers_meta=services_meta)

    # 2. Isochrones Archive (Zoom 10 - 15)
    isochrones_meta = [{
        "id": "isochrones",
        "description": "Pedestrian network walking isochrones (5, 10, 15 min)",
        "fields": {
            "id": "Number",
            "target_type": "String",
            "speed_scenario": "String",
            "speed_kmh": "Number",
            "cutoff_minutes": "Number",
            "area_sqkm": "Number",
            "coverage_pct_pmc": "Number"
        }
    }]
    build_pmtiles_archive("pmc_isochrones", prep_isochrones_table, query_isochrones_mvt, min_zoom=10, max_zoom=15, vector_layers_meta=isochrones_meta)

    # 3. H3 Hexagonal Grid Archive (Zoom 10 - 15)
    h3_meta = [{
        "id": "h3_accessibility",
        "description": "H3 discrete global grid resolution 8 accessibility cells",
        "fields": {
            "id": "Number",
            "h3_index": "String",
            "resolution": "Number",
            "hospital_count": "Number",
            "clinic_count": "Number",
            "is_accessible_15min_normal": "Boolean",
            "min_dist_to_hospital_m": "Number",
            "min_dist_to_clinic_m": "Number"
        }
    }]
    build_pmtiles_archive("pmc_h3", prep_h3_table, query_h3_mvt, min_zoom=10, max_zoom=15, vector_layers_meta=h3_meta)

    print("\n[COMPLETE] All 3 PMTiles archives built and verified successfully!", flush=True)

if __name__ == "__main__":
    main()
