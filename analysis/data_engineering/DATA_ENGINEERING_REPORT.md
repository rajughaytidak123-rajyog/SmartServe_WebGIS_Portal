# SmartServe GIS – Spatial Data Engineering Report (Phase 1)

**Study Area:** Pune Municipal Corporation (PMC), Maharashtra, India  
**Secondary Study Area:** Pimpri-Chinchwad Municipal Corporation (PCMC)  
**CRS Standard:** Storage/Exchange: EPSG:4326 (WGS 84) | Planar Metric Analysis: EPSG:32643 (UTM Zone 43N)  
**Date:** November 23, 2026  
**Status:** Validated, Verified & Reproducible (Phase 1 Complete)

---

## 1. Overview & Objective

Phase 1 establishes the verified data engineering foundation for the experiential learning assignment. The primary objectives are:
1. Validate geometry validity and topological consistency for all municipal boundaries and Points of Interest (POIs).
2. Enforce explicit Coordinate Reference Systems (CRS) across all layers, establishing standard transformations between geographic WGS 84 (`EPSG:4326`) and conformal projected UTM Zone 43N (`EPSG:32643`).
3. Audit attribute completeness, check missing values, and analyze duplicate identifiers.
4. Execute spatial Point-in-Polygon (PIP) containment analysis confirming that all PMC features strictly reside within the official PMC boundary polygon.
5. Extract primary healthcare facilities (Hospitals and Clinics) into a dedicated analytical dataset for the upcoming walking-network accessibility analysis while strictly preserving every other service category and subcategory in the portal.
6. Provide an automated, reproducible data engineering pipeline under `analysis/data_engineering/`.

---

## 2. Coordinate Reference System (CRS) Selection Rationale

### Why EPSG:4326 for Storage and Exchange?
- **Global Standard:** EPSG:4326 (WGS 84 geographic coordinate system in decimal degrees) is the universal standard for GeoJSON, OpenStreetMap (OSM) extractions, web mapping APIs, and Leaflet/MapLibre GL visual clients.
- **Interoperability:** PostGIS uses EPSG:4326 geometry and geography types to interface with external web services and GPS coordinate streams.

### Why EPSG:32643 (UTM Zone 43N) for Analytical Operations?
- **Planar Metric Accuracy:** EPSG:4326 coordinates are angular (degrees of longitude and latitude). Distance and area calculations performed directly on geographic coordinates introduce significant distortion away from the equator.
- **Optimal Conformal Projection:** Pune is situated at approximately latitude 18.52° N and longitude 73.85° E. It lies centrally within **Universal Transverse Mercator (UTM) Zone 43 North** (spanning 72° E to 78° E longitude).
- **Metric Unit Uniformity:** UTM Zone 43N uses planar meters as its linear unit with minimal scale distortion (< 0.04% across the study area). It enables accurate Euclidean buffers, network distance evaluations, graph traversal, and polygon area computations (`ST_Area` / `shapely.area`).

---

## 3. Boundary Geometry & Topological Validation

All boundary files were audited using `shapely.is_valid` and reprojected to UTM Zone 43N to calculate ground areas:

| Boundary Layer | Native CRS | Validity | Features | Geometry Type | Projected Area (EPSG:32643) | PostGIS Geodesic Area |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: |
| `pmc.geojson` | EPSG:4326 | **Valid** | 1 | MultiPolygon | **251.02 km²** | 251.13 km² |
| `pcmc.geojson` | EPSG:4326 | **Valid** | 1 | MultiPolygon | **176.74 km²** | 176.81 km² |
| `pmc_pcmc_combined.geojson` | EPSG:4326 | **Valid** | 2 | MultiPolygon | **427.76 km²** | 427.94 km² |
| `study_area.geojson` | EPSG:4326 | **Valid** | 1 | MultiPolygon | **427.76 km²** | 427.94 km² |

*Topological Finding:* Zero self-intersections or unclosed rings detected. The combined municipal area of 427.76 km² establishes the unified spatial mask.

---

## 4. POI Master Dataset & Attribute Completeness

The master dataset (`data/final/all_services.geojson`) comprises **4,742 POIs** (and 4,747 in PostGIS following landmark mall enrichment):

### 4.1 Attribute Quality Metrics
- `id`: 100% populated (unique integer keys 1–4,742).
- `name`: 100% populated (clean facility names standardized from OSM name tags).
- `category`: 100% populated across 9 standardized domains.
- `subcategory`: 100% populated across 20 standardized types.
- `latitude` / `longitude`: 100% populated, valid WGS 84 coordinates.
- `municipality`: 100% classified (`PMC` or `PCMC`).
- `address`: 72.4% populated.
- `phone`: 19.8% populated (contact information from OSM).
- `website`: 16.5% populated.
- `wheelchair`: Populated where surveyed in OSM.

### 4.2 Duplicate Analysis
- **Duplicate OSM IDs:** 0 duplicates. Every record maps to a distinct OpenStreetMap node or centroid.
- **Duplicate Coordinates:** 38 coordinate pairings share the same location. Manual inspection confirms these represent legitimate co-located services (e.g. multi-specialty polyclinics, diagnostic labs, or bank branches located in the same shopping complex or multi-story medical building).

---

## 5. Spatial Point-in-Polygon (PIP) Containment Results

Using `shapely.within` against the official dissolved PMC municipal polygon:
- **Total POIs tagged `municipality == 'PMC'`:** 3,536 (in GeoJSON) / 3,541 (in PostGIS).
- **Spatial Containment within PMC boundary:** **3,536 / 3,536 (100.0%)**.
- **Mismatched / Boundary spillover:** **0 features (0.0%)**.
- **Total POIs tagged `municipality == 'PCMC'`:** 1,206.
- **Spatial Containment within PCMC boundary:** **1,206 / 1,206 (100.0%)**.

*Conclusion:* The administrative municipality tagging matches spatial reality with 100% precision.

---

## 6. Primary Healthcare Accessibility Target Extraction

To support Phase 4 (Pedestrian Accessibility Analysis) without altering the multi-service nature of the WebGIS portal:
- The entire portal retains all 9 service categories.
- A specialized analytical subset was extracted and written to `data/analysis/pmc_healthcare_facilities.geojson`:
  - **PMC Hospitals:** 409 facilities.
  - **PMC Clinics & Dispensaries:** 336 facilities.
  - **Total Primary Healthcare Destinations:** **745 facilities**.
- Each feature in the analytical output includes both WGS 84 (`latitude`, `longitude`) and planar UTM Zone 43N projected coordinates (`utm_x`, `utm_y` in meters) for rapid network distance computation.

### Retained Categories in PMC
| Domain Category | Total Facilities in PMC | Retained in Portal |
| :--- | :---: | :---: |
| Food (Restaurants, Cafes, Bakeries) | 902 | YES |
| Healthcare (Hospitals, Clinics, Pharmacies) | 850 | YES |
| Finance (Banks, ATMs) | 580 | YES |
| Recreation (Parks) | 329 | YES |
| Education (Schools, Colleges) | 349 | YES |
| Transport (Petrol Pumps, Metro Stations, Bus Stations, EV Charging) | 228 | YES |
| Shopping (Shopping Malls, Supermarkets) | 140 | YES |
| Accommodation (Hotels) | 100 | YES |
| Emergency (Police Stations, Fire Stations) | 58 | YES |
| **Total PMC Services** | **3,536** | **All Preserved** |

---

## 7. Data Limitations & Documentation

1. **OSM Survey Completeness:** OpenStreetMap data relies on crowd-sourced community contributions. While central PMC (Shivajinagar, Kothrud, Deccan, Pune Station) has dense coverage, peripheral suburban wards (e.g. Wagholi, Ambegaon) may have lower survey density.
2. **Opening Hours & Contact Details:** Telephone numbers and operating schedules are available for approximately 20% of POIs. The spatial coordinates and facility classifications, however, are 100% verified.
3. **Footway Coverage:** Pedestrian-specific pathways and informal cut-throughs in older urban cores may be under-represented in raw road datasets. This is mitigated in Phase 4 by constructing an OSMnx walkable network incorporating residential, living streets, pedestrian zones, and footpaths.

---

## 8. Verification & Execution

The automated pipeline can be reproduced at any time via:
```bash
python analysis/data_engineering/run_data_engineering_pipeline.py
```
Outputs generated in `data/analysis/`:
- `data_validation_report.json`
- `pmc_containment_report.json`
- `pmc_all_services.geojson` (3,536 PMC POIs with UTM 43N coordinates)
- `pmc_healthcare_facilities.geojson` (745 primary healthcare destinations)
