# SmartServe GIS – Phase 5 MapLibre GL JS Vector WebGIS Portal

**Project:** SmartServe GIS – Multi-Service Location-Based WebGIS Portal  
**Target Municipality:** Pune Municipal Corporation (PMC), Maharashtra, India  
**Phase:** Phase 5 – MapLibre GL JS Frontend Visualization  
**Server Port:** `http://127.0.0.1:5600`  
**Engine:** MapLibre GL JS 4.7.1 (GPU WebGL Hardware Accelerated)  

---

## 1. Executive Summary

Phase 5 introduces an enterprise-grade, high-performance vector mapping portal built with **MapLibre GL JS**. While the existing **Leaflet.js frontend (`http://127.0.0.1:5500`)** remains 100% intact and untouched, the new **MapLibre portal (`http://127.0.0.1:5600`)** elevates the project into modern spatial infrastructure capable of rendering hundreds of thousands of vertices at 60 FPS using client-side GPU acceleration.

### Core Capabilities Delivered:
- **Vector Tile Streaming:** Consumes Mapbox Vector Tiles (MVT) directly from `pg_tileserv` (Port 7800) and serverless PMTiles v3 archives.
- **Pedestrian Accessibility Exploration:** Real-time multi-scenario toggling between Normal walking speed (4.8 km/h) and Slower walking speed (3.6 km/h) across 5, 10, and 15-minute isochrones.
- **Facility Filtering:** Instant switching between All Healthcare (745 facilities), Hospitals Only (409 facilities), and Clinics Only (336 facilities).
- **H3 Hexagonal Grid Visualization:** Resolution 8 hexagonal cells dynamically styled into green accessible areas and red spatial gap deserts.
- **Population Density Grid:** Continuous choropleth visualization of resident distribution across Pune.
- **Multi-Category POI Exploration:** Retention of all 9 service categories and 20 subcategories (4,747 POIs total) with custom color matching.
- **Real-Time Accessibility Metrics HUD:** Floating heads-up display reflecting live coverage percentages, accessible square kilometres, reachable population, and spatial gap counts based on active user filters.
- **Cross-Platform Integration:** Bi-directional navigation links between Leaflet and MapLibre portals.

---

## 2. Architecture & File Layout

```
client/maplibre/
├── index.html                   # Master WebGIS UI with glassmorphic layout
├── css/
│   └── style.css                # Responsive dark/glass UI, animations, popup styling
├── js/
│   └── app.js                   # MapLibre map lifecycle, layer binding, filters, HUD
├── serve.py                     # Custom Python HTTP server with RFC 7233 Range support
├── run_maplibre.bat             # One-click Windows batch launcher
├── verify_phase5_maplibre.py    # 31-point automated verification suite
└── MAPLIBRE_FRONTEND_REPORT.md  # Architectural documentation and run guide
```

---

## 3. Visual Layer Hierarchy & Rendering Stack

Layers are registered into MapLibre in strict bottom-to-top visual stacking order to prevent visual occlusion while maximizing GPU rendering throughput:

```
[ Top: Markers & Highlights ] ──▶ Healthcare Target Highlights (Glowing Hospital & Clinic Rings)
              │
              ▼
    [ Layer 6: POIs ]         ──▶ Master Services (4,747 Circles colored by 9 domain categories)
              │
              ▼
   [ Layer 5: Network ]       ──▶ Walkable Street Segments (7,163 km OSMnx Street Centerlines)
              │
              ▼
  [ Layer 4: Isochrones ]     ──▶ Walking Isochrones (5 min #1d4ed8, 10 min #3b82f6, 15 min #93c5fd)
              │
              ▼
   [ Layer 3: H3 Grid ]       ──▶ H3 Hexagonal Cells (Green = Accessible, Red = Gap Desert)
              │
              ▼
 [ Layer 2: Demographics ]   ──▶ Population Density Grid (Orange/Brown Choropleth Ramp)
              │
              ▼
  [ Layer 1: Municipal ]      ──▶ Official PMC Boundary Line & Soft Fill (251.02 km²)
              │
              ▼
    [ Base: Basemap ]         ──▶ Carto Dark Matter / Positron / Voyager Vector Styles
```

---

## 4. Interactive Controls & Features

### A. Accessibility Scenario Filters
- **Walking Speed Dropdown:**
  - `Normal (4.8 km/h)`: Baseline adult walking speed (400m / 800m / 1200m catchments).
  - `Slower (3.6 km/h)`: Vulnerable demographic walking speed (300m / 600m / 900m catchments).
- **Target Facility Dropdown:**
  - `All Healthcare`: Unified 745 primary facilities.
  - `Hospitals Only`: 409 secondary/tertiary hospitals.
  - `Clinics Only`: 336 primary clinics & dispensaries.

### B. Real-Time Metrics Heads-Up Display (HUD)
A floating glassmorphic card on the bottom-left updates dynamically whenever scenario filters change:

| Scenario Filter | 15-Min Catchment Area | Land Coverage % | Reachable Population | Spatial Gap Deserts |
| :--- | :---: | :---: | :---: | :---: |
| **All Healthcare (4.8 km/h)** | **142.4 km²** | **56.7%** | **3.71M (93.1%)** | **42 H3 Cells** |
| **All Healthcare (3.6 km/h)** | **124.5 km²** | **49.6%** | **3.60M (90.3%)** | **68 H3 Cells** |
| **Hospitals Only (4.8 km/h)** | **132.8 km²** | **52.9%** | **3.58M (89.7%)** | **58 H3 Cells** |
| **Hospitals Only (3.6 km/h)** | **110.2 km²** | **43.9%** | **3.41M (85.5%)** | **89 H3 Cells** |
| **Clinics Only (4.8 km/h)** | **136.2 km²** | **54.3%** | **3.62M (90.8%)** | **51 H3 Cells** |
| **Clinics Only (3.6 km/h)** | **116.9 km²** | **46.6%** | **3.49M (87.5%)** | **77 H3 Cells** |

### C. Vector Delivery Engine Selector
Users can toggle between:
1. **Live MVT Server (`http://localhost:7800`):** PostGIS-backed dynamic tile rendering.
2. **Serverless PMTiles v3 Archive (`pmtiles://...`):** Static single-file cloud-native vector tiles.

### D. Layer Opacity Slider & Quick Tools
- **Isochrone Opacity Slider:** Real-time opacity adjustment (10% to 90%) using `map.setPaintProperty`.
- **Reset Extent Button:** Instantly flies the camera to the full PMC extent (`[73.8567, 18.5204]`, Zoom 12).
- **Toggle 3D Pitch Button:** Smoothly eases between 2D flat view ($0^\circ$) and 3D isometric view ($45^\circ$).

---

## 5. Automated Verification Results

The automated verification suite (`client/maplibre/verify_phase5_maplibre.py`) evaluated 31 distinct integration points across files, DOM nodes, datasets, and server endpoints:

```text
===========================================================================
  PHASE 5 VERIFICATION RESULT: 31/31 PASSED (100.0%)
===========================================================================
--- 1. MapLibre Frontend File Assets ---
[PASS] ✔ Asset: index.html (13.4 KB)
[PASS] ✔ Asset: style.css (10.2 KB)
[PASS] ✔ Asset: app.js (17.8 KB)
[PASS] ✔ Asset: serve.py (5.9 KB)
[PASS] ✔ Asset: run_maplibre.bat (0.5 KB)

--- 2. Required DOM Interactive Controls ---
[PASS] ✔ DOM Control: Map Container (#map)
[PASS] ✔ DOM Control: Sidebar Container (#sidebar)
[PASS] ✔ DOM Control: Tile Engine Switcher (#select-tile-source)
[PASS] ✔ DOM Control: Basemap Switcher (#select-basemap)
[PASS] ✔ DOM Control: Speed Scenario Dropdown (#select-speed)
[PASS] ✔ DOM Control: Facility Target Dropdown (#select-target)
[PASS] ✔ DOM Control: Isochrone Opacity Slider (#slider-opacity)
[PASS] ✔ DOM Control: Real-Time Metrics HUD (#metrics-hud)
[PASS] ✔ DOM Control: Quick Reset Extent Button (#btn-reset-view)
[PASS] ✔ DOM Control: Quick 3D Pitch Button (#btn-toggle-pitch)
[PASS] ✔ DOM Control: Back to Leaflet Link Button (#btn-back-leaflet)
[PASS] ✔ DOM Control: PMTiles Client Library Inclusion
[PASS] ✔ DOM Control: MapLibre GL JS CSS & JS Inclusions

--- 3. Client Spatial Datasets (GeoJSON & PMTiles) ---
[PASS] ✔ Dataset: PMC Municipal Boundary (360.5 KB)
[PASS] ✔ Dataset: Walking Isochrones GeoJSON (127.3 MB)
[PASS] ✔ Dataset: H3 Res 8 Hexagons GeoJSON (281.4 KB)
[PASS] ✔ Dataset: Population Grid GeoJSON (244.7 KB)
[PASS] ✔ Dataset: Services POI PMTiles Archive (1,255.6 KB)
[PASS] ✔ Dataset: Isochrones PMTiles Archive (4,527.5 KB)
[PASS] ✔ Dataset: H3 Accessibility PMTiles Archive (202.5 KB)

--- 4. HTTP Server & RFC 7233 Range Request Live Test ---
[PASS] ✔ HTTP 200: Root / (index.html)
[PASS] ✔ HTTP 200: /css/style.css (MIME text/css)
[PASS] ✔ HTTP 200: /js/app.js (Main Logic)
[PASS] ✔ HTTP 200: /data/boundary/pmc.geojson (Root Route)
[PASS] ✔ HTTP 206: PMTiles Range Request (bytes 0-511)

--- 5. Leaflet Frontend Cross-Link Integration ---
[PASS] ✔ Cross-Link: Leaflet -> MapLibre (Port 5600)
```

---

## 6. How to Launch and Test

### Option A: Using the Batch Launcher (Windows)
Double-click:
```cmd
client\maplibre\run_maplibre.bat
```

### Option B: Using the Command Line
```bash
python client/maplibre/serve.py
```
Then open your web browser at:  
👉 **`http://127.0.0.1:5600`**

### Running Both Portals Concurrently:
- **Leaflet Frontend:** `python frontend/serve.py` (Port 5500)
- **MapLibre Frontend:** `python client/maplibre/serve.py` (Port 5600)
- **FastAPI Backend:** `uvicorn backend.app.main:app --port 8000` (Port 8000)
- **MVT Tile Server:** `python services/tiles/pg_tileserv.py` (Port 7800)
