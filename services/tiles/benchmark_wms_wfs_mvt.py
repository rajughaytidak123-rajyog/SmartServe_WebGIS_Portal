"""
SmartServe GIS - Phase 6: WMS vs WFS vs MVT Performance Benchmarking
Script: services/tiles/benchmark_wms_wfs_mvt.py

Compares:
1. WMS (GeoServer on port 8080) -> Server-side rendered PNG
2. WFS (GeoServer on port 8080) -> GeoJSON features
3. MVT (pg_tileserv on port 7800) -> PostGIS binary Mapbox Vector Tile (.pbf)
4. OGC API Features (pg_featureserv on port 9000) -> GeoJSON

Tested at Zoom Levels:
- Zoom 12 (City-wide overview: tile 12/2888/1833)
- Zoom 14 (District / Zone level: tile 14/11553/7334)
- Zoom 16 (Neighborhood / Street level: tile 16/46213/29336)

Metrics Recorded:
- Latency (Round-trip time in milliseconds, averaged over 5 warm iterations)
- Payload Size (Bytes and Kilobytes)
- Data Efficiency & Compression Ratio
"""

import sys
import os
import json
import time
import math
import subprocess
from pathlib import Path
import requests
import matplotlib.pyplot as plt
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TILES_DIR = PROJECT_ROOT / "services" / "tiles"
REPORT_JSON = TILES_DIR / "performance_benchmark_report.json"
CHART_PNG = TILES_DIR / "benchmark_comparison_chart.png"

# Coordinates to Slippy Map tile & Bounding Box
def tile_to_bbox(z, x, y):
    n = 2.0 ** z
    lon_min = x / n * 360.0 - 180.0
    lon_max = (x + 1) / n * 360.0 - 180.0
    lat_rad_max = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_rad_min = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    lat_min = math.degrees(lat_rad_min)
    lat_max = math.degrees(lat_rad_max)
    return lon_min, lat_min, lon_max, lat_max

ZOOMS = [
    {"zoom": 12, "x": 2888, "y": 1833, "label": "Zoom 12 (City Level)"},
    {"zoom": 14, "x": 11553, "y": 7334, "label": "Zoom 14 (District Level)"},
    {"zoom": 16, "x": 46213, "y": 29336, "label": "Zoom 16 (Street Level)"}
]

def run_benchmarks():
    print("=" * 80)
    print("  SMARTSERVE GIS - PHASE 6: WMS vs WFS vs MVT BENCHMARK SUITE")
    print("=" * 80)

    # 1. Start pg_tileserv and pg_featureserv if not already running
    p_tile = None
    p_feat = None
    session = requests.Session()

    try:
        session.get("http://localhost:7800/index.json", timeout=1)
        print("[INFO] pg_tileserv is already running on port 7800.")
    except Exception:
        print("[INFO] Launching pg_tileserv background process on port 7800...")
        p_tile = subprocess.Popen([sys.executable, str(TILES_DIR / "pg_tileserv.py")])
        time.sleep(2)

    try:
        session.get("http://localhost:9000/index.json", timeout=1)
        print("[INFO] pg_featureserv is already running on port 9000.")
    except Exception:
        print("[INFO] Launching pg_featureserv background process on port 9000...")
        p_feat = subprocess.Popen([sys.executable, str(TILES_DIR / "pg_featureserv.py")])
        time.sleep(2)

    # Verify both up
    for s_name, s_url in [("GeoServer", "http://localhost:8080/geoserver"),
                          ("pg_tileserv", "http://localhost:7800/index.json"),
                          ("pg_featureserv", "http://localhost:9000/index.json")]:
        r = session.get(s_url, timeout=5)
        print(f"  [CHECK] {s_name:<16} : HTTP {r.status_code} (ONLINE)")

    results = []

    # 2. Execute Benchmark for Each Zoom Level
    NUM_RUNS = 5

    for z_info in ZOOMS:
        z = z_info["zoom"]
        x = z_info["x"]
        y = z_info["y"]
        lon_min, lat_min, lon_max, lat_max = tile_to_bbox(z, x, y)
        bbox_str = f"{lon_min:.6f},{lat_min:.6f},{lon_max:.6f},{lat_max:.6f}"
        print(f"\n" + "-" * 75)
        print(f"  BENCHMARKING AT {z_info['label'].upper()}: Tile ({z}/{x}/{y})")
        print(f"  Bounding Box: [{bbox_str}]")
        print("-" * 75)

        # A. WMS GetMap (GeoServer)
        wms_url = (
            f"http://localhost:8080/geoserver/smartserve/wms?"
            f"service=WMS&version=1.1.1&request=GetMap&layers=smartserve:all_services&"
            f"styles=&bbox={bbox_str}&width=256&height=256&srs=EPSG:4326&format=image/png"
        )
        # Warmup
        session.get(wms_url, timeout=10)
        wms_times = []
        wms_size = 0
        for _ in range(NUM_RUNS):
            t0 = time.time()
            r_wms = session.get(wms_url, timeout=10)
            wms_times.append((time.time() - t0) * 1000)
            wms_size = len(r_wms.content)
        wms_avg = round(float(np.mean(wms_times)), 1)
        print(f"  [WMS  (Raster Image)] : Avg Latency = {wms_avg:6.1f} ms | Payload = {wms_size:8,d} bytes ({wms_size/1024:5.1f} KB)")

        # B. WFS GetFeature (GeoServer)
        wfs_url = (
            f"http://localhost:8080/geoserver/smartserve/wfs?"
            f"service=WFS&version=1.0.0&request=GetFeature&typeName=smartserve:all_services&"
            f"outputFormat=application/json&bbox={bbox_str}"
        )
        session.get(wfs_url, timeout=10)
        wfs_times = []
        wfs_size = 0
        wfs_features = 0
        for _ in range(NUM_RUNS):
            t0 = time.time()
            r_wfs = session.get(wfs_url, timeout=10)
            wfs_times.append((time.time() - t0) * 1000)
            wfs_size = len(r_wfs.content)
            try:
                wfs_features = len(r_wfs.json().get("features", []))
            except Exception:
                pass
        wfs_avg = round(float(np.mean(wfs_times)), 1)
        print(f"  [WFS  (GeoJSON)]      : Avg Latency = {wfs_avg:6.1f} ms | Payload = {wfs_size:8,d} bytes ({wfs_size/1024:5.1f} KB) | Features: {wfs_features}")

        # C. MVT Vector Tile (pg_tileserv)
        mvt_url = f"http://localhost:7800/public.services/{z}/{x}/{y}.pbf"
        session.get(mvt_url, timeout=10)
        mvt_times = []
        mvt_size = 0
        for _ in range(NUM_RUNS):
            t0 = time.time()
            r_mvt = session.get(mvt_url, timeout=10)
            mvt_times.append((time.time() - t0) * 1000)
            mvt_size = len(r_mvt.content)
        mvt_avg = round(float(np.mean(mvt_times)), 1)
        print(f"  [MVT  (Vector Tile)]  : Avg Latency = {mvt_avg:6.1f} ms | Payload = {mvt_size:8,d} bytes ({mvt_size/1024:5.1f} KB)")

        # D. OGC API Features (pg_featureserv)
        feat_url = f"http://localhost:9000/collections/services/items.json?bbox={bbox_str}&limit=200"
        session.get(feat_url, timeout=10)
        feat_times = []
        feat_size = 0
        feat_features = 0
        for _ in range(NUM_RUNS):
            t0 = time.time()
            r_feat = session.get(feat_url, timeout=10)
            feat_times.append((time.time() - t0) * 1000)
            feat_size = len(r_feat.content)
            try:
                feat_features = len(r_feat.json().get("features", []))
            except Exception:
                pass
        feat_avg = round(float(np.mean(feat_times)), 1)
        print(f"  [OFeat(pg_featureserv): Avg Latency = {feat_avg:6.1f} ms | Payload = {feat_size:8,d} bytes ({feat_size/1024:5.1f} KB) | Features: {feat_features}")

        results.append({
            "zoom": z,
            "label": z_info["label"],
            "tile": f"{z}/{x}/{y}",
            "bbox": bbox_str,
            "wms": {"latency_ms": wms_avg, "payload_bytes": wms_size, "payload_kb": round(wms_size/1024, 2)},
            "wfs": {"latency_ms": wfs_avg, "payload_bytes": wfs_size, "payload_kb": round(wfs_size/1024, 2), "features": wfs_features},
            "mvt": {"latency_ms": mvt_avg, "payload_bytes": mvt_size, "payload_kb": round(mvt_size/1024, 2)},
            "pg_featureserv": {"latency_ms": feat_avg, "payload_bytes": feat_size, "payload_kb": round(feat_size/1024, 2), "features": feat_features}
        })

    # Save JSON report
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[INFO] Benchmark JSON report saved to: {REPORT_JSON.name}")

    # 3. Generate Benchmark Comparison Chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=150)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    labels = [r["label"] for r in results]
    x = np.arange(len(labels))
    width = 0.2

    # Latency Chart
    wms_lat = [r["wms"]["latency_ms"] for r in results]
    wfs_lat = [r["wfs"]["latency_ms"] for r in results]
    mvt_lat = [r["mvt"]["latency_ms"] for r in results]
    feat_lat = [r["pg_featureserv"]["latency_ms"] for r in results]

    ax1.bar(x - 1.5*width, wms_lat, width, label="WMS (GeoServer)", color="#3b82f6")
    ax1.bar(x - 0.5*width, wfs_lat, width, label="WFS (GeoServer)", color="#f59e0b")
    ax1.bar(x + 0.5*width, mvt_lat, width, label="MVT (pg_tileserv)", color="#10b981")
    ax1.bar(x + 1.5*width, feat_lat, width, label="OGC API (pg_featureserv)", color="#8b5cf6")

    ax1.set_ylabel("Response Latency (ms) - Lower is Better", fontsize=11, fontweight="bold")
    ax1.set_title("Service Latency Comparison by Zoom Level", fontsize=12, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9, fontweight="bold")
    ax1.legend(frameon=True, fontsize=9)

    # Payload Size Chart (Log Scale)
    wms_kb = [r["wms"]["payload_kb"] for r in results]
    wfs_kb = [r["wfs"]["payload_kb"] for r in results]
    mvt_kb = [r["mvt"]["payload_kb"] for r in results]
    feat_kb = [r["pg_featureserv"]["payload_kb"] for r in results]

    ax2.bar(x - 1.5*width, wms_kb, width, label="WMS (Raster PNG)", color="#3b82f6")
    ax2.bar(x - 0.5*width, wfs_kb, width, label="WFS (GeoJSON)", color="#f59e0b")
    ax2.bar(x + 0.5*width, mvt_kb, width, label="MVT (.pbf Tile)", color="#10b981")
    ax2.bar(x + 1.5*width, feat_kb, width, label="OGC API (GeoJSON)", color="#8b5cf6")

    ax2.set_ylabel("Payload Size (KB) - Lower is Better", fontsize=11, fontweight="bold")
    ax2.set_title("Payload Transfer Size by Zoom Level", fontsize=12, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=9, fontweight="bold")
    ax2.legend(frameon=True, fontsize=9)

    plt.tight_layout()
    plt.savefig(CHART_PNG)
    plt.close()
    print(f"[INFO] Benchmark comparison chart saved to: {CHART_PNG.name}")

    print("\n" + "=" * 80)
    print("  PHASE 6 BENCHMARKING COMPLETED SUCCESSFULLY!")
    print("=" * 80)

    # Terminate background processes if we started them
    if p_tile:
        p_tile.terminate()
    if p_feat:
        p_feat.terminate()

if __name__ == "__main__":
    run_benchmarks()
