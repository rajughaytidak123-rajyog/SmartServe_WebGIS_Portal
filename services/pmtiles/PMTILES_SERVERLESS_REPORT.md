# SmartServe GIS – Cloud-Native PMTiles & Serverless WebGIS Architecture

**Project:** SmartServe GIS – Multi-Service Location-Based WebGIS Portal  
**Study Area:** Pune Municipal Corporation (PMC), Maharashtra, India  
**Phase:** Phase 8 – PMTiles Single-File Archives & Serverless GitHub Deployment  
**Specification:** PMTiles v3 (Protomaps Open Specification)  

---

## 1. Executive Summary

As WebGIS systems scale from localized research prototypes to enterprise municipal infrastructure, traditional tile architectures present significant operational bottlenecks:
1. **Dynamic Tile Servers (`pg_tileserv` / GeoServer):** Require running backend services, database connection pools, memory allocations, and active server management.
2. **Pre-rendered Tile Folders (Z/X/Y on disk):** Create hundreds of thousands of individual files, causing inode exhaustion, slow file transfer, and high cloud hosting costs.

**PMTiles** solves both challenges by packing an entire multi-zoom pyramid of vector tiles into a **single, immutable archive file (`.pmtiles`)**. Using standard HTTP Range Requests (RFC 7233), web browsers fetch only the exact byte offsets for the visible viewport directly from any static web server (such as GitHub Pages, AWS S3, Cloudflare R2, or local storage)—**with zero database, zero backend, and zero tile server running**.

In this phase, we developed a reproducible, PostGIS-native PMTiles generator that produced three production-ready archives covering Pune Municipal Corporation:
1. `pmc_services.pmtiles` (1.25 MB, 989 tiles, Z10–Z16)
2. `pmc_isochrones.pmtiles` (4.52 MB, 310 tiles, Z10–Z15)
3. `pmc_h3.pmtiles` (202.5 KB, 379 tiles, Z10–Z15)

---

## 2. Technical PMTiles v3 Architecture

### A. Binary Structure & Layout

A PMTiles v3 archive consists of four sequential sections stored in a single binary file:

```
┌─────────────────────────────────────────────────────────────┐
│ Header (127 bytes)                                          │
│ Magic Number "PMTiles", version 3, tile bounds, offsets     │
├─────────────────────────────────────────────────────────────┤
│ Root Directory (compressed via GZIP)                        │
│ Maps tile IDs (Hilbert curve order) to byte offsets/lengths │
├─────────────────────────────────────────────────────────────┤
│ JSON Metadata (compressed via GZIP)                         │
│ Layer schemas, attribute data types, bounding boxes         │
├─────────────────────────────────────────────────────────────┤
│ Leaf Directories (for large archives > 16,384 tiles)        │
├─────────────────────────────────────────────────────────────┤
│ Tile Data Payload                                           │
│ Compressed MVT (Mapbox Vector Tile) Protocol Buffers        │
└─────────────────────────────────────────────────────────────┘
```

### B. Hilbert Tile Indexing

PMTiles translates standard `(zoom, x, y)` Mercator tile coordinates into a 1-dimensional integer using a **Hilbert space-filling curve**:
$$\text{TileID} = f_{\text{hilbert}}(z, x, y)$$

Because the Hilbert curve preserves spatial locality, geographically adjacent tiles reside in contiguous byte offsets within the file. This drastically minimizes disk seek operations and enables efficient range reading.

### C. HTTP Range Request Lifecycle

When a user pans or zooms in MapLibre GL JS:
1. MapLibre determines the required tile coordinates $(z, x, y)$.
2. The `pmtiles.Protocol` adapter calculates the Hilbert TileID.
3. If not cached, it queries the root directory using an initial HTTP request:
   ```http
   GET /data/pmtiles/pmc_services.pmtiles HTTP/1.1
   Range: bytes=0-16383
   ```
4. The server responds with `206 Partial Content` delivering the 127-byte header and root directory.
5. Once the directory entry is resolved, MapLibre requests the exact tile payload:
   ```http
   GET /data/pmtiles/pmc_services.pmtiles HTTP/1.1
   Range: bytes=1048576-1052671
   ```
6. The browser decodes the Mapbox Vector Tile (MVT) protobuf and renders it directly on the GPU via WebGL.

---

## 3. Generated Archive Inventory & Validation

All archives were generated directly from PostGIS `smartserve_db` using `services/pmtiles/generate_pmtiles.py` and validated using the `pmtiles.reader.Reader` API:

| Archive Name | Layer Name | Geometry Type | Zoom Range | Addressed Tiles | File Size | Generation Time |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `pmc_services.pmtiles` | `services` | Point | Z10 – Z16 | **989 tiles** | **1,255.6 KB** | 1.92 s |
| `pmc_isochrones.pmtiles` | `isochrones` | MultiPolygon | Z10 – Z15 | **310 tiles** | **4,527.5 KB** | ~40 s (simplified) |
| `pmc_h3.pmtiles` | `h3_accessibility` | Polygon | Z10 – Z15 | **379 tiles** | **202.5 KB** | 1.09 s |
| **TOTAL** | **3 Archives** | | | **1,678 tiles** | **5,985.6 KB (~5.8 MB)** | **~43 s** |

### Header Verification Evidence

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

---

## 4. Architectural Comparison: WFS vs. MVT vs. PMTiles

The table below contrasts the three vector service delivery mechanisms available in SmartServe GIS:

| Architectural Metric | OGC WFS 2.0 (GeoServer) | Live MVT Server (`pg_tileserv`) | Serverless PMTiles (GitHub Pages / S3) |
| :--- | :--- | :--- | :--- |
| **Format** | GML / GeoJSON | Mapbox Vector Tile (`.pbf`) | Single-file archive (`.pmtiles`) |
| **Network Protocol** | Full Feature Retrieval | Dynamic HTTP Tile Service | HTTP Range Requests (RFC 7233) |
| **Database Dependency** | Mandatory (Live PostGIS) | Mandatory (Live PostGIS) | **Zero (Completely Serverless)** |
| **Backend Runtime** | Java / Tomcat | Python / Go Binary | **None (Pure Static Storage)** |
| **Zoom 16 Tile Payload** | 9,300 bytes (GeoJSON) | 958 bytes (Protobuf) | **958 bytes (Protobuf)** |
| **Latency (Local Host)** | 85 – 120 ms | 12 – 25 ms | **< 5 ms (Static Byte Range)** |
| **Hosting Cost** | High (Dedicated Cloud VM) | Moderate (Container Pod) | **$0.00 (GitHub Pages / Free Tier S3)** |
| **Offline Deployment** | Difficult | Requires local server stack | **Trivial (Single USB / File Copy)** |

---

## 5. MapLibre GL JS Client Integration

To enable zero-backend visualization in the modern frontend client (`client/maplibre/`):

1. **Include Protocol Library:**
   ```html
   <script src="https://unpkg.com/pmtiles@3.0.7/dist/pmtiles.js"></script>
   ```

2. **Register Protocol with MapLibre:**
   ```javascript
   const protocol = new pmtiles.Protocol();
   maplibregl.addProtocol("pmtiles", protocol.tile);
   ```

3. **Configure Map Source:**
   ```javascript
   map.addSource("services_pmtiles_src", {
     type: "vector",
     tiles: ["pmtiles://http://127.0.0.1:5600/data/pmtiles/pmc_services.pmtiles/{z}/{x}/{y}"],
     minzoom: 10,
     maxzoom: 22
   });
   ```

4. **Engine Switcher:**  
   The application header provides a real-time selector dropdown allowing the user to seamlessly toggle between **Live MVT Server (Port 7800)** and **Serverless PMTiles Archive**, demonstrating both enterprise dynamic architectures and cloud-native static deployment.

---

## 6. GitHub Actions Continuous Deployment Pipeline

A complete GitHub Actions CI/CD workflow is implemented under `.github/workflows/deploy.yml`:

- **Trigger:** Automated on push to `main` branch or manual execution (`workflow_dispatch`).
- **Target:** GitHub Pages (`https://<username>.github.io/<repo>/`).
- **Staging Step:**
  - Packages `client/maplibre/` (HTML, CSS, JS).
  - Copies `data/pmtiles/` archives directly into the static site bundle.
  - Bundles fallback GeoJSON layers for boundary and accessibility grids.
- **Result:** Fully autonomous, global static WebGIS deployment with zero server maintenance overhead.
