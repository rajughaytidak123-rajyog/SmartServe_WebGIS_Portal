# SmartServe GIS – Project Audit & Assignment Gap Analysis

**Project Name:** SmartServe GIS – Location-Based Multi-Service WebGIS Portal  
**Primary Study Area:** Pune Municipal Corporation (PMC), Maharashtra, India  
**Secondary Retained Area:** Pimpri-Chinchwad Municipal Corporation (PCMC)  
**Audit Date:** November 23, 2026  
**Status:** Baseline Audited & Verified (100% Core Tests Passing)

---

## 1. Executive Summary

This audit establishes a rigorous baseline of the existing **SmartServe GIS** repository before undertaking the remaining phases of the experiential learning assignment: **"From Nearby Services to a Deployed Map Service"**.

SmartServe GIS is currently an operational, high-performance WebGIS application featuring:
- A spatial database in PostgreSQL 18 with PostGIS 3.6 hosting **4,747 verified Points of Interest (POIs)** across **9 service domains** and **20 subcategories**;
- Official boundary polygons for PMC and PCMC with exact geometric and projected metrics (UTM Zone 43N / EPSG:32643);
- A FastAPI asynchronous REST backend exposing 13 spatial and analytical endpoints (ST_DWithin proximity, KNN `<->` index search, full-text search, native GeoJSON feature generation, and spatial density aggregation);
- A responsive, modern Leaflet.js frontend with dynamic marker clustering, radius proximity sliders, routing, category filters, and Chart.js analytics;
- Automated test suites passing 13 of 13 tests (100% pass rate).

This document catalogs existing assets, maps them to the experiential learning requirements, and defines the phased transition toward enterprise spatial infrastructure (OGC GeoServer, OSMnx pedestrian network modeling, H3 hexagonal spatial aggregation, MapLibre GL JS vector rendering, pg_tileserv / pg_featureserv, PMTiles, Docker Compose, and Kubernetes deployment) while strictly preserving all existing functionality and datasets.

---

## 2. Existing Repository Architecture & Directory Structure

```
SmartServe_WebGIS_Portal/
│
├── .env                              # Host database credentials & environment variables
├── .env.example                      # Sanitized environment template
├── .gitignore                        # Git exclusion rules
├── requirements.txt                  # Python dependencies
├── run_all.bat                       # Windows double-click dual launcher (backend + frontend)
├── run_backend.bat                   # FastAPI launcher on http://127.0.0.1:8000
├── run_frontend.bat                  # HTTP server launcher on http://127.0.0.1:5500
│
├── backend/
│   ├── run.py                        # Uvicorn entry point
│   └── app/
│       ├── __init__.py
│       ├── main.py                   # FastAPI initialization, CORS, OpenAPI metadata, health check
│       ├── api/
│       │   └── v1/
│       │       ├── router.py         # Main API router aggregating endpoints
│       │       └── endpoints/
│       │           ├── services.py   # Nearby, KNN, search, detail, GeoJSON streaming
│       │           ├── categories.py # Taxonomy flat list & category tree
│       │           ├── boundaries.py # GeoJSON municipal boundaries
│       │           └── analytics.py  # Overview stats, spatial density, nearby summary
│       ├── core/
│       │   └── config.py             # Pydantic v2 BaseSettings, database URL generator
│       ├── db/
│       │   ├── base.py               # Declarative Base
│       │   └── session.py            # SQLAlchemy sessionmaker & dependency
│       ├── models/
│       │   ├── service.py            # Service SQLAlchemy model with PostGIS Geometry & Geography
│       │   ├── category.py           # Category lookup model
│       │   └── boundary.py           # StudyAreaBoundary model
│       ├── schemas/
│       │   ├── service.py            # Pydantic validation schemas for POIs
│       │   ├── category.py           # Taxonomy schemas
│       │   ├── boundary.py           # Boundary GeoJSON schemas
│       │   └── stats.py              # Analytical response schemas
│       └── services/
│           └── spatial_service.py    # Raw PostGIS SQL query implementations
│
├── data/
│   ├── boundary/
│   │   ├── pmc.geojson               # Official PMC boundary (EPSG:4326, 251.02 km² projected)
│   │   ├── pcmc.geojson              # Official PCMC boundary (EPSG:4326, 176.74 km² projected)
│   │   ├── pmc_pcmc_combined.geojson # Both boundaries in a 2-feature collection
│   │   ├── study_area.geojson        # Dissolved urban agglomeration boundary
│   │   ├── study_area_interactive.html
│   │   └── study_area_preview.png
│   ├── raw/                          # 20 raw Overpass API extracted GeoJSON layers
│   │   ├── atms.geojson, bakeries.geojson, banks.geojson, bus_stations.geojson, cafes.geojson...
│   ├── cleaned/                      # 20 cleaned & standardized GeoJSON layers + quality reports
│   │   ├── all_services_quality_report.json
│   │   ├── all_services_inspection_map.html
│   │   └── [category_subcategories].geojson
│   └── final/
│       └── all_services.geojson      # Consolidated master GeoJSON dataset (4,742 POIs)
│
├── database/
│   ├── schema.sql                    # PostGIS DDL, tables, constraints, GIST & B-Tree indexes
│   └── spatial_queries.sql           # Reference SQL queries (ST_DWithin, KNN, ST_AsGeoJSON)
│
├── frontend/
│   ├── index.html                    # Responsive WebGIS dashboard with sidebar & map container
│   ├── serve.py                      # Python HTTP server for local hosting
│   ├── css/
│   │   ├── style.css                 # Custom portal theme & responsive UI styling
│   │   └── leaflet-custom.css        # Leaflet popup, control, and cluster overrides
│   └── js/
│       ├── config.js                 # API base URL, spatial constants, category color palette
│       ├── api.js                    # Fetch client for all FastAPI backend endpoints
│       ├── map.js                    # Leaflet map manager, layers, marker clustering, locate-me
│       ├── charts.js                 # Chart.js visualization for spatial density & analytics
│       └── app.js                    # Main controller, event wiring, proximity slider, search
│
└── scripts/
    ├── 01_fetch_and_validate_boundaries.py  # Boundary acquisition from DataMeet & dissolution
    ├── 02_fetch_raw_pois.py                 # Overpass API extraction script (pilot)
    ├── 03_clean_and_standardize_pois.py     # POI cleaning & standardization (pilot)
    ├── 04_fetch_all_core_pois.py            # Comprehensive 20-subcategory POI extraction
    ├── 05_clean_and_standardize_all_pois.py # Comprehensive cleaning & master consolidation
    ├── 06_load_to_postgis.py                # Schema initialization & GeoJSON loading into PostGIS
    ├── enrich_major_malls.py                # Landmark validation adding 5 major regional malls
    ├── test_api_endpoints.py                # Automated 13-test FastAPI verification suite
    ├── view_database_summary.py             # CLI database inspector & tabular summary
    ├── test_restaurant_radius.py
    ├── generate_viva_pdf.py
    └── package_for_moodle.py
```

---

## 3. Existing Datasets & Quantitative Baseline

### 3.1 Study Area Boundaries

| Boundary Layer | Geometry Type | Native CRS | Projected Area (UTM 43N / EPSG:32643) | PostGIS Geodesic Area | Bounding Box [W, S, E, N] |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PMC (Pune Municipal Corp.)** | MultiPolygon | EPSG:4326 | **251.02 km²** | 251.13 km² | [73.7516, 18.4288, 73.9630, 18.6216] |
| **PCMC (Pimpri-Chinchwad)** | MultiPolygon | EPSG:4326 | **176.74 km²** | 176.81 km² | [73.7104, 18.5639, 73.9340, 18.7211] |
| **Combined Agglomeration** | MultiPolygon | EPSG:4326 | **427.76 km²** | 427.94 km² | [73.7104, 18.4288, 73.9630, 18.7211] |

*Verification Note:* Area values in PostGIS match UTM Zone 43N (EPSG:32643) projections within 0.04% precision.

### 3.2 Service POI Inventory by Domain & Subcategory

The database currently indexes **4,747 POIs** across 9 domains and 20 subcategories. The master GeoJSON contains 4,742 POIs, and 5 landmark regional malls were added via `scripts/enrich_major_malls.py` to ensure complete coverage of major commercial centers.

| Domain Category | Subcategory | Slug | GeoJSON Count | PostGIS Count | PMC Share | PCMC Share | Primary Target for Accessibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **Healthcare** | **Hospital** | `hospitals` | 588 | **588** | 409 | 179 | **YES (Primary)** |
| **Healthcare** | **Clinic** | `clinics` | 414 | **414** | 336 | 78 | **YES (Primary)** |
| **Healthcare** | **Pharmacy** | `pharmacies` | 150 | **150** | 105 | 45 | Retained in Portal |
| **Food** | Restaurant | `restaurants` | 812 | **812** | 613 | 199 | Retained in Portal |
| **Food** | Cafe | `cafes` | 298 | **298** | 223 | 75 | Retained in Portal |
| **Food** | Bakery | `bakeries` | 87 | **87** | 66 | 21 | Retained in Portal |
| **Transport** | Petrol Pump | `petrol_pumps` | 151 | **151** | 91 | 60 | Retained in Portal |
| **Transport** | Metro Station | `metro_stations` | 104 | **104** | 77 | 27 | Retained in Portal |
| **Transport** | Bus Station | `bus_stations` | 79 | **79** | 44 | 35 | Retained in Portal |
| **Transport** | EV Charging | `ev_charging` | 28 | **28** | 16 | 12 | Retained in Portal |
| **Accommodation** | Hotel | `hotels` | 132 | **132** | 100 | 32 | Retained in Portal |
| **Finance** | Bank | `banks` | 413 | **413** | 358 | 55 | Retained in Portal |
| **Finance** | ATM | `atms` | 271 | **271** | 222 | 49 | Retained in Portal |
| **Emergency** | Police Station | `police_stations` | 59 | **59** | 48 | 11 | Retained in Portal |
| **Emergency** | Fire Station | `fire_stations` | 15 | **15** | 10 | 5 | Retained in Portal |
| **Education** | School | `schools` | 276 | **276** | 214 | 62 | Retained in Portal |
| **Education** | College | `colleges` | 168 | **168** | 135 | 33 | Retained in Portal |
| **Shopping** | Supermarket | `supermarkets` | 136 | **136** | 104 | 32 | Retained in Portal |
| **Shopping** | Shopping Mall | `shopping_malls` | 54 | **59** | 41 | 18 | Retained in Portal |
| **Recreation** | Park | `parks` | 507 | **507** | 329 | 178 | Retained in Portal |
| **TOTAL** | **20 Subcategories** | | **4,742** | **4,747** | **3,541 (74.6%)** | **1,206 (25.4%)** | |

*Key Takeaway for Accessibility Analysis:*  
In PMC alone, there are **409 Hospitals** and **336 Clinics** (745 primary healthcare facilities total). These constitute the exact destination set for pedestrian walking-network accessibility analysis in Phase 4.

---

## 4. Existing Database Architecture

- **Engine:** PostgreSQL 18.x with PostGIS 3.6 (GEOS 3.13, PROJ 9.5)
- **Database Name:** `smartserve_db`
- **Tables:**
  1. `categories` (Taxonomy lookup: id, category, subcategory, slug, icon, color)
  2. `study_area_boundaries` (Municipal boundaries: id, name, municipality, area_sqkm, source, geom MultiPolygon EPSG:4326)
  3. `services` (POI master table: id, name, category, subcategory, latitude, longitude, address, phone, website, opening_hours, operator, brand, wheelchair, municipality, osm_id, source, geom Geometry(Point, 4326), geog Geography(Point, 4326) GENERATED STORED)
- **Indexes:**
  - `idx_services_geom` (GIST R-Tree on `geom`)
  - `idx_services_geog` (GIST R-Tree on `geog` for `ST_DWithin` & geodesic distances)
  - `idx_boundaries_geom` (GIST on `study_area_boundaries.geom`)
  - `idx_services_category`, `idx_services_subcategory`, `idx_services_municipality`, `idx_services_name` (B-Trees)
  - `idx_services_cat_muni` (Composite B-Tree on `(category, municipality)`)

---

## 5. Existing FastAPI Backend & API Endpoints

The FastAPI backend (`backend/app/main.py`) runs on `http://127.0.0.1:8000` and serves the following verified endpoints:

| Endpoint | Method | Purpose | PostGIS SQL Operator / Mechanism |
| :--- | :--- | :--- | :--- |
| `/` | GET | Root API metadata & documentation index | Static metadata |
| `/health` | GET | Health check, PostGIS version, table counts | `PostGIS_Version()`, `COUNT(*)` |
| `/api/v1/categories/` | GET | Flat list of all 20 categories/subcategories | SQL SELECT from `categories` |
| `/api/v1/categories/tree` | GET | Hierarchical taxonomy tree (9 domain categories) | SQL aggregation |
| `/api/v1/boundaries/` | GET | GeoJSON FeatureCollection of PMC and PCMC boundaries | `ST_AsGeoJSON(geom)` |
| `/api/v1/services/nearby` | GET | Radius search within user-defined distance | `ST_DWithin(geog, ...)` |
| `/api/v1/services/knn` | GET | K-Nearest Neighbors fast search | Index-accelerated `geom <-> point` |
| `/api/v1/services/search` | GET | Case-insensitive keyword search by name/address | ILIKE / B-Tree index |
| `/api/v1/services/{id}` | GET | Service detail lookup by ID | Primary key lookup |
| `/api/v1/services/geojson` | GET | GeoJSON stream with filtering | Direct `json_build_object` & `ST_AsGeoJSON` |
| `/api/v1/analytics/overview` | GET | System metrics, category counts, municipality share | SQL aggregations |
| `/api/v1/analytics/density` | GET | POI density per km² across boundaries | `COUNT(s.id) / b.area_sqkm` |
| `/api/v1/analytics/nearby-summary`| GET | Subcategory breakdown within a radius | `ST_DWithin` + `GROUP BY` |

---

## 6. Existing Frontend Architecture

- **Technology:** Vanilla JavaScript (ES6+), HTML5, CSS3, Leaflet 1.9.4, Leaflet.markercluster 1.5.3, Chart.js 4.4.1, FontAwesome 6.5.1.
- **Port:** Served locally via `frontend/serve.py` at `http://127.0.0.1:5500`.
- **Features:**
  - Interactive multi-category exploration sidebar with checkboxes and badge counts;
  - Real-time search with Google-style autocomplete dropdown;
  - Interactive Proximity Filter with draggable location pin and radius slider (500m to 10km);
  - KNN "Find 5 Nearest" quick action;
  - Spatial analytics modal with interactive doughnut & bar charts;
  - Informative popups with address, phone, website, wheelchair accessibility, and directions link;
  - Dynamic municipal boundary toggling (PMC in blue, PCMC in green).

---

## 7. Assignment Requirements vs. Existing State Comparison

The table below correlates the Experiential Learning Assignment components against current implementation status.

| Phase | Assignment Component | Existing State | Gap / Action Required | Status |
| :---: | :--- | :--- | :--- | :---: |
| **0** | **Project Inspection & Audit** | Inspected, 13/13 tests verified | Formally complete `docs/PROJECT_AUDIT.md` | **COMPLETED** |
| **1** | **Spatial Data Engineering** | Clean GeoJSONs exist, but need pipeline validation | Scripted validation of PMC containment, CRS verification, UTM 43N projected metrics, reproducible workflow in `analysis/data_engineering/` | **PENDING** |
| **2** | **PostGIS Database Extension** | `services` and `study_area_boundaries` exist | Add tables for walking network, accessibility areas, H3 cells, population grid; create SQL scripts in `database/experiential_learning/` | **PENDING** |
| **3** | **GeoServer OGC Services** | Not installed/configured | PostGIS datastore connection, WMS, WFS, SLD styles for layers in `geoserver/` | **PENDING** |
| **4** | **Pedestrian Accessibility Analysis** | No network or isochrone analysis yet | OSMnx walking network for PMC, 5/10/15 min isochrones (4.8 & 3.6 km/h), H3 resolution 8/9 analysis, population access analysis in `analysis/accessibility/` | **PENDING** |
| **5** | **MapLibre GL JS Frontend** | Leaflet frontend exists | Build separate modern MapLibre GL JS client in `client/maplibre/` consuming OGC/vector services; keep Leaflet intact | **PENDING** |
| **6** | **Vector Tile Services** | Not configured | Set up and benchmark `pg_tileserv` and `pg_featureserv`, test zoom 12/14/16, compare WMS/WFS/MVT in `services/tiles/` | **PENDING** |
| **7** | **Docker Compose Deployment** | Running directly on Windows | Build `docker-compose.yml` for PostGIS, GeoServer, pg_tileserv, pg_featureserv; environment variables & health checks | **PENDING** |
| **8** | **PMTiles & GitHub Deployment** | None | Generate PMTiles via Tippecanoe/PMTiles CLI; configure MapLibre PMTiles source; GitHub Actions workflow for Pages | **PENDING** |
| **9** | **Local Kubernetes Deployment** | None | Manifests for PostGIS StatefulSet, PVC, Secrets, Client Deployment & Service in `k8s/` | **PENDING** |
| **10**| **Documentation & Evidence** | Baseline notes in scripts | Comprehensive `docs/ANSWERS.md`, architecture diagrams, genuine test logs & screenshots in `docs/evidence/` | **PENDING** |

---

## 8. Detailed Gap Analysis & Checklist

### Completed Items
- [x] Full repository structure inspected and cataloged.
- [x] Python virtual environment and dependencies audited.
- [x] PostgreSQL 18 and PostGIS 3.6 verified operational on host.
- [x] 4,747 POIs across 9 domains and 20 subcategories verified in database.
- [x] PMC (251.02 km²) and PCMC (176.74 km²) boundaries validated in EPSG:4326 and EPSG:32643.
- [x] All 13 FastAPI backend endpoints tested and passing (100%).
- [x] Existing Leaflet WebGIS frontend and batch run scripts verified.

### Pending Items (To be implemented phase-by-phase)
- [ ] **Phase 1: Spatial Data Engineering**
  - Geometry validity check (ST_IsValid / shapely.is_valid).
  - Explicit CRS check and reprojection to UTM Zone 43N (EPSG:32643).
  - Point-in-polygon verification confirming all 3,541 PMC POIs fall strictly inside PMC.
  - Data limitation documentation and reproducible pipeline in `analysis/data_engineering/`.
- [ ] **Phase 2: PostGIS Extension**
  - DDL for `walking_network_nodes`, `walking_network_edges`, `accessibility_isochrones`, `h3_accessibility`, `population_grid`, `accessibility_summary`.
  - GiST spatial indexes and foreign keys.
  - Reproducible migration script in `database/experiential_learning/`.
- [ ] **Phase 3: GeoServer Setup & OGC Services**
  - PostGIS JNDI / JDBC datastore connection.
  - WMS and WFS layer publishing (PMC boundary, POIs, Healthcare, Walking Network, Isochrones, H3).
  - Production SLD styling for all published layers in `geoserver/sld/`.
  - WMS GetCapabilities / GetMap and WFS GetFeature verification.
- [ ] **Phase 4: Pedestrian Accessibility Analysis**
  - PMC walkable street network extraction and cleaning via OSMnx.
  - Shortest path walking distance calculations to nearest Hospital and Clinic.
  - Isochrone generation for 5, 10, and 15 minutes at 4.8 km/h (normal) and 3.6 km/h (slower).
  - H3 hexagonal spatial indexing (Resolution 8 & 9) assessing spatial gaps and coverage percentages.
  - Population accessibility evaluation using open high-resolution data (WorldPop / GHSL) or documented gap.
  - Analytical maps, comparison charts, and statistical tables in `analysis/accessibility/`.
- [ ] **Phase 5: MapLibre GL JS Frontend**
  - Standalone client in `client/maplibre/` (Leaflet remains 100% untouched).
  - Vector tile / GeoJSON rendering of PMC boundary, all 20 service categories, network, isochrones, H3 hexagons.
  - Interactive layer controls, category filters, legend, and popups.
- [ ] **Phase 6: Vector Tile Services (pg_tileserv & pg_featureserv)**
  - Configuration of Crunchy Data `pg_tileserv` and `pg_featureserv`.
  - Performance benchmarking comparing WMS, WFS, and MVT across zoom levels 12, 14, and 16.
  - Latency and payload size documentation in `services/tiles/`.
- [ ] **Phase 7: Docker Compose Orchestration**
  - Multi-container `docker-compose.yml` (PostGIS, GeoServer, pg_tileserv, pg_featureserv).
  - Persistent volume mounts, internal network bridge, health checks, environment variables.
- [ ] **Phase 8: PMTiles & GitHub Deployment**
  - Generation of `.pmtiles` archives using Tippecanoe.
  - MapLibre PMTiles protocol integration.
  - GitHub Actions workflow (`.github/workflows/deploy.yml`) for GitHub Pages static deployment.
- [ ] **Phase 9: Kubernetes Deployment**
  - Production manifests in `k8s/` (PostGIS StatefulSet, PVC, Secret, Web Deployment, Service).
  - Local deployment verification on Kind / Minikube.
- [ ] **Phase 10: Final Documentation & Viva Evidence**
  - Complete `docs/ANSWERS.md` addressing every assignment question.
  - System architecture and data flow diagrams.
  - Verification screenshots and log evidence in `docs/evidence/`.
  - Comprehensive updated `README.md`.

---

## 9. Recommended Implementation Sequence

To guarantee stability, zero regressions, and full reproducibility, the following order of execution is recommended:

```
[Phase 0: Audit & Baseline Check] (Completed)
               │
               ▼
[Phase 1: Spatial Data Engineering] ──▶ Validate geometries, CRS (EPSG:32643), PMC containment
               │
               ▼
[Phase 2: PostGIS Database Extension] ──▶ Create DDL for networks, isochrones, H3, & summary
               │
               ▼
[Phase 4: Pedestrian Accessibility Analysis] ──▶ OSMnx pedestrian graph, 5/10/15 min isochrones, H3, scenarios
               │
               ▼
[Phase 3: GeoServer & OGC Services] ──▶ Connect PostGIS, publish WMS/WFS, write SLD styles
               │
               ▼
[Phase 6: Vector Tile Services] ──▶ Run pg_tileserv/pg_featureserv, benchmark MVT vs WMS/WFS
               │
               ▼
[Phase 5: MapLibre GL JS Frontend] ──▶ Build modern client consuming vector tiles & GeoJSON
               │
               ▼
[Phase 8: PMTiles & GitHub Deployment] ──▶ Tippecanoe tiles, PMTiles client, GitHub Actions
               │
               ▼
[Phase 7: Docker Compose Deployment] ──▶ Containerize full stack (PostGIS + GeoServer + tile servers)
               │
               ▼
[Phase 9: Local Kubernetes Deployment] ──▶ StatefulSet, PVC, Secret, Service manifests & testing
               │
               ▼
[Phase 10: Final Documentation & Evidence] ──▶ ANSWERS.md, diagrams, evidence logs, updated README
```

*Note on Sequence Logic:* Running Phase 4 (Analysis) before Phase 3 (GeoServer) and Phase 6 (Tile Services) ensures that all analytical layers (walking network edges, isochrones, H3 hexagons) exist in PostGIS so that GeoServer and tile servers can publish and benchmark real analytical data rather than empty schemas.

---

## 10. Required Dependencies for Next Phases

To execute the data engineering, network analysis, and H3 aggregation, the following Python libraries will be added modularly to the environment:
- `networkx` and `osmnx` (pedestrian street network acquisition and graph shortest-path routing)
- `h3` / `h3-py` (Uber H3 discrete global grid system)
- `scipy` (spatial KDTree / graph support)
- `rasterio` / `rioxarray` (optional raster population analysis if population grid is ingested)

The existing `requirements.txt` will be preserved and extended cleanly without breaking any existing imports.
