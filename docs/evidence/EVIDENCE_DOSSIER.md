# SmartServe GIS – Experiential Learning Technical Evidence Dossier

**Project:** SmartServe GIS – Location-Based Multi-Service WebGIS & Spatial Infrastructure Platform  
**Target Municipality:** Pune Municipal Corporation (PMC), Maharashtra, India (with PCMC intact)  
**Deliverable:** Master Verification & Viva Evidence Dossier  
**Date of Audit:** November 2026  

---

## 1. Executive Verification Dashboard

| Phase | Component | Key Output / Metric | Status | Automated Test Result |
| :---: | :--- | :--- | :---: | :---: |
| **0** | **Project Inspection & Audit** | 4,747 POIs, 9 domains, 20 subcategories verified | **PASSED** | 13/13 API Tests (100%) |
| **1** | **Spatial Data Engineering** | 100% valid geometries; 3,536 PMC POIs confirmed in boundary; UTM 43N projected | **PASSED** | Geometry & CRS Validation Pipeline |
| **2** | **PostGIS Schema Extension** | 6 new tables, GiST R-Tree indexes, foreign keys | **PASSED** | 21/21 Unit Tests (100%) |
| **4** | **Pedestrian Accessibility** | 39,454 nodes, 99,062 edges, 7,163 km; 15m isochrones; 363 H3 cells; 110k vulnerability gap | **PASSED** | 14 Pipeline Artifacts Verified |
| **3** | **GeoServer OGC Services** | PostGIS JDBC store, 7 SLD styles, 6 published layers, WMS & WFS operational | **PASSED** | 15/15 OGC Unit Tests (100%) |
| **6** | **Vector Tile Services** | Standalone MVT on Port 7800; 12ms latency; 90% payload reduction vs WFS | **PASSED** | Multi-zoom Benchmark Suite |
| **5** | **MapLibre GL JS Client** | GPU WebGL client on Port 5600; Live MVT + PMTiles; HUD; 3D isometric pitch | **PASSED** | 31/31 Frontend Unit Tests (100%) |
| **8** | **PMTiles Serverless Archives** | 3 `.pmtiles` archives (5.98 MB total); RFC 7233 HTTP Range 206 support; GitHub Actions | **PASSED** | PMTiles v3 Header Reader Validation |
| **7** | **Docker Compose** | 6 microservices (`postgis`, `backend`, `pg_tileserv`, `pg_featureserv`, `geoserver`, `client`) | **PASSED** | PyYAML Config Validation |
| **9** | **Kubernetes Deployment** | StatefulSet, PVC 10Gi, Secret, Deployments, NodePort 30080, Ingress | **PASSED** | K8s Manifest Linting & Testing |
| **10**| **Viva Guide & Documentation** | Comprehensive `docs/ANSWERS.md` and root `README.md` | **PASSED** | Complete Viva Evidence Package |

---

## 2. PostGIS Database Evidence & Table Inventory

The PostgreSQL 18 / PostGIS 3.6 database (`smartserve_db`) contains 10 public spatial tables:

```text
Table Name                 Geometry Column   SRID   Index Type       Feature Count   Purpose
─────────────────────────────────────────────────────────────────────────────────────────────────────────────
categories                 N/A               N/A    B-Tree           20 rows         Taxonomy taxonomy lookup
study_area_boundaries      geom              4326   GiST (R-Tree)    2 polygons      PMC (251.02 km²) & PCMC (176.74 km²)
services                   geom, geog        4326   GiST (Geom/Geog) 4,747 points    Master multi-domain POI catalog
walking_network_nodes      geom              4326   GiST (R-Tree)    39,454 points   Pedestrian graph vertices
walking_network_edges      geom              4326   GiST (R-Tree)    99,062 lines    7,163.5 km pedestrian street network
accessibility_isochrones   geom              4326   GiST (R-Tree)    18 polygons     5, 10, 15 min walking catchments
h3_accessibility           geom              4326   GiST (R-Tree)    363 polygons    Uber H3 Resolution 8 cells
population_grid            geom              4326   GiST (R-Tree)    363 polygons    Demographic population distribution
accessibility_summary      N/A               N/A    B-Tree           18 rows         Aggregated benchmark metrics
─────────────────────────────────────────────────────────────────────────────────────────────────────────────
```

---

## 3. Empirical Accessibility Analysis Results

### A. Reachable Surface Area by Scenario
- **PMC Total Boundary Area:** **251.02 km²** (EPSG:32643 UTM Zone 43N)

| Destination Target | Walking Pace | 5-Minute Area | 10-Minute Area | 15-Minute Area | 15-Min PMC Coverage % |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **All Healthcare** | **Normal (4.8 km/h)** | 48.71 km² | 104.16 km² | **142.42 km²** | **56.74%** |
| **All Healthcare** | **Slower (3.6 km/h)** | 35.20 km² | 82.35 km² | **124.47 km²** | **49.59%** |
| **Hospitals Only** | **Normal (4.8 km/h)** | 39.12 km² | 92.48 km² | **132.84 km²** | **52.92%** |
| **Hospitals Only** | **Slower (3.6 km/h)** | 27.56 km² | 71.30 km² | **110.15 km²** | **43.88%** |
| **Clinics Only** | **Normal (4.8 km/h)** | 42.60 km² | 98.70 km² | **136.21 km²** | **54.26%** |
| **Clinics Only** | **Slower (3.6 km/h)** | 30.18 km² | 77.40 km² | **116.89 km²** | **46.57%** |

### B. Network Isochrones vs. Euclidean Circular Buffers (Tortuosity Impact)
Circular buffers drastically overestimate walkable catchments because they ignore physical street networks, rivers, and terrain barriers:

| Facility Type | 15-Min Buffer Area (4.8 km/h) | 15-Min Network Area (4.8 km/h) | Buffer Overestimation % | Path Tortuosity Efficiency |
| :--- | :---: | :---: | :---: | :---: |
| **Hospitals Only** | 224.18 km² | 132.84 km² | **+40.7% overestimation** | **59.3% efficiency** |
| **Clinics Only** | 219.64 km² | 136.21 km² | **+38.0% overestimation** | **62.0% efficiency** |
| **All Healthcare** | 229.40 km² | 142.42 km² | **+37.9% overestimation** | **62.1% efficiency** |

### C. H3 Discrete Global Grid Hexagonal Metrics (Resolution 8)
- Total H3 Cells covering PMC: **363 cells** (~0.737 km² each).
- **Accessible Cells (within 15 min):** **321 cells (88.4%)**.
- **Spatial Gap Cells (Deserts > 15 min):** **42 cells (11.6%)**.

### D. Demographic Population Coverage & Vulnerability Gap
- **Baseline PMC Population:** ~3,989,000 residents across the 363 H3 cells.
- **Normal Walking Access (4.8 km/h):** **3,714,728 citizens (93.12%)** reachable.
- **Slower Walking Access (3.6 km/h):** **3,604,072 citizens (90.35%)** reachable.
- **Demographic Vulnerability Gap:** Exactly **110,656 residents (2.77%)** become stranded when walking speed decreases to 3.6 km/h.

---

## 4. Vector Tile Performance Benchmarking Evidence

Empirical measurements comparing GeoServer OGC WFS vs. `pg_tileserv` MVT across three representative zoom scales:

```text
========================================================================================
Zoom Level       Scale Type        GeoServer WFS Latency   pg_tileserv MVT Latency   Speedup Factor
────────────────────────────────────────────────────────────────────────────────────────
Zoom 12          City-Wide         118 ms                  25 ms                     4.7x Faster
Zoom 14          District-Level    94 ms                   18 ms                     5.2x Faster
Zoom 16          Street-Level      85 ms                   12 ms                     7.1x Faster
────────────────────────────────────────────────────────────────────────────────────────

Payload Size at Zoom 16:
- GeoServer WFS (GeoJSON): 9,300 bytes (9.1 KB)
- pg_tileserv (Binary MVT Protobuf): 958 bytes (0.9 KB)
- Payload Compression Savings: 89.7% reduction
```

---

## 5. Cloud-Native PMTiles v3 Verification Logs

Direct inspection output from `pmtiles.reader.Reader`:

```text
[VERIFY] Header Check for pmc_services.pmtiles:
  ├─ Spec Version : 3
  ├─ Tile Type    : MVT
  ├─ Compression  : GZIP
  ├─ Min/Max Zoom : Z10 - Z16
  ├─ Tile Entries : 989
  └─ Root Length  : 4,586 bytes

[VERIFY] Header Check for pmc_isochrones.pmtiles:
  ├─ Spec Version : 3
  ├─ Tile Type    : MVT
  ├─ Compression  : GZIP
  ├─ Min/Max Zoom : Z10 - Z15
  ├─ Tile Entries : 310
  └─ Root Length  : 1,751 bytes

[VERIFY] Header Check for pmc_h3.pmtiles:
  ├─ Spec Version : 3
  ├─ Tile Type    : MVT
  ├─ Compression  : GZIP
  ├─ Min/Max Zoom : Z10 - Z15
  ├─ Tile Entries : 379
  └─ Root Length  : 1,611 bytes
```

RFC 7233 HTTP Range Request Verification (`client/maplibre/serve.py`):
```text
GET /data/pmtiles/pmc_services.pmtiles HTTP/1.1
Range: bytes=0-511
--> HTTP/1.1 206 Partial Content
--> Content-Range: bytes 0-511/1285727
--> Content-Length: 512
--> Result: PASS (Exact 512 bytes delivered for MapLibre GPU rendering)
```

---

## 6. API Regression Pass Rate (FastAPI Backend)

Output of `scripts/test_api_endpoints.py`:

```text
  [PASS] GET / (Root API Metadata) 
  [PASS] GET /health (PostGIS Connectivity) - PostGIS: 3.6 USE_GEOS=1 USE_PROJ=1 USE_STATS=1, POIs: 4747
  [PASS] GET /api/v1/categories/ (Categories List) Found 20 categories/subcategories
  [PASS] GET /api/v1/categories/tree (Category Tree) Found 9 top-level categories
  [PASS] GET /api/v1/boundaries/ (Municipal Polygons) Features: 2
  [PASS] GET /api/v1/services/nearby (Hospitals within 3km of Pune Station) Found 77 hospitals nearby
  [PASS] GET /api/v1/services/knn (5 Closest Petrol Pumps to Swargate) Returned 5 nearest POIs
  [PASS] GET /api/v1/services/search (Keyword Search 'Ruby') Matches found: 16
  [PASS] GET /api/v1/services/431 (Service Detail) Name: Nityashraddha super speciality hospital
  [PASS] GET /api/v1/services/geojson (Native PostGIS GeoJSON Stream) Returned 74 features in Emergency category
  [PASS] GET /api/v1/analytics/overview (System Metrics) Total services: 4747, Municipalities: 2
  [PASS] GET /api/v1/analytics/density (Spatial POI Density per km²) Overall Density: 11.12 POIs/km²
  [PASS] GET /api/v1/analytics/nearby-summary (Category Breakdown within 2km) Found 593 total POIs
===========================================================================
>> TEST RESULTS: 13/13 tests passed (100.0%)
```
