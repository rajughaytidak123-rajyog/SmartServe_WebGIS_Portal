# SmartServe GIS – Pedestrian Accessibility Analysis Report (Phase 4)

**Study Area:** Pune Municipal Corporation (PMC), Maharashtra, India  
**Target Municipality Land Area:** 251.02 km² (UTM Zone 43N / EPSG:32643)  
**Primary Facilities Evaluated:** 745 Primary Healthcare Facilities (409 Hospitals, 336 Clinics)  
**Methodology:** Multimodal Walking Network Graph Shortest-Path Traversal & Uber H3 Discrete Global Grid  
**Date:** November 23, 2026  
**Status:** Completed, Verified, and Ingested into PostGIS

---

## 1. Executive Summary

This study executes a comprehensive pedestrian walking accessibility assessment across Pune Municipal Corporation (PMC) to quantify spatial and demographic access to essential healthcare infrastructure.

Unlike conventional planar Euclidean (straight-line) buffer analyses that assume unobstructed movement, this study models the actual walkable street network extracted from OpenStreetMap using OSMnx, measuring genuine travel impedance (distance in meters and time in seconds) across 39,454 intersections and 99,062 street segments spanning 7,163.5 km.

Two distinct pedestrian velocity scenarios were evaluated across 5, 10, and 15-minute thresholds:
1. **Normal Walking Speed (4.8 km/h or 1.333 m/s):** The global standard pedestrian velocity for healthy adults.
2. **Slower Walking Speed (3.6 km/h or 1.000 m/s):** Represents vulnerable demographics, including senior citizens, mobility-impaired individuals, and parents accompanying young children.

Spatial aggregation was executed using **Uber H3 Discrete Global Grid** hexagons (Resolution 8: ~0.737 km²; Resolution 9: ~0.105 km²) to eliminate modifiable areal unit problem (MAUP) boundary biases, identify spatial accessibility gaps, and assess demographic coverage across PMC's ~3.99 million residents.

---

## 2. Walking Network Topology & Graph Properties

- **Network Source:** OpenStreetMap (OSM) via OSMnx 2.2.0 (`network_type='walk'`).
- **Target Spatial Mask:** Official dissolved boundary polygon of Pune Municipal Corporation (`data/boundary/pmc.geojson`, 251.02 km²).
- **Graph Type:** Directed Multi-Edge Graph (`MultiDiGraph`).
- **Graph Nodes (Vertices):** **39,454 nodes** (stored in PostGIS table `walking_network_nodes`).
- **Graph Edges (Segments):** **99,062 edges** (stored in PostGIS table `walking_network_edges`).
- **Total Network Length:** **7,163.5 km** of walkable pathways, footways, living streets, pedestrian tracks, and residential corridors.
- **Topological Connectivity:** 100.0% of nodes reside within a single weakly connected component, confirming network continuity across the municipal core.
- **Facility Snapping Quality:** 745 primary healthcare facilities were snapped to their nearest street network node with a median snapping distance of **18.4 meters** (maximum snap distance 142.1 m in peripheral semi-rural pockets).

---

## 3. Network Isochrones vs. Euclidean Buffers: The Tortuosity Factor

A critical methodological finding of this study is the substantial divergence between actual network isochrones and simplistic circular Euclidean buffers:
- **Circular Euclidean Buffers** assume direct "as-the-crow-flies" flight paths, ignoring physical barriers such as the Mutha and Mula rivers, railway corridors, steep topography (Vetal Tekdi, Taljai hills), and non-permeable superblock developments.
- **Walking Network Isochrones** follow actual walkable street geometry, accounting for street intersections, cul-de-sacs, and winding terrain.

### Path Tortuosity Efficiency
The ratio of reachable network area to theoretical circular buffer area is termed the **Network Tortuosity Efficiency**:
$$\text{Efficiency} = \frac{\text{Area}_{\text{network}}}{\text{Area}_{\text{euclidean}}} \times 100\%$$

In central grid-like areas (e.g. Shivajinagar, Deccan), network efficiency reaches **65%–72%**. In peripheral undulating wards (e.g. Katraj, Ambegaon, Dhanori), efficiency drops to **42%–52%**, demonstrating that circular buffers severely overestimate actual pedestrian accessibility by 30% to 50%.

---

## 4. Multi-Interval Walking Accessibility Results

All isochrones were generated using multi-source Dijkstra shortest-path traversal on the projected metric graph (UTM Zone 43N) and clipped strictly to the PMC boundary.

### 4.1 Scenario A: Normal Walking Speed (4.8 km/h / 1.333 m/s)
- **5 Minutes (400 meters):**
  - Hospitals: Reachable area = **32.8 km²** (13.1% of PMC)
  - Clinics: Reachable area = **38.4 km²** (15.3% of PMC)
  - Combined Primary Healthcare: Reachable area = **54.2 km²** (21.6% of PMC)
- **10 Minutes (800 meters):**
  - Hospitals: Reachable area = **84.5 km²** (33.7% of PMC)
  - Clinics: Reachable area = **88.2 km²** (35.1% of PMC)
  - Combined Primary Healthcare: Reachable area = **112.8 km²** (44.9% of PMC)
- **15 Minutes (1,200 meters - Standard 15-Minute City Benchmark):**
  - Hospitals: Reachable area = **132.6 km²** (52.8% of PMC)
  - Clinics: Reachable area = **131.4 km²** (52.3% of PMC)
  - Combined Primary Healthcare: Reachable area = **156.4 km²** (**62.3% of PMC**)
  - Areas Outside 15-Min Threshold: **94.6 km²** (37.7% of PMC)

### 4.2 Scenario B: Slower Walking Speed (3.6 km/h / 1.000 m/s - Vulnerable Populations)
- **5 Minutes (300 meters):**
  - Combined Primary Healthcare: Reachable area = **36.8 km²** (14.7% of PMC)
- **10 Minutes (600 meters):**
  - Combined Primary Healthcare: Reachable area = **79.5 km²** (31.7% of PMC)
- **15 Minutes (900 meters):**
  - Hospitals: Reachable area = **96.2 km²** (38.3% of PMC)
  - Clinics: Reachable area = **98.4 km²** (39.2% of PMC)
  - Combined Primary Healthcare: Reachable area = **124.6 km²** (**49.6% of PMC**)
  - Areas Outside 15-Min Threshold: **126.4 km²** (50.4% of PMC)

### 4.3 The Mobility Vulnerability Gap
When walking speed decreases from 4.8 km/h to 3.6 km/h:
- The accessible land area drops from **156.4 km² to 124.6 km²** (a net loss of **31.8 km²** or **12.7% of the city**).
- More than half (50.4%) of PMC land area is inaccessible within 15 minutes for elderly or mobility-impaired residents.

---

## 5. Uber H3 Hexagonal Spatial Aggregation

To eliminate administrative boundary arbitrary effects, PMC was partitioned into discrete global hexagonal cells:

### H3 Resolution 8 (~0.737 km² per cell, ~461m edge length):
- **Total Cells covering PMC:** **373 cells**
- **Cells with Direct Primary Healthcare:** **188 cells (50.4%)**
- **Cells Accessible within 15 Min (Normal Speed):** **264 cells (70.8%)**
- **Cells Accessible within 15 Min (Slower Speed):** **214 cells (57.4%)**
- **Spatial Gap Cells (Zero facility & > 15 min walk):** **109 cells (29.2%)**
- **Mean Network Distance to Nearest Hospital:** **1,148 meters**
- **Mean Network Distance to Nearest Clinic:** **1,192 meters**

### Spatial Gap Identification
The spatial gap cells are heavily concentrated in:
1. **Far-Eastern Urban Fringe:** Wagholi, Manjari Khurd, Keshavnagar peripheral sectors.
2. **Southern Hilly Ridges:** Katraj southern spurs, Ambegaon Khurd, Narhe hillocks.
3. **South-Western Periphery:** Dhayari upper ridges, Shivane fringe.
In contrast, central wards (Kasba Peth, Deccan Gymkhana, Shivajinagar, Camp, Kothrud) exhibit exceptional redundancy, with average walking distances to the nearest hospital under 350 meters.

---

## 6. Population Accessibility Assessment

- **Demographic Baseline:** ~3,990,000 residents across 251.02 km² (average density ~15,895 persons/km²).
- **Core High-Density Zones:** 25,000–35,000 persons/km².
- **Intermediate Residential Zones:** 12,000–20,000 persons/km².
- **Peripheral Suburbs:** 5,000–10,000 persons/km².

### Population Access to Primary Healthcare
| Scenario | Accessible Population | Share of City Population | Unserved Population | Unserved Share |
| :--- | :---: | :---: | :---: | :---: |
| **Normal Walking Speed (4.8 km/h, 15 min)** | **3,215,940** | **80.6%** | **774,060** | **19.4%** |
| **Slower Walking Speed (3.6 km/h, 15 min)** | **2,573,550** | **64.5%** | **1,416,450** | **35.5%** |
| **Vulnerability Disparity Gap** | **-642,390** | **-16.1%** | **+642,390** | **+16.1%** |

*Key Planning Takeaway:*  
While 62.3% of the land area is accessible under normal walking conditions, **80.6% of the human population** is served due to the strong concentration of healthcare facilities in high-density urban wards. However, for senior citizens and mobility-challenged individuals, **over 642,000 residents** transition from served to unserved status.

---

## 7. Artifacts & Database Ingestion Summary

All analytical results are stored in the PostGIS database and exported as standard GeoJSON files:
1. `walking_network_nodes`: 39,454 vertices with GiST spatial indexes.
2. `walking_network_edges`: 99,062 segments with length in meters, travel times, and GiST indexes.
3. `accessibility_isochrones`: 18 multi-interval polygon service areas.
4. `h3_accessibility`: 373 Res-8 and 2,520 Res-9 hexagonal cells with reachability flags.
5. `population_grid`: Demographic density grid.
6. `accessibility_summary`: Scenario benchmarking metrics.
7. GeoJSON outputs in `data/analysis/` and static figures in `analysis/accessibility/maps/`.
