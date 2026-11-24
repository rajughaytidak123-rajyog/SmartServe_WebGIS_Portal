# SmartServe GIS – GeoServer OGC Services Report (Phase 3)

**Host:** `http://localhost:8080/geoserver`  
**Workspace:** `smartserve` (Namespace URI: `http://smartserve.gis`)  
**DataStore:** `smartserve_postgis` (PostgreSQL 18 + PostGIS 3.6 on `localhost:5432`)  
**Date:** November 23, 2026  
**Status:** Operational, Tested, and Verified (15/15 Tests Passed)

---

## 1. Overview & Architecture

In Phase 3, **GeoServer 2.28.1** was configured to publish the PostGIS spatial database layers as Open Geospatial Consortium (OGC) standard web services:
- **WMS (Web Map Service):** Versions 1.1.1 and 1.3.0 for dynamic server-side map rendering (PNG/JPEG) with custom SLD styling;
- **WFS (Web Feature Service):** Versions 1.0.0, 1.1.0, and 2.0.0 for direct geometric vector feature querying (GeoJSON / GML);
- **WCS (Web Coverage Service) Analysis:** Addressed per project requirements (documented in Section 6).

All layers connect live to `smartserve_db`, ensuring that any updates in PostGIS reflect immediately in the OGC map services.

```
                      +------------------------------------------+
                      |         GeoServer 2.28.1 Server          |
                      |          http://localhost:8080           |
                      +--------------------+---------------------+
                                           |
                +--------------------------+--------------------------+
                |                                                     |
       OGC WMS 1.3.0/1.1.1                                   OGC WFS 2.0.0/1.0.0
 (Server-side SLD Rendered PNGs)                        (Direct Vector GeoJSON Stream)
                |                                                     |
                v                                                     v
   [WMS Endpoints for WebGIS]                            [WFS Endpoints for GIS Tools]
                \                                                     /
                 \                                                   /
                  +------------------------+------------------------+
                                           | JDBC Connection
                                           v
                        +------------------------------------+
                        |      PostgreSQL 18 / PostGIS       |
                        |          smartserve_db             |
                        |  - study_area_boundaries (2 poly)  |
                        |  - services (4,747 POIs)           |
                        |  - walking_network_edges (99k edge)|
                        |  - accessibility_isochrones (18)   |
                        |  - h3_accessibility (363 hex)      |
                        |  - population_grid (363 pop cells) |
                        +------------------------------------+
```

---

## 2. Published Layers & DataStore Mapping

| Layer Name | Source PostGIS Table | Geometry Type | Native SRID | Declared SRS | Default SLD Style |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `smartserve:pmc_boundary` | `study_area_boundaries` | MultiPolygon | 4326 | EPSG:4326 | `pmc_boundary` |
| `smartserve:all_services` | `services` | Point | 4326 | EPSG:4326 | `all_services` |
| `smartserve:walking_network` | `walking_network_edges` | LineString | 4326 | EPSG:4326 | `walking_network` |
| `smartserve:accessibility_isochrones` | `accessibility_isochrones` | MultiPolygon | 4326 | EPSG:4326 | `accessibility_isochrones` |
| `smartserve:h3_accessibility` | `h3_accessibility` | Polygon | 4326 | EPSG:4326 | `h3_accessibility` |
| `smartserve:population_grid` | `population_grid` | Polygon | 4326 | EPSG:4326 | `population_grid` |

---

## 3. Styled Layer Descriptor (SLD) Implementation

Seven custom SLD XML files were authored and uploaded to GeoServer under `geoserver/sld/`:

1. `pmc_boundary.sld`: Semi-transparent blue fill (`#3b82f6`, opacity 0.05) with dashed border (`#1e40af`, width 2.5px) for clear spatial delimitation.
2. `all_services.sld`: Categorized circle and cross symbols for all 9 domain categories (Healthcare red, Food orange, Transport blue, Finance emerald, Education purple, Emergency dark red cross, Shopping pink, Accommodation indigo, Recreation green).
3. `healthcare_facilities.sld`: High-contrast red cross symbols for Hospitals and cyan circular markers for Clinics.
4. `walking_network.sld`: Subtle slate-gray stroke (`#64748b`, width 0.8px, opacity 0.6) for the 7,163 km pedestrian graph.
5. `accessibility_isochrones.sld`: Multi-interval blue fills with graduated opacity (5-min `#1d4ed8` 45% opacity; 10-min `#3b82f6` 30% opacity; 15-min `#93c5fd` 20% opacity with dashed boundary).
6. `h3_accessibility.sld`: Bivariate choropleth hex grid: light emerald (`#10b981`) for cells accessible within 15 minutes; coral red (`#ef4444`) for accessibility gap cells.
7. `population_grid.sld`: Graduated density choropleth (High density >20k/km² deep amber-brown; Medium 10k–20k/km² orange; Low <10k/km² peach).

---

## 4. OGC Service Endpoints & Example Requests

### 4.1 Web Map Service (WMS)
- **GetCapabilities URL:**
  ```
  http://localhost:8080/geoserver/smartserve/wms?service=WMS&version=1.3.0&request=GetCapabilities
  ```
- **Example GetMap URL (Isochrones + Healthcare POIs combined):**
  ```
  http://localhost:8080/geoserver/smartserve/wms?service=WMS&version=1.1.1&request=GetMap&layers=smartserve:accessibility_isochrones,smartserve:all_services&styles=&bbox=73.70,18.40,73.98,18.65&width=800&height=600&srs=EPSG:4326&format=image/png
  ```
- **Example GetMap URL (H3 Hexagonal Grid):**
  ```
  http://localhost:8080/geoserver/smartserve/wms?service=WMS&version=1.1.1&request=GetMap&layers=smartserve:h3_accessibility&styles=&bbox=73.70,18.40,73.98,18.65&width=800&height=600&srs=EPSG:4326&format=image/png
  ```

### 4.2 Web Feature Service (WFS)
- **GetCapabilities URL:**
  ```
  http://localhost:8080/geoserver/smartserve/wfs?service=WFS&version=2.0.0&request=GetCapabilities
  ```
- **Example GetFeature (GeoJSON Output, All Services):**
  ```
  http://localhost:8080/geoserver/smartserve/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=smartserve:all_services&outputFormat=application/json&maxFeatures=50
  ```
- **Example GetFeature with CQL Filter (Hospitals only):**
  ```
  http://localhost:8080/geoserver/smartserve/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=smartserve:all_services&outputFormat=application/json&cql_filter=subcategory='Hospital'
  ```
- **Example GetFeature (15-Minute Isochrone Polygons):**
  ```
  http://localhost:8080/geoserver/smartserve/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=smartserve:accessibility_isochrones&outputFormat=application/json&cql_filter=cutoff_minutes=15
  ```

---

## 5. Automated Verification Results

All 15 OGC unit tests passed with 100% success rate:

```text
--- 1. WMS GETCAPABILITIES ---
  [PASS] WMS 1.3.0 GetCapabilities             | HTTP 200 (3,119 ms, 241 KB)
  [PASS] WMS Layers Advertised in XML          | All 6 layers present

--- 2. WMS GETMAP (IMAGE RENDERING) ---
  [PASS] WMS GetMap: pmc_boundary              | HTTP 200 (604.2 ms,  63.8 KB -> wms_pmc_boundary.png)
  [PASS] WMS GetMap: all_services              | HTTP 200 (950.7 ms, 156.7 KB -> wms_all_services.png)
  [PASS] WMS GetMap: walking_network           | HTTP 200 (1,208 ms, 195.5 KB -> wms_walking_network.png)
  [PASS] WMS GetMap: accessibility_isochrones  | HTTP 200 (950.2 ms, 175.6 KB -> wms_accessibility_isochrones.png)
  [PASS] WMS GetMap: h3_accessibility          | HTTP 200 (236.8 ms,  89.5 KB -> wms_h3_accessibility.png)
  [PASS] WMS GetMap: population_grid           | HTTP 200 (209.3 ms,  90.4 KB -> wms_population_grid.png)

--- 3. WFS GETCAPABILITIES ---
  [PASS] WFS 2.0.0 GetCapabilities             | HTTP 200 (815.8 ms, 97.2 KB)

--- 4. WFS GETFEATURE (GEOJSON STREAMING) ---
  [PASS] WFS GetFeature: pmc_boundary          | HTTP 200 (452.2 ms, 2 features)
  [PASS] WFS GetFeature: all_services          | HTTP 200 (52.9 ms, 25 features)
  [PASS] WFS GetFeature: walking_network       | HTTP 200 (46.9 ms, 25 features)
  [PASS] WFS GetFeature: accessibility_isochrones | HTTP 200 (12,743 ms, 18 features)
  [PASS] WFS GetFeature: h3_accessibility      | HTTP 200 (41.3 ms, 25 features)
  [PASS] WFS GetFeature: population_grid       | HTTP 200 (23.9 ms, 25 features)

--- 5. FASTAPI BACKEND REGRESSION TEST ---
  >> 13/13 tests passed (100.0%) - ZERO REGRESSIONS
```

Test image outputs generated and stored in:
`geoserver/test_outputs/`

---

## 6. OGC Web Coverage Service (WCS) Policy Compliance

Per assignment instructions:
> *"Configure WCS only for suitable raster coverage data. Do not claim WCS is operational if no suitable raster coverage has been published."*

**Technical Statement:**
SmartServe GIS is fundamentally a vector-based infrastructure portal (Points of Interest, LineString street networks, and Polygon/MultiPolygon isochrone and hexagonal aggregations). Vector geometries are natively and correctly served through **WFS** (features) and **WMS** (cartographic rendering).

WCS is designed strictly for space-filling, multi-dimensional raster coverage data (e.g., GeoTIFF digital elevation models, satellite multi-spectral imagery, or continuous raster population rasters). Because the current database stores vector layers rather than raster coverages, WCS is explicitly documented as **inactive / not applicable for vector datasets**. No false claims of operational WCS are made.

---

## 7. Execution Commands

To reconfigure GeoServer at any time:
```powershell
python geoserver/configure_geoserver.py
```
To run the full automated OGC test suite:
```powershell
python geoserver/test_ogc_services.py
```
