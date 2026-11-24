"""
SmartServe GIS - Phase 6: PostGIS OGC Feature Server (pg_featureserv)
Path: services/tiles/pg_featureserv.py

Implements Crunchy Data pg_featureserv / OGC API Features specification:
- GET /index.json                           -> Service metadata
- GET /collections.json                     -> Catalog of published spatial feature collections
- GET /collections/{table}.json             -> Collection details & extent
- GET /collections/{table}/items.json       -> GeoJSON FeatureCollection with limit, offset, bbox
- GET /collections/{table}/items/{id}.json  -> Single GeoJSON Feature

Default Port: 9000
"""

import sys
import os
import json
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

app = FastAPI(
    title="SmartServe pg_featureserv",
    description="High-Performance PostGIS OGC API Features Service",
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

PUBLISHED_COLLECTIONS = {
    "services": {
        "title": "SmartServe Points of Interest",
        "description": "4,747 multi-service POIs across Pune and PCMC",
        "id_col": "id",
        "geom_col": "geom"
    },
    "study_area_boundaries": {
        "title": "Municipal Boundaries",
        "description": "PMC and PCMC municipal administrative boundary polygons",
        "id_col": "id",
        "geom_col": "geom"
    },
    "walking_network_edges": {
        "title": "Pedestrian Street Network",
        "description": "Walkable network segments with travel times and lengths",
        "id_col": "edge_id",
        "geom_col": "geom"
    },
    "accessibility_isochrones": {
        "title": "Walking Accessibility Isochrones",
        "description": "5, 10, and 15-minute walking service areas to healthcare",
        "id_col": "id",
        "geom_col": "geom"
    },
    "h3_accessibility": {
        "title": "H3 Hexagonal Healthcare Grid",
        "description": "Uber H3 resolution 8 cells aggregated with healthcare access",
        "id_col": "h3_index",
        "geom_col": "geom"
    },
    "population_grid": {
        "title": "Population Density Grid",
        "description": "Demographic spatial cells for population accessibility",
        "id_col": "id",
        "geom_col": "geom"
    }
}

@app.get("/")
@app.get("/index.json")
def get_service_index():
    return {
        "title": "SmartServe pg_featureserv",
        "description": "OGC API Features implementation powered by PostGIS",
        "links": [
            {"rel": "self", "type": "application/json", "href": "http://localhost:9000/index.json"},
            {"rel": "data", "type": "application/json", "href": "http://localhost:9000/collections.json"}
        ]
    }

@app.get("/collections.json")
def get_collections():
    collections = []
    with engine.connect() as conn:
        for tbl, meta in PUBLISHED_COLLECTIONS.items():
            extent = conn.execute(text(f"""
                SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e)
                FROM (SELECT ST_Extent({meta['geom_col']}) as e FROM {tbl}) sub;
            """)).fetchone()
            bbox = [float(c) for c in extent] if extent and extent[0] is not None else [73.7, 18.4, 74.0, 18.7]
            collections.append({
                "id": tbl,
                "title": meta["title"],
                "description": meta["description"],
                "extent": {"spatial": {"bbox": [bbox]}},
                "links": [
                    {"rel": "self", "type": "application/json", "href": f"http://localhost:9000/collections/{tbl}.json"},
                    {"rel": "items", "type": "application/geo+json", "href": f"http://localhost:9000/collections/{tbl}/items.json"}
                ]
            })
    return {"collections": collections}

@app.get("/collections/{table}.json")
def get_collection_detail(table: str):
    if table not in PUBLISHED_COLLECTIONS:
        raise HTTPException(status_code=404, detail="Collection not found")
    meta = PUBLISHED_COLLECTIONS[table]
    with engine.connect() as conn:
        extent = conn.execute(text(f"""
            SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e)
            FROM (SELECT ST_Extent({meta['geom_col']}) as e FROM {table}) sub;
        """)).fetchone()
        bbox = [float(c) for c in extent] if extent and extent[0] is not None else [73.7, 18.4, 74.0, 18.7]
    return {
        "id": table,
        "title": meta["title"],
        "description": meta["description"],
        "extent": {"spatial": {"bbox": [bbox]}}
    }

@app.get("/collections/{table}/items.json")
def get_collection_items(
    table: str,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    bbox: Optional[str] = None
):
    """
    Returns features directly as a native GeoJSON FeatureCollection generated inside PostGIS.
    """
    if table not in PUBLISHED_COLLECTIONS:
        raise HTTPException(status_code=404, detail="Collection not found")

    meta = PUBLISHED_COLLECTIONS[table]
    geom_col = meta["geom_col"]

    where_clause = "1=1"
    params = {"limit": limit, "offset": offset}

    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) == 4:
                minx, miny, maxx, maxy = parts
                where_clause += f" AND {geom_col} && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)"
                params.update({"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy})
        except Exception:
            pass

    sql = text(f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'id', {meta['id_col']},
                    'geometry', ST_AsGeoJSON({geom_col})::json,
                    'properties', to_jsonb(t.*) - '{geom_col}'
                )
            ), '[]'::json)
        ) AS geojson
        FROM (
            SELECT * FROM {table}
            WHERE {where_clause}
            LIMIT :limit OFFSET :offset
        ) t;
    """)

    with engine.connect() as conn:
        res = conn.execute(sql, params).scalar()

    return Response(
        content=json.dumps(res),
        media_type="application/geo+json",
        headers={"Access-Control-Allow-Origin": "*"}
    )

if __name__ == "__main__":
    print("[INFO] Starting SmartServe pg_featureserv on http://localhost:9000 ...")
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="warning")
