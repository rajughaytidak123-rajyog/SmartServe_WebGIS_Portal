"""
SmartServe GIS - Phase 6: PostGIS Vector Tile Server (pg_tileserv)
Path: services/tiles/pg_tileserv.py

Implements Crunchy Data pg_tileserv REST API specification:
- GET /index.json                        -> Lists published PostGIS spatial tables
- GET /public.{table}.json               -> Table metadata, geometry column, and bounding box
- GET /public.{table}/{z}/{x}/{y}.pbf    -> Dynamic Mapbox Vector Tile (MVT) generated via PostGIS ST_AsMVT

Default Port: 7800
"""

import sys
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

app = FastAPI(
    title="SmartServe pg_tileserv",
    description="High-Performance PostGIS MVT Vector Tile Service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

engine = create_engine(settings.database_url, pool_size=10, max_overflow=20)

PUBLISHED_TABLES = {
    "services": {
        "geom_col": "geom",
        "properties": ["id", "name", "category", "subcategory", "municipality"]
    },
    "study_area_boundaries": {
        "geom_col": "geom",
        "properties": ["id", "name", "municipality", "area_sqkm"]
    },
    "walking_network_edges": {
        "geom_col": "geom",
        "properties": ["edge_id", "highway", "length_meters", "travel_time_normal_sec"]
    },
    "accessibility_isochrones": {
        "geom_col": "geom",
        "properties": ["id", "target_type", "speed_scenario", "cutoff_minutes", "area_sqkm", "coverage_pct_pmc"]
    },
    "h3_accessibility": {
        "geom_col": "geom",
        "properties": ["h3_index", "resolution", "hospital_count", "clinic_count", "is_accessible_15min_normal", "is_accessible_15min_slower"]
    },
    "population_grid": {
        "geom_col": "geom",
        "properties": ["id", "grid_id", "population", "density_per_sqkm", "is_accessible_15min"]
    }
}

@app.get("/")
@app.get("/index.json")
def get_catalog():
    """Returns pg_tileserv catalog of published spatial layers."""
    catalog = {}
    with engine.connect() as conn:
        for tbl, conf in PUBLISHED_TABLES.items():
            extent = conn.execute(text(f"""
                SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e)
                FROM (SELECT ST_Extent({conf['geom_col']}) as e FROM {tbl}) sub;
            """)).fetchone()
            bbox = [float(c) for c in extent] if extent and extent[0] is not None else [73.7, 18.4, 74.0, 18.7]
            catalog[f"public.{tbl}"] = {
                "id": f"public.{tbl}",
                "schema": "public",
                "name": tbl,
                "description": f"PostGIS layer for {tbl}",
                "bounds": bbox,
                "minzoom": 0,
                "maxzoom": 22,
                "tileurl": f"http://localhost:7800/public.{tbl}/{{z}}/{{x}}/{{y}}.pbf"
            }
    return catalog

@app.get("/public.{table}.json")
def get_table_metadata(table: str):
    """Returns metadata for a specific spatial table."""
    if table not in PUBLISHED_TABLES:
        raise HTTPException(status_code=404, detail=f"Table 'public.{table}' not published.")
    conf = PUBLISHED_TABLES[table]
    with engine.connect() as conn:
        extent = conn.execute(text(f"""
            SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e)
            FROM (SELECT ST_Extent({conf['geom_col']}) as e FROM {table}) sub;
        """)).fetchone()
        bbox = [float(c) for c in extent] if extent and extent[0] is not None else [73.7, 18.4, 74.0, 18.7]

    return {
        "id": f"public.{table}",
        "schema": "public",
        "name": table,
        "geometrytype": "Geometry",
        "srid": 4326,
        "bounds": bbox,
        "properties": conf["properties"],
        "minzoom": 0,
        "maxzoom": 22,
        "tileurl": f"http://localhost:7800/public.{table}/{{z}}/{{x}}/{{y}}.pbf"
    }

@app.get("/public.{table}/{z}/{x}/{y}.pbf")
def get_vector_tile(table: str, z: int, x: int, y: int):
    """
    Dynamically generates MVT protobuf vector tile from PostGIS using ST_AsMVT.
    """
    if table not in PUBLISHED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    conf = PUBLISHED_TABLES[table]
    geom_col = conf["geom_col"]
    props_sql = ", ".join(conf["properties"])

    query = text(f"""
        WITH mvtgeom AS (
            SELECT {props_sql},
                   ST_AsMVTGeom(
                       ST_Transform({geom_col}, 3857), 
                       ST_TileEnvelope(:z, :x, :y), 
                       4096, 64, true
                   ) AS geom
            FROM {table}
            WHERE ST_Transform({geom_col}, 3857) && ST_TileEnvelope(:z, :x, :y)
        )
        SELECT ST_AsMVT(mvtgeom.*, :layer_name, 4096, 'geom') FROM mvtgeom;
    """)

    with engine.connect() as conn:
        tile_bytes = conn.execute(query, {
            "z": z, "x": x, "y": y, "layer_name": table
        }).scalar()

    if not tile_bytes:
        tile_bytes = b""

    return Response(
        content=bytes(tile_bytes),
        media_type="application/x-protobuf",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Content-Disposition": f"attachment; filename={table}_{z}_{x}_{y}.pbf",
            "Cache-Control": "max-age=3600"
        }
    )

if __name__ == "__main__":
    print("[INFO] Starting SmartServe pg_tileserv on http://localhost:7800 ...")
    uvicorn.run(app, host="127.0.0.1", port=7800, log_level="warning")
