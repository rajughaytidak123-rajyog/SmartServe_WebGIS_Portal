# SmartServe GIS – Location-Based Multi-Service WebGIS & Spatial Infrastructure Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.110-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_18-336791?logo=postgresql)](https://www.postgresql.org/)
[![PostGIS](https://img.shields.io/badge/Spatial-PostGIS_3.6-5B8C00?logo=postgis)](https://postgis.net/)
[![MapLibre GL JS](https://img.shields.io/badge/Vector_Frontend-MapLibre_4.7-2A3B90?logo=maplibre)](https://maplibre.org/)
[![Leaflet](https://img.shields.io/badge/Raster_Frontend-Leaflet_1.9-199900?logo=leaflet)](https://leafletjs.com/)
[![GeoServer](https://img.shields.io/badge/OGC_Services-GeoServer_2.28-F37023?logo=geoserver)](https://geoserver.org/)
[![PMTiles](https://img.shields.io/badge/Cloud_Native-PMTiles_v3-7057ff)](https://protomaps.com/docs/pmtiles)
[![Docker](https://img.shields.io/badge/Container-Docker_Compose-2496ED?logo=docker)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Orchestration-Kubernetes-326CE5?logo=kubernetes)](https://kubernetes.io/)

**SmartServe GIS** is an enterprise-grade spatial data platform and multi-service WebGIS portal engineered for the twin municipal corporations of **Pune Municipal Corporation (PMC)** and **Pimpri-Chinchwad Municipal Corporation (PCMC)** in Maharashtra, India. 

Originally developed as a location-based multi-service nearby directory, this project has been fully extended into a modern **cloud-native geospatial infrastructure platform** featuring pedestrian street network modeling, multi-criteria walking isochrone analysis, Uber H3 discrete global grid aggregation, Mapbox Vector Tile (MVT) generation, serverless PMTiles archives, Docker Compose orchestration, and Kubernetes production manifests.

---

## 1. Study Area & Master Service Inventory

### Study Area Geometry
- **Primary Study Area (Accessibility Analysis):** **Pune Municipal Corporation (PMC)** — Area: **251.02 km²** (Projected CRS: `EPSG:32643` / UTM Zone 43N).
- **Secondary Study Area (Maintained in Portal):** **Pimpri-Chinchwad Municipal Corporation (PCMC)** — Area: **176.74 km²**.
- **Total Combined Area:** **427.76 km²**.

### Multi-Domain Service Inventory (100% Preserved)
The portal indexes **4,747 Points of Interest (POIs)** across **9 functional domains** and **20 subcategories** (3,541 in PMC, 1,206 in PCMC):

| Domain | Subcategories | PMC Count | PCMC Count | Total POIs | Spatial Symbology |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Healthcare** | Hospitals (409), Clinics (336), Pharmacies (105) | **850** | **231** | **1,081** | `#ef4444` (Red) |
| **Food & Dining** | Restaurants (718), Cafes (120), Bakeries (64) | **902** | **315** | **1,217** | `#f97316` (Orange) |
| **Transport** | Petrol Pumps (140), Bus Stations (42), Metro (30), EV (16) | **228** | **106** | **334** | `#0ea5e9` (Sky Blue) |
| **Finance** | Banks (358), ATMs (222) | **580** | **178** | **758** | `#10b981` (Emerald) |
| **Education** | Schools (214), Colleges (135) | **349** | **95** | **444** | `#8b5cf6` (Purple) |
| **Emergency** | Police Stations (48), Fire Stations (10) | **58** | **16** | **74** | `#dc2626` (Crimson) |
| **Shopping** | Supermarkets (104), Shopping Malls (36) | **140** | **55** | **195** | `#ec4899` (Pink) |
| **Accommodation**| Hotels (100) | **100** | **28** | **128** | `#6366f1` (Indigo) |
| **Recreation** | Parks & Gardens (329) | **329** | **178** | **507** | `#22c55e` (Green) |
| **TOTAL** | **20 Subcategories** | **3,541** | **1,206** | **4,747** | |

*Primary Healthcare Destinational Target:* **745 facilities** (409 Hospitals + 336 Clinics) in PMC were utilized for the pedestrian walking network accessibility model.

---

## 2. System Architecture

```
                                [ Client Layer ]
              ┌─────────────────────────┴─────────────────────────┐
              │                                                   │
              ▼                                                   ▼
     [ Leaflet 1.9 Frontend ]                           [ MapLibre GL JS 4.7 ]
   (Port 5500: Proximity/KNN/Charts)                 (Port 5600: GPU 3D Vector Tiles)
              │                                                   │
              │                               ┌───────────────────┴───────────────────┐
              │                               │                                       │
              ▼                               ▼                                       ▼
     [ FastAPI Backend ]             [ pg_tileserv ]                    [ PMTiles Serverless ]
  (Port 8000: REST / GeoJSON)     (Port 7800: Dynamic MVT)            (Port 5600: HTTP Range 206)
              │                               │                                       │
              └───────────────────────┬───────┴───────────────────────────────────────┘
                                      │
                                      ▼
                        [ PostgreSQL 18 / PostGIS 3.6 ]
                                 (Port 5432)
                       ├── services (4,747 POIs)
                       ├── study_area_boundaries (PMC & PCMC)
                       ├── walking_network_nodes (39,454 nodes)
                       ├── walking_network_edges (99,062 edges)
                       ├── accessibility_isochrones (18 scenarios)
                       ├── h3_accessibility (363 Res-8 cells)
                       └── population_grid (Demographic layer)
                                      ▲
                                      │
                         [ GeoServer 2.28 (Port 8080) ]
                            ├── WMS 1.3.0 GetMap (PNG)
                            └── WFS 2.0.0 GetFeature (GeoJSON)
```

---

## 3. Experiential Learning Platform Extensions

### Phase 1: Spatial Data Engineering
- **Scripted Pipeline:** Automated CRS reprojection to metric **UTM Zone 43N (`EPSG:32643`)** and point-in-polygon topological validation.
- **Results:** 100% valid geometries (`ST_IsValid = TRUE`). Verified **3,536 / 3,536 PMC POIs** fall strictly within the 251.02 km² PMC municipal polygon. 745 primary healthcare facilities isolated for accessibility modeling.
- **Artifacts:** `analysis/data_engineering/DATA_ENGINEERING_REPORT.md`.

### Phase 2: PostGIS Database Extensions
- **DDL Migration:** Created 6 dedicated analytical tables (`walking_network_nodes`, `walking_network_edges`, `accessibility_isochrones`, `h3_accessibility`, `population_grid`, `accessibility_summary`).
- **Spatial Indexing:** GiST R-Tree 2D bounding-box spatial indexes on all geometry columns, composite B-Trees on taxonomy, and foreign key relationships.
- **Unit Testing:** 21/21 database unit tests passed; 13/13 FastAPI regression tests passed (100%).

### Phase 4: Pedestrian Accessibility Analysis
- **Walking Network:** Downloaded and cleaned Pune's walkable pedestrian network via OSMnx: **39,454 nodes**, **99,062 edges**, and **7,163.5 kilometres** of walkable streets.
- **Multi-Source Dijkstra Routing:** Generated 5, 10, and 15-minute walking isochrones for **Normal walking pace (4.8 km/h)** and **Slower walking pace (3.6 km/h)** across Hospitals, Clinics, and All Healthcare.
- **Circular Buffer Comparison:** Proved that straight-line Euclidean buffers **overestimate accessible area by 36% to 41%** due to street network tortuosity (street path efficiency is only 61%–64%).
- **H3 Discrete Global Grid:** Indexed PMC into **363 Resolution 8 hexagonal cells** (~0.737 km² each). Identified **42 spatial gap cells (11.6%)** lacking 15-minute healthcare access.
- **Demographic Vulnerability Gap:** Reached **3,714,728 citizens (93.1%)** at 4.8 km/h versus **3,604,072 citizens (90.3%)** at 3.6 km/h, revealing a **Vulnerability Gap of 110,656 residents**.
- **Artifacts:** `analysis/accessibility/ACCESSIBILITY_REPORT.md` and comparison charts in `analysis/accessibility/maps/`.

### Phase 3: GeoServer & OGC Web Services
- **Automated REST Configuration:** Programmatically created workspace `smartserve`, connected JDBC DataStore to PostGIS, uploaded 7 SLD style sheets, and published 6 core layers.
- **OGC Validation:** 15/15 unit tests passed across WMS 1.3.0 GetCapabilities, GetMap PNG rendering, and WFS 2.0.0 GetFeature GeoJSON streams.
- **Artifacts:** `geoserver/GEOSERVER_OGC_REPORT.md`.

### Phase 6: Vector Tile Services & Benchmarking
- **Standalone Engines:** Implemented high-throughput Python implementations of Crunchy Data `pg_tileserv` (Port 7800) and `pg_featureserv` (Port 9000) using PostGIS native `ST_AsMVT` and `ST_TileEnvelope`.
- **Benchmarking (MVT vs WFS):**
  - **Latency:** MVT responds in **12–25 ms** (2.5x to 7x faster than GeoServer WFS at 85–120 ms).
  - **Payload Size:** At street zoom (Z16), MVT tile size is **958 bytes** (89.7% payload reduction vs 9.3 KB GeoJSON).
- **Artifacts:** `services/tiles/VECTOR_TILE_BENCHMARK_REPORT.md`.

### Phase 5: MapLibre GL JS 3D Vector Client
- **Separate Client:** Stored under `client/maplibre/` (Port 5600); Leaflet frontend remains 100% untouched.
- **Features:** Dynamic MVT / PMTiles vector tile streaming, multi-scenario speed selector (4.8 vs 3.6 km/h), facility target selector, real-time metrics HUD, layer opacity slider, 3D pitch controls, and micro-detail popups.
- **Artifacts:** `client/maplibre/MAPLIBRE_FRONTEND_REPORT.md`.

### Phase 8: Cloud-Native PMTiles & GitHub Deployment
- **Single-File Archives:** Generated 3 PMTiles v3 archives using PostGIS native MVT and Hilbert tile ordering:
  - `pmc_services.pmtiles` (1.25 MB, 989 tiles, Z10–Z16)
  - `pmc_isochrones.pmtiles` (4.52 MB, 310 tiles, Z10–Z15)
  - `pmc_h3.pmtiles` (202.5 KB, 379 tiles, Z10–Z15)
- **HTTP Range Support:** Built RFC 7233 byte-range request handling into `client/maplibre/serve.py` (`206 Partial Content`).
- **CI/CD Pipeline:** Authored `.github/workflows/deploy.yml` for automated static deployment to GitHub Pages.
- **Artifacts:** `services/pmtiles/PMTILES_SERVERLESS_REPORT.md`.

### Phase 7 & 9: Docker Compose & Kubernetes
- **Docker Compose:** Multi-container `docker-compose.yml` orchestrating PostGIS 16, GeoServer 2.24, FastAPI backend, pg_tileserv, pg_featureserv, and Nginx client with health checks and bridge network.
- **Kubernetes:** Production manifests under `k8s/` including PostGIS `StatefulSet` with 10Gi `PersistentVolumeClaim`, Secret management, FastAPI `Deployment`, Nginx `Deployment`, NodePort service on 30080, and Ingress.
- **Artifacts:** `k8s/README.md`.

### Phase 10: Technical Viva Documentation & Evidence
- **Comprehensive Guide:** Authored `docs/ANSWERS.md` providing in-depth, scientifically rigorous answers to all assignment questions.

---

## 4. Port Allocation Matrix

| Service | Technology | Port | Access URL |
| :--- | :--- | :---: | :--- |
| **Leaflet WebGIS Frontend** | Vanilla JS / Leaflet 1.9 | **5500** | `http://127.0.0.1:5500` |
| **MapLibre Vector Frontend**| MapLibre GL JS 4.7 | **5600** | `http://127.0.0.1:5600` |
| **FastAPI REST API** | Python 3 / Uvicorn | **8000** | `http://127.0.0.1:8000` (Docs: `/docs`) |
| **pg_tileserv (MVT)** | PostGIS ST_AsMVT | **7800** | `http://127.0.0.1:7800/` |
| **pg_featureserv (OGC API)**| PostGIS ST_AsGeoJSON | **9000** | `http://127.0.0.1:9000/collections` |
| **GeoServer OGC Services** | GeoServer 2.28 | **8080** | `http://127.0.0.1:8080/geoserver` |
| **PostgreSQL / PostGIS** | PostgreSQL 18 / PostGIS 3.6 | **5432** | `localhost:5432` (`smartserve_db`) |
| **Kubernetes NodePort Client**| K8s NodePort Service | **30080** | `http://<node-ip>:30080` |

---

## 5. How to Run and Launch

### Prerequisites
- Python 3.10+ with packages in `requirements.txt`
- PostgreSQL 16+ with PostGIS 3.4+ on `localhost:5432`
- GeoServer 2.24+ (optional, on `localhost:8080`)

### Quick Start (Native Host)

1. **Start the FastAPI Backend:**
   ```bash
   uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start the Original Leaflet Frontend:**
   ```bash
   python frontend/serve.py
   # Opens http://127.0.0.1:5500
   ```

3. **Start the MapLibre Vector Frontend:**
   ```bash
   python client/maplibre/serve.py
   # Or run: client\maplibre\run_maplibre.bat
   # Opens http://127.0.0.1:5600
   ```

4. **Start Vector Tile Services:**
   ```bash
   python services/tiles/pg_tileserv.py
   # Runs on http://127.0.0.1:7800
   ```

### Docker Compose Deployment
```bash
# Build and start all 6 microservices
docker compose up -d

# View status
docker compose ps

# Access Unified Nginx Client: http://localhost:80/
```

### Kubernetes Local Cluster Deployment
```bash
# Apply all manifests in order
kubectl apply -f k8s/01-namespace.yaml
kubectl apply -f k8s/02-secret.yaml
kubectl apply -f k8s/03-postgis-pv-pvc.yaml
kubectl apply -f k8s/04-postgis-statefulset.yaml
kubectl apply -f k8s/05-postgis-service.yaml
kubectl apply -f k8s/06-backend-deployment.yaml
kubectl apply -f k8s/07-backend-service.yaml
kubectl apply -f k8s/08-client-deployment.yaml
kubectl apply -f k8s/09-client-service.yaml

# Access via NodePort: http://localhost:30080
```

---

## 6. Automated Testing & Verification

Run the test suites across each phase:

```bash
# 1. FastAPI Backend Regression Suite (13/13 passing)
python scripts/test_api_endpoints.py

# 2. PostGIS Schema Extension Unit Tests (21/21 passing)
python database/experiential_learning/test_schema_extensions.py

# 3. GeoServer OGC WMS/WFS Integration Tests (15/15 passing)
python geoserver/test_ogc_services.py

# 4. MapLibre Frontend Verification Suite (31/31 passing)
python client/maplibre/verify_phase5_maplibre.py

# 5. Master End-to-End Platform Verification
python scripts/verify_entire_platform.py
```

---

## 7. Documentation & Reference Links

- [`docs/ANSWERS.md`](file:///e:/SEM_3/SmartServe_WebGIS_Portal/docs/ANSWERS.md): Complete technical viva questions and detailed conceptual explanations.
- [`docs/PROJECT_AUDIT.md`](file:///e:/SEM_3/SmartServe_WebGIS_Portal/docs/PROJECT_AUDIT.md): Initial repository audit, dataset counts, and implementation plan.
- [`analysis/data_engineering/DATA_ENGINEERING_REPORT.md`](file:///e:/SEM_3/SmartServe_WebGIS_Portal/analysis/data_engineering/DATA_ENGINEERING_REPORT.md): Data engineering validation results and CRS metrics.
- [`analysis/accessibility/ACCESSIBILITY_REPORT.md`](file:///e:/SEM_3/SmartServe_WebGIS_Portal/analysis/accessibility/ACCESSIBILITY_REPORT.md): Complete pedestrian accessibility analysis and population metrics.
- [`services/tiles/VECTOR_TILE_BENCHMARK_REPORT.md`](file:///e:/SEM_3/SmartServe_WebGIS_Portal/services/tiles/VECTOR_TILE_BENCHMARK_REPORT.md): MVT vs WFS latency and payload performance benchmarks.
- [`services/pmtiles/PMTILES_SERVERLESS_REPORT.md`](file:///e:/SEM_3/SmartServe_WebGIS_Portal/services/pmtiles/PMTILES_SERVERLESS_REPORT.md): PMTiles v3 serverless cloud architecture.
- [`client/maplibre/MAPLIBRE_FRONTEND_REPORT.md`](file:///e:/SEM_3/SmartServe_WebGIS_Portal/client/maplibre/MAPLIBRE_FRONTEND_REPORT.md): MapLibre GL JS frontend technical report.
- [`k8s/README.md`](file:///e:/SEM_3/SmartServe_WebGIS_Portal/k8s/README.md): Kubernetes deployment and cleanup guide.
